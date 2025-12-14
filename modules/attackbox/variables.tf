# modules/attackbox/variables.tf

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be dev, staging, or production."
  }
}

variable "custom_ami_id" {
  description = "Custom AMI ID for AttackBox (leave empty to use latest Kali)"
  type        = string
  default     = ""
}

variable "use_custom_ami" {
  description = "Use custom built AMI from Packer"
  type        = bool
  default     = true
}

variable "instance_type" {
  description = "EC2 instance type for AttackBox"
  type        = string
  default     = "t3.medium"
  validation {
    condition     = can(regex("^t[2-3]\\.(micro|small|medium|large|xlarge)", var.instance_type))
    error_message = "Instance type must be a valid t2 or t3 instance."
  }
}

variable "subnet_ids" {
  description = "List of subnet IDs for AttackBox pool"
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group ID for AttackBox instances"
  type        = string
}

variable "iam_instance_profile_name" {
  description = "IAM instance profile name for AttackBox instances"
  type        = string
}

variable "key_name" {
  description = "SSH key pair name"
  type        = string
}

variable "guacamole_private_ip" {
  description = "Private IP of Guacamole server"
  type        = string
}

# Pool Configuration
variable "pool_size" {
  description = "Desired number of AttackBox instances in pool"
  type        = number
  validation {
    condition     = var.pool_size >= 1 && var.pool_size <= 100
    error_message = "Pool size must be between 1 and 100."
  }
}

variable "min_pool_size" {
  description = "Minimum number of AttackBox instances"
  type        = number

}

variable "max_pool_size" {
  description = "Maximum number of AttackBox instances"
  type        = number
  
}

# Volume Configuration
variable "root_volume_size" {
  description = "Size of root volume in GB"
  type        = number
  default     = 80
  validation {
    condition     = var.root_volume_size >= 20 && var.root_volume_size <= 100
    error_message = "Root volume size must be between 20 and 100 GB."
  }
}

variable "root_volume_iops" {
  description = "IOPS for root volume (gp3)"
  type        = number
  default     = 3000
}

variable "root_volume_throughput" {
  description = "Throughput for root volume in MB/s (gp3)"
  type        = number
  default     = 125
}

# Auto Scaling Configuration
variable "enable_auto_scaling" {
  description = "Enable auto scaling based on CPU"
  type        = bool
  default     = false
}

variable "scale_up_adjustment" {
  description = "Number of instances to add when scaling up"
  type        = number
  default     = 2
}

variable "scale_down_adjustment" {
  description = "Number of instances to remove when scaling down"
  type        = number
  default     = -1
}

variable "scale_up_cooldown" {
  description = "Cooldown period in seconds after scale up"
  type        = number
  default     = 300
}

variable "scale_down_cooldown" {
  description = "Cooldown period in seconds after scale down"
  type        = number
  default     = 600
}

# Scheduled Scaling
variable "enable_scheduled_scaling" {
  description = "Enable scheduled scaling for off-hours"
  type        = bool
  default     = false
}

variable "offhours_min_size" {
  description = "Minimum pool size during off-hours"
  type        = number
  default     = 0
}

variable "offhours_desired_size" {
  description = "Desired pool size during off-hours"
  type        = number
  default     = 2
}

# Monitoring
variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

variable "enable_notifications" {
  description = "Enable SNS notifications for Auto Scaling events"
  type        = bool
  default     = false
}

# Session Tracking
variable "enable_session_tracking" {
  description = "Enable DynamoDB table for session tracking"
  type        = bool
  default     = true
}

# Tags
variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}