# modules/orchestrator/outputs.tf

output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = aws_apigatewayv2_api.orchestrator.api_endpoint
}

output "api_id" {
  description = "API Gateway ID"
  value       = aws_apigatewayv2_api.orchestrator.id
}

output "api_stage_url" {
  description = "Full API stage URL"
  value       = "${aws_apigatewayv2_api.orchestrator.api_endpoint}/${var.api_stage_name}"
}

output "sessions_table_name" {
  description = "DynamoDB sessions table name"
  value       = aws_dynamodb_table.sessions.name
}

output "sessions_table_arn" {
  description = "DynamoDB sessions table ARN"
  value       = aws_dynamodb_table.sessions.arn
}

output "instance_pool_table_name" {
  description = "DynamoDB instance pool table name"
  value       = aws_dynamodb_table.instance_pool.name
}

output "instance_pool_table_arn" {
  description = "DynamoDB instance pool table ARN"
  value       = aws_dynamodb_table.instance_pool.arn
}

output "usage_table_name" {
  description = "DynamoDB usage tracking table name"
  value       = aws_dynamodb_table.usage.name
}

output "usage_table_arn" {
  description = "DynamoDB usage tracking table ARN"
  value       = aws_dynamodb_table.usage.arn
}

output "lambda_role_arn" {
  description = "IAM role ARN for Lambda functions"
  value       = aws_iam_role.lambda_role.arn
}

output "create_session_function_name" {
  description = "Create session Lambda function name"
  value       = aws_lambda_function.create_session.function_name
}

output "terminate_session_function_name" {
  description = "Terminate session Lambda function name"
  value       = aws_lambda_function.terminate_session.function_name
}

output "get_session_status_function_name" {
  description = "Get session status Lambda function name"
  value       = aws_lambda_function.get_session_status.function_name
}

output "pool_manager_function_name" {
  description = "Pool manager Lambda function name"
  value       = aws_lambda_function.pool_manager.function_name
}

output "get_usage_function_name" {
  description = "Get usage Lambda function name"
  value       = aws_lambda_function.get_usage.function_name
}

# API Endpoints for Moodle integration
output "create_session_endpoint" {
  description = "Endpoint to create a new session"
  value       = "${aws_apigatewayv2_api.orchestrator.api_endpoint}/${var.api_stage_name}/sessions"
}

output "get_session_endpoint" {
  description = "Endpoint to get session status (append /{sessionId})"
  value       = "${aws_apigatewayv2_api.orchestrator.api_endpoint}/${var.api_stage_name}/sessions"
}

output "terminate_session_endpoint" {
  description = "Endpoint to terminate a session (append /{sessionId})"
  value       = "${aws_apigatewayv2_api.orchestrator.api_endpoint}/${var.api_stage_name}/sessions"
}

output "student_sessions_endpoint" {
  description = "Endpoint to get student sessions (append /{studentId}/sessions)"
  value       = "${aws_apigatewayv2_api.orchestrator.api_endpoint}/${var.api_stage_name}/students"
}

output "get_usage_endpoint" {
  description = "Endpoint to get usage statistics"
  value       = "${aws_apigatewayv2_api.orchestrator.api_endpoint}/${var.api_stage_name}/usage"
}
