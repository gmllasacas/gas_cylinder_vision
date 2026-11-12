/**
 * Gas Tank Stream Dashboard - V2 Alpine.js & DaisyUI Controller
 * Clean reactive state management, telemetry polling, and video controls.
 */

document.addEventListener('alpine:init', () => {
    Alpine.data('streamDashboard', () => ({
        // Telemetry & Runtime State
        status: {
            current_video: '',
            current_source_id: '',
            is_live: false,
            is_file_missing: false,
            camera_connected: true,
            connection_error_msg: '',
            active_model: 'best.pt',
            device: 'Auto',
            conf: 0.50,
            imgsz: 640,
            frame_skip: 2,
            playback_speed: 1.0,
            output_width: 1024,
            lang: 'es',
            video_native_fps: 25.0,
            actual_stream_fps: 0.0,
            max_hardware_fps: 0.0,
            ai_latency_ms: 0.0,
            encode_latency_ms: 0.0,
            debug_mode: true,
            current_frame: 0,
            total_frames: 0,
            fps: 0.0,
            current_time: 0.0,
            duration: 0.0,
            is_paused: false,
            loop: true,
            in_count: 0,
            out_count: 0,
            net_count: 0,
            active_tracks: 0,
            active_alerts_count: 0,
            latest_alert: null
        },

        // UI View State
        showStats: true,
        activeTab: 'alerts', // 'alerts' | 'history' | 'settings'
        isScrubbing: false,
        sliderFrame: 0,
        isConfDragging: false,
        confValue: '0.50',
        speedValue: '1.00',
        resetModalOpen: false,
        selectedAlert: null,
        sources: [],
        alerts: [],
        history: [],
        toasts: [],
        
        // Localization
        currentLang: 'es',
        localeData: {},
        
        // Internal audio & polling references
        pollTimer: null,
        lastSeenAlertId: -1,
        audioUnlocked: false,
        audioElement: null,
        audioCtx: null,

        async init() {
            // 1. Detect language from cookie or navigator
            const savedLang = document.cookie.match(/app_lang=([a-z]{2})/i);
            this.currentLang = savedLang ? savedLang[1] : (navigator.language.startsWith('en') ? 'en' : 'es');

            // 2. Load translations
            await this.loadLocale(this.currentLang);

            // 3. Audio & interaction unlock listeners
            this.setupAudioUnlock();

            // 4. Initial data loads
            await this.fetchSources();
            await this.fetchStatus();
            await this.fetchAlerts();
            await this.fetchHistory();

            // 5. Start high-frequency telemetry polling (200ms)
            this.pollTimer = setInterval(() => this.fetchStatus(), 200);

            // 6. Setup global keyboard shortcuts
            this.setupKeyboardShortcuts();
        },

        // Helper to translate keys from loaded locale dictionary
        t(key, fallback = '') {
            if (this.localeData && this.localeData.ui && this.localeData.ui[key]) {
                return this.localeData.ui[key];
            }
            return fallback || key;
        },

        async loadLocale(lang) {
            try {
                const res = await fetch(`/locales/${lang}.json?v=4.0`);
                if (res.ok) {
                    this.localeData = await res.json();
                    this.currentLang = lang;
                    document.cookie = `app_lang=${lang};path=/;max-age=31536000`;
                }
            } catch (err) {
                console.error("Failed loading locale:", err);
            }
        },

        async changeLanguage(newLang) {
            try {
                await fetch(`/api/settings/lang?value=${encodeURIComponent(newLang)}`, { method: 'POST' });
                await this.loadLocale(newLang);
            } catch (err) {
                console.error("Failed updating language:", err);
            }
        },

        setupAudioUnlock() {
            const unlock = () => {
                if (!this.audioUnlocked) {
                    try {
                        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
                        if (AudioContextClass) {
                            this.audioCtx = new AudioContextClass();
                            if (this.audioCtx.state === 'suspended') {
                                this.audioCtx.resume();
                            }
                        }
                        this.audioElement = new Audio('/static/audio/alert.wav');
                        this.audioElement.volume = 1.0;
                        this.audioElement.load();
                        this.audioUnlocked = true;
                    } catch (e) {
                        console.warn("Audio unlock issue:", e);
                    }
                }
            };
            ['click', 'keydown', 'touchstart'].forEach(evt => {
                document.addEventListener(evt, unlock, { once: true, passive: true });
            });
        },

        playChimeSound() {
            try {
                if (!this.audioCtx) return;
                const now = this.audioCtx.currentTime;
                const master = this.audioCtx.createGain();
                master.gain.setValueAtTime(0.9, now);
                master.connect(this.audioCtx.destination);

                const strikes = [
                    { freq: 1046.50, time: 0.00, dur: 0.40, gain: 0.7 },
                    { freq: 1318.51, time: 0.15, dur: 0.45, gain: 0.8 },
                    { freq: 2093.00, time: 0.30, dur: 0.80, gain: 1.0 }
                ];

                strikes.forEach(s => {
                    const osc = this.audioCtx.createOscillator();
                    const g = this.audioCtx.createGain();
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(s.freq, now + s.time);
                    g.gain.setValueAtTime(0.0, now + s.time);
                    g.gain.setValueAtTime(s.gain * 0.7, now + s.time + 0.003);
                    g.gain.exponentialRampToValueAtTime(0.001, now + s.time + s.dur);
                    osc.connect(g);
                    g.connect(master);
                    osc.start(now + s.time);
                    osc.stop(now + s.time + s.dur);
                });
            } catch (e) {
                console.warn("Chime error:", e);
            }
        },

        triggerAlertNotification(alert) {
            // Play audio
            this.playChimeSound();
            if (this.audioElement) {
                this.audioElement.currentTime = 0;
                this.audioElement.play().catch(() => {});
            }

            // Push floating toast
            const toastId = Date.now();
            this.toasts.push({
                id: toastId,
                title: this.t('toast_alert_title', 'CRITICAL ALERT: Inconsistency Detected'),
                message: alert.message,
                discrepancy: alert.discrepancy
            });

            // Auto-dismiss toast after 6 seconds
            setTimeout(() => {
                this.toasts = this.toasts.filter(t => t.id !== toastId);
            }, 6000);
        },

        async fetchStatus() {
            try {
                const res = await fetch('/api/status');
                if (!res.ok) return;
                const data = await res.json();
                
                // Detect new anomalies
                if (data.latest_alert && data.latest_alert.id > this.lastSeenAlertId) {
                    if (this.lastSeenAlertId !== -1) {
                        this.triggerAlertNotification(data.latest_alert);
                        this.fetchAlerts();
                    }
                    this.lastSeenAlertId = data.latest_alert.id;
                }

                this.status = data;

                // Sync slider position only if the user is not actively scrubbing
                if (!this.isScrubbing) {
                    this.sliderFrame = data.current_frame;
                }
                if (!this.isConfDragging && data.conf !== undefined) {
                    this.confValue = Number(data.conf).toFixed(2);
                }
                if (data.playback_speed !== undefined) {
                    this.speedValue = Number(data.playback_speed).toFixed(2);
                }
            } catch (err) {
                console.error("Telemetry fetch error:", err);
            }
        },

        async fetchSources() {
            try {
                const res = await fetch('/api/sources');
                if (res.ok) {
                    this.sources = await res.json();
                }
            } catch (err) {
                console.error("Failed fetching sources:", err);
            }
        },

        async changeSource(sourceId) {
            try {
                await fetch(`/api/sources/change?source_id=${encodeURIComponent(sourceId)}`, { method: 'POST' });
                await this.fetchStatus();
            } catch (err) {
                console.error("Source change error:", err);
            }
        },

        async fetchAlerts() {
            try {
                const res = await fetch('/api/alerts?limit=25');
                if (res.ok) {
                    const data = await res.json();
                    this.alerts = data.alerts || [];
                }
            } catch (err) {
                console.error("Failed fetching alerts:", err);
            }
        },

        async clearAlerts() {
            try {
                await fetch('/api/alerts/clear', { method: 'POST' });
                this.alerts = [];
                this.status.active_alerts_count = 0;
                this.lastSeenAlertId = 0;
            } catch (err) {
                console.error("Failed clearing alerts:", err);
            }
        },

        async fetchHistory() {
            try {
                const res = await fetch('/api/counts/history?limit=10');
                if (res.ok) {
                    const data = await res.json();
                    this.history = data.history || [];
                }
            } catch (err) {
                console.error("Failed fetching history:", err);
            }
        },

        // Playback Controls
        async togglePlayback() {
            try {
                await fetch('/api/playback/toggle', { method: 'POST' });
                await this.fetchStatus();
            } catch (err) {
                console.error("Playback toggle error:", err);
            }
        },

        async restartVideo() {
            try {
                const res = await fetch('/api/playback/restart', { method: 'POST' });
                if (!res.ok) {
                    await fetch('/api/playback/seek?frame=0', { method: 'POST' });
                }
                await this.fetchStatus();
            } catch (err) {
                console.error("Restart error:", err);
                try {
                    await fetch('/api/playback/seek?frame=0', { method: 'POST' });
                    await this.fetchStatus();
                } catch (e) {}
            }
        },

        async seekOffset(seconds) {
            try {
                await fetch(`/api/playback/seek_offset?seconds=${encodeURIComponent(seconds)}`, { method: 'POST' });
                await this.fetchStatus();
            } catch (err) {
                console.error("Seek error:", err);
            }
        },

        async stepFrame(deltaFrames) {
            try {
                await fetch(`/api/playback/step?delta=${encodeURIComponent(deltaFrames)}`, { method: 'POST' });
                await this.fetchStatus();
            } catch (err) {
                console.error("Step error:", err);
            }
        },

        async setSpeed(spd) {
            try {
                const val = parseFloat(spd);
                this.speedValue = Number(val).toFixed(2);
                this.status.playback_speed = val;
                await fetch(`/api/settings/speed?value=${encodeURIComponent(val)}`, { method: 'POST' });
                await this.fetchStatus();
            } catch (err) {
                console.error("Speed setting error:", err);
            }
        },

        async toggleLoop() {
            try {
                this.status.loop = !this.status.loop;
                const res = await fetch('/api/playback/loop', { method: 'POST' });
                if (res.ok) {
                    const data = await res.json();
                    this.status.loop = Boolean(data.loop);
                }
            } catch (err) {
                console.error("Loop toggle error:", err);
            }
        },

        async toggleDebugMode() {
            try {
                await fetch('/api/settings/debug', { method: 'POST' });
                await this.fetchStatus();
            } catch (err) {
                console.error("Debug toggle error:", err);
            }
        },

        onScrubStart() {
            this.isScrubbing = true;
        },

        async onScrubEnd() {
            try {
                const frame = parseInt(this.sliderFrame, 10);
                await fetch(`/api/playback/seek?frame=${frame}`, { method: 'POST' });
            } catch (err) {
                console.error("Scrub seek error:", err);
            } finally {
                this.isScrubbing = false;
                this.fetchStatus();
            }
        },

        async setConfidence(conf) {
            try {
                const val = parseFloat(conf);
                this.confValue = Number(val).toFixed(2);
                this.status.conf = val;
                await fetch(`/api/settings/conf?value=${encodeURIComponent(val)}`, { method: 'POST' });
                await this.fetchStatus();
            } catch (err) {
                console.error("Confidence change error:", err);
            }
        },

        async onConfidenceChange() {
            await this.setConfidence(this.confValue);
        },

        openResetModal() {
            this.resetModalOpen = true;
        },

        async confirmReset() {
            try {
                await fetch('/api/playback/reset', { method: 'POST' });
                await this.clearAlerts();
                await this.fetchStatus();
                await this.fetchHistory();
            } catch (err) {
                console.error("Reset error:", err);
            } finally {
                this.resetModalOpen = false;
            }
        },

        formatTime(seconds) {
            if (!seconds || isNaN(seconds) || seconds < 0) return "0:00";
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${mins}:${secs.toString().padStart(2, '0')}`;
        },

        setupKeyboardShortcuts() {
            window.addEventListener('keydown', (e) => {
                if (['input', 'textarea', 'select'].includes(e.target.tagName.toLowerCase())) {
                    return;
                }
                switch (e.key) {
                    case ' ':
                        e.preventDefault();
                        this.togglePlayback();
                        break;
                    case 'r':
                    case 'R':
                        e.preventDefault();
                        this.restartVideo();
                        break;
                    case 'n':
                    case 'N':
                        e.preventDefault();
                        this.showStats = !this.showStats;
                        break;
                    case 'ArrowLeft':
                        e.preventDefault();
                        this.seekOffset(-5);
                        break;
                    case 'ArrowRight':
                        e.preventDefault();
                        this.seekOffset(5);
                        break;
                    case '[':
                        e.preventDefault();
                        this.stepFrame(-1);
                        break;
                    case ']':
                        e.preventDefault();
                        this.stepFrame(1);
                        break;
                }
            });
        }
    }));
});

