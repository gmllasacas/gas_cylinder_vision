let isUserDragging = false;
let isConfDragging = false;
let currentLang = 'es';
let currentLocaleData = null;
let lastSeenAlertId = 0;
let audioCtx = null;

function initAudioContext() {
    if (!audioCtx) {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) {
            audioCtx = new AudioContext();
        }
    }
    if (audioCtx && audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
}

function playNotificationSound() {
    try {
        initAudioContext();
        if (!audioCtx) return;

        const now = audioCtx.currentTime;
        
        // Tone 1: High crisp chime (880 Hz - A5 ramping to 1174.66 Hz - D6)
        const osc1 = audioCtx.createOscillator();
        const gain1 = audioCtx.createGain();
        osc1.type = 'sine';
        osc1.frequency.setValueAtTime(880, now);
        osc1.frequency.exponentialRampToValueAtTime(1174.66, now + 0.12);
        gain1.gain.setValueAtTime(0.25, now);
        gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
        osc1.connect(gain1);
        gain1.connect(audioCtx.destination);
        osc1.start(now);
        osc1.stop(now + 0.35);

        // Tone 2: Secondary harmonic accent (1318.51 Hz - E6)
        const osc2 = audioCtx.createOscillator();
        const gain2 = audioCtx.createGain();
        osc2.type = 'sine';
        osc2.frequency.setValueAtTime(1318.51, now + 0.12);
        gain2.gain.setValueAtTime(0.0, now);
        gain2.gain.setValueAtTime(0.22, now + 0.12);
        gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.55);
        osc2.connect(gain2);
        gain2.connect(audioCtx.destination);
        osc2.start(now + 0.12);
        osc2.stop(now + 0.55);
    } catch (e) {
        console.warn("Audio notification chime could not be played:", e);
    }
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

