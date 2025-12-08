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

define(['jquery', 'core/str'], function($, Str) {
    'use strict';

    /**
     * Progress messages mapped to percentage thresholds.
     */
    const PROGRESS_THRESHOLDS = [5, 10, 18, 25, 33, 42, 50, 62, 70, 85, 94, 100];

    /**
     * String keys needed for the UI.
     */
    const STRING_KEYS = [
        {key: 'button:launch', component: 'local_attackbox'},
        {key: 'button:active', component: 'local_attackbox'},
        {key: 'button:terminate', component: 'local_attackbox'},
        {key: 'button:tooltip', component: 'local_attackbox'},
        {key: 'button:tooltip_active', component: 'local_attackbox'},
        {key: 'overlay:title', component: 'local_attackbox'},
        {key: 'overlay:subtitle', component: 'local_attackbox'},
        {key: 'overlay:cancel', component: 'local_attackbox'},
        {key: 'error:title', component: 'local_attackbox'},
        {key: 'error:retry', component: 'local_attackbox'},
        {key: 'error:close', component: 'local_attackbox'},
        {key: 'success:title', component: 'local_attackbox'},
        {key: 'success:message', component: 'local_attackbox'},
        {key: 'success:open', component: 'local_attackbox'},
        {key: 'terminate:confirm', component: 'local_attackbox'},
        {key: 'terminate:success', component: 'local_attackbox'},
        {key: 'terminate:error', component: 'local_attackbox'},
        {key: 'progress:5', component: 'local_attackbox'},
        {key: 'progress:10', component: 'local_attackbox'},
        {key: 'progress:18', component: 'local_attackbox'},
        {key: 'progress:25', component: 'local_attackbox'},
        {key: 'progress:33', component: 'local_attackbox'},
        {key: 'progress:42', component: 'local_attackbox'},
        {key: 'progress:50', component: 'local_attackbox'},
        {key: 'progress:62', component: 'local_attackbox'},
        {key: 'progress:70', component: 'local_attackbox'},
        {key: 'progress:85', component: 'local_attackbox'},
        {key: 'progress:94', component: 'local_attackbox'},
        {key: 'progress:100', component: 'local_attackbox'},
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

            this.init();
        }

        /**
         * Initialize the launcher
         */
        init() {
            this.createButton();
            this.createOverlay();
            this.bindEvents();
        }

        /**
         * Create the floating button
         */
        createButton() {
            const position = this.config.buttonPosition || 'bottom-right';
            const positionClasses = {
                'bottom-right': 'attackbox-btn-bottom-right',
                'bottom-left': 'attackbox-btn-bottom-left',
                'top-right': 'attackbox-btn-top-right',
                'top-left': 'attackbox-btn-top-left'
            };

            const html = `
                <div id="attackbox-launcher" class="attackbox-launcher ${positionClasses[position]}">
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

            $('body').append(html);
            this.$button = $('#attackbox-btn');
            this.$terminateButton = $('#attackbox-terminate-btn');
            this.$launcher = $('#attackbox-launcher');
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

            $('body').append(html);
            this.$overlay = $('#attackbox-overlay');
            this.$progressFill = $('#attackbox-progress-fill');
            this.$progressPercent = $('#attackbox-progress-percent');
            this.$statusMessage = $('#attackbox-status-message');
            this.$successContainer = $('#attackbox-success');
            this.$errorContainer = $('#attackbox-error');
            this.$overlayContent = this.$overlay.find('.attackbox-overlay-content');
        }

        /**
         * Bind event handlers
         */
        bindEvents() {
            const self = this;

            this.$button.on('click', function(e) {
                e.preventDefault();
                if (self.hasActiveSession && self.activeSessionUrl) {
                    window.open(self.activeSessionUrl, '_blank', 'noopener');
                } else {
                    self.launch();
                }
            });

            this.$terminateButton.on('click', function(e) {
                e.preventDefault();
                self.terminateSession();
            });

            $('#attackbox-cancel').on('click', function(e) {
                e.preventDefault();
                self.cancel();
            });

            $('#attackbox-retry').on('click', function(e) {
                e.preventDefault();
                self.hideError();
                self.launch();
            });

            $('#attackbox-close-error').on('click', function(e) {
                e.preventDefault();
                self.hideOverlay();
            });

            $('#attackbox-open').on('click', function(e) {
                e.preventDefault();
                if (self.activeSessionUrl) {
                    window.open(self.activeSessionUrl, '_blank', 'noopener');
                }
                self.hideOverlay();
            });

            // ESC key to cancel
            $(document).on('keydown.attackbox', function(e) {
                if (e.key === 'Escape' && self.$overlay.is(':visible')) {
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

            this.isLaunching = true;
            this.showOverlay();
            this.updateProgress(0, this.strings.progress5);

            try {
                // Step 1: Get token from Moodle
                this.updateProgress(5, this.strings.progress5);
                const tokenData = await this.getToken();

                // Step 2: Create session
                this.updateProgress(10, this.strings.progress10);
                const sessionData = await this.createSession(tokenData.token, tokenData.api_url);

                // API returns { success, message, data, timestamp }
                const session = sessionData.data || sessionData.body || sessionData;

                if (!session || !session.session_id) {
                    throw new Error(sessionData.message || 'Invalid response from API');
                }

                if (session.reused) {
                    // Existing session found
                    this.handleExistingSession(session);
                    return;
                }

                this.sessionId = session.session_id;

                if (session.status === 'ready') {
                    // Already ready (warm pool)
                    this.handleReady(session);
                } else {
                    // Start polling
                    this.startPolling(tokenData.api_url);
                }

            } catch (error) {
                console.error('LynkBox launch error:', error);
                this.showError(error.message || 'Failed to launch LynkBox');
            }
        }

        /**
         * Get authentication token from Moodle
         */
        async getToken() {
            const response = await fetch(this.config.tokenEndpoint + '?sesskey=' + this.config.sesskey, {
                method: 'GET',
                credentials: 'same-origin',
                headers: {
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error('Failed to get authentication token');
            }

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.error || 'Token generation failed');
            }

            return data;
        }

        /**
         * Create a session via the orchestrator API
         */
        async createSession(token, apiUrl) {
            const response = await fetch(apiUrl + '/sessions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Moodle-Token': token
                },
                body: JSON.stringify({
                    student_id: String(this.config.userId),
                    student_name: this.config.userFullname,
                    metadata: {
                        source: 'moodle_attackbox_plugin',
                        page_url: window.location.href
                    }
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `API error: ${response.status}`);
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

            this.pollTimer = setInterval(async function() {
                attempts++;

                if (attempts > maxAttempts) {
                    self.stopPolling();
                    self.showError('Session creation timed out. Please try again.');
                    return;
                }

                try {
                    const response = await fetch(apiUrl + '/sessions/' + self.sessionId, {
                        method: 'GET',
                        headers: {
                            'Accept': 'application/json'
                        }
                    });

                    if (!response.ok) {
                        throw new Error('Failed to get session status');
                    }

                    const data = await response.json();
                    // API returns { success, message, data, timestamp }
                    const session = data.data || data.body || data;

                    if (!session || !session.session_id) {
                        return;
                    }

                    // Update progress based on API response
                    const progress = session.progress || self.estimateProgress(session.status, attempts);
                    const message = self.getProgressMessage(progress);
                    self.updateProgress(progress, message);

                    if (session.status === 'ready' || session.status === 'active') {
                        self.stopPolling();
                        self.handleReady(session);
                    } else if (session.status === 'error' || session.status === 'terminated') {
                        self.stopPolling();
                        self.showError(session.error || 'Session failed to start');
                    }

                } catch (error) {
                    console.error('Polling error:', error);
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
                'pending': 10,
                'provisioning': 25,
                'ready': 100,
                'active': 100
            };

            let progress = baseProgress[status] || 10;

            // Add some progress based on time
            if (status === 'provisioning') {
                progress = Math.min(94, 25 + (attempts * 2));
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
                    const key = 'progress' + threshold;
                    return this.strings[key] || 'Processing...';
                }
            }

            return this.strings.progress5 || 'Initializing...';
        }

        /**
         * Handle existing session
         */
        handleExistingSession(session) {
            this.isLaunching = false;
            this.hasActiveSession = true;

            // Try multiple possible URL locations
            this.activeSessionUrl = null;
            if (session.connection_info) {
                this.activeSessionUrl = session.connection_info.direct_url ||
                                        session.connection_info.guacamole_connection_url;
            }
            if (!this.activeSessionUrl) {
                this.activeSessionUrl = session.direct_url;
            }

            console.log('Existing session found, URL:', this.activeSessionUrl);

            if (this.activeSessionUrl) {
                this.updateProgress(100, this.strings.progress100);

                // Update button state
                this.$button.addClass('attackbox-btn-active');
                this.$button.find('.attackbox-btn-text').text(this.strings.buttonTextActive);
                this.$button.attr('title', this.strings.buttonTooltipActive);
                this.$terminateButton.show();

                setTimeout(() => {
                    this.showSuccess();
                }, 500);
            } else {
                console.error('No connection URL in session:', session);
                this.showError('Session found but no connection URL available. Check console for details.');
            }
        }

        /**
         * Handle ready state
         */
        handleReady(session) {
            this.isLaunching = false;
            this.hasActiveSession = true;

            // Try multiple possible URL locations
            this.activeSessionUrl = null;
            if (session.connection_info) {
                this.activeSessionUrl = session.connection_info.direct_url ||
                                        session.connection_info.guacamole_connection_url;
            }
            if (!this.activeSessionUrl) {
                this.activeSessionUrl = session.direct_url;
            }

            console.log('LynkBox ready, URL:', this.activeSessionUrl);

            if (this.activeSessionUrl) {
                this.updateProgress(100, this.strings.progress100);

                // Update button state
                this.$button.addClass('attackbox-btn-active');
                this.$button.find('.attackbox-btn-text').text(this.strings.buttonTextActive);
                this.$button.attr('title', this.strings.buttonTooltipActive);
                this.$terminateButton.show();

                // Show success then open window
                setTimeout(() => {
                    this.showSuccess();
                }, 500);
            } else {
                console.error('No connection URL in session:', session);
                this.showError('LynkBox is ready but no connection URL available. Check console for details.');
            }
        }

        /**
         * Update progress display
         */
        updateProgress(percent, message) {
            this.$progressFill.css('width', percent + '%');
            this.$progressPercent.text(percent + '%');

            if (message) {
                this.typeMessage(message);
            }
        }

        /**
         * Type out a message with typewriter effect
         */
        typeMessage(message) {
            const $container = this.$statusMessage;
            $container.html('<span class="attackbox-typed"></span><span class="attackbox-cursor">▋</span>');

            const $typed = $container.find('.attackbox-typed');
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
            $('body').addClass('attackbox-overlay-open');
        }

        /**
         * Hide the overlay
         */
        hideOverlay() {
            this.$overlay.fadeOut(300);
            $('body').removeClass('attackbox-overlay-open');
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
        showError(message) {
            this.isLaunching = false;
            $('#attackbox-error-message').text(message);
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
            this.updateProgress(0, '');
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
         * Terminate the current session
         */
        async terminateSession() {
            if (!this.sessionId) {
                console.warn('No session ID to terminate');
                return;
            }

            // Confirm termination
            if (!confirm(this.strings.terminateConfirm)) {
                return;
            }

            try {
                // Get token first
                const tokenData = await this.getToken();

                // Call terminate endpoint
                const response = await fetch(
                    tokenData.api_url + '/sessions/' + this.sessionId,
                    {
                        method: 'DELETE',
                        headers: {
                            'X-Moodle-Token': tokenData.token,
                            'Accept': 'application/json'
                        }
                    }
                );

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.message || `Failed to terminate session: ${response.status}`);
                }

                // Success - reset state
                this.sessionId = null;
                this.hasActiveSession = false;
                this.activeSessionUrl = null;

                // Update UI
                this.$button.removeClass('attackbox-btn-active');
                this.$button.find('.attackbox-btn-text').text(this.strings.buttonText);
                this.$button.attr('title', this.strings.buttonTooltip);
                this.$terminateButton.hide();

                // Show success message
                alert(this.strings.terminateSuccess);

            } catch (error) {
                console.error('Terminate session error:', error);
                alert(this.strings.terminateError + ': ' + error.message);
            }
        }
    }

    /**
     * Load all required strings from Moodle.
     * @returns {Promise<Object>} Promise resolving to strings object
     */
    const loadStrings = function() {
        return Str.get_strings(STRING_KEYS).then(function(results) {
            const strings = {};
            const keyNames = [
                'buttonText', 'buttonTextActive', 'buttonTerminate',
                'buttonTooltip', 'buttonTooltipActive',
                'overlayTitle', 'overlaySubtitle', 'cancelButton',
                'errorTitle', 'errorRetry', 'errorClose',
                'successTitle', 'successMessage', 'successOpen',
                'terminateConfirm', 'terminateSuccess', 'terminateError',
                'progress5', 'progress10', 'progress18', 'progress25',
                'progress33', 'progress42', 'progress50', 'progress62',
                'progress70', 'progress85', 'progress94', 'progress100'
            ];
            keyNames.forEach(function(key, index) {
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
        init: function(config) {
            // Wait for DOM ready and strings to load
            $(document).ready(function() {
                loadStrings().then(function(strings) {
                    new AttackBoxLauncher(config, strings);
                }).catch(function(error) {
                    console.error('Failed to load LynkBox strings:', error);
                });
            });
        }
    };
});

