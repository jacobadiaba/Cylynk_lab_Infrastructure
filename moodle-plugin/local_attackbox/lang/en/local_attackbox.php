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
 * Language strings for the AttackBox launcher plugin.
 *
 * @package    local_attackbox
 * @copyright  2024 CyberLab
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

defined('MOODLE_INTERNAL') || die();

// Plugin name.
$string['pluginname'] = 'LynkBox Launcher';
$string['plugindisabled'] = 'The LynkBox Launcher plugin is currently disabled.';
$string['notconfigured'] = 'The LynkBox Launcher plugin is not properly configured. Please contact your administrator.';
$string['admin_dashboard'] = 'LynkBox Admin Dashboard';

// Settings page.
$string['settings:apiheading'] = 'API Configuration';
$string['settings:apiheading_desc'] = 'Configure the connection to the CyberLynk Orchestrator API.';
$string['settings:api_url'] = 'Orchestrator API URL';
$string['settings:api_url_desc'] = 'The base URL of the CyberLynk Orchestrator API (e.g., https://api.example.com/v1)';
$string['settings:shared_secret'] = 'Shared Secret';
$string['settings:shared_secret_desc'] = 'The shared secret used for signing authentication tokens. Must match the secret configured in the orchestrator.';

$string['settings:sessionheading'] = 'Session Configuration';
$string['settings:sessionheading_desc'] = 'Configure session behavior and timeouts.';
$string['settings:session_ttl'] = 'Session Duration (hours)';
$string['settings:session_ttl_desc'] = 'How long a LynkBox session remains active (for display purposes only, actual TTL is controlled by the API).';
$string['settings:token_validity'] = 'Token Validity (seconds)';
$string['settings:token_validity_desc'] = 'How long an authentication token remains valid. Recommended: 300 seconds (5 minutes).';
$string['settings:quotaheading'] = 'Role-based quotas';
$string['settings:quotaheading_desc'] = 'Map Moodle roles to LynkBox plans and monthly time allowances.';
$string['settings:role_freemium'] = 'Freemium role shortname';
$string['settings:role_freemium_desc'] = 'Moodle role shortname that should receive the Freemium plan.';
$string['settings:role_starter'] = 'Starter role shortname';
$string['settings:role_starter_desc'] = 'Moodle role shortname that should receive the Starter plan.';
$string['settings:role_pro'] = 'Pro role shortname';
$string['settings:role_pro_desc'] = 'Moodle role shortname that should receive the Pro plan.';
$string['settings:limit_freemium'] = 'Freemium monthly minutes';
$string['settings:limit_freemium_desc'] = 'Total minutes per month allowed for Freemium users (default 300 = 5h).';
$string['settings:limit_starter'] = 'Starter monthly minutes';
$string['settings:limit_starter_desc'] = 'Total minutes per month allowed for Starter users (default 900 = 15h).';
$string['settings:limit_pro'] = 'Pro monthly minutes';
$string['settings:limit_pro_desc'] = 'Total minutes per month allowed for Pro users (-1 = unlimited).';

$string['settings:uiheading'] = 'User Interface';
$string['settings:uiheading_desc'] = 'Configure the appearance and behavior of the launcher.';
$string['settings:enabled'] = 'Enable Launcher';
$string['settings:enabled_desc'] = 'Show the floating LynkBox launcher button on all pages.';
$string['settings:button_position'] = 'Button Position';
$string['settings:button_position_desc'] = 'Where to display the floating launcher button on the screen.';
$string['settings:poll_interval'] = 'Poll Interval (ms)';
$string['settings:poll_interval_desc'] = 'How often to check for session status updates while launching. Recommended: 3000ms.';

// Button positions.
$string['position:bottomright'] = 'Bottom Right';
$string['position:bottomleft'] = 'Bottom Left';
$string['position:topright'] = 'Top Right';
$string['position:topleft'] = 'Top Left';

// Button text and tooltip.
$string['button:launch'] = 'Launch LynkBox';
$string['button:active'] = 'Open LynkBox';
$string['button:terminate'] = 'End Session';
$string['button:tooltip'] = 'Launch your personal Kali Linux hacking environment in the browser. No installation required!';
$string['button:tooltip_active'] = 'Click to open LynkBox or end your current session';
$string['button:usage_dashboard'] = 'View usage history and statistics';

// Timer text.
$string['timer:time_remaining'] = 'Time remaining';

// Overlay text.
$string['overlay:title'] = 'Deploying LynkBox';
$string['overlay:subtitle'] = 'Initializing your secure hacking environment';
$string['overlay:cancel'] = 'Cancel';

// Error messages.
$string['error:title'] = 'Launch Failed';
$string['error:retry'] = 'Try Again';
$string['error:close'] = 'Close';

