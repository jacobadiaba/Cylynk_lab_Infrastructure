# modules/security/variables.tf

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where security groups will be created"
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH"
  type        = string
  default     = "0.0.0.0/0"
}

variable "vpn_port" {
  description = "WireGuard VPN port"
  type        = number
  default     = 51820
}

variable "vpn_subnet_cidr" {
  description = "VPN subnet CIDR for WireGuard"
  type        = string
  default     = "10.50.0.0/16"
}

variable "attackbox_subnet_cidr" {
  description = "AttackBox pool subnet CIDR"
  type        = string
}

variable "existing_key_pair_name" {
  description = "Name of an existing AWS key pair to associate with EC2 instances"
  type        = string
  validation {
    condition     = trimspace(var.existing_key_pair_name) != ""
    error_message = "Existing_key_pair_name must be provided."
  }
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}