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
 * Token manager for generating signed authentication tokens.
 *
 * @package    local_attackbox
 * @copyright  2024 CyberLab
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

namespace local_attackbox;

defined('MOODLE_INTERNAL') || die();

/**
 * Manages generation of signed tokens for API authentication.
 *
 * Tokens are signed using HMAC-SHA256 with a shared secret configured
 * in the plugin settings. Each token contains user information,
 * a timestamp, expiry time, and a nonce to prevent replay attacks.
 */
class token_manager
{

    /** @var string The shared secret for signing tokens. */
    private $secret;

    /** @var int Token validity period in seconds. */
    private $validity;

    /** @var array Default monthly quota minutes per plan. */
    private $default_plan_limits = [
        'freemium' => 300, // 5 hours
        'starter' => 900,  // 15 hours
        'pro' => -1,       // unlimited
    ];

    /**
     * Constructor.
     *
     * @param string|null $secret The shared secret (uses config if null).
     * @param int|null $validity Token validity in seconds (uses config if null).
     */
    public function __construct(?string $secret = null, ?int $validity = null)
    {
        $this->secret = $secret ?? get_config('local_attackbox', 'shared_secret');
        $this->validity = $validity ?? (int) get_config('local_attackbox', 'token_validity') ?: 300;
    }

    /**
     * Generate a signed token for the given user.
     *
     * @param \stdClass $user The Moodle user object.
     * @return string The signed token (base64 payload + '.' + signature).
     * @throws \coding_exception If shared secret is not configured.
     */
    public function generate_token(\stdClass $user): string
    {
        if (empty($this->secret)) {
            throw new \coding_exception('AttackBox shared secret is not configured');
        }

        $now = time();
        $payload = [
            'user_id' => (string) $user->id,
            'username' => $user->username,
            'email' => $user->email,
            'firstname' => $user->firstname,
            'lastname' => $user->lastname,
            'fullname' => fullname($user),
            'roles' => $this->get_user_role_shortnames($user),
            'timestamp' => $now,
            'expires' => $now + $this->validity,
            'nonce' => $this->generate_nonce(),
            'issuer' => 'moodle',
            'site_url' => $this->get_site_url(),
        ];

        // Attach plan/quota info for orchestrator enforcement.
        [$plan, $quota_minutes] = $this->resolve_plan_and_quota($user);
        $payload['plan'] = $plan;
        $payload['quota_minutes'] = $quota_minutes;

        $payload_json = json_encode($payload, JSON_UNESCAPED_SLASHES);
        $payload_base64 = $this->base64url_encode($payload_json);
        $signature = $this->sign($payload_base64);

        return $payload_base64 . '.' . $signature;
    }

    /**
     * Generate a cryptographically secure nonce.
     *
     * @return string A 32-character hex string.
     */
    private function generate_nonce(): string
    {
        return bin2hex(random_bytes(16));
    }

    /**
     * Sign the payload using HMAC-SHA256.
     *
     * @param string $payload The base64-encoded payload.
     * @return string The signature as a hex string.
     */
    private function sign(string $payload): string
    {
        return hash_hmac('sha256', $payload, $this->secret);
    }

    /**
     * Base64 URL-safe encoding.
     *
     * @param string $data The data to encode.
     * @return string The URL-safe base64 encoded string.
     */
    private function base64url_encode(string $data): string
    {
        return rtrim(strtr(base64_encode($data), '+/', '-_'), '=');
    }

    /**
     * Get the site URL for token issuer identification.
     *
     * @return string The Moodle site URL.
     */
    private function get_site_url(): string
    {
        global $CFG;
        return $CFG->wwwroot;
    }

