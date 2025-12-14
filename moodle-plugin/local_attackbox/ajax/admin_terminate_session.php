<?php
// This file is part of Moodle - http://moodle.org/
//
// Moodle is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

/**
 * Admin API endpoint to terminate a session.
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
    // Get session ID from request.
    $sessionId = required_param('sessionId', PARAM_ALPHANUMEXT);
    $reason = optional_param('reason', 'admin', PARAM_TEXT);

    if (empty($sessionId)) {
        throw new moodle_exception('invalidsessionid', 'local_attackbox');
    }

    // Get admin token.
    $tokenData = $tokenManager->get_token_for_admin($USER->id);

    if (!$tokenData || !isset($tokenData['token']) || !isset($tokenData['api_url'])) {
        throw new moodle_exception('failedtogeneratetoken', 'local_attackbox');
    }

    // Call the orchestrator API to terminate the session.
    $apiUrl = $tokenData['api_url'] . '/sessions/' . $sessionId;

    $curl = curl_init();
    curl_setopt_array($curl, [
        CURLOPT_URL => $apiUrl,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CUSTOMREQUEST => 'DELETE',
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_TIMEOUT => 30,
        CURLOPT_HTTPHEADER => [
            'X-Admin-Token: ' . $tokenData['token'],
            'Content-Type: application/json',
            'Accept: application/json',
        ],
        CURLOPT_POSTFIELDS => json_encode([
            'reason' => $reason,
            'stop_instance' => true,
        ]),
    ]);

    $response = curl_exec($curl);
    $httpCode = curl_getinfo($curl, CURLINFO_HTTP_CODE);
    $error = curl_error($curl);
    curl_close($curl);

    if ($error) {
        throw new moodle_exception('apirequestfailed', 'local_attackbox', '', $error);
    }

    if ($httpCode !== 200) {
        throw new moodle_exception('apirequestfailed', 'local_attackbox', '', 'HTTP ' . $httpCode);
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
