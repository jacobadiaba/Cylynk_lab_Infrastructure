# modules/orchestrator/variables.tf

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

# Networking
variable "vpc_id" {
  description = "VPC ID for Lambda VPC configuration"
  type        = string
  default     = ""
}

variable "subnet_ids" {
  description = "Subnet IDs for Lambda VPC configuration"
  type        = list(string)
  default     = []
}

variable "lambda_security_group_id" {
  description = "Security group ID for Lambda functions"
  type        = string
  default     = ""
}

variable "enable_vpc_config" {
  description = "Enable VPC configuration for Lambda (requires VPC endpoints for AWS services)"
  type        = bool
  default     = false
}

# AttackBox Integration - Multi-tier pools
variable "attackbox_pools" {
  description = "ASG configuration per plan tier (freemium, starter, pro)"
  type = map(object({
    asg_name = string
    asg_arn  = string
  }))
  default = {}
}

variable "attackbox_security_group_id" {
  description = "Security group ID for AttackBox instances"
  type        = string
}

# Guacamole Integration
variable "guacamole_private_ip" {
  description = "Private IP of the Guacamole server (for internal API calls)"
  type        = string
}

variable "guacamole_public_ip" {
  description = "Public IP of the Guacamole server (for student-facing URLs)"
  type        = string
  default     = ""
}

variable "guacamole_api_url" {
  description = "Guacamole public URL (e.g., https://guac.example.com/guacamole) - used for student connections"
  type        = string
  default     = ""
}

variable "guacamole_admin_username" {
  description = "Guacamole admin username"
  type        = string
  default     = "guacadmin"
  sensitive   = true
}

variable "guacamole_admin_password" {
  description = "Guacamole admin password"
  type        = string
  default     = ""
  sensitive   = true
}

# RDP Connection Defaults
variable "rdp_username" {
  description = "Default RDP username for AttackBox connections"
  type        = string
  default     = "kali"
}

variable "rdp_password" {
  description = "Default RDP password for AttackBox connections"
  type        = string
  default     = "kali"
  sensitive   = true
}

# Session Configuration
variable "session_ttl_hours" {
  description = "Session TTL in hours before auto-cleanup"
  type        = number
  default     = 4
}

variable "max_sessions_per_student" {
  description = "Maximum concurrent sessions per student"
  type        = number
  default     = 1
}

variable "instance_warmup_timeout_seconds" {
  description = "Timeout in seconds to wait for instance to become ready"
  type        = number
  default     = 300
}

# API Configuration
variable "api_stage_name" {
  description = "API Gateway stage name"
  type        = string
  default     = "v1"
}

variable "enable_api_key" {
  description = "Require API key for API Gateway"
  type        = bool
  default     = true
}

variable "allowed_origins" {
  description = "Allowed CORS origins"
  type        = list(string)
  default     = ["*"]
}

# Moodle Integration
variable "moodle_webhook_secret" {
  description = "Shared secret for Moodle webhook authentication (must match the secret in Moodle plugin settings)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "require_moodle_auth" {
  description = "Require Moodle token authentication for session creation"
  type        = bool
  default     = false
}

# Monitoring
variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "enable_xray_tracing" {
  description = "Enable AWS X-Ray tracing for Lambda"
  type        = bool
  default     = false
}

variable "alarm_sns_topic_arns" {
  description = "SNS topic ARNs for CloudWatch alarms"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}

