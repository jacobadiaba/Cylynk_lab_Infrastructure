# modules/cost-optimization/variables.tf

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

# =============================================================================
# Budget Configuration
# =============================================================================

variable "enable_daily_budget" {
  description = "Enable daily budget tracking and alerts"
  type        = bool
  default     = false
}

variable "daily_budget_limit" {
  description = "Daily budget limit in USD"
  type        = number
  default     = 20
}

variable "enable_monthly_budget" {
  description = "Enable monthly budget tracking and alerts"
  type        = bool
  default     = false
}

variable "monthly_budget_limit" {
  description = "Monthly budget limit in USD"
  type        = number
  default     = 500
}

variable "enable_ec2_usage_budget" {
  description = "Enable EC2 usage hours budget tracking"
  type        = bool
  default     = false
}

variable "ec2_usage_hours_limit" {
  description = "Monthly EC2 usage hours limit"
  type        = number
  default     = 1000
}

variable "budget_alert_emails" {
  description = "List of email addresses to receive budget alerts"
  type        = list(string)
  default     = []
}

# =============================================================================
# Compute Optimizer Configuration
# =============================================================================

variable "enable_compute_optimizer" {
  description = "Enable AWS Compute Optimizer for right-sizing recommendations"
  type        = bool
  default     = true
}

variable "enable_cost_optimizer_lambda" {
  description = "Enable Lambda function for scheduled cost optimization reports"
  type        = bool
  default     = false
}

# =============================================================================
# Cost Anomaly Detection Configuration
# =============================================================================

variable "enable_cost_anomaly_detection" {
  description = "Enable AWS Cost Anomaly Detection"
  type        = bool
  default     = false
}

variable "monitor_linked_accounts" {
  description = "Monitor linked accounts for anomalies (for AWS Organizations)"
  type        = bool
  default     = false
}

variable "anomaly_alert_emails" {
  description = "List of email addresses to receive anomaly alerts"
  type        = list(string)
  default     = []
}

variable "anomaly_alert_sns_arn" {
  description = "SNS topic ARN for anomaly alerts (optional)"
  type        = string
  default     = ""
}

variable "anomaly_threshold_amount" {
  description = "Minimum anomaly impact amount in USD to trigger alert"
  type        = string
  default     = "10"
}

# =============================================================================
# Cost Dashboard Configuration
# =============================================================================

variable "enable_cost_dashboard" {
  description = "Enable CloudWatch dashboard for cost monitoring"
  type        = bool
  default     = true
}

variable "enable_cost_alarms" {
  description = "Enable CloudWatch alarms for cost thresholds"
  type        = bool
  default     = true
}

variable "cost_alarm_sns_arn" {
  description = "SNS topic ARN for cost alarm notifications"
  type        = string
  default     = ""
}

# =============================================================================
# SNS Configuration
# =============================================================================

variable "enable_sns_encryption" {
  description = "Enable KMS encryption for SNS topics"
  type        = bool
  default     = false
}

# =============================================================================
# Logging Configuration
# =============================================================================

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

# =============================================================================
# Tags
# =============================================================================

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}
