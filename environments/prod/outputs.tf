# environments/prod/outputs.tf

# =============================================================================
# Networking Outputs
# =============================================================================

output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
}

output "management_subnet_id" {
  description = "Management subnet ID"
  value       = module.networking.management_subnet_id
}

output "attackbox_subnet_id" {
  description = "AttackBox pool subnet ID"
  value       = module.networking.attackbox_pool_subnet_id
}

# =============================================================================
# Guacamole Outputs
# =============================================================================

output "guacamole_public_ip" {
  description = "Guacamole server public IP"
  value       = module.guacamole.public_ip
}

output "guacamole_private_ip" {
  description = "Guacamole server private IP"
  value       = module.guacamole.private_ip
}

output "guacamole_url" {
  description = "Guacamole web interface URL"
  value       = "https://${var.guacamole_domain_name}"
}

# =============================================================================
# AttackBox Outputs - Multi-Tier Pools
# =============================================================================

output "attackbox_pools" {
  description = "AttackBox Auto Scaling Group names by tier"
  value = {
    freemium = module.attackbox_freemium.autoscaling_group_name
    starter  = module.attackbox_starter.autoscaling_group_name
    pro      = module.attackbox_pro.autoscaling_group_name
  }
}

# =============================================================================
# Orchestrator API Outputs
# =============================================================================

output "orchestrator_api_endpoint" {
  description = "Orchestrator API base endpoint"
  value       = module.orchestrator.api_endpoint
}

output "orchestrator_api_url" {
  description = "Full Orchestrator API URL with stage"
  value       = module.orchestrator.api_stage_url
}

