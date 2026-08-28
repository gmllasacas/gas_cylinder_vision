import time
from typing import Optional, List, Dict, Any, Callable
from app.core import logger, i18n as global_i18n, I18nManager
from app.db import db_repo, DailyCountRepository

class AnomalyDetector:
    """
    Evaluates real-time stream crossing patterns and generates alerts when
    OUT events do not match the expected IN events within a sliding time window.
    
    Rules:
    - If N tanks enter (IN), exactly N tanks are expected to exit (OUT) within window_seconds (default 60s).
    - While tanks are inside and 0 have exited (out_count == 0), wait up to window_seconds for processing.
    - If OUT count exceeds IN count (e.g. 3 OUT vs 2 IN), trigger immediate OVER_EXIT alert and reset batch window.
    - If tanks start exiting but stop before matching (e.g. 1 OUT vs 2 IN), trigger UNDER_EXIT alert after batch_idle_seconds and reset batch window.
    - If window_seconds elapses with 0 exits when IN > 0, trigger UNDER_EXIT alert and reset batch window.
    - If OUT == IN (e.g. 2 IN -> 2 OUT), batch is balanced and resets cleanly after batch_idle_seconds without alerts.
    """

    def __init__(
        self,
        enabled: bool = True,
        window_seconds: float = 60.0,
        batch_idle_seconds: float = 15.0,
        db: Optional[DailyCountRepository] = None,
        i18n: Optional[I18nManager] = None,
        on_alert: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.enabled = enabled
        self.window_seconds = float(window_seconds)
        self.batch_idle_seconds = float(batch_idle_seconds)
        self.db = db or db_repo
        self.i18n = i18n or global_i18n
        self.on_alert = on_alert

        self.active_batch_in: List[Dict[str, Any]] = []
        self.active_batch_out: List[Dict[str, Any]] = []
        self.first_in_time: float = 0.0
        self.last_in_time: float = 0.0
        self.last_out_time: float = 0.0
        self.latest_alert: Optional[Dict[str, Any]] = None
        self.unread_alerts_count: int = 0

    def set_config(self, enabled: bool, window_seconds: float, batch_idle_seconds: float):
        self.enabled = enabled
        self.window_seconds = float(window_seconds)
        self.batch_idle_seconds = float(batch_idle_seconds)

    def _reset_batch(self):
        """Clears the active in-memory batch state for a clean new cycle."""
        self.active_batch_in.clear()
        self.active_batch_out.clear()
        self.first_in_time = 0.0
        self.last_in_time = 0.0
        self.last_out_time = 0.0

    def record_event(
        self,
        direction: str,
        track_id: int,
        timestamp: Optional[float] = None,
        source_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None

        now = timestamp if timestamp is not None else time.time()
        direction = direction.upper()

        if direction == "IN":
            # If previous batch had exits and now a new IN comes after idle threshold
            if self.active_batch_out and (now - self.last_out_time) >= self.batch_idle_seconds:
                self._check_batch_completion(now, source_id)
                self._reset_batch()

            if not self.active_batch_in:
                self.first_in_time = now

            self.active_batch_in.append({"track_id": track_id, "time": now})
            self.last_in_time = now
            return None

        elif direction == "OUT":
            self.active_batch_out.append({"track_id": track_id, "time": now})
            self.last_out_time = now

            in_count = len(self.active_batch_in)
            out_count = len(self.active_batch_out)

            # Check: Immediate over-exit anomaly (More OUT than IN)
            if out_count > in_count:
                discrepancy = out_count - in_count
                tmpl = self.i18n.t(
                    "alerts.over_exit",
                    "Inconsistency Detected: {out_count} tanks went OUT, but only {in_count} came IN within {window}s (Discrepancy: +{discrepancy})."
                )
                msg = tmpl.format(
                    out_count=out_count,
                    in_count=in_count,
                    window=int(self.window_seconds),
                    discrepancy=discrepancy
                )
                alert = self._emit_alert(
                    in_count=in_count,
                    out_count=out_count,
                    message=msg,
                    severity="ERROR",
                    source_id=source_id
                )
                # Reset window immediately upon registering alert to prevent cascading duplicates
                self._reset_batch()
                return alert

            # Check: Balanced batch reached (e.g. 2 IN and 2 OUT)
            if in_count > 0 and out_count == in_count:
                logger.info(f"Batch currently balanced: {in_count} IN -> {out_count} OUT.")

        return None

    def check_idle_timeout(
        self,
        current_time: Optional[float] = None,
        source_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None

        now = current_time if current_time is not None else time.time()
        in_count = len(self.active_batch_in)
        out_count = len(self.active_batch_out)

        if in_count == 0:
            return None

        # Case 1: Batch was perfectly balanced (e.g. 2 IN and 2 OUT) and has sat idle
        if in_count > 0 and out_count == in_count:
            if (now - self.last_out_time) >= self.batch_idle_seconds:
                logger.info(f"Batch completed cleanly after idle: {in_count} IN -> {out_count} OUT.")
                self._reset_batch()
            return None

        # Case 2: Tanks started exiting but stopped before all exited (0 < out_count < in_count)
        if 0 < out_count < in_count:
            idle_since_out = now - self.last_out_time
            total_duration = now - self.first_in_time
            if idle_since_out >= self.batch_idle_seconds or total_duration >= self.window_seconds:
                missing = in_count - out_count
                tmpl = self.i18n.t(
                    "alerts.under_exit_idle",
                    "Inconsistency Detected: {in_count} tanks came IN, but only {out_count} went OUT after {idle}s idle (Missing: {missing})."
                )
                msg = tmpl.format(
                    in_count=in_count,
                    out_count=out_count,
                    idle=int(idle_since_out),
                    missing=missing
                )
                alert = self._emit_alert(
                    in_count=in_count,
                    out_count=out_count,
                    message=msg,
                    severity="WARNING",
                    source_id=source_id
                )
                self._reset_batch()
                return alert

        # Case 3: 0 tanks have exited yet (out_count == 0)
        # Tanks may still be being processed. Only trigger if the entire window_seconds (60s) expires!
        if out_count == 0 and in_count > 0:
            time_since_first_in = now - self.first_in_time
            if time_since_first_in >= self.window_seconds:
                tmpl = self.i18n.t(
                    "alerts.under_exit_window",
                    "Inconsistency Detected: {in_count} tanks came IN, but 0 went OUT after {window}s window (Missing: {missing})."
                )
                msg = tmpl.format(
                    in_count=in_count,
                    window=int(time_since_first_in),
                    missing=in_count
                )
                alert = self._emit_alert(
                    in_count=in_count,
                    out_count=0,
                    message=msg,
                    severity="WARNING",
                    source_id=source_id
                )
                self._reset_batch()
                return alert

        return None

    def _check_batch_completion(self, now: float, source_id: Optional[str]) -> Optional[Dict[str, Any]]:
        in_count = len(self.active_batch_in)
        out_count = len(self.active_batch_out)
        if in_count > 0 and out_count != in_count:
            discrepancy = out_count - in_count
            sign = "+" if discrepancy > 0 else ""
            tmpl = self.i18n.t(
                "alerts.batch_closed",
                "Inconsistency Detected: Batch closed with {in_count} IN vs {out_count} OUT (Discrepancy: {sign}{discrepancy})."
            )
            msg = tmpl.format(
                in_count=in_count,
                out_count=out_count,
                sign=sign,
                discrepancy=discrepancy
            )
            alert = self._emit_alert(
                in_count=in_count,
                out_count=out_count,
                message=msg,
                severity="WARNING" if out_count < in_count else "ERROR",
                source_id=source_id
            )
            self._reset_batch()
            return alert
        return None

    def _emit_alert(
        self,
        in_count: int,
        out_count: int,
        message: str,
        severity: str = "WARNING",
        source_id: Optional[str] = None
    ) -> Dict[str, Any]:
        alert_data = self.db.record_inconsistency(
            in_count=in_count,
            out_count=out_count,
            message=message,
            severity=severity,
            source_id=source_id
        )
        self.latest_alert = alert_data
        self.unread_alerts_count += 1

        if self.on_alert:
            try:
                self.on_alert(alert_data)
            except Exception as e:
                logger.error(f"Error in anomaly on_alert callback: {e}")

        return alert_data

    def clear_alerts(self):
        self.latest_alert = None
        self.unread_alerts_count = 0
        self._reset_batch()

    def reset(self):
        self.clear_alerts()
