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
 * Usage Dashboard AMD Module
 *
 * Displays usage statistics and session history
 *
 * @module     local_attackbox/usage-dashboard
 * @copyright  2025 CyberLab
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

define(["jquery"], function ($) {
  "use strict";

  /**
   * Usage Dashboard class
   */
  class UsageDashboard {
    constructor(config) {
      this.config = config;
      this.init();
    }

    /**
     * Initialize the dashboard
     */
    init() {
      this.loadUsageData();
      this.loadSessionHistory();
    }

    /**
     * Load current usage data
     */
    async loadUsageData() {
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
          throw new Error("Failed to load usage data");
        }

        const data = await response.json();

        if (!data.success) {
          throw new Error(data.message || "Failed to load usage");
        }

        this.renderQuotaDisplay(data);
      } catch (error) {
        console.error("Error loading usage:", error);
        this.showError("#quota-container", error.message);
      }
    }

    /**
     * Load session history
     */
    async loadSessionHistory() {
      try {
        const response = await fetch(
          M.cfg.wwwroot +
            "/local/attackbox/ajax/get_history.php?sesskey=" +
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
          throw new Error("Failed to load session history");
        }

        const data = await response.json();

        if (!data.success) {
          throw new Error(data.message || "Failed to load history");
        }

        this.renderSessionHistory(data);
      } catch (error) {
        console.error("Error loading history:", error);
        this.showError("#session-history", error.message);
      }
    }

    /**
     * Render quota display
     */
    renderQuotaDisplay(data) {
      const container = $("#quota-container");

      const percentageUsed = data.percentage || 0;
      const progressColor =
        percentageUsed >= 90
          ? "#f44336"
          : percentageUsed >= 70
          ? "#ffc107"
          : "#4caf50";

      const html = `
                <div class="quota-cards">
                    <div class="quota-card">
                        <div class="quota-label">Plan</div>
                        <div class="quota-value">${data.plan}</div>
                    </div>
                    <div class="quota-card">
                        <div class="quota-label">Used</div>
                        <div class="quota-value">${data.hours_used}h</div>
                        <div class="quota-sublabel">of ${
                          data.hours_limit === "Unlimited"
                            ? "∞"
                            : data.hours_limit + "h"
                        }</div>
                    </div>
                    <div class="quota-card">
                        <div class="quota-label">Remaining</div>
                        <div class="quota-value">${
                          data.hours_remaining === "Unlimited"
                            ? "∞"
                            : data.hours_remaining + "h"
                        }</div>
                    </div>
                    <div class="quota-card">
                        <div class="quota-label">Resets On</div>
                        <div class="quota-value quota-reset-date">${
                          data.reset_date
                        }</div>
                    </div>
                </div>
                ${
                  data.hours_limit !== "Unlimited"
                    ? `
                <div class="quota-progress-container">
                    <div class="quota-progress-bar">
                        <div class="quota-progress-fill" style="width: ${percentageUsed}%; background: ${progressColor};"></div>
                    </div>
                    <div class="quota-progress-label">${percentageUsed}% used</div>
                </div>
                `
                    : ""
                }
            `;

      container.html(html);
    }

    /**
     * Render session history table
     */
    renderSessionHistory(data) {
      const container = $("#session-history");

      if (!data.sessions || data.sessions.length === 0) {
        container.html('<p class="no-sessions">No sessions found</p>');
        return;
      }

      let html = `
                <div class="history-stats">
                    <div class="stat-card">
                        <div class="stat-label">Total Sessions</div>
                        <div class="stat-value">${data.total_sessions}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Total Time</div>
                        <div class="stat-value">${data.total_hours}h</div>
                    </div>
                </div>
                <div class="session-table-container">
                    <table class="session-table">
                        <thead>
                            <tr>
                                <th>Session ID</th>
                                <th>Started</th>
                                <th>Ended</th>
                                <th>Duration</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

      data.sessions.forEach((session) => {
        const statusClass =
          session.status === "terminated"
            ? "status-ended"
            : session.status === "ready" || session.status === "active"
            ? "status-active"
            : "status-other";

        // Use created_at instead of started_at
        const startTime = session.created_at || session.started_at;
        // Use terminated_at instead of ended_at (active sessions won't have this)
        const endTime = session.terminated_at || session.ended_at;

        const isActive = session.status !== "terminated" && !endTime;

        html += `
                    <tr>
                        <td class="session-id">${this.truncateId(
                          session.session_id
                        )}</td>
                        <td>${this.formatDateTime(startTime)}</td>
                        <td>${
                          isActive
                            ? '<span class="badge-active">Active</span>'
                            : this.formatDateTime(endTime)
                        }</td>
                        <td>${session.duration_display || "N/A"}</td>
                        <td><span class="status-badge ${statusClass}">${this.capitalizeFirst(
          session.status
        )}</span></td>
                    </tr>
                `;
      });

      html += `
                        </tbody>
                    </table>
                </div>
            `;

      container.html(html);
    }

    /**
     * Show error message
     */
    showError(selector, message) {
      $(selector).html(`
                <div class="error-message">
                    <div class="error-icon">⚠️</div>
                    <p>${message}</p>
                </div>
            `);
    }

    /**
     * Truncate session ID for display
     */
    truncateId(id) {
      if (!id || id === "N/A") return id;
      return id.length > 12 ? id.substring(0, 12) + "..." : id;
    }

    /**
     * Format datetime for display
     */
    formatDateTime(timestamp) {
      if (!timestamp || timestamp === "N/A") return "N/A";
      try {
        // Handle Unix timestamp (number)
        let date;
        if (typeof timestamp === "number") {
          date = new Date(timestamp * 1000); // Convert seconds to milliseconds
        } else if (typeof timestamp === "string") {
          // Try parsing as ISO string first
          date = new Date(timestamp);
          // If invalid, try parsing as number
          if (isNaN(date.getTime())) {
            const numTimestamp = parseInt(timestamp, 10);
            if (!isNaN(numTimestamp)) {
              date = new Date(numTimestamp * 1000);
            }
          }
        } else {
          return "N/A";
        }

        // Check if date is valid
        if (isNaN(date.getTime())) {
          return "N/A";
        }

        return date.toLocaleString("en-US", {
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        });
      } catch (e) {
        console.error("Error formatting date:", timestamp, e);
        return "N/A";
      }
    }

    /**
     * Capitalize first letter
     */
    capitalizeFirst(str) {
      if (!str) return "";
      return str.charAt(0).toUpperCase() + str.slice(1);
    }
  }

  return {
    /**
     * Initialize the usage dashboard
     * @param {Object} config Configuration object
     */
    init: function (config) {
      $(document).ready(function () {
        new UsageDashboard(config);
      });
    },
  };
});
