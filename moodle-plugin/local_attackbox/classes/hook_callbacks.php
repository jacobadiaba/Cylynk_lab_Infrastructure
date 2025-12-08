<?php
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
 * Hook callbacks for the AttackBox launcher plugin.
 *
 * @package    local_attackbox
 * @copyright  2024 CyberLab
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

namespace local_attackbox;

defined('MOODLE_INTERNAL') || die();

/**
 * Hook callbacks for injecting the AttackBox launcher.
 */
class hook_callbacks {

    /**
     * Callback for before_footer_html_generation hook.
     *
     * Injects the floating AttackBox launcher button for logged-in users.
     *
     * @param \core\hook\output\before_footer_html_generation $hook The hook instance.
     */
    public static function before_footer(\core\hook\output\before_footer_html_generation $hook): void {
        global $PAGE, $USER, $CFG;

        // Only show for logged-in users.
        if (!isloggedin() || isguestuser()) {
            return;
        }

        // Check if plugin is enabled.
        if (!get_config('local_attackbox', 'enabled')) {
            return;
        }

        // Check if properly configured.
        $api_url = get_config('local_attackbox', 'api_url');
        $shared_secret = get_config('local_attackbox', 'shared_secret');

        if (empty($api_url) || empty($shared_secret)) {
            return;
        }

        // Don't show on certain pages (login, admin upgrade, etc.).
        $pagetype = $PAGE->pagetype;
        $excluded_pages = ['login-index', 'admin-index', 'admin-upgradesettings'];
        if (in_array($pagetype, $excluded_pages)) {
            return;
        }

        // Get configuration.
        $button_position = get_config('local_attackbox', 'button_position') ?: 'bottom-right';
        $poll_interval = (int) get_config('local_attackbox', 'poll_interval') ?: 3000;
        $session_ttl = (int) get_config('local_attackbox', 'session_ttl_hours') ?: 4;

        // Prepare minimal configuration for JavaScript.
        // Strings are loaded via Moodle's string API in JS to avoid data size warning.
        $config = [
            'apiUrl' => $api_url,
            'tokenEndpoint' => $CFG->wwwroot . '/local/attackbox/ajax/get_token.php',
            'sesskey' => sesskey(),
            'userId' => $USER->id,
            'userFullname' => fullname($USER),
            'buttonPosition' => $button_position,
            'pollInterval' => $poll_interval,
            'sessionTtlHours' => $session_ttl,
        ];

        // Initialize the AMD module.
        $PAGE->requires->js_call_amd('local_attackbox/launcher', 'init', [$config]);
    }
}

