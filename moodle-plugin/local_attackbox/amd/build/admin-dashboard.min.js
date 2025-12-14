// This file is part of Moodle - http://moodle.org/
//
// Moodle is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

/**
 * Admin Dashboard JavaScript for AttackBox session management.
 *
 * @module     local_attackbox/admin-dashboard
 * @copyright  2024 CyberLab Team
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

define(["jquery", "core/ajax", "core/notification"], function (
  $,
  Ajax,
  Notification
) {
  "use strict";

  /**
   * Admin Dashboard class
   */
  class AdminDashboard {
    constructor(config) {
      this.config = config;
      this.sessions = [];
      this.filteredSessions = [];
      this.autoRefreshInterval = null;
    }

    /**
     * Initialize the dashboard
     */
    init() {
      this.setupEventListeners();
      this.loadSessions();
      this.startAutoRefresh();
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
      // Refresh button
      $("#refresh-sessions").on("click", () => {
        this.loadSessions();
      });

      // Status filter
      $("#status-filter").on("change", () => {
        this.applyFilters();
      });

      // Search filter
      $("#search-filter").on("input", () => {
        this.applyFilters();
      });
    }

    /**
     * Load all sessions from API
     */
    async loadSessions() {
      this.showLoading(true);
      this.hideError();

      try {
        const status = $("#status-filter").val();
        const search = $("#search-filter").val();

        const params = new URLSearchParams({
          sesskey: this.config.sesskey,
          status: status || "all",
          search: search || "",
          limit: 200,
        });

        const response = await fetch(
          `${this.config.wwwroot}/local/attackbox/ajax/get_all_sessions.php?${params}`,
          {
            method: "GET",
            credentials: "same-origin",
            headers: {
              Accept: "application/json",
            },
          }
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (!data.success) {
          throw new Error(data.message || "Failed to load sessions");
        }

        this.sessions = data.data.sessions || [];
        this.filteredSessions = this.sessions;
        this.renderStats(data.data);
        this.renderSessionsTable();
      } catch (error) {
        console.error("Error loading sessions:", error);
        this.showError(error.message);
      } finally {
        this.showLoading(false);
      }
    }

    /**
     * Apply filters to sessions
     */
    applyFilters() {
      const status = $("#status-filter").val();
      const search = $("#search-filter").val().toLowerCase();

      this.filteredSessions = this.sessions.filter((session) => {
        // Status filter
        if (status !== "all" && session.status !== status) {
          return false;
        }

        // Search filter
        if (search) {
          const searchableText = [
            session.session_id,
            session.student_id,
            session.student_name,
            session.instance_id,
          ]
            .join(" ")
            .toLowerCase();

          if (!searchableText.includes(search)) {
            return false;
          }
        }

        return true;
      });

      this.renderSessionsTable();
    }

    /**
     * Render statistics cards
     */
    renderStats(data) {
      const stats = data.stats || {};
      const html = `
                <div class="stat-card">
                    <div class="stat-label">Total Sessions</div>
                    <div class="stat-value">${stats.total_sessions || 0}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Active Now</div>
                    <div class="stat-value stat-active">${
                      stats.active_count || 0
                    }</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Provisioning</div>
                    <div class="stat-value stat-warning">${
                      stats.provisioning_count || 0
                    }</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Instances Used</div>
                    <div class="stat-value">${stats.instances_in_use || 0}/${
        stats.total_instances || 0
      }</div>
                </div>
            `;

      $("#admin-stats").html(html);
    }

    /**
     * Render sessions table
     */
    renderSessionsTable() {
      const container = $("#sessions-table-container");

      if (this.filteredSessions.length === 0) {
        container.html('<p class="no-sessions">No sessions found</p>');
        return;
      }

      let html = `
                <table class="admin-sessions-table table table-striped">
                    <thead>
                        <tr>
                            <th>Session ID</th>
                            <th>Student</th>
                            <th>Status</th>
                            <th>Instance ID</th>
                            <th>Started</th>
                            <th>Duration</th>
                            <th>Expires</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

      this.filteredSessions.forEach((session) => {
        const statusClass = this.getStatusClass(session.status);
        const duration = this.calculateDuration(session);
        const expiresIn = this.calculateExpiresIn(session);
        const isActive = [
          "active",
          "ready",
          "provisioning",
          "pending",
        ].includes(session.status);

        html += `
                    <tr class="${statusClass}">
                        <td class="session-id" title="${session.session_id}">
                            ${this.truncateId(session.session_id)}
                        </td>
                        <td>
                            <div class="student-info">
                                <div class="student-name">${this.escapeHtml(
                                  session.student_name || session.student_id
                                )}</div>
                                <div class="student-id">${
                                  session.student_id
                                }</div>
                            </div>
                        </td>
                        <td>
                            <span class="badge badge-${this.getStatusBadge(
                              session.status
                            )}">
                                ${session.status}
                            </span>
                        </td>
                        <td class="instance-id">
                            ${
                              session.instance_id
                                ? this.truncateId(session.instance_id)
                                : '<span class="text-muted">N/A</span>'
                            }
                        </td>
                        <td>${this.formatDateTime(session.created_at)}</td>
                        <td>${duration}</td>
                        <td>${expiresIn}</td>
                        <td class="actions">
                            ${
                              isActive
                                ? `
                                <button class="btn btn-sm btn-danger terminate-btn" 
                                        data-session-id="${session.session_id}"
                                        data-student-name="${this.escapeHtml(
                                          session.student_name ||
                                            session.student_id
                                        )}">
                                    Terminate
                                </button>
                            `
                                : '<span class="text-muted">-</span>'
                            }
                        </td>
                    </tr>
                `;
      });

      html += `
                    </tbody>
                </table>
            `;

      container.html(html);

      // Attach terminate button handlers
      $(".terminate-btn").on("click", (e) => {
        const sessionId = $(e.target).data("session-id");
        const studentName = $(e.target).data("student-name");
        this.confirmTerminateSession(sessionId, studentName);
      });
    }

    /**
     * Get status CSS class
     */
    getStatusClass(status) {
      switch (status) {
        case "ready":
        case "active":
          return "status-active";
        case "provisioning":
        case "pending":
          return "status-warning";
        case "terminated":
          return "status-terminated";
        case "error":
          return "status-error";
        default:
          return "";
      }
    }

    /**
     * Get status badge color
     */
    getStatusBadge(status) {
      switch (status) {
        case "active":
        case "ready":
          return "success";
        case "provisioning":
        case "pending":
          return "warning";
        case "terminated":
          return "secondary";
        case "error":
          return "danger";
        default:
          return "info";
      }
    }

    /**
     * Calculate session duration
     */
    calculateDuration(session) {
      const start = session.created_at;
      const end = session.terminated_at || Math.floor(Date.now() / 1000);

      if (!start) return "N/A";

      const durationSeconds = end - start;
      const hours = Math.floor(durationSeconds / 3600);
      const minutes = Math.floor((durationSeconds % 3600) / 60);

      if (hours > 0) {
        return `${hours}h ${minutes}m`;
      }
      return `${minutes}m`;
    }

    /**
     * Calculate time until expiry
     */
    calculateExpiresIn(session) {
      if (!session.expires_at) return "N/A";
      if (session.status === "terminated") return "-";

      const now = Math.floor(Date.now() / 1000);
      const expiresIn = session.expires_at - now;

      if (expiresIn < 0) return "Expired";

      const hours = Math.floor(expiresIn / 3600);
      const minutes = Math.floor((expiresIn % 3600) / 60);

      if (hours > 0) {
        return `${hours}h ${minutes}m`;
      }
      return `${minutes}m`;
    }

    /**
     * Confirm and terminate session
     */
    confirmTerminateSession(sessionId, studentName) {
      if (
        !confirm(
          `Are you sure you want to terminate the session for ${studentName}?\n\nSession ID: ${sessionId}`
        )
      ) {
        return;
      }

      this.terminateSession(sessionId);
    }

    /**
     * Terminate a session
     */
    async terminateSession(sessionId) {
      try {
        const params = new URLSearchParams({
          sesskey: this.config.sesskey,
          sessionId: sessionId,
          reason: "admin",
        });

        const response = await fetch(
          `${this.config.wwwroot}/local/attackbox/ajax/admin_terminate_session.php?${params}`,
          {
            method: "POST",
            credentials: "same-origin",
            headers: {
              Accept: "application/json",
            },
          }
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (!data.success) {
          throw new Error(data.message || "Failed to terminate session");
        }

        Notification.addNotification({
          message: "Session terminated successfully",
          type: "success",
        });

        // Reload sessions
        this.loadSessions();
      } catch (error) {
        console.error("Error terminating session:", error);
        Notification.addNotification({
          message: `Error: ${error.message}`,
          type: "error",
        });
      }
    }

    /**
     * Start auto-refresh
     */
    startAutoRefresh() {
      // Refresh every 30 seconds
      this.autoRefreshInterval = setInterval(() => {
        this.loadSessions();
      }, 30000);
    }

    /**
     * Truncate ID for display
     */
    truncateId(id) {
      if (!id) return "";
      return id.length > 12 ? id.substring(0, 12) + "..." : id;
    }

    /**
     * Format datetime
     */
    formatDateTime(timestamp) {
      if (!timestamp) return "N/A";

      // Check if timestamp is in seconds (Unix timestamp) or milliseconds
      const date =
        timestamp < 10000000000
          ? new Date(timestamp * 1000)
          : new Date(timestamp);

      if (isNaN(date.getTime())) return "Invalid Date";

      const now = new Date();
      const diffMs = now - date;
      const diffMins = Math.floor(diffMs / 60000);

      if (diffMins < 60) {
        return `${diffMins}m ago`;
      }

      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) {
        return `${diffHours}h ago`;
      }

      return date.toLocaleString();
    }

    /**
     * Escape HTML
     */
    escapeHtml(text) {
      const div = document.createElement("div");
      div.textContent = text;
      return div.innerHTML;
    }

    /**
     * Show loading state
     */
    showLoading(show) {
      if (show) {
        $("#sessions-loading").show();
        $("#sessions-table-container").hide();
      } else {
        $("#sessions-loading").hide();
        $("#sessions-table-container").show();
      }
    }

    /**
     * Show error message
     */
    showError(message) {
      $("#sessions-error").text(message).show();
    }

    /**
     * Hide error message
     */
    hideError() {
      $("#sessions-error").hide();
    }
  }

  return {
    init: function (config) {
      const dashboard = new AdminDashboard(config);
      dashboard.init();
    },
  };
});
