let isUserDragging = false;
let isConfDragging = false;
let currentLang = 'es';
let currentLocaleData = null;
let lastSeenAlertId = -1;
let audioCtx = null;
let alertsMap = {};
let historyTotal = 0;
let alertsTotal = 0;

let notificationAudio = null;

function initNotificationAudio() {
    if (!notificationAudio) {
        try {
            notificationAudio = new Audio('/static/audio/alert.wav');
            notificationAudio.volume = 1.0;
            notificationAudio.preload = 'auto';
        } catch (e) {
            console.warn("Could not create Audio element:", e);
        }
    }
}

function initAudioContext() {
    if (!audioCtx) {
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        if (AudioContextClass) {
            audioCtx = new AudioContextClass();
        }
    }
    if (audioCtx && audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
    return audioCtx;
}

// Ensure Web Audio and HTML5 audio are unlocked on first user interaction anywhere
['click', 'keydown', 'touchstart', 'mousedown'].forEach(evt => {
    document.addEventListener(evt, () => {
        initAudioContext();
        initNotificationAudio();
    }, { passive: true });
});

function playWebAudioChime() {
    try {
        const ctx = initAudioContext();
        if (!ctx) return;

        const now = ctx.currentTime;
        const masterGain = ctx.createGain();
        masterGain.gain.setValueAtTime(0.95, now);
        masterGain.connect(ctx.destination);

        const strikes = [
            { freq: 1046.50, time: 0.00, dur: 0.45, gain: 0.70 }, // C6
            { freq: 1318.51, time: 0.16, dur: 0.50, gain: 0.80 }, // E6
            { freq: 2093.00, time: 0.32, dur: 0.90, gain: 1.00 }  // High C7 (crystal peak)
        ];

        strikes.forEach(({ freq, time, dur, gain }) => {
            const osc = ctx.createOscillator();
            const gNode = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(freq, now + time);
            gNode.gain.setValueAtTime(0.0, now + time);
            gNode.gain.setValueAtTime(gain * 0.75, now + time + 0.003);
            gNode.gain.exponentialRampToValueAtTime(0.001, now + time + dur);
            osc.connect(gNode);
            gNode.connect(masterGain);
            osc.start(now + time);
            osc.stop(now + time + dur);

            // Resonant octave harmonic
            const oscHarm = ctx.createOscillator();
            const gHarm = ctx.createGain();
            oscHarm.type = 'sine';
            oscHarm.frequency.setValueAtTime(freq * 2.0, now + time);
            gHarm.gain.setValueAtTime(0.0, now + time);
            gHarm.gain.setValueAtTime(gain * 0.25, now + time + 0.003);
            gHarm.gain.exponentialRampToValueAtTime(0.001, now + time + (dur * 0.6));
            oscHarm.connect(gHarm);
            gHarm.connect(masterGain);
            oscHarm.start(now + time);
            oscHarm.stop(now + time + (dur * 0.6));
        });
    } catch (e) {
        console.warn("Web Audio fallback error:", e);
    }
}

function playNotificationSound() {
    try {
        initNotificationAudio();
        if (notificationAudio) {
            notificationAudio.currentTime = 0;
            const playPromise = notificationAudio.play();
            if (playPromise !== undefined) {
                playPromise.catch(e => {
                    playWebAudioChime();
                });
            }
        } else {
            playWebAudioChime();
        }
    } catch (e) {
        playWebAudioChime();
    }
}

function formatTime12h(isoString) {
    if (!isoString) return '-';
    try {
        let timePart = '';
        if (isoString.includes('T')) {
            timePart = isoString.split('T')[1].substring(0, 8);
        } else if (isoString.includes(' ')) {
            timePart = isoString.split(' ')[1].substring(0, 8);
        } else {
            timePart = isoString.substring(0, 8);
        }
        const parts = timePart.split(':');
        if (parts.length >= 2) {
            let h = parseInt(parts[0], 10);
            const m = parts[1] || '00';
            const s = parts[2] ? parts[2].substring(0, 2) : '00';
            const ampm = h >= 12 ? 'PM' : 'AM';
            h = h % 12 || 12;
            const hh = String(h).padStart(2, '0');
            return `${hh}:${m}:${s} ${ampm}`;
        }
        return isoString;
    } catch (e) {
        return isoString;
    }
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

async function loadLocale(lang) {
    try {
        const res = await fetch(`/locales/${lang}.json?v=2.9`);
        if (res.ok) {
            currentLocaleData = await res.json();
            currentLang = lang;
            applyLocalization();
        }
    } catch (e) {
        console.error("Error loading locale:", e);
    }
}

function applyLocalization() {
    if (!currentLocaleData) return;
    const ui = currentLocaleData.ui;
    const setText = (id, text) => {
        const el = document.getElementById(id);
        if (el && text) el.innerText = text;
    };
    const setHtml = (id, html) => {
        const el = document.getElementById(id);
        if (el && html) el.innerHTML = html;
    };

    if (ui.page_title) {
        document.title = ui.page_title;
    }

    setText('i18n_title', ui.title);
    setHtml('i18n_subtitle', ui.subtitle);
    setText('i18n_kpi_in', ui.kpi_in);
    setText('i18n_kpi_badge_in', ui.kpi_badge_in || "↓ IN");
    setText('i18n_kpi_in_sub', ui.kpi_in_sub);
    setText('i18n_kpi_out', ui.kpi_out);
    setText('i18n_kpi_badge_out', ui.kpi_badge_out || "↑ OUT");
    setText('i18n_kpi_out_sub', ui.kpi_out_sub);
    setText('i18n_kpi_net', ui.kpi_net);
    setText('i18n_kpi_badge_net', ui.kpi_badge_net || "± NET");
    setText('i18n_kpi_net_sub', ui.kpi_net_sub);
    setText('i18n_kpi_alerts', ui.kpi_alerts || "Inconsistencies");
    setText('i18n_kpi_badge_alerts', ui.kpi_badge_alerts || "⚠️ ALERTS");
    setText('i18n_kpi_alerts_sub', ui.kpi_alerts_sub || "Flagged Today");

    setText('i18n_telemetry_title', ui.telemetry_title || "AI & System Telemetry");
    setText('i18n_telemetry_online', ui.telemetry_online || "ONLINE");
    setText('i18n_telemetry_fps', ui.telemetry_fps || "Processing FPS");
    setText('i18n_telemetry_latency', ui.telemetry_latency || "AI Latency");
    setText('i18n_telemetry_model', ui.telemetry_model || "Active Model");
    setText('i18n_telemetry_tracks', ui.telemetry_tracks || "Objects in View");

    setText('i18n_conf', ui.conf);
    setText('i18n_speed', ui.speed);
    setText('btnRestart', ui.btn_restart);
    setText('btnRewind', ui.btn_rewind);
    setText('btnStepBack', ui.btn_step_back);
    setText('btnStepFwd', ui.btn_step_fwd);
    setText('btnForward', ui.btn_forward);
    setText('btnReset', ui.btn_reset);

    setText('i18n_nerd_title', ui.nerd_title);
    setText('i18n_nerd_video', ui.nerd_video);
    setText('i18n_nerd_viewport', ui.nerd_viewport);
    setText('i18n_nerd_res', ui.nerd_res);
    setText('i18n_nerd_fps', ui.nerd_fps);
    setText('i18n_nerd_model', ui.nerd_model);
    setText('i18n_nerd_device', ui.nerd_device);
    setText('i18n_nerd_latency', ui.nerd_latency);
    setText('i18n_nerd_tracks', ui.nerd_tracks);
    setText('i18n_nerd_counts', ui.nerd_counts);

    setText('i18n_history_title', ui.daily_history_title || "Daily Count History");
    setText('th_date', ui.col_date || "Date");
    setText('th_in', ui.col_in || "IN (Inbound)");
    setText('th_out', ui.col_out || "OUT (Outbound)");
    setText('th_net', ui.col_net || "Net Total");
    setText('th_updated', ui.col_updated || "Last Updated");

    setText('i18n_alerts_title', ui.alerts_title || "Inconsistency & Anomaly Alerts");
    setText('th_alert_time', ui.th_alert_time || "Time");
    setText('th_alert_in', ui.th_alert_in || "IN");
    setText('th_alert_out', ui.th_alert_out || "OUT");
    setText('th_alert_disc', ui.th_alert_disc || "Diff");
    setText('th_alert_action', ui.th_alert_action || "Action");

    // Modal Localization
    setText('modalAlertTitle', ui.modal_alert_title || "Inconsistency Details");
    setText('modalLabelIn', ui.modal_in || "IN");
    setText('modalLabelOut', ui.modal_out || "OUT");
    setText('modalLabelDiff', ui.modal_diff || "Diff");
    setText('modalLabelMessage', ui.modal_message || "Description");
    setText('btnModalClose', ui.modal_close || "Close");

    // Dynamic Table Badges Localization (N records / N registros)
    const histBadge = document.getElementById('historyCountBadge');
    if (histBadge) {
        const label = historyTotal === 1 ? (ui.record || 'record') : (ui.records || 'records');
        histBadge.innerText = `${historyTotal} ${label}`;
    }
    const alertBadge = document.getElementById('alertsCountBadge');
    if (alertBadge) {
        const label = alertsTotal === 1 ? (ui.record || 'record') : (ui.records || 'records');
        alertBadge.innerText = `${alertsTotal} ${label}`;
    }

    setHtml('i18n_shortcuts', ui.shortcuts);
}

async function toggleStatsAndDebug() {
    try {
        const res = await fetch('/api/settings/debug', { method: 'POST' });
        if (res.ok) {
            fetchStatus();
        }
    } catch (e) {
        console.error("Error toggling stats and debug mode:", e);
    }
}

async function controlTogglePlay() {
    try {
        await fetch('/api/playback/toggle', { method: 'POST' });
        fetchStatus();
    } catch (e) {
        console.error("Error toggling play state:", e);
    }
}

async function controlRestart() {
    try {
        await fetch('/api/playback/restart', { method: 'POST' });
        fetchStatus();
    } catch (e) {
        console.error("Error restarting video:", e);
    }
}

async function controlSeekOffset(seconds) {
    try {
        await fetch(`/api/playback/seek_offset?seconds=${encodeURIComponent(seconds)}`, { method: 'POST' });
        fetchStatus();
    } catch (e) {
        console.error("Error seeking video offset:", e);
    }
}

async function controlStep(deltaFrames) {
    try {
        await fetch(`/api/playback/step?delta_frames=${encodeURIComponent(deltaFrames)}`, { method: 'POST' });
        fetchStatus();
    } catch (e) {
        console.error("Error stepping frames:", e);
    }
}

async function onSpeedSelectChange(speedVal) {
    try {
        await fetch(`/api/settings/speed?value=${encodeURIComponent(speedVal)}`, { method: 'POST' });
        fetchStatus();
    } catch (e) {
        console.error("Error setting playback speed:", e);
    }
}

async function fetchStatus() {
    try {
        const res = await fetch('/api/status');
        if (!res.ok) return;
        const data = await res.json();
        const ui = currentLocaleData ? currentLocaleData.ui : null;

        // Ensure active locale matches server config
        if (data.lang && data.lang !== currentLang) {
            await loadLocale(data.lang);
        }

        // Update KPI Counters
        const inEl = document.getElementById('inCount');
        const outEl = document.getElementById('outCount');
        const netEl = document.getElementById('netCount');
        if (inEl && data.in_count !== undefined) inEl.innerText = data.in_count;
        if (outEl && data.out_count !== undefined) outEl.innerText = data.out_count;
        if (netEl && data.net_count !== undefined) netEl.innerText = (data.net_count > 0 ? `+${data.net_count}` : data.net_count);

        // Update Bento Alerts KPI & Badge
        const alertsKpiCount = document.getElementById('alertsKpiCount');
        const alertsBadge = document.getElementById('alertsBadge');
        const alertsBadgeText = document.getElementById('alertsBadgeText');
        const activeAlerts = data.active_alerts_count !== undefined ? data.active_alerts_count : 0;
        
        if (alertsKpiCount) alertsKpiCount.innerText = activeAlerts;

        if (activeAlerts > 0) {
            if (alertsBadge) {
                alertsBadge.classList.remove('hidden');
                alertsBadge.classList.add('flex');
            }
            if (alertsBadgeText) {
                const label = activeAlerts === 1 ? (ui && ui.alert_singular ? ui.alert_singular : 'inconsistency') : (ui && ui.alert_plural ? ui.alert_plural : 'inconsistencies');
                alertsBadgeText.innerText = `⚠️ ${activeAlerts} ${label}`;
            }
        } else {
            if (alertsBadge) {
                alertsBadge.classList.add('hidden');
                alertsBadge.classList.remove('flex');
            }
        }

        // Update Live Telemetry Bento Widget
        const telFps = document.getElementById('telemetryFps');
        const telLat = document.getElementById('telemetryLatency');
        const telMod = document.getElementById('telemetryModel');
        const telTrk = document.getElementById('telemetryTracks');

        if (telFps && typeof data.actual_stream_fps === 'number') {
            telFps.innerText = data.actual_stream_fps.toFixed(1);
        }
        if (telLat && data.ai_latency_ms !== undefined) {
            telLat.innerText = `${data.ai_latency_ms} ms`;
        }
        if (telMod && data.active_model) {
            telMod.innerText = data.active_model;
        }
        if (telTrk && data.active_tracks !== undefined) {
            telTrk.innerText = data.active_tracks;
        }

        // Toast on new alert (only for new events occurring in real-time)
        if (data.latest_alert && data.latest_alert.id) {
            if (lastSeenAlertId === -1) {
                // Initial page load: sync baseline without showing popup toast or chime
                lastSeenAlertId = data.latest_alert.id;
            } else if (data.latest_alert.id > lastSeenAlertId) {
                // Real-time new anomaly event
                lastSeenAlertId = data.latest_alert.id;
                showToastAlert(data.latest_alert);
                fetchAlerts();
            }
        } else if (lastSeenAlertId === -1) {
            lastSeenAlertId = 0;
        }

        // Toggle Stats for Nerds button style
        const statsBtn = document.getElementById('statsToggleBtn');
        const statsPanel = document.getElementById('statsForNerds');

        if (statsBtn) {
            const onLabel = ui ? ui.stats_on : "📊 Stats for Nerds: ON";
            const offLabel = ui ? ui.stats_off : "📊 Stats for Nerds: OFF";

            if (data.debug_mode) {
                statsBtn.innerText = onLabel;
                statsBtn.className = "bg-sky-700 hover:bg-sky-600 text-white border border-sky-500/40 px-4 py-2 rounded-md font-bold inline-flex items-center gap-2 transition-all cursor-pointer shadow-sm";
            } else {
                statsBtn.innerText = offLabel;
                statsBtn.className = "bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 px-4 py-2 rounded-md font-semibold inline-flex items-center gap-2 transition-all cursor-pointer";
            }
        }

        if (statsPanel) {
            if (data.debug_mode) {
                statsPanel.classList.remove('hidden');

                // Update YouTube-style "Stats for Nerds" HUD fields
                const feedImg = document.getElementById('videoFeed');
                const vWidth = feedImg ? feedImg.clientWidth : 0;
                const vHeight = feedImg ? feedImg.clientHeight : 0;

                const nVideo = document.getElementById('nerdVideoName');
                const nViewport = document.getElementById('nerdViewport');
                const nRes = document.getElementById('nerdResolution');
                const nStreamFps = document.getElementById('nerdStreamFps');
                const nMaxFps = document.getElementById('nerdMaxFps');
                const nModel = document.getElementById('nerdModel');
                const nDevice = document.getElementById('nerdDevice');
                const nLatency = document.getElementById('nerdLatency');
                const nTracks = document.getElementById('nerdTracks');
                const nIn = document.getElementById('nerdIn');
                const nOut = document.getElementById('nerdOut');

                const sourceLabel = data.is_live ? `🔴 ${data.current_video} (RTSP)` : data.current_video;
                if (nVideo) nVideo.innerText = sourceLabel || 'stream.mp4';
                if (nViewport) nViewport.innerText = `${vWidth}x${vHeight}*1.00 (Max: ${data.output_width || 1024}w)`;
                if (nRes) nRes.innerText = `${data.video_native_fps} FPS base / ${data.imgsz || 640} imgsz`;
                if (nStreamFps && typeof data.actual_stream_fps === 'number') nStreamFps.innerText = data.actual_stream_fps.toFixed(1);
                if (nMaxFps && typeof data.max_hardware_fps === 'number') nMaxFps.innerText = data.max_hardware_fps.toFixed(0);
                if (nModel) nModel.innerText = `${data.active_model} (conf: ${data.conf})`;
                if (nDevice) nDevice.innerText = data.device || 'Auto';
                if (nLatency) nLatency.innerText = `AI: ${data.ai_latency_ms || 0}ms | Enc: ${data.encode_latency_ms || 0}ms`;
                if (nTracks) nTracks.innerText = `${data.active_tracks || 0} objects`;
                if (nIn) nIn.innerText = `${data.in_count} IN`;
                if (nOut) nOut.innerText = `${data.out_count} OUT (Net: ${data.net_count >= 0 ? '+' : ''}${data.net_count})`;
            } else {
                statsPanel.classList.add('hidden');
            }
        }

        // Update Confidence slider & display
        if (!isConfDragging) {
            const confSlider = document.getElementById('confSlider');
            const confDisplay = document.getElementById('confDisplay');
            if (confSlider && typeof data.conf === 'number') {
                confSlider.value = data.conf;
            }
            if (confDisplay && typeof data.conf === 'number') {
                confDisplay.innerText = data.conf.toFixed(2);
            }
        }

        // Update Timeline controls based on Live Camera vs File Stream
        const currEl = document.getElementById('timeCurrent');
        const durEl = document.getElementById('timeDuration');
        const slider = document.getElementById('timelineSlider');
        const btnRewind = document.getElementById('btnRewind');
        const btnStepBack = document.getElementById('btnStepBack');
        const btnStepFwd = document.getElementById('btnStepFwd');
        const btnForward = document.getElementById('btnForward');
        const btnRestart = document.getElementById('btnRestart');

        if (data.is_live) {
            if (data.camera_connected) {
                if (currEl) currEl.innerHTML = '<span class="text-rose-500 font-bold flex items-center gap-1">🔴 LIVE</span>';
            } else {
                if (currEl) currEl.innerHTML = '<span class="text-amber-400 font-bold flex items-center gap-1">⚠️ CONNECTING</span>';
            }

            if (durEl) durEl.innerText = '--:--';
            if (slider) {
                slider.disabled = true;
                slider.value = 100;
                slider.className = "w-full opacity-40 cursor-not-allowed";
            }
            if (btnRewind) btnRewind.classList.add('hidden');
            if (btnStepBack) btnStepBack.classList.add('hidden');
            if (btnStepFwd) btnStepFwd.classList.add('hidden');
            if (btnForward) btnForward.classList.add('hidden');
            if (btnRestart) btnRestart.classList.add('hidden');
        } else {
            if (currEl) currEl.innerText = formatTime(data.current_time || 0);
            if (durEl) durEl.innerText = formatTime(data.duration || 0);

            if (slider) {
                slider.disabled = false;
                slider.className = "w-full cursor-pointer";
                slider.max = data.total_frames || 100;
                if (!isUserDragging) {
                    slider.value = data.current_frame || 0;
                }
            }
            if (btnRewind) btnRewind.classList.remove('hidden');
            if (btnStepBack) btnStepBack.classList.remove('hidden');
            if (btnStepFwd) btnStepFwd.classList.remove('hidden');
            if (btnForward) btnForward.classList.remove('hidden');
            if (btnRestart) btnRestart.classList.remove('hidden');
        }

        // Camera Reconnecting Error Banner
        const camBanner = document.getElementById('cameraErrorBanner');
        const camMsg = document.getElementById('cameraErrorMsg');
        if (camBanner) {
            if (data.is_live && !data.camera_connected) {
                camBanner.classList.remove('hidden');
                if (camMsg) camMsg.innerText = data.connection_error_msg || "Camera Unreachable (Reconnecting...)";
            } else if (data.is_file_missing) {
                camBanner.classList.remove('hidden');
                if (camMsg) camMsg.innerText = "Video file not found in videos/ (Waiting...)";
            } else {
                camBanner.classList.add('hidden');
            }
        }

        // Status Badge
        const statusBadge = document.getElementById('statusBadge');
        if (statusBadge) {
            if (data.is_file_missing) {
                statusBadge.innerText = (ui && ui.status_file_missing) ? ui.status_file_missing : (ui && ui.video_missing ? ui.video_missing : "FILE MISSING");
                statusBadge.className = "bg-rose-500 text-white px-4 py-1.5 rounded-md text-xs font-bold uppercase tracking-wider whitespace-nowrap shadow-sm";
            } else if (data.is_live) {
                if (data.camera_connected) {
                    statusBadge.innerText = (ui && ui.status_live) ? ui.status_live : (ui && ui.playing ? ui.playing : "LIVE STREAM");
                    statusBadge.className = "bg-emerald-500 text-slate-950 px-4 py-1.5 rounded-md text-xs font-extrabold uppercase tracking-wider whitespace-nowrap shadow-sm";
                } else {
                    statusBadge.innerText = (ui && ui.status_connecting) ? ui.status_connecting : (ui && ui.cam_connecting ? ui.cam_connecting : "CONNECTING...");
                    statusBadge.className = "bg-amber-500 text-slate-950 px-4 py-1.5 rounded-md text-xs font-extrabold uppercase tracking-wider whitespace-nowrap shadow-sm animate-pulse";
                }
            } else {
                if (data.is_paused) {
                    const label = (ui && (ui.status_paused || ui.paused)) ? (ui.status_paused || ui.paused) : "PAUSED";
                    statusBadge.innerText = label;
                    statusBadge.className = "bg-amber-500 text-slate-950 px-4 py-1.5 rounded-md text-xs font-extrabold uppercase tracking-wider whitespace-nowrap shadow-sm";
                } else {
                    const label = (ui && (ui.status_playing || ui.playing)) ? (ui.status_playing || ui.playing) : "PLAYING";
                    statusBadge.innerText = label;
                    statusBadge.className = "bg-emerald-500 text-slate-950 px-4 py-1.5 rounded-md text-xs font-extrabold uppercase tracking-wider whitespace-nowrap shadow-sm";
                }
            }
        }

        // Play/Pause Button Label
        const playBtn = document.getElementById('playBtn');
        if (playBtn) {
            if (data.is_paused) {
                playBtn.innerText = ui ? ui.btn_play : "▶ Play";
                playBtn.className = "bg-emerald-600 hover:bg-emerald-500 text-white border border-emerald-400/30 px-5 py-2 rounded-md text-xs font-bold inline-flex items-center gap-1.5 transition-all active:translate-y-0.5 cursor-pointer shadow-lg shadow-emerald-600/25";
            } else {
                playBtn.innerText = ui ? ui.btn_pause : "⏸ Pause";
                playBtn.className = "bg-sky-600 hover:bg-sky-500 text-white border border-sky-400/30 px-5 py-2 rounded-md text-xs font-bold inline-flex items-center gap-1.5 transition-all active:translate-y-0.5 cursor-pointer shadow-lg shadow-sky-600/25";
            }
        }

    } catch (e) {
        console.error("Error fetching stream status:", e);
    }
}

function onConfSliderInput(val) {
    isConfDragging = true;
    const disp = document.getElementById('confDisplay');
    if (disp) disp.innerText = parseFloat(val).toFixed(2);
}

async function onConfSliderChange(val) {
    try {
        await fetch(`/api/settings/confidence?value=${encodeURIComponent(val)}`, { method: 'POST' });
        isConfDragging = false;
        fetchStatus();
    } catch (e) {
        console.error("Error setting confidence:", e);
        isConfDragging = false;
    }
}

async function fetchDailyHistory() {
    try {
        const res = await fetch('/api/counts/history?limit=7');
        if (!res.ok) return;
        const data = await res.json();
        const tbody = document.getElementById('historyTableBody');
        const countBadge = document.getElementById('historyCountBadge');
        const ui = currentLocaleData ? currentLocaleData.ui : null;
        
        if (!tbody) return;

        if (countBadge && data.total !== undefined) {
            historyTotal = data.total;
            const label = data.total === 1 ? (ui && ui.record ? ui.record : 'record') : (ui && ui.records ? ui.records : 'records');
            countBadge.innerText = `${data.total} ${label}`;
        }
        
        if (!data.history || data.history.length === 0) {
            const noRecText = ui ? ui.no_records : "No daily records saved yet";
            tbody.innerHTML = `<tr><td colspan="5" class="py-10 text-center text-slate-500 font-sans">${noRecText}</td></tr>`;
            return;
        }
        
        tbody.innerHTML = data.history.map(row => {
            const updatedTime = row.updated_at ? row.updated_at.replace('T', ' ').substring(0, 19) : '-';
            const netSign = row.net_count > 0 ? '+' : '';
            const netColor = row.net_count >= 0 ? 'text-sky-400' : 'text-rose-400';
            
            return `
                <tr class="hover:bg-slate-800/60 transition-colors">
                    <td class="py-4 px-5 font-bold text-slate-200">${row.date}</td>
                    <td class="py-4 px-5 text-emerald-400 font-bold">${row.in_count}</td>
                    <td class="py-4 px-5 text-amber-400 font-bold">${row.out_count}</td>
                    <td class="py-4 px-5 ${netColor} font-black">${netSign}${row.net_count}</td>
                    <td class="py-4 px-5 text-slate-400 text-xs">${updatedTime}</td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        console.error("Error fetching daily history:", e);
    }
}

async function fetchAlerts() {
    try {
        const res = await fetch('/api/alerts?limit=25');
        if (!res.ok) return;
        const data = await res.json();
        const tbody = document.getElementById('alertsTableBody');
        const countBadge = document.getElementById('alertsCountBadge');
        const alertsKpiCount = document.getElementById('alertsKpiCount');
        const ui = currentLocaleData ? currentLocaleData.ui : null;
        
        if (!tbody) return;
        
        if (countBadge && data.total !== undefined) {
            alertsTotal = data.total;
            const label = data.total === 1 ? (ui && ui.record ? ui.record : 'record') : (ui && ui.records ? ui.records : 'records');
            countBadge.innerText = `${data.total} ${label}`;
        }
        if (alertsKpiCount && data.total !== undefined) {
            alertsKpiCount.innerText = data.total;
        }
        
        if (!data.alerts || data.alerts.length === 0) {
            const emptyText = ui ? ui.no_alerts : "No inconsistencies detected yet.";
            tbody.innerHTML = `<tr><td colspan="5" class="py-10 text-center text-slate-500 font-sans">${emptyText}</td></tr>`;
            return;
        }
        
        const btnText = ui ? (ui.btn_view_alert || "Details") : "Details";

        tbody.innerHTML = data.alerts.map(row => {
            alertsMap[row.id] = row;
            const timeStr = formatTime12h(row.timestamp);
            const discSign = row.discrepancy > 0 ? `+${row.discrepancy}` : `${row.discrepancy}`;
            const discColor = row.discrepancy > 0 ? 'text-rose-400 font-bold' : 'text-amber-400 font-bold';
            
            return `
                <tr class="hover:bg-slate-800/60 transition-colors">
                    <td class="py-3 px-3.5 text-slate-300 text-[11px] font-mono whitespace-nowrap">${timeStr}</td>
                    <td class="py-3 px-2 text-emerald-400 font-bold">${row.in_count}</td>
                    <td class="py-3 px-2 text-amber-400 font-bold">${row.out_count}</td>
                    <td class="py-3 px-2 ${discColor}">${discSign}</td>
                    <td class="py-3 px-3.5 text-right">
                        <button onclick="openAlertDetailsModal(${row.id})" title="${btnText}" class="p-1.5 bg-slate-800 hover:bg-sky-600 text-slate-400 hover:text-white border border-slate-700 hover:border-sky-500/50 rounded-md transition-all inline-flex items-center justify-center cursor-pointer shadow-sm">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        console.error("Error fetching alerts:", e);
    }
}

function openAlertDetailsModal(alertId) {
    const alert = alertsMap[alertId];
    if (!alert) return;

    const modal = document.getElementById('alertDetailsModal');
    const inEl = document.getElementById('modalAlertIn');
    const outEl = document.getElementById('modalAlertOut');
    const diffEl = document.getElementById('modalAlertDiff');
    const msgEl = document.getElementById('modalAlertMessage');
    const timeEl = document.getElementById('modalAlertTime');

    if (inEl) inEl.innerText = alert.in_count;
    if (outEl) outEl.innerText = alert.out_count;
    if (diffEl) {
        const sign = alert.discrepancy > 0 ? `+${alert.discrepancy}` : alert.discrepancy;
        diffEl.innerText = sign;
    }
    if (msgEl) msgEl.innerText = alert.message;
    if (timeEl) timeEl.innerText = formatTime12h(alert.timestamp);

    if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }
}

function closeAlertDetailsModal() {
    const modal = document.getElementById('alertDetailsModal');
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }
}

function showToastAlert(alert) {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const ui = currentLocaleData ? currentLocaleData.ui : null;
    const title = ui ? (ui.toast_alert_title || "🚨 CRITICAL ALERT: Inconsistency Detected") : "🚨 CRITICAL ALERT: Inconsistency Detected";
    
    // Play critical alert notification sound
    playNotificationSound();

    const toast = document.createElement('div');
    toast.className = "pointer-events-auto bg-slate-900/95 border-2 border-rose-500/90 text-slate-100 p-4 rounded-lg shadow-2xl shadow-rose-950/70 ring-1 ring-rose-500/50 flex items-start gap-3 transition-all duration-300 transform translate-y-2 opacity-0 backdrop-blur-xl";
    toast.innerHTML = `
        <div class="p-2 bg-rose-500/20 text-rose-400 rounded-md shrink-0 border border-rose-500/30">
            <svg class="w-5 h-5 animate-pulse text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>
        </div>
        <div class="flex-1 min-w-0">
            <div class="text-xs font-black text-rose-400 uppercase tracking-wide flex items-center justify-between">
                <span>${title}</span>
                <span class="bg-rose-600 text-white font-bold text-[9px] px-1.5 py-0.5 rounded uppercase tracking-wider">CRITICAL</span>
            </div>
            <div class="text-xs text-slate-200 mt-1 font-semibold leading-relaxed">${alert.message}</div>
            <div class="text-[10px] text-rose-300/80 mt-1.5 font-mono font-bold">${formatTime12h(alert.timestamp)}</div>
        </div>
        <button onclick="this.parentElement.remove()" class="text-slate-400 hover:text-white text-base font-bold ml-1 cursor-pointer">&times;</button>
    `;
    
    container.appendChild(toast);
    
    // Animate in
    setTimeout(() => {
        toast.classList.remove('translate-y-2', 'opacity-0');
    }, 50);
    
    // Auto-dismiss after 10 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.classList.add('opacity-0', 'translate-y-2');
            setTimeout(() => toast.remove(), 400);
        }
    }, 10000);
}

