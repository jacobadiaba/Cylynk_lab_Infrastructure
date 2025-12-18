# modules/networking/variables.tf

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
  description = "CIDR block for student lab subnets (will be subdivided)"
  type        = string
  default     = "10.0.100.0/20"
}

variable "student_lab_subnet_count" {
  description = "Number of student lab subnets to create"
  type        = number
  default     = 10
  validation {
    condition     = var.student_lab_subnet_count > 0 && var.student_lab_subnet_count <= 64
    error_message = "Student lab subnet count must be between 1 and 64."
  }
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnets (not needed if attackbox_public_subnet is true)"
  type        = bool
  default     = true
}

variable "attackbox_public_subnet" {
  description = "Place AttackBox instances in public subnet (saves NAT Gateway cost, uses security groups for protection)"
  type        = bool
  default     = false
}

variable "enable_flow_logs" {
  description = "Enable VPC Flow Logs"
  type        = bool
  default     = true
}

variable "flow_logs_role_arn" {
  description = "IAM role ARN for VPC Flow Logs"
  type        = string
  default     = ""
}

variable "flow_logs_destination_arn" {
  description = "CloudWatch Log Group ARN for Flow Logs"
  type        = string
  default     = ""
}

variable "enable_vpc_endpoints" {
  description = "Enable VPC endpoints for AWS services"
  type        = bool
  default     = false
}

variable "vpc_endpoint_security_group_ids" {
  description = "Security group IDs for VPC endpoints"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}