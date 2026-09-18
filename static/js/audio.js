/**
 * AegisVault Audio Synthesizer Engine
 * Generates realistic biometric HUD pings, alarms, and mechanical vault sounds via Web Audio API.
 */
class VaultAudioEngine {
    constructor() {
        this.ctx = null;
        this.alarmInterval = null;
        this.muted = false;
    }

    init() {
        if (!this.ctx) {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (AudioCtx) {
                this.ctx = new AudioCtx();
            }
        }
        if (this.ctx && this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
    }

    playKeypadBeep() {
        if (this.muted) return;
        this.init();
        if (!this.ctx) return;

        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(1200, this.ctx.currentTime);
        gain.gain.setValueAtTime(0.08, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.06);

        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start();
        osc.stop(this.ctx.currentTime + 0.06);
    }

    playScanChirp() {
        if (this.muted) return;
        this.init();
        if (!this.ctx) return;

        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(800, this.ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(1600, this.ctx.currentTime + 0.12);
        gain.gain.setValueAtTime(0.06, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.12);

        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start();
        osc.stop(this.ctx.currentTime + 0.12);
    }

    playGrantedChime() {
        if (this.muted) return;
        this.init();
        if (!this.ctx) return;

        const t = this.ctx.currentTime;
        [523.25, 659.25, 783.99, 1046.50].forEach((freq, idx) => {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(freq, t + idx * 0.08);
            gain.gain.setValueAtTime(0.12, t + idx * 0.08);
            gain.gain.exponentialRampToValueAtTime(0.001, t + idx * 0.08 + 0.4);

            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(t + idx * 0.08);
            osc.stop(t + idx * 0.08 + 0.4);
        });

        // Hydraulic rumble effect
        setTimeout(() => this.playHydraulicRelease(), 300);
    }

    playHydraulicRelease() {
        if (this.muted || !this.ctx) return;
        const t = this.ctx.currentTime;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(90, t);
        osc.frequency.linearRampToValueAtTime(40, t + 1.2);
        gain.gain.setValueAtTime(0.15, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 1.2);

        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(t);
        osc.stop(t + 1.2);
    }

    playDeniedBuzzer() {
        if (this.muted) return;
        this.init();
        if (!this.ctx) return;

        const t = this.ctx.currentTime;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(150, t);
        osc.frequency.setValueAtTime(120, t + 0.15);
        gain.gain.setValueAtTime(0.15, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.35);

        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(t);
        osc.stop(t + 0.35);
    }

    startIntruderAlarm(durationSec = 4) {
        if (this.muted) return;
        this.init();
        if (!this.ctx) return;
        this.stopAlarm();

        let high = true;
        const playWarble = () => {
            if (!this.ctx) return;
            const t = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = 'square';
            osc.frequency.setValueAtTime(high ? 980 : 700, t);
            gain.gain.setValueAtTime(0.2, t);
            gain.gain.exponentialRampToValueAtTime(0.02, t + 0.18);
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(t);
            osc.stop(t + 0.18);
            high = !high;
        };

        playWarble();
        this.alarmInterval = setInterval(playWarble, 200);

        setTimeout(() => {
            this.stopAlarm();
        }, durationSec * 1000);
    }

    stopAlarm() {
        if (this.alarmInterval) {
            clearInterval(this.alarmInterval);
            this.alarmInterval = null;
        }
    }

    speak(text, priority = false) {
        if (this.muted || !('speechSynthesis' in window)) return;
        try {
            if (priority) {
                window.speechSynthesis.cancel();
            }
            const utter = new SpeechSynthesisUtterance(text);
            utter.rate = 1.05;
            utter.pitch = 0.95;
            // Prefer an English voice
            const voices = window.speechSynthesis.getVoices();
            const voice = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('David') || v.name.includes('Zira')));
            if (voice) utter.voice = voice;
            window.speechSynthesis.speak(utter);
        } catch (e) {
            console.warn("Speech synthesis error:", e);
        }
    }
}

window.vaultAudio = new VaultAudioEngine();
