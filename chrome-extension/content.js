/**
 * content.js - Core logic for VideoDub extension.
 *
 * Responsibilities:
 * 1. Extract YouTube video ID from URL
 * 2. Fetch translated subtitles + TTS audio from backend
 * 3. Schedule Vietnamese audio playback synced to video timeline
 * 4. Handle video seek/pause/resume
 * 5. Mute/unmute original video
 */

(function () {
  'use strict';

  // ── State ──────────────────────────────────────────────
  let isActive = false;
  let videoElement = null;
  let originalVolume = 1;
  let segments = [];          // Translated subtitle segments from backend
  let scheduledTimers = [];   // setTimeout IDs for scheduled playback
  let currentAudio = null;    // Currently playing Audio element
  let audioQueue = [];        // Queue of Audio elements to play
  let isPlaying = false;
  let isLoading = false;
  let lastSyncTime = -1;
  let wasPlayingBeforeDub = false;  // Track if video was playing before we paused it
  let resumePosition = 0;          // Video position to resume from

  // ── Config ─────────────────────────────────────────────
  const API_URL = 'http://localhost:8000/api/subtitles';
  const SYNC_INTERVAL_MS = 500; // How often to check video time for sync
  let syncIntervalId = null;

  // ── Logging helper ─────────────────────────────────────
  function log(...args) {
    console.log('[VideoDub]', ...args);
  }

  function logError(...args) {
    console.error('[VideoDub]', ...args);
  }

  // ── Message listener from popup ────────────────────────
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    log('Message received:', message.type);

    switch (message.type) {
      case 'START_DUB':
        startDubbing();
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
    if (video) {
      log('Found video element, duration:', video.duration);
    }
    return video;
  }

  // ── Start dubbing pipeline ─────────────────────────────
  async function startDubbing() {
    if (isActive) {
      log('Already active, ignoring start');
      return;
    }

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
    notifyPopup('loading', 'Fetching subtitles & translating...');
    log('Fetching subtitles for video:', videoId);

    // Pause video while backend is processing
    wasPlayingBeforeDub = !videoElement.paused;
    resumePosition = videoElement.currentTime;
    if (wasPlayingBeforeDub) {
      videoElement.pause();
      log('Video paused during processing (will resume when ready)');
    }

    try {
      // Fetch translated subtitles from backend
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ videoId }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMsg = errorData.detail || `Server error: ${response.status}`;
        throw new Error(errorMsg);
      }

      const data = await response.json();
      segments = data.segments || [];
      isLoading = false;

      if (segments.length === 0) {
        throw new Error('No subtitles found for this video');
      }

      log(`Received ${segments.length} translated segments`);

      // Pre-decode and preload all audio segments
      log('Pre-decoding and preloading audio segments...');
      for (let i = 0; i < segments.length; i++) {
        const seg = segments[i];
        seg._index = i;
        seg._audioBlob = base64ToBlob(seg.audioBase64, 'audio/mp3');
        seg._audioUrl = URL.createObjectURL(seg._audioBlob);
        // Create Audio element and preload for gapless playback
        seg._audio = new Audio(seg._audioUrl);
        seg._audio.preload = 'auto';
        seg._audio.load();
        // Free the base64 string to save memory
        delete seg.audioBase64;
      }

      // Mute original video
      originalVolume = videoElement.volume;
      videoElement.volume = 0;
      log('Original video muted');

      // Resume video from saved position now that audio is ready
      videoElement.currentTime = resumePosition;
      if (wasPlayingBeforeDub) {
        videoElement.play().then(() => {
          log('Video resumed after processing');
        }).catch(err => {
          logError('Failed to resume video:', err);
        });
      }

      // Start syncing audio to video timeline
      startSync();
      notifyPopup('active', `Playing ${segments.length} translated segments`);

    } catch (err) {
      logError('Failed to start dubbing:', err.message);
      isActive = false;
      isLoading = false;
      // Resume video if we paused it
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

    // Restore original volume
    if (videoElement) {
      videoElement.volume = originalVolume;
      log('Original video volume restored');
    }

    // Stop sync
    stopSync();

    // Cancel all scheduled timers
    cancelAllScheduled();

    // Stop current audio
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
    }

    // Revoke audio URLs
    for (const seg of segments) {
      if (seg._audioUrl) {
        URL.revokeObjectURL(seg._audioUrl);
      }
    }

    // Clear state
    segments = [];
    audioQueue = [];
    isPlaying = false;
    lastSyncTime = -1;

    notifyPopup('inactive', 'Stopped');
    log('Dubbing stopped');
  }

  // ── Sync engine: schedule audio based on video currentTime ──
  function startSync() {
    // Listen for video events
    videoElement.addEventListener('seeked', onVideoSeek);
    videoElement.addEventListener('pause', onVideoPause);
    videoElement.addEventListener('play', onVideoPlay);

    // Start periodic sync
    scheduleUpcoming();
    syncIntervalId = setInterval(() => {
      if (isActive && !videoElement.paused) {
        scheduleUpcoming();
      }
    }, SYNC_INTERVAL_MS);

    log('Sync engine started');
  }

  function stopSync() {
    if (syncIntervalId) {
      clearInterval(syncIntervalId);
      syncIntervalId = null;
    }

    if (videoElement) {
      videoElement.removeEventListener('seeked', onVideoSeek);
      videoElement.removeEventListener('pause', onVideoPause);
      videoElement.removeEventListener('play', onVideoPlay);
    }
  }

  function onVideoSeek() {
    log('Video seeked to:', videoElement.currentTime);
    cancelAllScheduled();
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
      isPlaying = false;
    }
    lastSyncTime = -1;
    scheduleUpcoming();
  }

  function onVideoPause() {
    log('Video paused');
    cancelAllScheduled();
    if (currentAudio) {
      currentAudio.pause();
    }
  }

  function onVideoPlay() {
    log('Video resumed');
    if (currentAudio && currentAudio.paused) {
      currentAudio.play().catch(() => {});
    }
    lastSyncTime = -1;
    scheduleUpcoming();
  }

  // ── Schedule upcoming segments ─────────────────────────
  function scheduleUpcoming() {
    if (!isActive || !videoElement || videoElement.paused) return;

    const currentTime = videoElement.currentTime;
    const lookAheadSec = 10; // Schedule segments up to 10 seconds ahead

    for (const seg of segments) {
      // Skip segments in the past or already scheduled
      if (seg.start < currentTime - 0.5) continue;
      if (seg.start > currentTime + lookAheadSec) break;
      if (seg._scheduled) continue;

      const delayMs = (seg.start - currentTime) * 1000;

      if (delayMs < 0) {
        // Segment should have started already, skip it
        continue;
      }

      seg._scheduled = true;
      const timerId = setTimeout(() => {
        if (!isActive || videoElement.paused) return;
        playSegmentAudio(seg);
      }, delayMs);

      scheduledTimers.push(timerId);
    }
  }

  function cancelAllScheduled() {
    for (const id of scheduledTimers) {
      clearTimeout(id);
    }
    scheduledTimers = [];

    // Reset scheduled flags
    for (const seg of segments) {
      seg._scheduled = false;
    }
  }

  // ── Play a segment's audio ─────────────────────────────
  function playSegmentAudio(seg) {
    if (!isActive) return;

    // Use preloaded Audio element if available, otherwise create new
    const audio = seg._audio || new Audio(seg._audioUrl);

    audio.onended = () => {
      if (currentAudio === audio) {
        currentAudio = null;
        isPlaying = false;
      }
    };

    audio.onerror = (err) => {
      logError('Audio playback error:', err);
      if (currentAudio === audio) {
        currentAudio = null;
        isPlaying = false;
      }
    };

    // If something is already playing, stop it
    if (currentAudio) {
      currentAudio.pause();
    }

    currentAudio = audio;
    isPlaying = true;

    // Eagerly preload the next segment for gapless playback
    preloadNextSegment(seg._index);

    audio.play().catch(err => {
      logError('Cannot play audio (autoplay blocked?):', err);
      currentAudio = null;
      isPlaying = false;
    });
  }

  // ── Preload next segment ───────────────────────────────
  function preloadNextSegment(currentIndex) {
    if (currentIndex == null) return;
    const nextIdx = currentIndex + 1;
    if (nextIdx < segments.length) {
      const next = segments[nextIdx];
      if (next._audio && next._audio.readyState < 3) {
        next._audio.load();
      }
    }
  }

  // ── Convert base64 to Blob ─────────────────────────────
  function base64ToBlob(base64, mimeType) {
    const byteChars = atob(base64);
    const byteArray = new Uint8Array(byteChars.length);
    for (let i = 0; i < byteChars.length; i++) {
      byteArray[i] = byteChars.charCodeAt(i);
    }
    return new Blob([byteArray], { type: mimeType });
  }

  // ── Notify popup of status changes ─────────────────────
  function notifyPopup(status, message) {
    chrome.runtime.sendMessage({
      type: 'STATUS_UPDATE',
      status,
      message,
    }).catch(() => {
      // Popup might not be open, that's fine
    });
  }

  // ── Init ───────────────────────────────────────────────
  log('Content script loaded on:', window.location.href);

})();