async function clearAllAlerts() {
    try {
        await fetch('/api/alerts/clear', { method: 'POST' });
        lastSeenAlertId = 0;
        const alertsBadge = document.getElementById('alertsBadge');
        if (alertsBadge) {
            alertsBadge.classList.add('hidden');
            alertsBadge.classList.remove('flex');
        }
        fetchAlerts();
        fetchStatus();
    } catch (e) {
        console.error("Error clearing alerts:", e);
    }
}

function scrollToAlerts() {
    const card = document.getElementById('inconsistencyCard');
    if (card) {
        card.scrollIntoView({ behavior: 'smooth' });
    }
}

async function controlResetAll() {
    const ui = currentLocaleData ? currentLocaleData.ui : null;
    const msg = ui && ui.reset_confirm ? ui.reset_confirm : "Reset detector counts and restart video from beginning?";
    if (confirm(msg)) {
        await fetch('/api/playback/reset', { method: 'POST' });
        await clearAllAlerts();
        fetchStatus();
        fetchDailyHistory();
        fetchAlerts();
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    // Unlock AudioContext on first user interaction
    const unlockAudio = () => {
        initAudioContext();
        window.removeEventListener('click', unlockAudio);
        window.removeEventListener('keydown', unlockAudio);
        window.removeEventListener('touchstart', unlockAudio);
    };
    window.addEventListener('click', unlockAudio);
    window.addEventListener('keydown', unlockAudio);
    window.addEventListener('touchstart', unlockAudio);

    try {
        const cfgRes = await fetch('/api/config');
        if (cfgRes.ok) {
            const cfg = await cfgRes.json();
            currentLang = cfg.language || 'es';
        }
    } catch (e) {
        console.error("Error fetching config on startup:", e);
    }

    await loadLocale(currentLang);

    const slider = document.getElementById('timelineSlider');
    if (slider) {
        slider.addEventListener('mousedown', () => { isUserDragging = true; });
        slider.addEventListener('touchstart', () => { isUserDragging = true; });
        slider.addEventListener('change', async (e) => {
            const targetFrame = parseInt(e.target.value);
            await fetch(`/api/playback/seek?frame=${targetFrame}`, { method: 'POST' });
            isUserDragging = false;
            fetchStatus();
        });
    }

    const feed = document.getElementById('videoFeed');
    if (feed) {
        feed.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            toggleStatsAndDebug();
        });
    }

    // Modal backdrop click handler
    const modal = document.getElementById('alertDetailsModal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeAlertDetailsModal();
            }
        });
    }

    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeAlertDetailsModal();
            return;
        }
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
        if (e.code === 'Space') {
            e.preventDefault();
            controlTogglePlay();
        } else if (e.code === 'ArrowLeft') {
            e.preventDefault();
            controlSeekOffset(-5);
        } else if (e.code === 'ArrowRight') {
            e.preventDefault();
            controlSeekOffset(5);
        } else if (e.key === '[' || e.key === ',') {
            e.preventDefault();
            controlStep(-1);
        } else if (e.key === ']' || e.key === '.') {
            e.preventDefault();
            controlStep(1);
        } else if (e.key === 'r' || e.key === 'R') {
            e.preventDefault();
            controlRestart();
        } else if (e.key === 'n' || e.key === 'N') {
            e.preventDefault();
            toggleStatsAndDebug();
        }
    });

    setInterval(fetchStatus, 300);
    setInterval(fetchDailyHistory, 4000);
    setInterval(fetchAlerts, 3000);
    fetchStatus();
    fetchDailyHistory();
    fetchAlerts();
});
