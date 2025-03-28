// Track tab/page navigation
chrome.tabs.onUpdated.addListener(function(tabId, changeInfo, tab) {
    // Only send message when page is completely loaded and it's the active tab
    if (changeInfo.status === 'complete' && tab.active) {
      chrome.runtime.sendMessage({
        action: "pageNavigation",
        url: tab.url,
        timestamp: new Date().toISOString(),
        title: tab.title
      });
    }
});

// Track when user switches between tabs
chrome.tabs.onActivated.addListener(function(activeInfo) {
    chrome.tabs.get(activeInfo.tabId, function(tab) {
      chrome.runtime.sendMessage({
        action: "tabSwitch",
        url: tab.url,
        timestamp: new Date().toISOString(),
        title: tab.title
      });
    });
});

// Open side panel when extension icon is clicked
chrome.action.onClicked.addListener((tab) => {
  chrome.sidePanel.open({ tabId: tab.id });
});