<?php
// This file is part of Moodle - http://moodle.org/
//
// Moodle is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

/**
 * Admin API endpoint to get all sessions.
 *
 * @package    local_attackbox
 * @copyright  2024 CyberLab Team
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

define('AJAX_SCRIPT', true);

require_once(__DIR__ . '/../../../config.php');
require_once($CFG->dirroot . '/local/attackbox/classes/token_manager.php');

// Require login.
require_login();
require_sesskey();

// Check capability.
require_capability('local/attackbox:managesessions', context_system::instance());

// Get the token manager.
$tokenManager = new \local_attackbox\token_manager();

try {
    // Get filter parameters
    $status = optional_param('status', 'all', PARAM_ALPHA);
    $search = optional_param('search', '', PARAM_TEXT);
    $limit = optional_param('limit', 100, PARAM_INT);

    // Get admin token (includes all permissions).
    $tokenData = $tokenManager->get_token_for_admin($USER->id);

    if (!$tokenData || !isset($tokenData['token']) || !isset($tokenData['api_url'])) {
        throw new moodle_exception('failedtogeneratetoken', 'local_attackbox');
    }

    // Call the orchestrator API to get all sessions.
    $apiUrl = $tokenData['api_url'] . '/admin/sessions';

    // Add query parameters
    $queryParams = [];
    if ($status !== 'all') {
        $queryParams['status'] = $status;
    }
    if (!empty($search)) {
        $queryParams['search'] = $search;
    }
    $queryParams['limit'] = $limit;

    if (!empty($queryParams)) {
        $apiUrl .= '?' . http_build_query($queryParams);
    }

    // Make the API request.
    $curl = curl_init();
    curl_setopt_array($curl, [
        CURLOPT_URL => $apiUrl,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_TIMEOUT => 30,
        CURLOPT_HTTPHEADER => [
            'X-Admin-Token: ' . $tokenData['token'],
            'Accept: application/json',
        ],
    ]);

    $response = curl_exec($curl);
    $httpCode = curl_getinfo($curl, CURLINFO_HTTP_CODE);
    $error = curl_error($curl);
    curl_close($curl);

    if ($error) {
        // Log the error for debugging
        error_log("Admin sessions API error: " . $error);
        throw new moodle_exception('apirequestfailed', 'local_attackbox', '', $error);
    }

    if ($httpCode !== 200) {
        // Log the response for debugging
        error_log("Admin sessions API HTTP $httpCode: " . substr($response, 0, 500));
        throw new moodle_exception('apirequestfailed', 'local_attackbox', '', 'HTTP ' . $httpCode . ': ' . substr($response, 0, 200));
    }

    $data = json_decode($response, true);

    if (!$data || !isset($data['success'])) {
        throw new moodle_exception('invalidapiresponse', 'local_attackbox');
    }

    // Return the data.
    header('Content-Type: application/json');
    echo json_encode($data);

} catch (Exception $e) {
    header('HTTP/1.1 500 Internal Server Error');
    header('Content-Type: application/json');
    echo json_encode([
        'success' => false,
        'message' => $e->getMessage(),
    ]);
}
