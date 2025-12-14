// This file is part of Moodle - http://moodle.org/
//
// Moodle is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Moodle is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Moodle.  If not, see <http://www.gnu.org/licenses/>.

/**
 * AttackBox Launcher AMD Module
 *
 * Renders a floating button and handles the session creation flow
 * with a cyberpunk-style loading overlay.
 *
 * @module     local_attackbox/launcher
 * @copyright  2024 CyberLab
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

define(["jquery", "core/str"], function ($, Str) {
  "use strict";

  /**
   * Progress messages mapped to percentage thresholds.
   */
  const PROGRESS_THRESHOLDS = [5, 10, 18, 25, 33, 42, 50, 62, 70, 85, 94, 100];

  /**
   * String keys needed for the UI.
   */
  const STRING_KEYS = [
    { key: "button:launch", component: "local_attackbox" },
    { key: "button:active", component: "local_attackbox" },
    { key: "button:terminate", component: "local_attackbox" },
    { key: "button:tooltip", component: "local_attackbox" },
    { key: "button:tooltip_active", component: "local_attackbox" },
    { key: "button:usage_dashboard", component: "local_attackbox" },
    { key: "timer:time_remaining", component: "local_attackbox" },
    { key: "overlay:title", component: "local_attackbox" },
    { key: "overlay:subtitle", component: "local_attackbox" },
    { key: "overlay:cancel", component: "local_attackbox" },
    { key: "error:title", component: "local_attackbox" },
    { key: "error:retry", component: "local_attackbox" },
    { key: "error:close", component: "local_attackbox" },
    { key: "success:title", component: "local_attackbox" },
    { key: "success:message", component: "local_attackbox" },
    { key: "success:open", component: "local_attackbox" },
    { key: "terminate:confirm", component: "local_attackbox" },
    { key: "terminate:success", component: "local_attackbox" },
    { key: "terminate:error", component: "local_attackbox" },
    { key: "progress:5", component: "local_attackbox" },
    { key: "progress:10", component: "local_attackbox" },
    { key: "progress:18", component: "local_attackbox" },
    { key: "progress:25", component: "local_attackbox" },
    { key: "progress:33", component: "local_attackbox" },
    { key: "progress:42", component: "local_attackbox" },
    { key: "progress:50", component: "local_attackbox" },
    { key: "progress:62", component: "local_attackbox" },
    { key: "progress:70", component: "local_attackbox" },
    { key: "progress:85", component: "local_attackbox" },
    { key: "progress:94", component: "local_attackbox" },
    { key: "progress:100", component: "local_attackbox" },
  ];

  /**
   * Launcher class
   */
  class AttackBoxLauncher {
    /**
     * Constructor
     * @param {Object} config Configuration object
     * @param {Object} strings Loaded strings
     */
    constructor(config, strings) {
      this.config = config;
      this.strings = strings;
      this.sessionId = null;
      this.pollTimer = null;
      this.isLaunching = false;
      this.hasActiveSession = false;
      this.activeSessionUrl = null;
      this.lastQuotaWarning = null; // Track last warning level shown
      this.currentUsageData = null; // Store latest usage data
      this.sessionExpiresAt = null; // Track when session expires
      this.timerInterval = null; // Timer update interval

      this.init();
    }

    /**
     * Initialize the launcher
     */
    init() {
      this.createButton();
      this.createOverlay();
      this.createNotificationBanner();
      this.createUsageDashboardLink();
      this.bindEvents();
      this.updateUsageDisplay();

      // Check for existing session after a short delay to ensure all is initialized
      setTimeout(() => {
        this.checkExistingSession().catch((err) => {
          console.log("Could not check for existing session:", err);
        });
      }, 100);

      // Update usage display every 30 seconds
      setInterval(() => this.updateUsageDisplay(), 30000);
    }

    /**
     * Check for existing session on page load
     */
    async checkExistingSession() {
      try {
        const tokenData = await this.getToken();
        // Use the correct endpoint: GET /students/{studentId}/sessions
        const response = await fetch(
          tokenData.api_url + "/students/" + this.config.userId + "/sessions",
          {
            method: "GET",
            headers: {
              "X-Moodle-Token": tokenData.token,
              Accept: "application/json",
            },
          }
        );

        if (!response.ok) {
          // No existing session or error - keep default state
          return;
        }

        const data = await response.json();

        // Check if there are any active sessions
        if (
          data.data &&
          data.data.active_sessions &&
          data.data.active_sessions.length > 0
        ) {
          // Get the first active session
          const session = data.data.active_sessions[0];

          // Found an active session - update UI without showing overlay
          this.sessionId = session.session_id;
          this.hasActiveSession = true;

          // Get connection URL - try multiple locations
          this.activeSessionUrl =
            session?.connection_info?.direct_url ||
            session?.connection_info?.guacamole_connection_url ||
            session?.connection_info?.guacamole_url ||
            session?.direct_url ||
            session?.guacamole_url ||
            session?.url ||
            session?.connection_url ||
            null;

          console.log("Session found on page load:", {
            sessionId: this.sessionId,
            status: session.status,
            hasUrl: !!this.activeSessionUrl,
            session: session,
          });

          // Check if session is ready with URL
          if (this.activeSessionUrl) {
            // Session is ready - update UI immediately
            this.$button.addClass("attackbox-btn-active");
            this.$button
              .find(".attackbox-btn-text")
              .text(this.strings.buttonTextActive);
            this.$button.attr("title", this.strings.buttonTooltipActive);

            // Show terminate button
            this.$terminateButton.show();
            console.log("Terminate button shown");

            // Start timer if expires_at available
            if (session.expires_at) {
              this.startSessionTimer(session.expires_at);
            }

            console.log("Existing session restored:", this.sessionId);
          } else if (
            session.status === "provisioning" ||
            session.status === "pending"
          ) {
            // Session exists but not ready yet - start polling to complete the launch
            console.log(
              "Session found but still provisioning, resuming polling..."
            );
            this.isLaunching = true;
            this.showOverlay();

            // Start polling to monitor session progress
            this.startPolling(tokenData.api_url);
          } else {
            // Session exists but in unexpected state
            console.warn(
              "Session found in unexpected state:",
              session.status,
              session
            );
          }
        }
      } catch (error) {
        console.log("No existing session found or error checking:", error);
        // Keep default state - no session
      }
    }

    /**
     * Create the floating button
     */
    createButton() {
      const position = this.config.buttonPosition || "bottom-right";
      const positionClasses = {
        "bottom-right": "attackbox-btn-bottom-right",
        "bottom-left": "attackbox-btn-bottom-left",
        "top-right": "attackbox-btn-top-right",
        "top-left": "attackbox-btn-top-left",
      };

      const html = `
                <div id="attackbox-launcher" class="attackbox-launcher ${positionClasses[position]}">
                    <div id="attackbox-usage-badge" class="attackbox-usage-badge" style="display: none;">
                        <span class="attackbox-usage-text"></span>
                    </div>
                    <button id="attackbox-btn" class="attackbox-btn" type="button" title="${this.strings.buttonTooltip}">
                        <span class="attackbox-btn-icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                                <line x1="8" y1="21" x2="16" y2="21"></line>
                                <line x1="12" y1="17" x2="12" y2="21"></line>
                                <path d="M7 8l3 3-3 3M12 14h4"></path>
                            </svg>
                        </span>
                        <span class="attackbox-btn-text">${this.strings.buttonText}</span>
                        <span class="attackbox-btn-pulse"></span>
                    </button>
                    <button id="attackbox-terminate-btn" class="attackbox-btn-terminate" type="button" title="${this.strings.buttonTerminate}" style="display: none;">
                        <span class="attackbox-btn-icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="12" r="10"/>
                                <line x1="15" y1="9" x2="9" y2="15"/>
                                <line x1="9" y1="9" x2="15" y2="15"/>
                            </svg>
                        </span>
                        <span class="attackbox-btn-text">${this.strings.buttonTerminate}</span>
                    </button>
                </div>
            `;

      $("body").append(html);
      this.$button = $("#attackbox-btn");
      this.$terminateButton = $("#attackbox-terminate-btn");
      this.$launcher = $("#attackbox-launcher");
      this.$timerBadge = $("#attackbox-timer-badge");
      this.$timerText = $("#attackbox-timer-text");
    }

    /**
     * Create notification banner for quota warnings
     */
    createNotificationBanner() {
      const html = `
        <div id="attackbox-quota-notification" class="attackbox-quota-notification" style="display: none;">
          <div class="attackbox-notification-content">
            <span class="attackbox-notification-icon">⚠️</span>
            <span id="attackbox-notification-message" class="attackbox-notification-message"></span>
            <button id="attackbox-notification-close" class="attackbox-notification-close" type="button">×</button>
          </div>
        </div>
      `;
      $("body").append(html);
      this.$notification = $("#attackbox-quota-notification");
      this.$notificationMessage = $("#attackbox-notification-message");

      // Close button handler
      $("#attackbox-notification-close").on("click", () => {
        this.$notification.fadeOut(300);
      });
    }

    /**
     * Create usage dashboard link
     */
    createUsageDashboardLink() {
      const html = `
        <a href="${M.cfg.wwwroot}/local/attackbox/usage.php" 
           id="attackbox-usage-link" 
           class="attackbox-usage-link" 
           title="${this.strings.buttonUsageDashboard}"
           target="_blank">
          <span class="attackbox-usage-link-icon">📊</span>
          <span class="attackbox-usage-link-text">Usage</span>
        </a>
      `;
      this.$launcher.append(html);
    }

    /**
     * Create the fullscreen overlay
     */
    createOverlay() {
      const html = `
                <div id="attackbox-overlay" class="attackbox-overlay" style="display: none;">
                    <div class="attackbox-overlay-scanlines"></div>
                    <div class="attackbox-overlay-content">
                        <div class="attackbox-overlay-header">
                            <div class="attackbox-overlay-logo">
                                <svg viewBox="0 0 100 100" class="attackbox-logo-svg">
                                    <circle cx="50" cy="50" r="45" fill="none" stroke="currentColor" stroke-width="2" opacity="0.3"/>
                                    <circle cx="50" cy="50" r="35" fill="none" stroke="currentColor" stroke-width="1" opacity="0.5"/>
                                    <path d="M50 20 L50 80 M20 50 L80 50" stroke="currentColor" stroke-width="1" opacity="0.3"/>
                                    <circle cx="50" cy="50" r="8" fill="currentColor" class="attackbox-logo-core"/>
                                    <path d="M30 30 L50 50 L70 30" fill="none" stroke="currentColor" stroke-width="2" class="attackbox-logo-arrow"/>
                                </svg>
                            </div>
                            <h1 class="attackbox-overlay-title">${this.strings.overlayTitle}</h1>
                            <p class="attackbox-overlay-subtitle">${this.strings.overlaySubtitle}</p>
                        </div>

                        <div class="attackbox-progress-container">
                            <div class="attackbox-progress-bar">
                                <div class="attackbox-progress-fill" id="attackbox-progress-fill"></div>
                                <div class="attackbox-progress-glow"></div>
                            </div>
                            <div class="attackbox-progress-text">
                                <span id="attackbox-progress-percent">0%</span>
                            </div>
                        </div>

                        <div class="attackbox-status-container">
                            <div class="attackbox-terminal">
                                <div class="attackbox-terminal-header">
                                    <span class="attackbox-terminal-dot red"></span>
                                    <span class="attackbox-terminal-dot yellow"></span>
                                    <span class="attackbox-terminal-dot green"></span>
                                    <span class="attackbox-terminal-title">cyberlynk@lynkbox:~$</span>
                                </div>
                                <div class="attackbox-terminal-body">
                                    <div id="attackbox-status-message" class="attackbox-status-message">
                                        <span class="attackbox-cursor">▋</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="attackbox-actions">
                            <button id="attackbox-cancel" class="attackbox-btn-cancel" type="button">
                                ${this.strings.cancelButton}
                            </button>
                        </div>
                    </div>

                    <!-- Success state -->
                    <div id="attackbox-success" class="attackbox-success-container" style="display: none;">
                        <div class="attackbox-success-icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="12" r="10"/>
                                <path d="M8 12l2 2 4-4"/>
                            </svg>
                        </div>
                        <h2 class="attackbox-success-title">${this.strings.successTitle}</h2>
                        <p class="attackbox-success-message">${this.strings.successMessage}</p>
                        <button id="attackbox-open" class="attackbox-btn-success" type="button">
                            ${this.strings.successOpen}
                        </button>
                    </div>

                    <!-- Error state -->
                    <div id="attackbox-error" class="attackbox-error-container" style="display: none;">
                        <div class="attackbox-error-icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="12" r="10"/>
                                <line x1="15" y1="9" x2="9" y2="15"/>
                                <line x1="9" y1="9" x2="15" y2="15"/>
                            </svg>
                        </div>
                        <h2 class="attackbox-error-title">${this.strings.errorTitle}</h2>
                        <p id="attackbox-error-message" class="attackbox-error-message"></p>
                        <div class="attackbox-error-actions">
                            <button id="attackbox-retry" class="attackbox-btn-retry" type="button">
                                ${this.strings.errorRetry}
                            </button>
                            <button id="attackbox-close-error" class="attackbox-btn-close" type="button">
                                ${this.strings.errorClose}
                            </button>
                        </div>
                    </div>
                </div>
            `;

      $("body").append(html);
      this.$overlay = $("#attackbox-overlay");
      this.$progressFill = $("#attackbox-progress-fill");
      this.$progressPercent = $("#attackbox-progress-percent");
      this.$statusMessage = $("#attackbox-status-message");
      this.$successContainer = $("#attackbox-success");
      this.$errorContainer = $("#attackbox-error");
      this.$overlayContent = this.$overlay.find(".attackbox-overlay-content");
    }

    /**
     * Bind event handlers
     */
    bindEvents() {
      const self = this;

      this.$button.on("click", function (e) {
        e.preventDefault();
        if (self.hasActiveSession && self.activeSessionUrl) {
          window.open(self.activeSessionUrl, "_blank", "noopener");
        } else {
          self.launch();
        }
      });

      this.$terminateButton.on("click", function (e) {
        e.preventDefault();
        self.terminateSession();
      });

      $("#attackbox-cancel").on("click", function (e) {
        e.preventDefault();
        self.cancel();
      });

      $("#attackbox-retry").on("click", function (e) {
        e.preventDefault();
        self.hideError();
        self.launch();
      });

      $("#attackbox-close-error").on("click", function (e) {
        e.preventDefault();
        self.hideOverlay();
      });

      $("#attackbox-open").on("click", function (e) {
        e.preventDefault();
        if (self.activeSessionUrl) {
          window.open(self.activeSessionUrl, "_blank", "noopener");
        }
        self.hideOverlay();
      });

      // ESC key to cancel
      $(document).on("keydown.attackbox", function (e) {
        if (e.key === "Escape" && self.$overlay.is(":visible")) {
          self.cancel();
        }
      });
    }

    /**
     * Launch the AttackBox
     */
    async launch() {
      if (this.isLaunching) {
        return;
      }

      // Check quota before launching
      if (!this.checkQuotaBeforeLaunch()) {
        return;
      }

      this.isLaunching = true;
      this.showOverlay();
      this.updateProgress(0, this.strings.progress5);

      try {
        // Step 1: Get token from Moodle
        this.updateProgress(5, this.strings.progress5);
        const tokenData = await this.getToken();

        // Step 2: Create session
        this.updateProgress(10, this.strings.progress10);
        const sessionData = await this.createSession(
          tokenData.token,
          tokenData.api_url
        );

        // API returns { success, message, data, timestamp }
        const session = sessionData.data || sessionData.body || sessionData;

        if (!session || !session.session_id) {
          throw new Error(sessionData.message || "Invalid response from API");
        }

        this.sessionId = session.session_id;

        // Check session status regardless of whether it was reused
        if (session.status === "ready" || session.status === "active") {
          // Session is ready to use
          if (session.reused) {
            this.handleExistingSession(session);
          } else {
            this.handleReady(session);
          }
        } else {
          // Session is still provisioning - start polling
          if (session.reused) {
            this.updateProgress(
              25,
              "Waiting for existing session to be ready..."
            );
          }
          this.startPolling(tokenData.api_url);
        }
      } catch (error) {
        console.error("LynkBox launch error:", error);
        this.showError(error.message || "Failed to launch LynkBox");
      }
    }

    /**
     * Get authentication token from Moodle
     */
    async getToken() {
      const response = await fetch(
        this.config.tokenEndpoint + "?sesskey=" + this.config.sesskey,
        {
          method: "GET",
          credentials: "same-origin",
          headers: {
            Accept: "application/json",
          },
        }
      );

      if (!response.ok) {
        throw new Error("Failed to get authentication token");
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || "Token generation failed");
      }

      return data;
    }

    /**
     * Create a session via the orchestrator API
     */
    async createSession(token, apiUrl) {
      const response = await fetch(apiUrl + "/sessions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Moodle-Token": token,
        },
        body: JSON.stringify({
          student_id: String(this.config.userId),
          student_name: this.config.userFullname,
          metadata: {
            source: "moodle_attackbox_plugin",
            page_url: window.location.href,
          },
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.log("API error response:", errorData);

        // Handle quota exceeded error (403)
        // Check errorData.details (Lambda response structure)
        const quotaData = errorData.details || errorData.data || errorData;
        if (response.status === 403 && quotaData.error === "quota_exceeded") {
          const hoursUsed =
            Math.round((quotaData.consumed_minutes / 60) * 10) / 10;
          const hoursLimit =
            Math.round((quotaData.quota_minutes / 60) * 10) / 10;
          const resetDate = new Date(quotaData.resets_at).toLocaleDateString();

          throw new Error(
            `Monthly usage limit reached!<br><br>` +
              `<strong>Plan:</strong> ${quotaData.plan || "Freemium"}<br>` +
              `<strong>Used:</strong> ${hoursUsed}h / ${hoursLimit}h<br><br>` +
              `Your quota resets on <strong>${resetDate}</strong>.<br><br>` +
              `<a href="/local/attackbox/upgrade.php" style="color: #00ff88; text-decoration: underline;">Upgrade your plan</a> for more hours.`
          );
        }

        throw new Error(
          errorData.error ||
            errorData.message ||
            `API error: ${response.status}`
        );
      }

      return await response.json();
    }

    /**
     * Start polling for session status
     */
    startPolling(apiUrl) {
      const self = this;
      const pollInterval = this.config.pollInterval || 3000;
      let attempts = 0;
      const maxAttempts = 120; // 6 minutes max

      this.pollTimer = setInterval(async function () {
        attempts++;

        if (attempts > maxAttempts) {
          self.stopPolling();
          self.showError("Session creation timed out. Please try again.");
          return;
        }

        try {
          const response = await fetch(apiUrl + "/sessions/" + self.sessionId, {
            method: "GET",
            headers: {
              Accept: "application/json",
            },
          });

          if (!response.ok) {
            throw new Error("Failed to get session status");
          }

          const data = await response.json();
          // API returns { success, message, data, timestamp }
          const session = data.data || data.body || data;

          if (!session || !session.session_id) {
            return;
          }

          // Update progress based on API response
          const progress =
            session.progress || self.estimateProgress(session.status, attempts);
          const message = self.getProgressMessage(progress);
          self.updateProgress(progress, message);

          if (session.status === "ready" || session.status === "active") {
            self.stopPolling();
            self.handleReady(session);
          } else if (
            session.status === "error" ||
            session.status === "terminated"
          ) {
            self.stopPolling();
            self.showError(session.error || "Session failed to start");
          }
        } catch (error) {
          console.error("Polling error:", error);
          // Continue polling on transient errors
        }
      }, pollInterval);
    }

    /**
     * Stop polling
     */
    stopPolling() {
      if (this.pollTimer) {
        clearInterval(this.pollTimer);
        this.pollTimer = null;
      }
    }

    /**
     * Estimate progress based on status when API doesn't return it
     */
    estimateProgress(status, attempts) {
      const baseProgress = {
        pending: 10,
        provisioning: 25,
        ready: 100,
        active: 100,
      };

      let progress = baseProgress[status] || 10;

      // Add some progress based on time
      if (status === "provisioning") {
        progress = Math.min(94, 25 + attempts * 2);
      }

      return progress;
    }

    /**
     * Get progress message for a given percentage
     */
    getProgressMessage(progress) {
      // Find the highest threshold that progress meets or exceeds
      const thresholds = PROGRESS_THRESHOLDS.slice().sort((a, b) => b - a);

      for (const threshold of thresholds) {
        if (progress >= threshold) {
          const key = "progress" + threshold;
          return this.strings[key] || "Processing...";
        }
      }

      return this.strings.progress5 || "Initializing...";
    }

    /**
     * Handle existing session
     */
    handleExistingSession(session) {
      this.isLaunching = false;
      this.hasActiveSession = true;

      console.log("Full session object:", session);

      // Verify session is actually ready
      if (session.status !== "ready" && session.status !== "active") {
        console.warn("Session not ready yet, status:", session.status);
        this.showError(
          `Session is ${session.status}. Please wait a moment and try again.`
        );
        return;
      }

      // Try multiple possible URL locations
      this.activeSessionUrl =
        session?.connection_info?.direct_url ||
        session?.connection_info?.guacamole_connection_url ||
        session?.direct_url ||
        session?.guacamole_url ||
        session?.url ||
        session?.connection_url ||
        null;

      console.log("Existing session found, URL:", this.activeSessionUrl);

      if (this.activeSessionUrl) {
        this.updateProgress(100, this.strings.progress100);

        // Update button state
        this.$button.addClass("attackbox-btn-active");
        this.$button
          .find(".attackbox-btn-text")
          .text(this.strings.buttonTextActive);
        this.$button.attr("title", this.strings.buttonTooltipActive);
        this.$terminateButton.show();

        // Start session timer if expires_at available
        if (session.expires_at) {
          this.startSessionTimer(session.expires_at);
        }

        setTimeout(() => {
          this.showSuccess();
        }, 500);
      } else {
        console.error("No connection URL in session:", session);
        console.error("Available keys:", Object.keys(session));
        this.showError(
          "Session found but no connection URL available. Please check CloudWatch logs or try terminating and creating a new session."
        );
      }
    }

    /**
     * Handle ready state
     */
    handleReady(session) {
      this.isLaunching = false;
      this.hasActiveSession = true;

      console.log("Full session object (ready):", session);

      // Try multiple possible URL locations
      this.activeSessionUrl =
        session?.connection_info?.direct_url ||
        session?.connection_info?.guacamole_connection_url ||
        session?.direct_url ||
        session?.guacamole_url ||
        session?.url ||
        session?.connection_url ||
        null;

      console.log("LynkBox ready, URL:", this.activeSessionUrl);

      if (this.activeSessionUrl) {
        this.updateProgress(100, this.strings.progress100);

        // Update button state
        this.$button.addClass("attackbox-btn-active");
        this.$button
          .find(".attackbox-btn-text")
          .text(this.strings.buttonTextActive);
        this.$button.attr("title", this.strings.buttonTooltipActive);
        this.$terminateButton.show();

        // Start session timer if expires_at available
        if (session.expires_at) {
          this.startSessionTimer(session.expires_at);
        }

        // Show success then open window
        setTimeout(() => {
          this.showSuccess();
        }, 500);
      } else {
        console.error("No connection URL in session:", session);
        console.error("Available keys:", Object.keys(session));
        this.showError(
          "LynkBox is ready but no connection URL available. Please check CloudWatch logs or contact support."
        );
      }
    }

    /**
     * Update progress display
     */
    updateProgress(percent, message) {
      this.$progressFill.css("width", percent + "%");
      this.$progressPercent.text(percent + "%");

      if (message) {
        this.typeMessage(message);
      }
    }

    /**
     * Type out a message with typewriter effect
     */
    typeMessage(message) {
      const $container = this.$statusMessage;
      $container.html(
        '<span class="attackbox-typed"></span><span class="attackbox-cursor">▋</span>'
      );

      const $typed = $container.find(".attackbox-typed");
      let index = 0;

      const type = () => {
        if (index < message.length) {
          $typed.text($typed.text() + message[index]);
          index++;
          setTimeout(type, 20);
        }
      };

      type();
    }

    /**
     * Show the overlay
     */
    showOverlay() {
      this.$overlay.fadeIn(300);
      this.$overlayContent.show();
      this.$successContainer.hide();
      this.$errorContainer.hide();
      $("body").addClass("attackbox-overlay-open");
    }

    /**
     * Hide the overlay
     */
    hideOverlay() {
      this.$overlay.fadeOut(300);
      $("body").removeClass("attackbox-overlay-open");
      this.isLaunching = false;
    }

    /**
     * Show success state
     */
    showSuccess() {
      this.$overlayContent.fadeOut(200, () => {
        this.$successContainer.fadeIn(200);
      });
    }

    /**
     * Show error state
     */
    /**
     * Update usage display badge
     */
    async updateUsageDisplay() {
      try {
        const response = await fetch(
          M.cfg.wwwroot +
            "/local/attackbox/ajax/get_usage.php?sesskey=" +
            this.config.sesskey,
          {
            method: "GET",
            credentials: "same-origin",
            headers: {
              Accept: "application/json",
            },
          }
        );

        if (!response.ok) {
          console.warn("Failed to fetch usage data");
          return;
        }

        const data = await response.json();

        if (!data.success) {
          console.warn("Usage data error:", data.message);
          return;
        }

        // Store current usage data
        this.currentUsageData = data;

        // Check for quota warnings
        this.checkQuotaWarnings(data);

        // Update the badge
        const $badge = $("#attackbox-usage-badge");
        const $badgeText = $badge.find(".attackbox-usage-text");

        if (data.hours_limit === "Unlimited") {
          $badgeText.html(`<strong>${data.plan}:</strong> Unlimited`);
          $badge
            .removeClass("usage-low usage-medium usage-high")
            .addClass("usage-unlimited");
        } else {
          $badgeText.html(
            `<strong>${data.plan}:</strong> ${data.hours_used}h / ${data.hours_limit}h ` +
              `<span class="usage-remaining">(${data.hours_remaining}h left)</span>`
          );

          // Color coding based on percentage
          $badge.removeClass(
            "usage-low usage-medium usage-high usage-unlimited"
          );
          if (data.percentage >= 90) {
            $badge.addClass("usage-high");
          } else if (data.percentage >= 70) {
            $badge.addClass("usage-medium");
          } else {
            $badge.addClass("usage-low");
          }
        }

        $badge.fadeIn(300);
      } catch (error) {
        console.error("Error updating usage display:", error);
      }
    }

    /**
     * Check quota levels and show warnings
     */
    checkQuotaWarnings(data) {
      // Skip if unlimited plan
      if (data.hours_limit === "Unlimited" || data.percentage === undefined) {
        return;
      }

      const percentage = data.percentage;
      let warningLevel = null;
      let message = "";

      // Determine warning level
      if (percentage >= 100) {
        warningLevel = "critical";
        message = `<strong>Quota Exhausted!</strong> You've used all ${data.hours_limit}h of your ${data.plan} plan. Quota resets ${data.reset_date}.`;
      } else if (percentage >= 90) {
        warningLevel = "high";
        message = `<strong>Low on Time!</strong> Only ${data.hours_remaining}h remaining of your ${data.hours_limit}h ${data.plan} quota.`;
      } else if (percentage >= 80) {
        warningLevel = "medium";
        message = `<strong>Heads up!</strong> You've used ${data.hours_used}h of ${data.hours_limit}h. ${data.hours_remaining}h remaining.`;
      }

      // Show notification if warning level changed
      if (warningLevel && warningLevel !== this.lastQuotaWarning) {
        this.showQuotaWarning(message, warningLevel);
        this.lastQuotaWarning = warningLevel;
      }
    }

    /**
     * Show quota warning notification
     */
    showQuotaWarning(message, level) {
      this.$notificationMessage.html(message);
      this.$notification
        .removeClass("warning-medium warning-high warning-critical")
        .addClass(`warning-${level}`);
      this.$notification.fadeIn(300);

      // Auto-hide medium warnings after 10 seconds
      if (level === "medium") {
        setTimeout(() => {
          this.$notification.fadeOut(300);
        }, 10000);
      }
      // Keep high/critical warnings visible
    }

    /**
     * Check quota before launching
     */
    checkQuotaBeforeLaunch() {
      if (!this.currentUsageData) {
        return true; // No data yet, allow launch
      }

      const data = this.currentUsageData;

      // Check if quota exhausted
      if (data.hours_limit !== "Unlimited" && data.percentage >= 100) {
        this.showError(
          `Monthly usage limit reached!<br><br>` +
            `<strong>Plan:</strong> ${data.plan}<br>` +
            `<strong>Used:</strong> ${data.hours_used}h / ${data.hours_limit}h<br><br>` +
            `Your quota resets on <strong>${data.reset_date}</strong>.<br><br>` +
            `<a href="/local/attackbox/upgrade.php" style="color: #00ff88; text-decoration: underline;">Upgrade your plan</a> for more hours.`
        );
        return false;
      }

      // Warn if very low (< 10 minutes remaining)
      if (data.hours_limit !== "Unlimited" && data.minutes_remaining < 10) {
        const confirmMsg = `You only have ${data.minutes_remaining} minutes remaining in your quota. Continue?`;
        return confirm(confirmMsg);
      }

      return true;
    }

    /**
     * Show error message
     */
    showError(message) {
      this.isLaunching = false;
      $("#attackbox-error-message").html(message); // Changed from .text() to .html() to support HTML errors
      this.$overlayContent.fadeOut(200, () => {
        this.$errorContainer.fadeIn(200);
      });
    }

    /**
     * Hide error state
     */
    hideError() {
      this.$errorContainer.hide();
      this.$overlayContent.show();
      this.updateProgress(0, "");
    }

    /**
     * Cancel the launch
     */
    cancel() {
      this.stopPolling();
      this.isLaunching = false;
      this.hideOverlay();
    }

    /**
     * Start session timer countdown
     * @param {string} expiresAt ISO 8601 timestamp when session expires
     */
    startSessionTimer(expiresAt) {
      this.sessionExpiresAt = new Date(expiresAt);
      this.stopSessionTimer(); // Clear any existing timer

      // Update immediately
      this.updateTimerDisplay();

      // Update every second
      this.timerInterval = setInterval(() => {
        this.updateTimerDisplay();
      }, 1000);

      // Show timer badge
      this.$timerBadge.fadeIn(300);
    }

    /**
     * Stop session timer
     */
    stopSessionTimer() {
      if (this.timerInterval) {
        clearInterval(this.timerInterval);
        this.timerInterval = null;
      }
      this.sessionExpiresAt = null;
      this.$timerBadge.fadeOut(300);
    }

    /**
     * Update timer display
     */
    updateTimerDisplay() {
      if (!this.sessionExpiresAt) {
        return;
      }

      const now = new Date();
      const remaining = this.sessionExpiresAt - now;

      if (remaining <= 0) {
        // Session expired
        this.$timerText.text("Expired");
        this.$timerBadge.addClass("timer-expired");
        this.stopSessionTimer();

        // Auto-terminate expired session
        setTimeout(() => {
          this.sessionId = null;
          this.hasActiveSession = false;
          this.activeSessionUrl = null;
          this.$button.removeClass("attackbox-btn-active");
          this.$button
            .find(".attackbox-btn-text")
            .text(this.strings.buttonText);
          this.$button.attr("title", this.strings.buttonTooltip);
          this.$terminateButton.hide();
          alert("Your session has expired. Please launch a new session.");
        }, 2000);
        return;
      }

      // Calculate hours and minutes
      const totalMinutes = Math.floor(remaining / (1000 * 60));
      const hours = Math.floor(totalMinutes / 60);
      const minutes = totalMinutes % 60;

      // Format display
      let timeText;
      if (hours > 0) {
        timeText = `${hours}h ${minutes}m`;
      } else {
        timeText = `${minutes}m`;
      }

      this.$timerText.text(timeText);

      // Color coding based on time remaining
      this.$timerBadge.removeClass(
        "timer-low timer-medium timer-high timer-expired"
      );
      if (totalMinutes <= 5) {
        this.$timerBadge.addClass("timer-low");
      } else if (totalMinutes <= 15) {
        this.$timerBadge.addClass("timer-medium");
      } else {
        this.$timerBadge.addClass("timer-high");
      }
    }

    /**
     * Terminate the current session
     */
    async terminateSession() {
      if (!this.sessionId) {
        console.warn("No session ID to terminate");
        return;
      }

      // Confirm termination
      if (!confirm(this.strings.terminateConfirm)) {
        return;
      }

      try {
        // Show loading state on button
        const $btnText = this.$terminateButton.find(".attackbox-btn-text");
        const originalText = $btnText.text();
        this.$terminateButton.prop("disabled", true);
        this.$terminateButton.css("opacity", "0.6");
        $btnText.html('<span class="spinner"></span> Ending...');

        // Get token first
        const tokenData = await this.getToken();

        // Call terminate endpoint
        const response = await fetch(
          tokenData.api_url + "/sessions/" + this.sessionId,
          {
            method: "DELETE",
            headers: {
              "X-Moodle-Token": tokenData.token,
              Accept: "application/json",
            },
          }
        );

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(
            errorData.message ||
              `Failed to terminate session: ${response.status}`
          );
        }

        // Success - reset state
        this.sessionId = null;
        this.hasActiveSession = false;
        this.activeSessionUrl = null;

        // Stop timer
        this.stopSessionTimer();

        // Update UI
        this.$button.removeClass("attackbox-btn-active");
        this.$button.find(".attackbox-btn-text").text(this.strings.buttonText);
        this.$button.attr("title", this.strings.buttonTooltip);
        this.$terminateButton.hide();
        this.$terminateButton.prop("disabled", false);
        this.$terminateButton.css("opacity", "1");

        // Show success message
        alert(this.strings.terminateSuccess);
      } catch (error) {
        console.error("Terminate session error:", error);

        // Restore button state on error
        this.$terminateButton.prop("disabled", false);
        this.$terminateButton.css("opacity", "1");
        this.$terminateButton
          .find(".attackbox-btn-text")
          .text(this.strings.buttonTerminate);

        alert(this.strings.terminateError + ": " + error.message);
      }
    }
  }

  /**
   * Load all required strings from Moodle.
   * @returns {Promise<Object>} Promise resolving to strings object
   */
  const loadStrings = function () {
    return Str.get_strings(STRING_KEYS).then(function (results) {
      const strings = {};
      const keyNames = [
        "buttonText",
        "buttonTextActive",
        "buttonTerminate",
        "buttonTooltip",
        "buttonTooltipActive",
        "buttonUsageDashboard",
        "timerTimeRemaining",
        "overlayTitle",
        "overlaySubtitle",
        "cancelButton",
        "errorTitle",
        "errorRetry",
        "errorClose",
        "successTitle",
        "successMessage",
        "successOpen",
        "terminateConfirm",
        "terminateSuccess",
        "terminateError",
        "progress5",
        "progress10",
        "progress18",
        "progress25",
        "progress33",
        "progress42",
        "progress50",
        "progress62",
        "progress70",
        "progress85",
        "progress94",
        "progress100",
      ];
      keyNames.forEach(function (key, index) {
        strings[key] = results[index];
      });
      return strings;
    });
  };

  return {
    /**
     * Initialize the launcher
     * @param {Object} config Configuration object
     */
    init: function (config) {
      // Wait for DOM ready and strings to load
      $(document).ready(function () {
        loadStrings()
          .then(function (strings) {
            new AttackBoxLauncher(config, strings);
          })
          .catch(function (error) {
            console.error("Failed to load LynkBox strings:", error);
          });
      });
    },
  };
});
