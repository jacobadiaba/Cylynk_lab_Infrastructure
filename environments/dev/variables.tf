# environments/prod/variables.tf

# General Configuration
variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "cyberlab"
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "owner" {
  description = "Owner of the infrastructure"
  type        = string
}

variable "cost_center" {
  description = "Cost center for billing"
  type        = string
  default     = "education"
}

# Networking Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "management_subnet_cidr" {
  description = "CIDR block for management subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "attackbox_subnet_cidr" {
  description = "CIDR block for AttackBox pool subnet"
  type        = string
  default     = "10.0.10.0/24"
}

variable "student_labs_cidr" {
  description = "CIDR block for student lab subnets"
  type        = string
  default     = "10.0.100.0/20"
}

variable "student_lab_subnet_count" {
  description = "Number of student lab subnets"
  type        = number
  default     = 20
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway"
  type        = bool
  default     = true
}

variable "enable_flow_logs" {
  description = "Enable VPC Flow Logs"
  type        = bool
  default     = true
}

variable "enable_vpc_endpoints" {
  description = "Enable VPC endpoints"
  type        = bool
  default     = true
}

# Security Configuration
variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH"
  type        = string
}

variable "vpn_port" {
  description = "WireGuard VPN port"
  type        = number
  default     = 51820
}

variable "vpn_subnet_cidr" {
  description = "VPN subnet CIDR"
  type        = string
  default     = "10.50.0.0/16"
}

variable "existing_key_pair_name" {
  description = "Existing AWS key pair name to associate with instances"
  type        = string
  validation {
    condition     = trimspace(var.existing_key_pair_name) != ""
    error_message = "Existing_key_pair_name must be provided."
  }
}

# Guacamole Configuration
variable "guacamole_instance_type" {
  description = "Instance type for Guacamole"
  type        = string
  default     = "t3.small"
}

variable "guacamole_domain_name" {
  description = "Domain name for Guacamole (for Let's Encrypt)"
  type        = string
  default     = ""
}

variable "enable_lets_encrypt" {
  description = "Enable Let's Encrypt SSL"
  type        = bool
  default     = false
}

# VPN Configuration
variable "vpn_instance_type" {
  description = "Instance type for VPN server"
  type        = string
  default     = "t3.micro"
}

# Monitoring Configuration
variable "enable_sns_alarms" {
  description = "Enable SNS alarm notifications"
  type        = bool
  default     = true
}

variable "alarm_email" {
  description = "Email for CloudWatch alarms"
  type        = string
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "enable_cost_anomaly_detection" {
  description = "Enable AWS Cost Anomaly Detection resources"
  type        = bool
  default     = false
}

variable "cost_anomaly_threshold" {
  description = "Dollar threshold for cost anomaly alerts"
  type        = number
  default     = 100
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