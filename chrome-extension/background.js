/**
 * background.js - Service worker for VideoDub extension.
 * 
 * Handles extension lifecycle events and relays messages
 * between popup and content scripts.
 */

// Log when extension is installed
chrome.runtime.onInstalled.addListener(() => {
  console.log('[VideoDub] Extension installed');
});

// Listen for messages from popup or content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[VideoDub Background] Message received:', message);

  if (message.type === 'LOG') {
    // Forward logs from content script for debugging
    console.log('[VideoDub Content]', message.data);
  }

  sendResponse({ received: true });
  return true;
});
