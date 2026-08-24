let isUserDragging = false;
let isConfDragging = false;
let currentLang = 'es';
let currentLocaleData = null;

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

async function loadLocale(lang) {
    try {
        const res = await fetch(`/locales/${lang}.json?v=2.1`);
        if (res.ok) {
            currentLocaleData = await res.json();
            currentLang = lang;
            applyLocalization();
        }
    } catch (e) {
        console.error("Error loading locale file for:", lang, e);
    }
}

function applyLocalization() {
    if (!currentLocaleData || !currentLocaleData.ui) return;
    const ui = currentLocaleData.ui;

    const setHtml = (id, html) => {
        const el = document.getElementById(id);
        if (el && html) el.innerHTML = html;
    };
    const setText = (id, text) => {
        const el = document.getElementById(id);
        if (el && text) el.innerText = text;
    };

    setHtml('i18n_title', ui.title);
    setHtml('i18n_subtitle', ui.subtitle);
    setText('i18n_kpi_in', ui.kpi_in);
    setText('i18n_kpi_out', ui.kpi_out);
    setText('i18n_kpi_net', ui.kpi_net);

    setText('btnRestart', ui.btn_restart);
    setText('btnRewind', ui.btn_rewind);
    setText('btnStepBack', ui.btn_step_back);
    setText('btnStepFwd', ui.btn_step_fwd);
    setText('btnForward', ui.btn_forward);
    setText('btnReset', ui.btn_reset);

    setText('i18n_conf', ui.conf);
    setText('i18n_speed', ui.speed);

    setText('i18n_nerd_title', ui.nerd_title);
    setText('i18n_nerd_video', ui.nerd_video);
    setText('i18n_nerd_viewport', ui.nerd_viewport);
    setText('i18n_nerd_res', ui.nerd_res);
    setText('i18n_nerd_fps', ui.nerd_fps);
    setText('i18n_nerd_model', ui.nerd_model);
    setText('i18n_nerd_latency', ui.nerd_latency);
    setText('i18n_nerd_tracks', ui.nerd_tracks);
    setText('i18n_nerd_counts', ui.nerd_counts);

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

const toggleStatsForNerds = toggleStatsAndDebug;

function onConfSliderInput(value) {
    isConfDragging = true;
    const display = document.getElementById('confDisplay');
    if (display) display.innerText = parseFloat(value).toFixed(2);
}

async function onConfSliderChange(value) {
    try {
        await fetch(`/api/settings/conf?value=${encodeURIComponent(value)}`, { method: 'POST' });
        isConfDragging = false;
        fetchStatus();
    } catch (e) {
        console.error("Error setting confidence:", e);
        isConfDragging = false;
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

            if (durEl) durEl.innerText = '00:00';
            if (slider) {
                slider.disabled = true;
                slider.value = 100;
                slider.classList.add('opacity-40', 'cursor-not-allowed');
            }
            [btnRewind, btnStepBack, btnStepFwd, btnForward, btnRestart].forEach(btn => {
                if (btn) {
                    btn.disabled = true;
                    btn.classList.add('opacity-40', 'cursor-not-allowed');
                }
            });
        } else {
            if (currEl) currEl.innerText = formatTime(data.current_time);
            if (durEl) durEl.innerText = formatTime(data.duration);
            if (slider && !isUserDragging) {
                slider.disabled = false;
                slider.classList.remove('opacity-40', 'cursor-not-allowed');
                slider.max = data.total_frames || 100;
                slider.value = data.current_frame || 0;
            }
            [btnRewind, btnStepBack, btnStepFwd, btnForward, btnRestart].forEach(btn => {
                if (btn) {
                    btn.disabled = false;
                    btn.classList.remove('opacity-40', 'cursor-not-allowed');
                }
            });
        }

        // Update Error Banner and Status Badge
        const errorBanner = document.getElementById('cameraErrorBanner');
        const errorMsg = document.getElementById('cameraErrorMsg');
        const badge = document.getElementById('statusBadge');
        const playBtn = document.getElementById('playBtn');

        if (playBtn) {
            const playText = ui ? ui.btn_play : "▶ Play";
            const pauseText = ui ? ui.btn_pause : "⏸ Pause";
            playBtn.innerText = data.is_paused ? playText : pauseText;
        }

        if (data.is_live) {
            if (data.camera_connected) {
                if (errorBanner) errorBanner.classList.add('hidden');
                if (badge) {
                    badge.innerText = ui ? ui.live_camera : "🔴 LIVE CAMERA";
                    badge.className = "bg-rose-600 text-white px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wider shadow-sm animate-pulse";
                }
            } else {
                if (errorBanner) {
                    errorBanner.classList.remove('hidden');
                    if (errorMsg && ui) {
                        errorMsg.innerText = ui.cam_disconnected || "⚠️ Camera Unreachable (Reconnecting...)";
                    }
                }
                if (badge) {
                    badge.innerText = ui ? ui.cam_connecting : "⚠️ CONNECTING...";
                    badge.className = "bg-amber-500 text-slate-900 px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wider shadow-sm animate-pulse";
                }
            }
        } else {
            if (errorBanner) errorBanner.classList.add('hidden');
            if (badge) {
                const playingText = ui ? ui.playing : "PLAYING";
                const pausedText = ui ? ui.paused : "PAUSED";
                if (data.is_paused) {
                    badge.innerText = pausedText;
                    badge.className = "bg-amber-400 text-slate-900 px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wider";
                } else {
                    badge.innerText = playingText;
                    badge.className = "bg-emerald-500 text-white px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wider";
                }
            }
        }
    } catch (e) {
        console.error("Status update error", e);
    }
}

async function controlTogglePlay() {
    await fetch('/api/playback/toggle', { method: 'POST' });
    fetchStatus();
}

async function controlSeekOffset(seconds) {
    await fetch(`/api/playback/seek?offset=${seconds}`, { method: 'POST' });
    fetchStatus();
}

async function controlStep(delta) {
    await fetch(`/api/playback/step?delta=${delta}`, { method: 'POST' });
    fetchStatus();
}

async function controlRestart() {
    await fetch(`/api/playback/seek?frame=0`, { method: 'POST' });
    fetchStatus();
}

async function controlResetAll() {
    const ui = currentLocaleData ? currentLocaleData.ui : null;
    const msg = ui && ui.reset_confirm ? ui.reset_confirm : "Reset detector counts and restart video from beginning?";
    if (confirm(msg)) {
        await fetch('/api/playback/reset', { method: 'POST' });
        fetchStatus();
    }
}

document.addEventListener('DOMContentLoaded', async () => {
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
    fetchStatus();
});
