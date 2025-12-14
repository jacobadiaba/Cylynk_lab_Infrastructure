<?php
/**
 * AJAX endpoint to get AttackBox usage statistics
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
    $api_key = get_config('local_attackbox', 'api_key');

    if (empty($api_url)) {
        throw new moodle_exception('API URL not configured');
    }

    // Generate token
    $token_manager = new \local_attackbox\token_manager();
    $token = $token_manager->generate_token($USER);

    // Call orchestrator API
    $usage_url = rtrim($api_url, '/') . '/usage';

    $ch = curl_init($usage_url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => [
            'X-Moodle-Token: ' . $token,
            'Content-Type: application/json',
        ],
        CURLOPT_TIMEOUT => 10,
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

    // Parse and format response
    $data = json_decode($response, true);

    if (!$data || !isset($data['data'])) {
        throw new moodle_exception('Invalid API response');
    }

    $usage = $data['data'];

    // Format for frontend
    $formatted = [
        'success' => true,
        'plan' => ucfirst($usage['plan'] ?? 'freemium'),
        'quota_minutes' => $usage['quota_minutes'] ?? 0,
        'consumed_minutes' => $usage['consumed_minutes'] ?? 0,
        'remaining_minutes' => $usage['remaining_minutes'] ?? 0,
        'session_count' => $usage['session_count'] ?? 0,
        'hours_used' => round(($usage['consumed_minutes'] ?? 0) / 60, 1),
        'hours_limit' => $usage['quota_minutes'] === -1 ? 'Unlimited' : round(($usage['quota_minutes'] ?? 0) / 60, 1),
        'hours_remaining' => $usage['quota_minutes'] === -1 ? 'Unlimited' : round(($usage['remaining_minutes'] ?? 0) / 60, 1),
        'percentage' => $usage['quota_minutes'] > 0 ? round((($usage['consumed_minutes'] ?? 0) / $usage['quota_minutes']) * 100) : 0,
        'resets_at' => $usage['resets_at'] ?? '',
        'reset_date' => !empty($usage['resets_at']) ? date('F j, Y', strtotime($usage['resets_at'])) : 'Unknown',
    ];

    echo json_encode($formatted);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'error' => true,
        'message' => $e->getMessage(),
    ]);
}