    /**
     * Resolve the user's plan and quota based on Moodle role shortnames.
     *
     * @param \stdClass $user Moodle user
     * @return array [string $plan, int $quota_minutes]
     */
    public function resolve_plan_and_quota(\stdClass $user): array
    {
        $roles = $this->get_user_role_shortnames($user);

        $freemium_role = get_config('local_attackbox', 'role_freemium_shortname') ?: 'freemium';
        $starter_role = get_config('local_attackbox', 'role_starter_shortname') ?: 'starter';
        $pro_role = get_config('local_attackbox', 'role_pro_shortname') ?: 'pro';

        $plan = 'freemium';
        if (in_array($pro_role, $roles)) {
            $plan = 'pro';
        } else if (in_array($starter_role, $roles)) {
            $plan = 'starter';
        } else if (in_array($freemium_role, $roles)) {
            $plan = 'freemium';
        }

        $quota_minutes = $this->get_plan_quota_minutes($plan);

        return [$plan, $quota_minutes];
    }

    /**
     * Get the configured monthly quota minutes for a plan.
     *
     * @param string $plan
     * @return int
     */
    private function get_plan_quota_minutes(string $plan): int
    {
        $config_key = "limit_{$plan}_minutes";
        $configured = get_config('local_attackbox', $config_key);

        if ($configured === null || $configured === false || $configured === '') {
            return $this->default_plan_limits[$plan] ?? -1;
        }

        return (int) $configured;
    }

    /**
     * Get Moodle role shortnames for the user at system context.
     *
     * @param \stdClass $user
     * @return array
     */
    private function get_user_role_shortnames(\stdClass $user): array
    {
        $roles = get_user_roles(\context_system::instance(), $user->id, true);
        if (empty($roles)) {
            return [];
        }

        return array_values(array_filter(array_map(function ($role) {
            return $role->shortname ?? null;
        }, $roles)));
    }

    /**
     * Verify a token signature (for testing/debugging purposes).
     *
     * @param string $token The signed token.
     * @return array|null The payload if valid, null if invalid.
     */
    public function verify_token(string $token): ?array
    {
        $parts = explode('.', $token);
        if (count($parts) !== 2) {
            return null;
        }

        [$payload_base64, $signature] = $parts;

        // Verify signature.
        $expected_signature = $this->sign($payload_base64);
        if (!hash_equals($expected_signature, $signature)) {
            return null;
        }

        // Decode payload.
        $payload_json = $this->base64url_decode($payload_base64);
        $payload = json_decode($payload_json, true);

        if (!$payload) {
            return null;
        }

        // Check expiry.
        if (isset($payload['expires']) && time() > $payload['expires']) {
            return null;
        }

        return $payload;
    }

    /**
     * Base64 URL-safe decoding.
     *
     * @param string $data The URL-safe base64 encoded string.
     * @return string The decoded data.
     */
    private function base64url_decode(string $data): string
    {
        $remainder = strlen($data) % 4;
        if ($remainder) {
            $data .= str_repeat('=', 4 - $remainder);
        }
        return base64_decode(strtr($data, '-_', '+/'));
    }

    /**
     * Check if the token manager is properly configured.
     *
     * @return bool True if configured, false otherwise.
     */
    public function is_configured(): bool
    {
        return !empty($this->secret) && !empty(get_config('local_attackbox', 'api_url'));
    }

    /**
     * Get the configured API URL.
     *
     * @return string The orchestrator API URL.
     */
    public function get_api_url(): string
    {
        return get_config('local_attackbox', 'api_url') ?: '';
    }

    /**
     * Generate a token for admin operations (for get_all_sessions.php).
     * Returns the token and API URL in a format compatible with the admin endpoint.
     *
     * @param int $userid The admin user ID
     * @return array|null Array with 'token' and 'api_url', or null if not configured
     */
    public function get_token_for_admin(int $userid): ?array
    {
        global $DB;

        if (!$this->is_configured()) {
            return null;
        }

        $user = $DB->get_record('user', ['id' => $userid]);
        if (!$user) {
            return null;
        }

        $token = $this->generate_token($user);
        $api_url = $this->get_api_url();

        return [
            'token' => $token,
            'api_url' => $api_url,
        ];
    }
}

