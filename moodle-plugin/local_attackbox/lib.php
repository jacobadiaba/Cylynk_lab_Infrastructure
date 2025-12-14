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
 * Library functions for the AttackBox launcher plugin.
 *
 * Note: The main functionality is handled via the hook system in Moodle 4.4+.
 * See classes/hook_callbacks.php and db/hooks.php for the implementation.
 *
 * The styles.css file is automatically loaded by Moodle for local plugins.
 *
 * @package    local_attackbox
 * @copyright  2024 CyberLab
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

defined('MOODLE_INTERNAL') || die();

// Note: The before_footer hook callback is now handled via the new hook system.
// See db/hooks.php for registration and classes/hook_callbacks.php for implementation.
// This approach is required for Moodle 4.4+ compatibility.

/**
 * Extend the navigation to add admin dashboard link.
 *
 * @param global_navigation $navigation
 */
function local_attackbox_extend_navigation(global_navigation $navigation)
{
    global $PAGE;

    // Only add for users with manage sessions capability.
    if (has_capability('local/attackbox:managesessions', context_system::instance())) {
        $node = $navigation->add(
            get_string('admin:dashboard_title', 'local_attackbox'),
            new moodle_url('/local/attackbox/admin_dashboard.php'),
            navigation_node::TYPE_CUSTOM,
            null,
            'attackbox_admin_dashboard',
            new pix_icon('i/settings', '')
        );
        $node->showinflatnavigation = true;
    }
}

/**
 * Extend the settings navigation to add admin dashboard link.
 *
 * @param settings_navigation $settingsnav
 * @param context $context
 */
function local_attackbox_extend_settings_navigation(settings_navigation $settingsnav, context $context)
{
    global $PAGE;

    // Only add for users with manage sessions capability.
    if (has_capability('local/attackbox:managesessions', context_system::instance())) {
        // Add to site administration if available.
        if ($siteadmin = $settingsnav->find('siteadministration', navigation_node::TYPE_SITE_ADMIN)) {
            $node = $siteadmin->add(
                get_string('admin:dashboard_title', 'local_attackbox'),
                new moodle_url('/local/attackbox/admin_dashboard.php'),
                navigation_node::TYPE_CUSTOM,
                null,
                'attackbox_admin_dashboard',
                new pix_icon('i/report', '')
            );
            $node->showinflatnavigation = true;
        }
    }
}
