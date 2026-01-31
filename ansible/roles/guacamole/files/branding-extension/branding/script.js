(function () {
  // Set favicon more robustly
  function setFavicon() {
    var head = document.head || document.getElementsByTagName("head")[0];
    var iconPath = "app/ext/cyberlab-branding/images/favicon.ico";

    // Remove existing favicons
    var existingIcons = document.querySelectorAll(
      'link[rel="icon"], link[rel="shortcut icon"]',
    );
    existingIcons.forEach(function (icon) {
      icon.parentNode.removeChild(icon);
    });

    // Create new icon links
    var icon = document.createElement("link");
    icon.rel = "icon";
    icon.type = "image/x-icon";
    icon.href = iconPath;
    head.appendChild(icon);

    var shortcut = document.createElement("link");
    shortcut.rel = "shortcut icon";
    shortcut.type = "image/x-icon";
    shortcut.href = iconPath;
    head.appendChild(shortcut);
  }

  setFavicon();

  // Re-apply after a short delay and on DOM changes to fight off default resets
  setTimeout(setFavicon, 1000);

  // Set title
  document.title = "CyberLab AttackBox";

  // Replace "Apache Guacamole" text anywhere in the DOM
  function replaceBranding() {
    if (!document.body) return;
    var walker = document.createTreeWalker(
      document.body,
      NodeFilter.SHOW_TEXT,
      null,
      false,
    );
    var node;
    while ((node = walker.nextNode())) {
      if (node.nodeValue.match(/apache\s*guacamole/i)) {
        node.nodeValue = node.nodeValue.replace(
          /apache\s*guacamole/gi,
          "CyberLab AttackBox",
        );
      }
      if (node.nodeValue.match(/guacamole/i)) {
        node.nodeValue = node.nodeValue.replace(/guacamole/gi, "CyberLab");
      }
    }
    // Also update document title
    if (document.title.match(/guacamole/i)) {
      document.title = document.title
        .replace(/apache\s*guacamole/gi, "CyberLab AttackBox")
        .replace(/guacamole/gi, "CyberLab");
    }
  }

  // Run on DOM ready and after any dynamic content loads
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", replaceBranding);
  } else {
    replaceBranding();
  }

  // Also observe for dynamic changes
  document.addEventListener("DOMContentLoaded", function () {
    var observer = new MutationObserver(function (mutations) {
      replaceBranding();
    });
    observer.observe(document.body, { childList: true, subtree: true });
  });

  // Handle logout/login page redirection
  // This prevents users from seeing the Guacamole login page when they log out
  function handleLogoutFlow() {
    if (window.location.hash.startsWith("#/login/")) {
      document.body.innerHTML =
        '<div style="background: #0a0a0a; color: #ff5722; height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; font-family: sans-serif; text-align: center; padding: 20px;">' +
        '<div style="margin-bottom: 30px;">' +
        '<svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18.36 6.64a9 9 0 1 1-12.73 0"></path><line x1="12" y1="2" x2="12" y2="12"></line></svg>' +
        "</div>" +
        '<h1 style="font-size: 28px; margin-bottom: 20px; letter-spacing: 2px; text-transform: uppercase;">Session Ended</h1>' +
        '<p style="color: #e0e0e0; margin-bottom: 40px; max-width: 400px; line-height: 1.5;">Your secure AttackBox session has been terminated. For security, please close this window.</p>' +
        '<button onclick="window.close()" style="background: #ff5722; color: #0a0a0a; border: none; padding: 15px 30px; border-radius: 4px; font-weight: bold; cursor: pointer; text-transform: uppercase; letter-spacing: 1px; transition: all 0.3s;">Close This Tab</button>' +
        '<p style="margin-top: 30px; font-size: 14px; color: #a0a0a0;">Return to Moodle to launch a new session when needed.</p>' +
        "</div>";

      // Also try to close the window automatically after a short delay
      // Note: browsers only allow window.close() on windows opened by script
      setTimeout(function () {
        window.close();
      }, 5000);
    }
  }

  window.addEventListener("hashchange", handleLogoutFlow);
  // Also check on initial load in case they bookmarked the login page or were redirected
  if (document.readyState === "complete") {
    handleLogoutFlow();
  } else {
    window.addEventListener("load", handleLogoutFlow);
  }
})();
