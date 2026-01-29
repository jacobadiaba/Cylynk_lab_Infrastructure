# environments/dev/outputs.tf

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
  value       = var.guacamole_domain_name != "" ? "https://${var.guacamole_domain_name}" : "https://${module.guacamole.public_ip}"
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

output "attackbox_pool_configs" {
  description = "AttackBox pool configurations by tier"
  value = {
    freemium = module.attackbox_freemium.pool_configuration
    starter  = module.attackbox_starter.pool_configuration
    pro      = module.attackbox_pro.pool_configuration
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

output "orchestrator_create_session_endpoint" {
  description = "Endpoint to create a new AttackBox session"
  value       = module.orchestrator.create_session_endpoint
}

output "orchestrator_sessions_table" {
  description = "DynamoDB table for session tracking"
  value       = module.orchestrator.sessions_table_name
}

# =============================================================================
# Moodle Integration Info
# =============================================================================

output "moodle_integration_info" {
  description = "Information needed to integrate with Moodle"
  value = {
    api_base_url        = module.orchestrator.api_stage_url
    create_session      = "POST ${module.orchestrator.create_session_endpoint}"
    get_session         = "GET ${module.orchestrator.get_session_endpoint}/{sessionId}"
    terminate_session   = "DELETE ${module.orchestrator.terminate_session_endpoint}/{sessionId}"
    get_student_sessions = "GET ${module.orchestrator.student_sessions_endpoint}/{studentId}/sessions"
    guacamole_url       = var.guacamole_domain_name != "" ? "https://${var.guacamole_domain_name}" : "https://${module.guacamole.public_ip}"
  }
}

# =============================================================================
# Monitoring Outputs
# =============================================================================

output "sns_topic_arn" {
  description = "SNS topic ARN for alarms"
  value       = module.monitoring.sns_topic_arn
}

