/**
 * popup.js - Controls the ON/OFF toggle for VideoDub.
 * Sends messages to the content script on the active YouTube tab.
 * Handles loading, active, and error states.
 */

let isActive = false;
let isLoading = false;

const toggleBtn = document.getElementById('toggleBtn');
const statusEl = document.getElementById('status');
const infoEl = document.getElementById('info');

// Listen for status updates from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'STATUS_UPDATE') {
    handleStatusUpdate(message.status, message.message);
  }
  sendResponse({ received: true });
  return true;
});

// On popup open, query the content script for current state
chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  if (tabs[0] && tabs[0].url && tabs[0].url.includes('youtube.com')) {
    chrome.tabs.sendMessage(tabs[0].id, { type: 'GET_STATUS' }, (response) => {
      if (chrome.runtime.lastError) {
        console.log('Content script not ready:', chrome.runtime.lastError.message);
        return;
      }
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
  if (isLoading) return; // Don't allow clicks while loading

  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (!tabs[0] || !tabs[0].url || !tabs[0].url.includes('youtube.com')) {
      statusEl.textContent = '⚠ Open a YouTube video first!';
      statusEl.className = 'status error';
      return;
    }

    if (isActive) {
      // Stop
      chrome.tabs.sendMessage(tabs[0].id, { type: 'STOP_DUB' }, (response) => {
        if (chrome.runtime.lastError) {
          statusEl.textContent = '⚠ Error: Reload the YouTube page';
          statusEl.className = 'status error';
          return;
        }
        isActive = false;
        isLoading = false;
        updateUI('inactive');
      });
    } else {
      // Start
      isLoading = true;
      updateUI('loading', 'Fetching subtitles & translating...');

      chrome.tabs.sendMessage(tabs[0].id, { type: 'START_DUB' }, (response) => {
        if (chrome.runtime.lastError) {
          statusEl.textContent = '⚠ Error: Reload the YouTube page';
          statusEl.className = 'status error';
          isLoading = false;
          return;
        }
      });
    }
  });
});

function handleStatusUpdate(status, message) {
  switch (status) {
    case 'loading':
      isLoading = true;
      isActive = false;
      updateUI('loading', message);
      break;
    case 'active':
      isLoading = false;
      isActive = true;
      updateUI('active', message);
      break;
    case 'error':
      isLoading = false;
      isActive = false;
      updateUI('error', message);
      break;
    case 'inactive':
      isLoading = false;
      isActive = false;
      updateUI('inactive');
      break;
  }
}

function updateUI(state, message) {
  switch (state) {
    case 'loading':
      statusEl.innerHTML = '<span class="spinner"></span> ' + (message || 'Loading...');
      statusEl.className = 'status loading';
      toggleBtn.textContent = '⏳ Loading...';
      toggleBtn.className = 'start';
      toggleBtn.disabled = true;
      infoEl.textContent = 'This may take a minute for long videos';
      break;
    case 'active':
      statusEl.textContent = 'Status: ON 🟢';
      statusEl.className = 'status active';
      toggleBtn.textContent = '⏹ Stop Translation';
      toggleBtn.className = 'stop';
      toggleBtn.disabled = false;
      infoEl.textContent = message || 'Vietnamese audio playing';
      break;
    case 'error':
      statusEl.textContent = '⚠ ' + (message || 'Error occurred');
      statusEl.className = 'status error';
      toggleBtn.textContent = '▶ Start Translation';
      toggleBtn.className = 'start';
      toggleBtn.disabled = false;
      infoEl.textContent = 'Video must have English subtitles/CC';
      break;
    case 'inactive':
    default:
      statusEl.textContent = 'Status: OFF';
      statusEl.className = 'status';
      toggleBtn.textContent = '▶ Start Translation';
      toggleBtn.className = 'start';
      toggleBtn.disabled = false;
      infoEl.textContent = 'Translates YouTube English subtitles to Vietnamese voice';
      break;
  }
}
