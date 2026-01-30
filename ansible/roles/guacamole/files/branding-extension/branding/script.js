(function () {
  // Set favicon
  var link =
    document.querySelector('link[rel="icon"]') ||
    document.createElement("link");
  link.rel = "icon";
  link.type = "image/png";
  link.href = "app/ext/cyberlab-branding/images/logo.png";
  document.head.appendChild(link);

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
