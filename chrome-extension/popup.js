/**
 * popup.js - Controls the ON/OFF toggle for VideoDub.
 * Sends messages to the content script on the active YouTube tab.
 * Handles loading, active, and error states.
 */

let isActive = false;
let isLoading = false;

const toggleBtn   = document.getElementById('toggleBtn');
const statusText  = document.getElementById('statusText');
const statusDot   = document.getElementById('statusDot');
const voiceSelect = document.getElementById('voiceSelect');
const srcLang     = document.getElementById('srcLang');
const tgtLang     = document.getElementById('tgtLang');

// Listen for status updates from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'STATUS_UPDATE') {
    handleStatusUpdate(message.status, message.message);
  }
  sendResponse({ received: true });
  return true;
});

// On popup open, query content script for current state
chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  if (tabs[0] && tabs[0].url && tabs[0].url.includes('youtube.com')) {
    chrome.tabs.sendMessage(tabs[0].id, { type: 'GET_STATUS' }, (response) => {
      if (chrome.runtime.lastError) return;
      if (response) {
        if (response.loading) {
          isLoading = true;
          updateUI('loading', 'Loading subtitles...');
        } else if (response.active) {
          isActive = true;
          updateUI('active');
        }
      }
    });
  }
});

toggleBtn.addEventListener('click', () => {
  if (isLoading) return;

  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (!tabs[0] || !tabs[0].url || !tabs[0].url.includes('youtube.com')) {
      updateUI('error', 'Open a YouTube video first');
      return;
    }

    if (isActive) {
      chrome.tabs.sendMessage(tabs[0].id, { type: 'STOP_DUB' }, (response) => {
        if (chrome.runtime.lastError) { updateUI('error', 'Reload the YouTube page'); return; }
        isActive = false;
        isLoading = false;
        updateUI('inactive');
      });
    } else {
      isLoading = true;
      updateUI('loading', 'Fetching subtitles & translating...');

      const voiceId = voiceSelect.value;
      chrome.tabs.sendMessage(tabs[0].id, { type: 'START_DUB', voiceId }, (response) => {
        if (chrome.runtime.lastError) {
          updateUI('error', 'Reload the YouTube page');
          isLoading = false;
        }
      });
    }
  });
});

function handleStatusUpdate(status, message) {
  switch (status) {
    case 'loading':  isLoading = true;  isActive = false; updateUI('loading', message); break;
    case 'active':   isLoading = false; isActive = true;  updateUI('active', message);  break;
    case 'error':    isLoading = false; isActive = false; updateUI('error', message);   break;
    case 'inactive': isLoading = false; isActive = false; updateUI('inactive');          break;
  }
}

function updateUI(state, message) {
  const controls = [voiceSelect, srcLang, tgtLang];

  switch (state) {
    case 'loading':
      statusText.innerHTML = '<span class="spinner"></span>' + (message || 'Loading...');
      statusText.className = 'status-text loading';
      statusDot.className  = 'status-dot loading';
      toggleBtn.textContent = '⏳ Loading...';
      toggleBtn.className  = 'btn-toggle start';
      toggleBtn.disabled   = true;
      controls.forEach(el => el.disabled = true);
      break;

    case 'active':
      statusText.textContent = '● Playing Vietnamese audio';
      statusText.className   = 'status-text active';
      statusDot.className    = 'status-dot active';
      toggleBtn.textContent  = '⏹ Stop';
      toggleBtn.className    = 'btn-toggle stop';
      toggleBtn.disabled     = false;
      controls.forEach(el => el.disabled = true);
      break;

    case 'error':
      statusText.textContent = '⚠ ' + (message || 'Error occurred');
      statusText.className   = 'status-text error';
      statusDot.className    = 'status-dot error';
      toggleBtn.textContent  = '▶ Start';
      toggleBtn.className    = 'btn-toggle start';
      toggleBtn.disabled     = false;
      controls.forEach(el => el.disabled = false);
      break;

    case 'inactive':
    default:
      statusText.textContent = 'Ready';
      statusText.className   = 'status-text';
      statusDot.className    = 'status-dot';
      toggleBtn.textContent  = '▶ Start';
      toggleBtn.className    = 'btn-toggle start';
      toggleBtn.disabled     = false;
      controls.forEach(el => el.disabled = false);
      break;
  }
}
