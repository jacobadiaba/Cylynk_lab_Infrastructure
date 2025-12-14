<?php
/**
 * LynkBox Usage Dashboard
 *
 * Display user's session history and usage statistics
 *
 * @package    local_attackbox
 * @copyright  2025 CyberLab
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

require_once(__DIR__ . '/../../config.php');
require_once($CFG->libdir . '/adminlib.php');

require_login();

$context = context_system::instance();

$PAGE->set_context($context);
$PAGE->set_url(new moodle_url('/local/attackbox/usage.php'));
$PAGE->set_pagelayout('standard');
$PAGE->set_title(get_string('usage:dashboard_title', 'local_attackbox'));
$PAGE->set_heading(get_string('usage:dashboard_title', 'local_attackbox'));

// Add custom CSS
$PAGE->requires->css('/local/attackbox/styles/usage-dashboard.css');

// Add JavaScript module
$PAGE->requires->js_call_amd('local_attackbox/usage-dashboard', 'init', [
    'userId' => $USER->id,
    'sesskey' => sesskey(),
]);

echo $OUTPUT->header();

?>

<div class="usage-dashboard">
    <!-- Current Quota Section -->
    <div class="usage-section quota-section">
        <h2><?php echo get_string('usage:current_quota', 'local_attackbox'); ?></h2>
        <div id="quota-container" class="quota-container">
            <div class="loading-spinner">
                <div class="spinner"></div>
                <p><?php echo get_string('usage:loading', 'local_attackbox'); ?></p>
            </div>
        </div>
    </div>

    <!-- Usage Chart Section -->
    <div class="usage-section chart-section">
        <h2>Monthly Usage Trend</h2>
        <div id="usage-chart" class="usage-chart">
            <canvas id="usageCanvas"></canvas>
        </div>
    </div>

    <!-- Session History Section -->
    <div class="usage-section history-section">
        <h2><?php echo get_string('usage:session_history', 'local_attackbox'); ?></h2>
        <div id="session-history" class="session-history">
            <div class="loading-spinner">
                <div class="spinner"></div>
                <p><?php echo get_string('usage:loading', 'local_attackbox'); ?></p>
            </div>
        </div>
    </div>
</div>

<?php

echo $OUTPUT->footer();
