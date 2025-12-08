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

