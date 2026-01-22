# environments/prod/variables.tf

# General Configuration
variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
}

variable "owner" {
  description = "Owner of the infrastructure"
  type        = string
}

variable "cost_center" {
  description = "Cost center for billing"
  type        = string
}

# Networking Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
}

variable "management_subnet_cidr" {
  description = "CIDR block for management subnet"
  type        = string
}

variable "attackbox_subnet_cidr" {
  description = "CIDR block for AttackBox pool subnet"
  type        = string
}

variable "student_labs_cidr" {
  description = "CIDR block for student lab subnets"
  type        = string
}

variable "student_lab_subnet_count" {
  description = "Number of student lab subnets"
  type        = number
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway (not needed if attackbox_public_subnet is true)"
  type        = bool
}

variable "attackbox_public_subnet" {
  description = "Place AttackBox in public subnet"
  type        = bool
}

variable "enable_flow_logs" {
  description = "Enable VPC Flow Logs"
  type        = bool
}

variable "enable_vpc_endpoints" {
  description = "Enable VPC endpoints"
  type        = bool
}

# Security Configuration
variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH"
  type        = string
}

variable "vpn_port" {
  description = "WireGuard VPN port"
  type        = number
}

variable "vpn_subnet_cidr" {
  description = "VPN subnet CIDR"
  type        = string
}

variable "existing_key_pair_name" {
  description = "Existing AWS key pair name to associate with instances"
  type        = string
  validation {
    condition     = trimspace(var.existing_key_pair_name) != ""
    error_message = "existing_key_pair_name must be provided."
  }
}

# Guacamole Configuration
variable "guacamole_instance_type" {
  description = "Instance type for Guacamole"
  type        = string
}

variable "guacamole_domain_name" {
  description = "Domain name for Guacamole (for Let's Encrypt)"
  type        = string
}

variable "enable_lets_encrypt" {
  description = "Enable Let's Encrypt SSL"
  type        = bool
}

# Monitoring Configuration
variable "enable_sns_alarms" {
  description = "Enable SNS alarm notifications"
  type        = bool
}

variable "alarm_email" {
  description = "Email for CloudWatch alarms"
  type        = string
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
}

variable "enable_cost_anomaly_detection" {
  description = "Enable AWS Cost Anomaly Detection resources"
  type        = bool
}

variable "cost_anomaly_threshold" {
  description = "Dollar threshold for cost anomaly alerts"
  type        = number
  validation {
    condition     = var.cost_anomaly_threshold >= 1
    error_message = "Cost anomaly threshold must be at least $1."
  }
}

# Contact Information
variable "admin_email" {
  description = "Administrator email"
  type        = string
}

# AttackBox Configuration
variable "attackbox_ami_id" {
  description = "Custom AMI ID for AttackBox"
  type        = string
}

variable "attackbox_tiers" {
  description = "Configuration for each AttackBox tier (freemium, starter, pro)"
  type = map(object({
    instance_type = string
    pool_size     = number
    min_pool_size = number
    max_pool_size = number
    warm_pool_min = number
    warm_pool_max = number
  }))
}

# Orchestrator Configuration
variable "session_ttl_hours" {
  description = "Session TTL in hours before auto-cleanup"
  type        = number
}

variable "max_sessions_per_student" {
  description = "Maximum concurrent sessions per student"
  type        = number
}

variable "enable_orchestrator_api_key" {
  description = "Require API key for orchestrator API"
  type        = bool
}

variable "orchestrator_allowed_origins" {
  description = "Allowed CORS origins for orchestrator API"
  type        = list(string)
}

variable "moodle_webhook_secret" {
  description = "Shared secret for Moodle webhook authentication"
  type        = string
  sensitive   = true
}

variable "guacamole_admin_username" {
  description = "Guacamole admin username for API access"
  type        = string
  sensitive   = true
}

variable "guacamole_admin_password" {
  description = "Guacamole admin password for API access"
  type        = string
  sensitive   = true
}

variable "rdp_username" {
  description = "RDP username for AttackBox (must match AMI configuration)"
  type        = string
}

variable "rdp_password" {
  description = "RDP password for AttackBox (must match AMI configuration)"
  type        = string
  sensitive   = true
}

