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
 * AJAX endpoint to generate a signed token for the AttackBox API.
 *
 * @package    local_attackbox
 * @copyright  2024 CyberLab
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

define('AJAX_SCRIPT', true);

require_once(__DIR__ . '/../../../config.php');
require_once($CFG->libdir . '/filelib.php');

// Require login.
require_login();
require_sesskey();

// Set JSON header.
header('Content-Type: application/json; charset=utf-8');

try {
    // Check if plugin is enabled.
    if (!get_config('local_attackbox', 'enabled')) {
        throw new \moodle_exception('plugindisabled', 'local_attackbox');
    }

    // Check if properly configured.
    $api_url = get_config('local_attackbox', 'api_url');
    $shared_secret = get_config('local_attackbox', 'shared_secret');

    if (empty($api_url) || empty($shared_secret)) {
        throw new \moodle_exception('notconfigured', 'local_attackbox');
    }

    // Get current user.
    global $USER;

    // Generate token.
    $token_manager = new \local_attackbox\token_manager();
    $token = $token_manager->generate_token($USER);
    [$plan, $quota_minutes] = $token_manager->resolve_plan_and_quota($USER);

    // Get session TTL for display.
    $session_ttl = (int) get_config('local_attackbox', 'session_ttl_hours') ?: 4;

    // Return success response.
    echo json_encode([
        'success' => true,
        'token' => $token,
        'api_url' => $api_url,
        'user' => [
            'id' => $USER->id,
            'fullname' => fullname($USER),
            'email' => $USER->email,
            'plan' => $plan,
            'quota_minutes' => $quota_minutes,
        ],
        'session_ttl_hours' => $session_ttl,
    ]);

} catch (\moodle_exception $e) {
    http_response_code(400);
    echo json_encode([
        'success' => false,
        'error' => $e->getMessage(),
        'errorcode' => $e->errorcode ?? 'unknown',
    ]);

} catch (\Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'An unexpected error occurred',
        'errorcode' => 'internal_error',
    ]);

    // Log the actual error for debugging.
    debugging('AttackBox token generation error: ' . $e->getMessage(), DEBUG_DEVELOPER);
}