async function loadLocale(lang) {
    try {
        const res = await fetch(`/locales/${lang}.json?v=2.3`);
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
    setText('i18n_kpi_out', ui.kpi_out);
    setText('i18n_kpi_net', ui.kpi_net);
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
    setText('i18n_nerd_latency', ui.nerd_latency);
    setText('i18n_nerd_tracks', ui.nerd_tracks);
    setText('i18n_nerd_counts', ui.nerd_counts);

    setText('i18n_db_badge', ui.db_synced || "💾 SQLite DB");
    setText('i18n_history_title', ui.daily_history_title || "Daily Count History (SQLite)");
    setText('th_date', ui.col_date || "Date");
    setText('th_in', ui.col_in || "IN (Inbound)");
    setText('th_out', ui.col_out || "OUT (Outbound)");
    setText('th_net', ui.col_net || "Net Total");
    setText('th_updated', ui.col_updated || "Last Updated");
    setText('btnRefreshHistory', ui.btn_refresh || "↻ Refresh");

    setText('i18n_alerts_title', ui.alerts_title || "Inconsistency & Anomaly Alerts");
    setText('th_alert_time', ui.th_alert_time || "Time");
    setText('th_alert_in', ui.th_alert_in || "IN");
    setText('th_alert_out', ui.th_alert_out || "OUT");
    setText('th_alert_disc', ui.th_alert_disc || "Discrepancy");
    setText('th_alert_details', ui.th_alert_details || "Details / Inconsistency");
    setText('btnRefreshAlerts', ui.btn_refresh || "↻ Refresh");

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
        if (netEl && data.net_count !== undefined) netEl.innerText = data.net_count;

        // Update Anomaly / Inconsistency Alerts Badge & Toast Notification
        const alertsBadge = document.getElementById('alertsBadge');
        const alertsBadgeText = document.getElementById('alertsBadgeText');
        if (data.active_alerts_count !== undefined && data.active_alerts_count > 0) {
            if (alertsBadge) {
                alertsBadge.classList.remove('hidden');
                alertsBadge.classList.add('flex');
            }
            if (alertsBadgeText) {
                const label = data.active_alerts_count === 1 ? (ui && ui.alert_singular ? ui.alert_singular : 'inconsistency') : (ui && ui.alert_plural ? ui.alert_plural : 'inconsistencies');
                alertsBadgeText.innerText = `⚠️ ${data.active_alerts_count} ${label}`;
            }
        } else {
            if (alertsBadge) {
                alertsBadge.classList.add('hidden');
                alertsBadge.classList.remove('flex');
            }
        }

        if (data.latest_alert && data.latest_alert.id && data.latest_alert.id > lastSeenAlertId) {
            lastSeenAlertId = data.latest_alert.id;
            showToastAlert(data.latest_alert);
            fetchAlerts();
        }

        // Toggle HUD and Update Button based on data.debug_mode
        const statsBtn = document.getElementById('statsToggleBtn');
        const statsPanel = document.getElementById('statsForNerds');

        if (statsBtn) {
            const onLabel = ui ? ui.stats_on : "📊 Stats for Nerds: ON";
            const offLabel = ui ? ui.stats_off : "📊 Stats for Nerds: OFF";

            if (data.debug_mode) {
                statsBtn.innerText = onLabel;
                statsBtn.className = "bg-indigo-600 hover:bg-indigo-500 text-white border border-indigo-500 px-3.5 py-1.5 rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 transition-all cursor-pointer shadow-sm";
            } else {
                statsBtn.innerText = offLabel;
                statsBtn.className = "bg-slate-700 hover:bg-slate-600 text-slate-300 border border-slate-600 px-3.5 py-1.5 rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 transition-all cursor-pointer";
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
                statusBadge.className = "bg-rose-500 text-white px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider whitespace-nowrap shadow-sm";
            } else if (data.is_live) {
                if (data.camera_connected) {
                    statusBadge.innerText = (ui && ui.status_live) ? ui.status_live : (ui && ui.playing ? ui.playing : "LIVE STREAM");
                    statusBadge.className = "bg-emerald-500 text-white px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider whitespace-nowrap shadow-sm";
                } else {
                    statusBadge.innerText = (ui && ui.status_connecting) ? ui.status_connecting : (ui && ui.cam_connecting ? ui.cam_connecting : "CONNECTING...");
                    statusBadge.className = "bg-amber-500 text-white px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider whitespace-nowrap shadow-sm animate-pulse";
                }
            } else {
                if (data.is_paused) {
                    const label = (ui && (ui.status_paused || ui.paused)) ? (ui.status_paused || ui.paused) : "PAUSED";
                    statusBadge.innerText = label;
                    statusBadge.className = "bg-amber-500 text-white px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider whitespace-nowrap shadow-sm";
                } else {
                    const label = (ui && (ui.status_playing || ui.playing)) ? (ui.status_playing || ui.playing) : "PLAYING";
                    statusBadge.innerText = label;
                    statusBadge.className = "bg-emerald-500 text-white px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider whitespace-nowrap shadow-sm";
                }
            }
        }

        // Play/Pause Button Label
        const playBtn = document.getElementById('playBtn');
        if (playBtn) {
            if (data.is_paused) {
                playBtn.innerText = ui ? ui.btn_play : "▶ Play";
                playBtn.className = "bg-emerald-600 hover:bg-emerald-500 text-white border border-emerald-500 px-4 py-2 rounded-lg text-sm font-semibold inline-flex items-center gap-1.5 transition-all active:translate-y-0.5 cursor-pointer shadow-sm";
            } else {
                playBtn.innerText = ui ? ui.btn_pause : "⏸ Pause";
                playBtn.className = "bg-blue-600 hover:bg-blue-500 text-white border border-blue-500 px-4 py-2 rounded-lg text-sm font-semibold inline-flex items-center gap-1.5 transition-all active:translate-y-0.5 cursor-pointer shadow-sm";
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
            const label = data.total === 1 ? (ui && ui.record ? ui.record : 'record') : (ui && ui.records ? ui.records : 'records');
            countBadge.innerText = `${data.total} ${label}`;
        }
        
        if (!data.history || data.history.length === 0) {
            const noRecText = ui ? ui.no_records : "No daily records saved yet";
            tbody.innerHTML = `<tr><td colspan="5" class="py-6 text-center text-slate-500 font-sans">${noRecText}</td></tr>`;
            return;
        }
        
        tbody.innerHTML = data.history.map(row => {
            const updatedTime = row.updated_at ? row.updated_at.replace('T', ' ').substring(0, 19) : '-';
            const netSign = row.net_count > 0 ? '+' : '';
            const netColor = row.net_count >= 0 ? 'text-blue-400' : 'text-rose-400';
            
            return `
                <tr class="hover:bg-slate-700/40 transition-colors">
                    <td class="py-3 px-4 font-bold text-slate-200">${row.date}</td>
                    <td class="py-3 px-4 text-emerald-400 font-semibold">${row.in_count}</td>
                    <td class="py-3 px-4 text-amber-400 font-semibold">${row.out_count}</td>
                    <td class="py-3 px-4 ${netColor} font-bold">${netSign}${row.net_count}</td>
                    <td class="py-3 px-4 text-slate-400 text-[11px]">${updatedTime}</td>
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
        const ui = currentLocaleData ? currentLocaleData.ui : null;
        
        if (!tbody) return;
        
        if (countBadge && data.total !== undefined) {
            const label = data.total === 1 ? (ui && ui.alert_singular ? ui.alert_singular : 'inconsistency') : (ui && ui.alert_plural ? ui.alert_plural : 'inconsistencies');
            countBadge.innerText = `${data.total} ${label}`;
        }
        
        if (!data.alerts || data.alerts.length === 0) {
            const emptyText = ui ? ui.no_alerts : "No inconsistencies detected yet.";
            tbody.innerHTML = `<tr><td colspan="5" class="py-6 text-center text-slate-500 font-sans">${emptyText}</td></tr>`;
            return;
        }
        
        tbody.innerHTML = data.alerts.map(row => {
            const timeStr = row.timestamp ? row.timestamp.replace('T', ' ').substring(0, 19) : '-';
            const discSign = row.discrepancy > 0 ? `+${row.discrepancy}` : `${row.discrepancy}`;
            const discColor = row.discrepancy > 0 ? 'text-rose-400 font-bold' : 'text-amber-400 font-bold';
            
            return `
                <tr class="hover:bg-slate-700/40 transition-colors">
                    <td class="py-3 px-4 text-slate-400 text-[11px] font-mono">${timeStr}</td>
                    <td class="py-3 px-4 text-emerald-400 font-semibold">${row.in_count}</td>
                    <td class="py-3 px-4 text-amber-400 font-semibold">${row.out_count}</td>
                    <td class="py-3 px-4 ${discColor}">${discSign}</td>
                    <td class="py-3 px-4 text-slate-200 text-xs">${row.message}</td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        console.error("Error fetching alerts:", e);
    }
}

function showToastAlert(alert) {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const ui = currentLocaleData ? currentLocaleData.ui : null;
    const title = ui ? ui.toast_alert_title : "⚠️ IN/OUT Inconsistency Detected";
    
    // Play synthesized modern chime sound
    playNotificationSound();

    const toast = document.createElement('div');
    toast.className = "pointer-events-auto bg-slate-900/95 border-2 border-rose-500 text-slate-100 p-4 rounded-xl shadow-2xl flex items-start gap-3 transition-all duration-300 transform translate-y-2 opacity-0 backdrop-blur-md";
    toast.innerHTML = `
        <div class="p-2 bg-rose-500/20 text-rose-400 rounded-lg shrink-0">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>
        </div>
        <div class="flex-1 min-w-0">
            <div class="text-xs font-bold text-rose-400 uppercase tracking-wide flex items-center justify-between">
                <span>${title}</span>
            </div>
            <div class="text-xs text-slate-200 mt-1 font-medium leading-relaxed">${alert.message}</div>
            <div class="text-[10px] text-slate-400 mt-1.5 font-mono">${alert.timestamp ? alert.timestamp.replace('T', ' ').substring(0, 19) : ''}</div>
        </div>
        <button onclick="this.parentElement.remove()" class="text-slate-400 hover:text-slate-200 text-base font-bold ml-1 cursor-pointer">&times;</button>
    `;
    
    container.appendChild(toast);
    
    // Animate in
    setTimeout(() => {
        toast.classList.remove('translate-y-2', 'opacity-0');
    }, 50);
    
    // Auto-dismiss after 9 seconds
    setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-y-2');
        setTimeout(() => toast.remove(), 400);
    }, 9000);
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

    window.addEventListener('keydown', (e) => {
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
