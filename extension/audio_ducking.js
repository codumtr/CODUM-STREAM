/**
 * StreamDub Adaptive Audio Graph & Ducking Engine (CODUM Production)
 * 1. Kick <video> etiketini Web Audio API grafiğine bağlar.
 * 2. Oynatıcı tamponunu ve duraklatma/oynatma durumunu takip eder.
 * 3. Ducking'i paket geldiğinde değil, ses ÇALMAYA BAŞLADIĞI ANDA tetikler.
 */

class StreamAudioGraph {
  constructor() {
    this.audioCtx = null;
    this.sourceNode = null;
    this.originalGainNode = null;
    this.dubGainNode = null;
    this.videoElement = null;
    this.isHooked = false;

    // Ayarlar
    this.duckingVolume = 0.20; // Orijinal sesi %20'ye indir (fısıltı seviyesi)
    this.normalVolume = 1.0;
    this.manualDelayMs = 0;    // İzleyicinin manuel ince ayar sürgüsü
  }

  init(videoElement) {
    if (this.isHooked || !videoElement) return;
    this.videoElement = videoElement;

    try {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      this.audioCtx = new AudioContextClass();

      // Video etiketini AudioContext'e bağla
      this.sourceNode = this.audioCtx.createMediaElementSource(videoElement);

      this.originalGainNode = this.audioCtx.createGain();
      this.originalGainNode.gain.setValueAtTime(this.normalVolume, this.audioCtx.currentTime);

      this.dubGainNode = this.audioCtx.createGain();
      this.dubGainNode.gain.setValueAtTime(1.0, this.audioCtx.currentTime);

      this.sourceNode.connect(this.originalGainNode);
      this.originalGainNode.connect(this.audioCtx.destination);
      this.dubGainNode.connect(this.audioCtx.destination);

      this.isHooked = true;
      console.log("[CODUM StreamDub] Audio Graph başarıyla bağlandı!");
    } catch (e) {
      console.warn("[CODUM StreamDub] Doğrudan MediaElementSource bağlanamadı (CORS kaynaklı olabilir):", e);
    }
  }

  /**
   * Kick oynatıcısının anlık canlı yayın tampon gecikmesini dinamik hesaplar.
   */
  calculateDynamicBufferDelay() {
    if (!this.videoElement) return 0;
    try {
      const buffered = this.videoElement.buffered;
      if (buffered.length > 0) {
        const liveEdge = buffered.end(buffered.length - 1);
        const currentPos = this.videoElement.currentTime;
        const latencySec = Math.max(0, liveEdge - currentPos);
        return latencySec * 1000; // Milisaniye
      }
    } catch (e) {}
    return 1800; // Tipik LL-HLS Kick tamponu
  }

  /**
   * Klonlanmış dublaj sesini oynatır. Ducking sadece oynatma başladığında tetiklenir.
   */
  async playDubbingAudio(audioBase64) {
    if (!this.audioCtx) return;

    // Yayın duraklatılmışsa dublajı çalma
    if (this.videoElement && this.videoElement.paused) {
      console.log("[CODUM StreamDub] Video duraklatılmış, dublaj atlandı.");
      return;
    }

    if (this.audioCtx.state === 'suspended') {
      await this.audioCtx.resume();
    }

    try {
      const binaryString = atob(audioBase64);
      const len = binaryString.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) bytes[i] = binaryString.charCodeAt(i);

      const audioBuffer = await this.audioCtx.decodeAudioData(bytes.buffer);

      // Dinamik Tampon + Kullanıcı İnce Ayarı
      const dynamicDelay = this.calculateDynamicBufferDelay() + this.manualDelayMs;

      setTimeout(() => {
        if (!this.audioCtx || (this.videoElement && this.videoElement.paused)) return;

        const now = this.audioCtx.currentTime;

        // 1. Ducking: Orijinal sesi tam ses çalmaya başlarken 80ms içinde %20'ye yumuşat
        this.originalGainNode.gain.cancelScheduledValues(now);
        this.originalGainNode.gain.linearRampToValueAtTime(this.duckingVolume, now + 0.08);

        // 2. Dublaj sesini AudioContext üzerinden çal
        const dubSource = this.audioCtx.createBufferSource();
        dubSource.buffer = audioBuffer;
        dubSource.connect(this.dubGainNode);
        dubSource.start(now + 0.08);

        // 3. Dublaj bittiğinde sesi eski haline (1.0) geri getir
        const finishTime = now + 0.08 + audioBuffer.duration;
        this.originalGainNode.gain.setValueAtTime(this.duckingVolume, finishTime);
        this.originalGainNode.gain.linearRampToValueAtTime(this.normalVolume, finishTime + 0.35);

      }, Math.max(0, dynamicDelay));

    } catch (err) {
      console.error("[CODUM StreamDub] Decode hatası:", err);
    }
  }

  setManualDelay(ms) {
    this.manualDelayMs = parseInt(ms, 10) || 0;
  }

  setDuckingVolume(percent) {
    const val = parseFloat(percent);
    if (!isNaN(val)) {
      this.duckingVolume = Math.max(0.02, Math.min(0.9, val > 1 ? val / 100.0 : val));
      console.log(`[CODUM StreamDub] Ducking seviyesi güncellendi: ${this.duckingVolume}`);
    }
  }
}

window.StreamAudioGraph = StreamAudioGraph;
