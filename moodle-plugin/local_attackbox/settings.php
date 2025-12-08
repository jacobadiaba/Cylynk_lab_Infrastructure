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
 * Admin settings for the AttackBox launcher plugin.
 *
 * @package    local_attackbox
 * @copyright  2024 CyberLab
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

defined('MOODLE_INTERNAL') || die();

if ($hassiteconfig) {
    $settings = new admin_settingpage('local_attackbox', get_string('pluginname', 'local_attackbox'));

    // API Configuration section.
    $settings->add(new admin_setting_heading(
        'local_attackbox/apiheading',
        get_string('settings:apiheading', 'local_attackbox'),
        get_string('settings:apiheading_desc', 'local_attackbox')
    ));

    // Orchestrator API URL.
    $settings->add(new admin_setting_configtext(
        'local_attackbox/api_url',
        get_string('settings:api_url', 'local_attackbox'),
        get_string('settings:api_url_desc', 'local_attackbox'),
        '',
        PARAM_URL
    ));

    // Shared secret for token signing.
    $settings->add(new admin_setting_configpasswordunmask(
        'local_attackbox/shared_secret',
        get_string('settings:shared_secret', 'local_attackbox'),
        get_string('settings:shared_secret_desc', 'local_attackbox'),
        ''
    ));

    // Session Configuration section.
    $settings->add(new admin_setting_heading(
        'local_attackbox/sessionheading',
        get_string('settings:sessionheading', 'local_attackbox'),
        get_string('settings:sessionheading_desc', 'local_attackbox')
    ));

    // Session TTL (for display purposes).
    $settings->add(new admin_setting_configtext(
        'local_attackbox/session_ttl_hours',
        get_string('settings:session_ttl', 'local_attackbox'),
        get_string('settings:session_ttl_desc', 'local_attackbox'),
        '4',
        PARAM_INT
    ));

    // Token validity in seconds.
    $settings->add(new admin_setting_configtext(
        'local_attackbox/token_validity',
        get_string('settings:token_validity', 'local_attackbox'),
        get_string('settings:token_validity_desc', 'local_attackbox'),
        '300',
        PARAM_INT
    ));

    // UI Configuration section.
    $settings->add(new admin_setting_heading(
        'local_attackbox/uiheading',
        get_string('settings:uiheading', 'local_attackbox'),
        get_string('settings:uiheading_desc', 'local_attackbox')
    ));

    // Enable/disable the launcher.
    $settings->add(new admin_setting_configcheckbox(
        'local_attackbox/enabled',
        get_string('settings:enabled', 'local_attackbox'),
        get_string('settings:enabled_desc', 'local_attackbox'),
        1
    ));

    // Button position.
    $positions = [
        'bottom-right' => get_string('position:bottomright', 'local_attackbox'),
        'bottom-left' => get_string('position:bottomleft', 'local_attackbox'),
        'top-right' => get_string('position:topright', 'local_attackbox'),
        'top-left' => get_string('position:topleft', 'local_attackbox'),
    ];
    $settings->add(new admin_setting_configselect(
        'local_attackbox/button_position',
        get_string('settings:button_position', 'local_attackbox'),
        get_string('settings:button_position_desc', 'local_attackbox'),
        'bottom-right',
        $positions
    ));

    // Poll interval in milliseconds.
    $settings->add(new admin_setting_configtext(
        'local_attackbox/poll_interval',
        get_string('settings:poll_interval', 'local_attackbox'),
        get_string('settings:poll_interval_desc', 'local_attackbox'),
        '3000',
        PARAM_INT
    ));

    $ADMIN->add('localplugins', $settings);
}

