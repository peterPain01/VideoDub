/**
 * content.js - Core logic for VideoDub extension.
 *
 * Responsibilities:
 * 1. Extract YouTube video ID from URL
 * 2. Fetch translated subtitles + TTS audio from backend
 * 3. Schedule Vietnamese audio playback synced to video timeline
 * 4. Handle video seek/pause/resume
 * 5. Mute/unmute original video
 * 6. Inject player button (after fullscreen) + loading overlay
 */

(function () {
  'use strict';

  // ── State ──────────────────────────────────────────────
  let isActive = false;
  let videoElement = null;
  let originalVolume = 1;
  let segments = [];
  let scheduledTimers = [];
  let currentAudio = null;
  let currentGain = null;
  let currentSeg = null;
  let audioQueue = [];
  let isPlaying = false;
  let isLoading = false;
  let lastSyncTime = -1;
  let wasPlayingBeforeDub = false;
  let resumePosition = 0;

  // ── Config ─────────────────────────────────────────────
  const API_URL = 'https://videodub-production.up.railway.app/api/subtitles';
  const SYNC_INTERVAL_MS = 500;
  const FADE_MS = 120;
  let syncIntervalId = null;

  // ── Web Audio API ──────────────────────────────────────
  let audioCtx = null;

  function getAudioContext() {
    if (!audioCtx || audioCtx.state === 'closed') {
      audioCtx = new AudioContext();
    }
    if (audioCtx.state === 'suspended') audioCtx.resume();
    return audioCtx;
  }

  function connectToAudioContext(audioEl) {
    const ctx = getAudioContext();
    const source = ctx.createMediaElementSource(audioEl);
    const gain = ctx.createGain();
    source.connect(gain);
    gain.connect(ctx.destination);
    return gain;
  }

  // ── Player UI refs ─────────────────────────────────────
  let playerBtn = null;
  let loadingOverlay = null;

  // ── Logging helper ─────────────────────────────────────
  function log(...args) { console.log('[VideoDub]', ...args); }
  function logError(...args) { console.error('[VideoDub]', ...args); }

  // ── Animation style (injected once into <head>) ────────
  function ensureAnimStyle() {
    if (document.getElementById('videodub-style')) return;
    const s = document.createElement('style');
    s.id = 'videodub-style';
    s.textContent = '@keyframes vd-spin{to{transform:rotate(360deg)}}';
    document.head.appendChild(s);
  }

  // ── Player button (after fullscreen) ───────────────────
  function injectButton() {
    if (document.getElementById('videodub-btn')) {
      playerBtn = document.getElementById('videodub-btn');
      return true;
    }

    const rightControls = document.querySelector('.ytp-right-controls');
    if (!rightControls) return false;

    playerBtn = document.createElement('button');
    playerBtn.id = 'videodub-btn';
    playerBtn.className = 'ytp-button';
    playerBtn.style.cssText = [
      'width:36px', 'height:36px', 'padding:0',
      'display:inline-flex', 'align-items:center', 'justify-content:center',
      'cursor:pointer', 'border:none', 'background:transparent',
    ].join(';');

    setButtonState('inactive');
    playerBtn.addEventListener('click', onPlayerBtnClick);
    rightControls.appendChild(playerBtn);
    log('Player button injected');
    return true;
  }

  // ── Loading overlay (covers the video area) ────────────
  function injectOverlay() {
    if (document.getElementById('videodub-overlay')) {
      loadingOverlay = document.getElementById('videodub-overlay');
      return true;
    }

    const player = document.getElementById('movie_player') ||
                   document.querySelector('.html5-video-player');
    if (!player) return false;

    loadingOverlay = document.createElement('div');
    loadingOverlay.id = 'videodub-overlay';
    loadingOverlay.style.cssText = [
      'position:absolute', 'inset:0',
      'display:none', 'flex-direction:column',
      'align-items:center', 'justify-content:center',
      'background:rgba(0,0,0,0.62)',
      'z-index:9998', 'pointer-events:none',
    ].join(';');
    loadingOverlay.innerHTML = `
      <div id="videodub-spinner" style="
        width:52px;height:52px;
        border:4px solid rgba(255,255,255,0.18);
        border-top-color:#fff;
        border-radius:50%;
        animation:vd-spin 0.85s linear infinite;
      "></div>
      <p id="videodub-overlay-text" style="
        color:#fff;font-size:15px;margin-top:20px;
        font-family:'Segoe UI',Arial,sans-serif;
        font-weight:500;letter-spacing:0.2px;
        text-shadow:0 1px 6px rgba(0,0,0,0.9);
      ">Đang xử lý...</p>
    `;

    player.appendChild(loadingOverlay);
    log('Loading overlay injected');
    return true;
  }

  function injectPlayerUI() {
    ensureAnimStyle();
    const btnOk = injectButton();
    const overlayOk = injectOverlay();
    return btnOk && overlayOk;
  }

  // ── Retry injection until player is ready ─────────────
  function tryInjectUI() {
    let attempts = 0;
    const timer = setInterval(() => {
      attempts++;
      if (injectPlayerUI() || attempts >= 30) clearInterval(timer);
    }, 500);
  }

  // ── Button click handler ───────────────────────────────
  function onPlayerBtnClick() {
    if (isLoading) return;
    if (isActive) stopDubbing();
    else startDubbing();
  }

  // ── Button visual states ───────────────────────────────
  function setButtonState(state) {
    if (!playerBtn) return;

    const viText = (color) =>
      `<svg viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg" width="28" height="28">
        <text x="18" y="19" text-anchor="middle" dominant-baseline="middle"
          font-size="13" font-weight="700" fill="${color}"
          font-family="Arial,sans-serif" letter-spacing="1">VI</text>
      </svg>`;

    const spinner =
      `<div style="width:18px;height:18px;border:2px solid rgba(255,255,255,0.25);
        border-top-color:#fff;border-radius:50%;
        animation:vd-spin 0.8s linear infinite;"></div>`;

    switch (state) {
      case 'loading':
        playerBtn.innerHTML = spinner;
        playerBtn.style.opacity = '1';
        playerBtn.title = 'VideoDub – Đang tải...';
        break;
      case 'active':
        playerBtn.innerHTML = viText('#4ade80');
        playerBtn.style.opacity = '1';
        playerBtn.title = 'VideoDub – Đang chạy (click để tắt)';
        break;
      case 'error':
        playerBtn.innerHTML = viText('#f87171');
        playerBtn.style.opacity = '1';
        playerBtn.title = 'VideoDub – Lỗi (click để thử lại)';
        break;
      default: // inactive
        playerBtn.innerHTML = viText('rgba(255,255,255,0.75)');
        playerBtn.style.opacity = '0.85';
        playerBtn.title = 'VideoDub – Lồng tiếng Việt';
    }
  }

  // ── Overlay show/hide ──────────────────────────────────
  function showOverlay(text = 'Đang xử lý...') {
    if (!loadingOverlay) injectOverlay();
    if (!loadingOverlay) return;
    const p = document.getElementById('videodub-overlay-text');
    if (p) p.textContent = text;
    loadingOverlay.style.display = 'flex';
  }

  function hideOverlay() {
    if (loadingOverlay) loadingOverlay.style.display = 'none';
  }

  // ── Message listener from popup ────────────────────────
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    log('Message received:', message.type);

    switch (message.type) {
      case 'START_DUB':
        startDubbing(message.voiceId);
        sendResponse({ success: true });
        break;
      case 'STOP_DUB':
        stopDubbing();
        sendResponse({ success: true });
        break;
      case 'GET_STATUS':
        sendResponse({ active: isActive, loading: isLoading });
        break;
      default:
        sendResponse({ success: false, error: 'Unknown message type' });
    }

    return true;
  });

  // ── Extract video ID from YouTube URL ──────────────────
  function getVideoId() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('v');
  }

  // ── Find YouTube video element ─────────────────────────
  function findVideoElement() {
    const video = document.querySelector('video.html5-main-video') ||
                  document.querySelector('video');
    if (video) log('Found video element, duration:', video.duration);
    return video;
  }

  // ── Start dubbing pipeline ─────────────────────────────
  async function startDubbing(voiceId) {
    if (isActive) { log('Already active, ignoring start'); return; }

    const videoId = getVideoId();
    if (!videoId) {
      logError('No video ID found in URL!');
      notifyPopup('error', 'Not a YouTube video page');
      return;
    }

    videoElement = findVideoElement();
    if (!videoElement) {
      logError('No video element found on page!');
      notifyPopup('error', 'No video found on page');
      return;
    }

    isActive = true;
    isLoading = true;

    setButtonState('loading');
    showOverlay('Đang tải phụ đề & dịch...');
    notifyPopup('loading', 'Fetching subtitles & translating...');
    log('Fetching subtitles for video:', videoId);

    // Pause video while backend processes
    wasPlayingBeforeDub = !videoElement.paused;
    resumePosition = videoElement.currentTime;
    if (wasPlayingBeforeDub) {
      videoElement.pause();
      log('Video paused during processing');
    }

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ videoId, voiceId: voiceId || undefined }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server error: ${response.status}`);
      }

      const data = await response.json();
      segments = data.segments || [];
      isLoading = false;

      if (segments.length === 0) throw new Error('No subtitles found for this video');

      log(`Received ${segments.length} translated segments`);

      // Pre-decode and preload all audio segments
      showOverlay('Đang chuẩn bị audio...');
      for (let i = 0; i < segments.length; i++) {
        const seg = segments[i];
        seg._index = i;
        seg._audioBlob = base64ToBlob(seg.audioBase64, 'audio/mp3');
        seg._audioUrl = URL.createObjectURL(seg._audioBlob);
        seg._audio = new Audio(seg._audioUrl);
        seg._audio.preload = 'auto';
        seg._audio.onloadedmetadata = () => {
          const audioDur = seg._audio.duration;
          // Natural rate = rate needed to fit TTS into subtitle window (cap at 2x)
          seg._naturalRate = (audioDur > 0 && audioDur > seg.duration)
            ? Math.min(audioDur / seg.duration, 2.0)
            : 1.0;
        };
        seg._audio.load();
        delete seg.audioBase64;
      }

      hideOverlay();

      // Mute original video
      originalVolume = videoElement.volume;
      videoElement.volume = 0;
      log('Original video muted');

      // Resume video
      videoElement.currentTime = resumePosition;
      if (wasPlayingBeforeDub) {
        videoElement.play().catch(err => logError('Failed to resume video:', err));
      }

      startSync();
      setButtonState('active');
      notifyPopup('active', `Playing ${segments.length} translated segments`);

    } catch (err) {
      logError('Failed to start dubbing:', err.message);
      isActive = false;
      isLoading = false;

      hideOverlay();
      setButtonState('error');

      if (wasPlayingBeforeDub && videoElement.paused) {
        videoElement.play().catch(() => {});
      }
      notifyPopup('error', err.message);
    }
  }

  // ── Stop dubbing pipeline ──────────────────────────────
  function stopDubbing() {
    if (!isActive && !isLoading) return;

    isActive = false;
    isLoading = false;
    log('Stopping dubbing...');

    hideOverlay();
    setButtonState('inactive');

    if (videoElement) {
      videoElement.volume = originalVolume;
      log('Original video volume restored');
    }

    stopSync();
    cancelAllScheduled();

    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
    }
    currentGain = null;

    if (audioCtx && audioCtx.state !== 'closed') {
      audioCtx.close();
      audioCtx = null;
    }

    for (const seg of segments) {
      if (seg._audioUrl) URL.revokeObjectURL(seg._audioUrl);
    }

    segments = [];
    audioQueue = [];
    isPlaying = false;
    lastSyncTime = -1;

    notifyPopup('inactive', 'Stopped');
    log('Dubbing stopped');
  }

  // ── Sync engine ────────────────────────────────────────
  function startSync() {
    videoElement.addEventListener('seeked', onVideoSeek);
    videoElement.addEventListener('pause', onVideoPause);
    videoElement.addEventListener('play', onVideoPlay);
    videoElement.addEventListener('ratechange', onVideoRateChange);

    scheduleUpcoming();
    syncIntervalId = setInterval(() => {
      if (isActive && !videoElement.paused) scheduleUpcoming();
    }, SYNC_INTERVAL_MS);

    log('Sync engine started');
  }

  function stopSync() {
    if (syncIntervalId) { clearInterval(syncIntervalId); syncIntervalId = null; }
    if (videoElement) {
      videoElement.removeEventListener('seeked', onVideoSeek);
      videoElement.removeEventListener('pause', onVideoPause);
      videoElement.removeEventListener('play', onVideoPlay);
      videoElement.removeEventListener('ratechange', onVideoRateChange);
    }
  }

  function onVideoSeek() {
    log('Video seeked to:', videoElement.currentTime);
    cancelAllScheduled();
    if (currentAudio) { currentAudio.pause(); currentAudio = null; isPlaying = false; }
    currentGain = null;
    currentSeg = null;
    lastSyncTime = -1;
    scheduleUpcoming();
  }

  function onVideoPause() {
    log('Video paused');
    cancelAllScheduled();
    if (currentAudio) currentAudio.pause();
  }

  function onVideoPlay() {
    log('Video resumed');
    if (currentAudio && currentAudio.paused) currentAudio.play().catch(() => {});
    lastSyncTime = -1;
    scheduleUpcoming();
  }

  function onVideoRateChange() {
    log('Playback rate changed to:', videoElement.playbackRate);
    if (currentAudio && currentSeg) {
      currentAudio.playbackRate = (currentSeg._naturalRate || 1) * (videoElement.playbackRate || 1);
    }
    cancelAllScheduled();
    scheduleUpcoming();
  }

  function scheduleUpcoming() {
    if (!isActive || !videoElement || videoElement.paused) return;

    const currentTime = videoElement.currentTime;
    const lookAheadSec = 10;

    for (const seg of segments) {
      if (seg.start + seg.duration < currentTime) continue;
      if (seg.start > currentTime + lookAheadSec) break;
      if (seg._scheduled) continue;

      const rate = videoElement.playbackRate || 1;
      const delayMs = Math.max(0, (seg.start - currentTime) * 1000 / rate - FADE_MS);

      seg._scheduled = true;
      const timerId = setTimeout(() => {
        if (!isActive || videoElement.paused) return;
        playSegmentAudio(seg);
      }, delayMs);

      scheduledTimers.push(timerId);
    }
  }

  function cancelAllScheduled() {
    for (const id of scheduledTimers) clearTimeout(id);
    scheduledTimers = [];
    for (const seg of segments) seg._scheduled = false;
  }

  // ── Audio playback ─────────────────────────────────────
  function playSegmentAudio(seg) {
    if (!isActive) return;

    const ctx = getAudioContext();
    const now = ctx.currentTime;
    const fadeSec = FADE_MS / 1000;

    // Fade-out câu đang phát, rồi pause sau khi fade xong
    if (currentAudio && currentGain) {
      const dyingAudio = currentAudio;
      currentGain.gain.setValueAtTime(currentGain.gain.value, now);
      currentGain.gain.linearRampToValueAtTime(0, now + fadeSec);
      setTimeout(() => dyingAudio.pause(), FADE_MS);
    }

    // Kết nối GainNode lần đầu (mỗi Audio element chỉ được connect 1 lần)
    if (!seg._gainNode) {
      seg._gainNode = connectToAudioContext(seg._audio);
    }

    // Fade-in câu mới
    seg._gainNode.gain.setValueAtTime(0, now);
    seg._gainNode.gain.linearRampToValueAtTime(1.0, now + fadeSec);

    seg._audio.onended = () => {
      if (currentAudio === seg._audio) { currentAudio = null; currentGain = null; currentSeg = null; isPlaying = false; }
    };
    seg._audio.onerror = (err) => {
      logError('Audio playback error:', err);
      if (currentAudio === seg._audio) { currentAudio = null; currentGain = null; currentSeg = null; isPlaying = false; }
    };

    seg._audio.playbackRate = (seg._naturalRate || 1) * (videoElement.playbackRate || 1);

    currentAudio = seg._audio;
    currentGain = seg._gainNode;
    currentSeg = seg;
    isPlaying = true;
    preloadNextSegment(seg._index);

    seg._audio.play().catch(err => {
      logError('Cannot play audio (autoplay blocked?):', err);
      currentAudio = null;
      currentGain = null;
      isPlaying = false;
    });
  }

  function preloadNextSegment(currentIndex) {
    if (currentIndex == null) return;
    const next = segments[currentIndex + 1];
    if (next && next._audio && next._audio.readyState < 3) next._audio.load();
  }

  // ── Helpers ────────────────────────────────────────────
  function base64ToBlob(base64, mimeType) {
    const byteChars = atob(base64);
    const byteArray = new Uint8Array(byteChars.length);
    for (let i = 0; i < byteChars.length; i++) byteArray[i] = byteChars.charCodeAt(i);
    return new Blob([byteArray], { type: mimeType });
  }

  function notifyPopup(status, message) {
    chrome.runtime.sendMessage({ type: 'STATUS_UPDATE', status, message }).catch(() => {});
  }

  // ── YouTube SPA navigation handler ─────────────────────
  document.addEventListener('yt-navigate-finish', () => {
    log('YouTube navigated, reinitializing UI...');
    // If dubbing was active, stop it cleanly
    if (isActive || isLoading) stopDubbing();
    // Reset UI refs (old elements were removed from DOM)
    playerBtn = null;
    loadingOverlay = null;
    tryInjectUI();
  });

  // ── Init ───────────────────────────────────────────────
  log('Content script loaded on:', window.location.href);
  tryInjectUI();

})();
