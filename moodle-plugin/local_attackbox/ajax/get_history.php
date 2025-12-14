<?php
/**
 * AJAX endpoint to get session history
 *
 * @package    local_attackbox
 * @copyright  2025 CyberLab
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

define('AJAX_SCRIPT', true);

require_once(__DIR__ . '/../../../config.php');
require_once($CFG->dirroot . '/local/attackbox/classes/token_manager.php');

require_login();

header('Content-Type: application/json');

try {
    // Get plugin configuration
    $api_url = get_config('local_attackbox', 'api_url');

    if (empty($api_url)) {
        throw new moodle_exception('API URL not configured');
    }

    // Generate token
    $token_manager = new \local_attackbox\token_manager();
    $token = $token_manager->generate_token($USER);

    // Call orchestrator API for session history
    $history_url = rtrim($api_url, '/') . '/sessions/history';

    $ch = curl_init($history_url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => [
            'X-Moodle-Token: ' . $token,
            'Content-Type: application/json',
        ],
        CURLOPT_TIMEOUT => 15,
        CURLOPT_SSL_VERIFYPEER => true,
    ]);

    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);

    if ($error) {
        throw new moodle_exception('API connection error: ' . $error);
    }

    if ($http_code !== 200) {
        $error_data = json_decode($response, true);
        $error_message = $error_data['message'] ?? 'Unknown error';
        http_response_code($http_code);
        echo json_encode([
            'error' => true,
            'message' => $error_message,
            'http_code' => $http_code,
        ]);
        exit;
    }

    // Parse response
    $data = json_decode($response, true);

    if (!$data || !isset($data['data'])) {
        throw new moodle_exception('Invalid API response');
    }

    $history = $data['data'];

    // Format sessions for display
    $sessions = [];
    if (isset($history['sessions']) && is_array($history['sessions'])) {
        foreach ($history['sessions'] as $session) {
            $started = !empty($session['created_at']) ? strtotime($session['created_at']) : null;
            $ended = !empty($session['terminated_at']) ? strtotime($session['terminated_at']) : null;

            $duration_minutes = 0;
            if ($started && $ended) {
                $duration_minutes = round(($ended - $started) / 60);
            }

            $sessions[] = [
                'session_id' => $session['session_id'] ?? 'N/A',
                'started_at' => $started ? date('Y-m-d H:i:s', $started) : 'N/A',
                'ended_at' => $ended ? date('Y-m-d H:i:s', $ended) : 'Active',
                'duration_minutes' => $duration_minutes,
                'duration_display' => $duration_minutes > 0 ?
                    floor($duration_minutes / 60) . 'h ' . ($duration_minutes % 60) . 'm' :
                    'N/A',
                'status' => $session['status'] ?? 'unknown',
            ];
        }
    }

    // Return formatted data
    echo json_encode([
        'success' => true,
        'sessions' => $sessions,
        'total_sessions' => count($sessions),
        'total_minutes' => $history['total_minutes'] ?? 0,
        'total_hours' => round(($history['total_minutes'] ?? 0) / 60, 1),
    ]);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'error' => true,
        'message' => $e->getMessage(),
    ]);
}
