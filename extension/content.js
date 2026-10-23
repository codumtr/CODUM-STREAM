/**
 * StreamDub Kick Player Content Script
 * Kick.com video oynatıcısını algılar, Web Audio grafiğini bağlar ve
 * Kick kontrol çubuğuna dil seçici düğmeler ekler.
 */

(function () {
  console.log("[StreamDub] Kick Canlı Dublaj Eklentisi devrede.");

  let audioGraph = null;
  let ws = null;
  let currentLang = "en";
  let isEnabled = true;
  let customServerUrl = "ws://localhost:8765";

  // Kayıtlı ayarları depodan çek
  if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
    chrome.storage.local.get(['serverUrl', 'syncDelay', 'duckingVol'], (res) => {
      if (res.serverUrl) customServerUrl = res.serverUrl.replace('http://', 'ws://').replace('https://', 'wss://');
      if (audioGraph) {
        if (res.syncDelay) audioGraph.setManualDelay(res.syncDelay);
        if (res.duckingVol) audioGraph.setDuckingVolume(res.duckingVol);
      }
    });

    // Popup'tan gelen canlı ayar değişikliklerini dinle
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      if (request.action === "update_settings") {
        if (audioGraph) {
          if (request.syncDelay !== undefined) audioGraph.setManualDelay(request.syncDelay);
          if (request.duckingVol !== undefined) audioGraph.setDuckingVolume(request.duckingVol);
        }
        if (request.serverUrl && request.serverUrl !== customServerUrl) {
          customServerUrl = request.serverUrl.replace('http://', 'ws://').replace('https://', 'wss://');
          connectToDubbingServer();
        }
        sendResponse({ status: "applied" });
      }
    });
  }

  function getChannelName() {
    const parts = window.location.pathname.split("/").filter(Boolean);
    return parts.length > 0 ? parts[0].toLowerCase() : "streamer";
  }

  function initAudio() {
    const video = document.querySelector("video");
    if (video && !audioGraph) {
      audioGraph = new window.StreamAudioGraph();
      audioGraph.init(video);
      console.log("[StreamDub] Kick video etiketi bağlandı.");
    }
  }

  function connectToDubbingServer() {
    const channel = getChannelName();
    const base = customServerUrl.replace(/\/$/, "");
    const wsUrl = `${base}/ws/stream/${channel}?role=viewer&lang=${currentLang}`;

    if (ws) {
      ws.close();
    }

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log(`[StreamDub WS] ${channel} kanalına dublaj bağlantısı kuruldu (${currentLang})`);
      updateButtonUI();
    };

    ws.onmessage = (event) => {
      if (!isEnabled) return;
      try {
        const data = JSON.parse(event.data);
        if (data.type === "dub_audio" && data.audio) {
          if (!audioGraph) initAudio();
          if (audioGraph) {
            audioGraph.playDubbingAudio(data.audio);
          }
        }
      } catch (err) {
        console.error("[StreamDub] Gelen ses işleme hatası:", err);
      }
    };

    ws.onclose = () => {
      console.log("[StreamDub WS] Bağlantı kapandı, 4s sonra tekrar denenecek...");
      setTimeout(connectToDubbingServer, 4000);
    };
  }

  function injectPlayerControls() {
    if (document.getElementById("streamdub-control-pill")) return;

    // Kick video kontrol alanı
    const controlsContainer = document.querySelector(".vjs-control-bar") ||
                              document.querySelector("[data-player-controls]") ||
                              document.querySelector("div[class*='controls']");

    const pill = document.createElement("div");
    pill.id = "streamdub-control-pill";
    pill.className = "streamdub-pill";
    pill.innerHTML = `
      <div class="streamdub-label">
        <span class="streamdub-dot"></span>
        <span id="streamdub-current-lang">🎙️ EN DUB</span>
      </div>
      <div class="streamdub-dropdown">
        <button data-lang="en" class="streamdub-btn active">English Dubbed</button>
        <button data-lang="es" class="streamdub-btn">Español</button>
        <button data-lang="de" class="streamdub-btn">Deutsch</button>
        <button data-lang="off" class="streamdub-btn">Kapalı (Orijinal)</button>
      </div>
    `;

    if (controlsContainer) {
      controlsContainer.appendChild(pill);
    } else {
      // Alternatif: Sayfanın sağ altına yerleştir
      pill.classList.add("floating");
      document.body.appendChild(pill);
    }

    // Tıklama olayları
    pill.querySelectorAll(".streamdub-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const lang = e.target.getAttribute("data-lang");
        if (lang === "off") {
          isEnabled = false;
          currentLang = "off";
        } else {
          isEnabled = true;
          currentLang = lang;
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "set_language", lang: lang }));
          } else {
            connectToDubbingServer();
          }
        }
        updateButtonUI();
      });
    });
  }

  function updateButtonUI() {
    const label = document.getElementById("streamdub-current-lang");
    if (label) {
      label.innerText = isEnabled ? `🎙️ ${currentLang.toUpperCase()} DUB` : "🔇 DUBLAJ KAPALI";
    }
  }

  // Sayfa değişimlerini ve video yüklenmesini izle
  const observer = new MutationObserver(() => {
    initAudio();
    injectPlayerControls();
  });

  observer.observe(document.body, { childList: true, subtree: true });

  // İlk başlatma
  setTimeout(() => {
    initAudio();
    injectPlayerControls();
    connectToDubbingServer();
  }, 1500);

})();