// Success messages.
$string['success:title'] = 'LynkBox Ready';
$string['success:message'] = 'Your secure hacking environment is now active.';
$string['success:open'] = 'Open LynkBox';

// Termination messages.
$string['terminate:confirm'] = 'Are you sure you want to end your LynkBox session?';
$string['terminate:success'] = 'Session terminated successfully';
$string['terminate:error'] = 'Failed to terminate session';

// Idle detection messages.
$string['idle:warning_title'] = 'Session Idle Warning';
$string['idle:warning_message'] = 'Your session has been idle. It will be automatically terminated to save resources.';
$string['idle:critical_message'] = '<strong>Critical:</strong> Your session will be terminated very soon due to inactivity!';
$string['idle:keep_active'] = "I'm still here!";
$string['idle:focus_mode'] = 'Enable Focus Mode';
$string['idle:focus_mode_desc'] = 'Focus mode disables idle termination for this session (useful for long-running tasks).';
$string['idle:terminated'] = 'Your session was terminated due to inactivity. You can launch a new session when needed.';

// Progress messages - these match the user's requested messages.
$string['progress:5'] = 'Initializing virtual SOC environment...';
$string['progress:10'] = 'Provisioning secure network tunnel...';
$string['progress:18'] = 'Deploying attack simulation modules...';
$string['progress:25'] = 'Configuring VPN and firewall bypass rules...';
$string['progress:33'] = 'Installing cyber tools: Nmap, Burp, Metasploit...';
$string['progress:42'] = 'Injecting Kali Linux exploit lab environment...';
$string['progress:50'] = 'Loading anonymous sandbox identity...';
$string['progress:62'] = 'Preparing you for red-team engagement...';
$string['progress:70'] = 'Verifying secure stream to Guacamole...';
$string['progress:85'] = 'Concealing your IP footprint...';
$string['progress:94'] = 'Finalizing attack chain workspace...';
$string['progress:100'] = 'LynkBox ready — launching now 🚀';

// Privacy.
$string['privacy:metadata'] = 'The AttackBox Launcher plugin does not store any personal data locally. User information is transmitted to the CyberLab Orchestrator API for session management.';

// Usage Dashboard.
$string['usage:dashboard_title'] = 'LynkBox Usage Dashboard';
$string['usage:current_quota'] = 'Current Quota';
$string['usage:plan'] = 'Plan';
$string['usage:used'] = 'Used';
$string['usage:remaining'] = 'Remaining';
$string['usage:resets_on'] = 'Resets on';
$string['usage:session_history'] = 'Session History';
$string['usage:no_sessions'] = 'No sessions found';
$string['usage:session_id'] = 'Session ID';
$string['usage:started_at'] = 'Started';
$string['usage:ended_at'] = 'Ended';
$string['usage:duration'] = 'Duration';
$string['usage:status'] = 'Status';
$string['usage:total_sessions'] = 'Total Sessions';
$string['usage:loading'] = 'Loading usage data...';
$string['usage:error'] = 'Failed to load usage data';
$string['usage:unlimited'] = 'Unlimited';

// Admin Dashboard.
$string['admin:dashboard_title'] = 'LynkBox Admin Dashboard';
$string['admin:filter_status'] = 'Filter by Status';
$string['admin:all'] = 'All';
$string['admin:active'] = 'Active';
$string['admin:ready'] = 'Ready';
$string['admin:provisioning'] = 'Provisioning';
$string['admin:terminated'] = 'Terminated';
$string['admin:search'] = 'Search';
$string['admin:search_placeholder'] = 'Search by session ID, student ID, or name...';
$string['admin:refresh'] = 'Refresh';
$string['admin:loading'] = 'Loading sessions...';
$string['admin:student_name'] = 'Student';
$string['admin:session_id'] = 'Session ID';
$string['admin:status'] = 'Status';
$string['admin:instance_id'] = 'Instance ID';
$string['admin:created'] = 'Started';
$string['admin:duration'] = 'Duration';
$string['admin:expires'] = 'Expires';
$string['admin:actions'] = 'Actions';
$string['admin:terminate_session'] = 'Terminate';
$string['admin:confirm_terminate'] = 'Are you sure you want to terminate this session?';
$string['admin:session_terminated'] = 'Session terminated successfully';
$string['admin:no_sessions'] = 'No sessions found';
$string['admin:total_sessions'] = 'Total Sessions';
$string['admin:active_now'] = 'Active Now';
$string['admin:provisioning_count'] = 'Provisioning';
$string['admin:instances_used'] = 'Instances Used';
$string['admin:error_loading'] = 'Error loading sessions';

// Capabilities.
$string['attackbox:launch'] = 'Launch LynkBox sessions';
$string['attackbox:configure'] = 'Configure LynkBox plugin settings';
$string['attackbox:managesessions'] = 'Manage all LynkBox sessions';

