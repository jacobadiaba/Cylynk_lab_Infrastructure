# modules/storage/variables.tf

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

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "enable_versioning" {
  description = "Enable versioning on S3 buckets"
  type        = bool
  default     = true
}

variable "enable_lifecycle_rules" {
  description = "Enable lifecycle rules for S3 buckets"
  type        = bool
  default     = false
}

variable "lifecycle_transition_days" {
  description = "Number of days before transitioning objects to IA storage"
  type        = number
  default     = 90
  validation {
    condition     = var.lifecycle_transition_days >= 30
    error_message = "Transition days must be at least 30."
  }
}

variable "lifecycle_expiration_days" {
  description = "Number of days before expiring objects"
  type        = number
  default     = 365
  validation {
    condition     = var.lifecycle_expiration_days >= 30
    error_message = "Expiration days must be at least 30 days."
  }
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}