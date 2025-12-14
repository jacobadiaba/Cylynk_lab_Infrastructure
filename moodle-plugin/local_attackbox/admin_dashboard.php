<?php
// This file is part of Moodle - http://moodle.org/
//
// Moodle is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

/**
 * Admin dashboard page for AttackBox session management.
 *
 * @package    local_attackbox
 * @copyright  2024 CyberLab Team
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

require_once(__DIR__ . '/../../config.php');
require_once($CFG->libdir . '/adminlib.php');

// Ensure user is logged in and has admin capability.
require_login();
require_capability('local/attackbox:managesessions', context_system::instance());

// Set up the page.
$PAGE->set_url(new moodle_url('/local/attackbox/admin_dashboard.php'));
$PAGE->set_context(context_system::instance());
$PAGE->set_title(get_string('admin_dashboard', 'local_attackbox'));
$PAGE->set_heading(get_string('admin_dashboard', 'local_attackbox'));
$PAGE->set_pagelayout('admin');

// Add JavaScript and CSS.
$PAGE->requires->jquery();
$PAGE->requires->js_call_amd('local_attackbox/admin-dashboard', 'init', [
    [
        'userId' => $USER->id,
        'sesskey' => sesskey(),
        'wwwroot' => $CFG->wwwroot,
    ]
]);

// Output header.
echo $OUTPUT->header();

// Page heading.
echo $OUTPUT->heading(get_string('admin_dashboard', 'local_attackbox'));

// Dashboard container.
echo '<div id="attackbox-admin-dashboard">';

// Filter section.
echo '<div class="admin-filters">';
echo '  <div class="filter-group">';
echo '    <label for="status-filter">' . get_string('filter_status', 'local_attackbox') . '</label>';
echo '    <select id="status-filter" class="form-control">';
echo '      <option value="all">' . get_string('all', 'local_attackbox') . '</option>';
echo '      <option value="active">' . get_string('active', 'local_attackbox') . '</option>';
echo '      <option value="ready">' . get_string('ready', 'local_attackbox') . '</option>';
echo '      <option value="provisioning">' . get_string('provisioning', 'local_attackbox') . '</option>';
echo '      <option value="terminated">' . get_string('terminated', 'local_attackbox') . '</option>';
echo '    </select>';
echo '  </div>';
echo '  <div class="filter-group">';
echo '    <label for="search-filter">' . get_string('search', 'local_attackbox') . '</label>';
echo '    <input type="text" id="search-filter" class="form-control" placeholder="' . get_string('search_placeholder', 'local_attackbox') . '">';
echo '  </div>';
echo '  <div class="filter-group">';
echo '    <button id="refresh-sessions" class="btn btn-primary">' . get_string('refresh', 'local_attackbox') . '</button>';
echo '  </div>';
echo '</div>';

// Stats cards.
echo '<div class="admin-stats" id="admin-stats"></div>';

// Sessions table.
echo '<div class="admin-sessions-container">';
echo '  <div id="sessions-loading" class="text-center" style="display: none;">';
echo '    <div class="spinner-border" role="status">';
echo '      <span class="sr-only">Loading...</span>';
echo '    </div>';
echo '    <p>' . get_string('loading', 'local_attackbox') . '</p>';
echo '  </div>';
echo '  <div id="sessions-error" class="alert alert-danger" style="display: none;"></div>';
echo '  <div id="sessions-table-container"></div>';
echo '</div>';

echo '</div>'; // End dashboard container.

// Output footer.
echo $OUTPUT->footer();
