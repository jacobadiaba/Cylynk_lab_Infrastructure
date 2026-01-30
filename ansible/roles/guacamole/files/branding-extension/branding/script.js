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
})();
