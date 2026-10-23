/**
 * CODUM StreamDub OBS Audio & Subtitle Engine
 * 1. Altyazıları ekrana basar.
 * 2. Dublaj sesini (dub_audio) Web Audio API ile çalar.
 *    OBS Browser Source'ta "Control audio via OBS" seçildiğinde bu ses doğrudan OBS mikserine gider!
 * 3. Cümlelerin üst üste binmesini önleyen sıralı ses kuyruğu (Smart Sync Queue).
 */

const urlParams = new URLSearchParams(window.location.search);
const channel = urlParams.get('channel') || 'streamer';
const host = window.location.host || 'localhost:8765';
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${host}/ws/stream/${channel}?role=overlay`;

const card = document.getElementById('subtitle-card');
const streamerNameEl = document.getElementById('streamer-name');
const translatedTextEl = document.getElementById('translated-text');
const originalTextEl = document.getElementById('original-text');
const langTagEl = document.getElementById('lang-tag');
const audioBadge = document.getElementById('audio-active-badge');
const unmuteBanner = document.getElementById('unmute-banner');

streamerNameEl.innerText = channel.toUpperCase();

let audioCtx = null;
let isAudioUnlocked = false;
let isPanicMuted = false;
let audioQueue = [];
let isPlayingAudio = false;
let fadeTimeout = null;

function initAudioContext() {
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    audioCtx = new AudioContextClass();
  }
  if (audioCtx.state === 'suspended') {
    audioCtx.resume().then(() => {
      isAudioUnlocked = true;
      if (unmuteBanner) unmuteBanner.classList.add('hidden');
    }).catch(() => {
      if (unmuteBanner) unmuteBanner.classList.remove('hidden');
    });
  } else {
    isAudioUnlocked = true;
    if (unmuteBanner) unmuteBanner.classList.add('hidden');
  }
}

// Tarayıcı autoplay politikası gereği tıklama dinleyicisi
document.addEventListener('click', initAudioContext);
if (unmuteBanner) {
  unmuteBanner.addEventListener('click', initAudioContext);
}

// Otomatik başlatmayı dene (OBS Browser Source'ta serbesttir)
initAudioContext();

function showSubtitles(original, translated, lang = 'EN') {
  translatedTextEl.innerText = translated || original;
  originalTextEl.innerText = translated ? `TR: "${original}"` : '';
  langTagEl.innerText = `${lang.toUpperCase()} DUB`;

  card.classList.remove('hidden');

  if (fadeTimeout) clearTimeout(fadeTimeout);
  fadeTimeout = setTimeout(() => {
    card.classList.add('hidden');
  }, 6000);
}

async function playNextInAudioQueue() {
  if (isPlayingAudio || audioQueue.length === 0 || isPanicMuted) return;

  isPlayingAudio = true;
  const audioBase64 = audioQueue.shift();

  try {
    initAudioContext();
    if (audioCtx.state === 'suspended') {
      await audioCtx.resume();
    }

    const binaryString = atob(audioBase64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) bytes[i] = binaryString.charCodeAt(i);

    const buffer = await audioCtx.decodeAudioData(bytes.buffer);
    const source = audioCtx.createBufferSource();
    source.buffer = buffer;
    source.connect(audioCtx.destination);

    audioBadge.classList.add('playing');
    audioBadge.innerText = "🔊 PLAYING";

    source.onended = () => {
      isPlayingAudio = false;
      audioBadge.classList.remove('playing');
      audioBadge.innerText = "🔊 OBS AUDIO";
      playNextInAudioQueue();
    };

    source.start(0);

  } catch (err) {
    console.warn("[OBS Audio] Çalma hatası:", err);
    isPlayingAudio = false;
    playNextInAudioQueue();
  }
}

function connectWebSocket() {
  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log(`[StreamDub OBS] Bağlandı: ${channel}`);
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);

      // Altyazı Mesajı
      if (data.type === 'subtitle') {
        showSubtitles(data.original, data.translated, data.lang);
      }

      // Dublaj Ses Mesajı (OBS Ses Çıkışı)
      else if (data.type === 'dub_audio' && data.audio) {
        if (!isPanicMuted) {
          audioQueue.push(data.audio);
          playNextInAudioQueue();
        }
      }

      // Acil Susturma (Panic Mute)
      else if (data.type === 'panic_mute') {
        isPanicMuted = !!data.muted;
        if (isPanicMuted) {
          audioQueue = [];
          audioBadge.innerText = "🔇 MUTED";
          audioBadge.style.color = "#ef4444";
        } else {
          audioBadge.innerText = "🔊 OBS AUDIO";
          audioBadge.style.color = "#94a3b8";
        }
      }
    } catch (err) {
      console.error('[StreamDub OBS] Mesaj ayrıştırma hatası:', err);
    }
  };

  ws.onclose = () => {
    console.warn('[StreamDub OBS] Bağlantı koptu, 3s sonra tekrar bağlanıyor...');
    setTimeout(connectWebSocket, 3000);
  };
}

connectWebSocket();
