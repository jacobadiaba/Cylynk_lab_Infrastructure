# modules/orchestrator/main.tf
# Lab Session Orchestrator - Lambda + API Gateway + DynamoDB

terraform {
  required_version = ">= 1.0"
}

locals {
  function_name_prefix = "${var.project_name}-${var.environment}"
  
  common_tags = merge(
    var.tags,
    {
      Component   = "Orchestrator"
      Environment = var.environment
    }
  )
}

# =============================================================================
# DynamoDB Tables
# =============================================================================

# Sessions table - tracks active student sessions
resource "aws_dynamodb_table" "sessions" {
  name         = "${var.project_name}-${var.environment}-sessions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "session_id"

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "student_id"
    type = "S"
  }

  attribute {
    name = "instance_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name            = "StudentIndex"
    hash_key        = "student_id"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "InstanceIndex"
    hash_key        = "instance_id"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "StatusIndex"
    hash_key        = "status"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = var.environment == "production"
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-${var.environment}-sessions"
    }
  )
}

# Instance pool table - tracks available/assigned AttackBox instances
resource "aws_dynamodb_table" "instance_pool" {
  name         = "${var.project_name}-${var.environment}-instance-pool"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "instance_id"

  attribute {
    name = "instance_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name            = "StatusIndex"
    hash_key        = "status"
    projection_type = "ALL"
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-${var.environment}-instance-pool"
    }
  )
}

# Usage tracking table - tracks monthly AttackBox usage per user
resource "aws_dynamodb_table" "usage" {
  name         = "${var.project_name}-${var.environment}-usage"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"
  range_key    = "usage_month"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "usage_month"
    type = "S"
  }

  global_secondary_index {
    name            = "MonthIndex"
    hash_key        = "usage_month"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = var.environment == "production"
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-${var.environment}-usage"
    }
  )
}

# =============================================================================
# IAM Role for Lambda Functions
# =============================================================================

resource "aws_iam_role" "lambda_role" {
  name = "${local.function_name_prefix}-orchestrator-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# Lambda basic execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Lambda VPC access policy
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Custom policy for orchestrator operations
resource "aws_iam_role_policy" "orchestrator_policy" {
  name = "${local.function_name_prefix}-orchestrator-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DynamoDBAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.sessions.arn,
          "${aws_dynamodb_table.sessions.arn}/index/*",
          aws_dynamodb_table.instance_pool.arn,
          "${aws_dynamodb_table.instance_pool.arn}/index/*",
          aws_dynamodb_table.usage.arn,
          "${aws_dynamodb_table.usage.arn}/index/*"
        ]
      },
      {
        Sid    = "EC2Describe"
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeInstanceStatus",
          "ec2:DescribeTags"
        ]
        Resource = "*"
      },
      {
        Sid    = "EC2InstanceManagement"
        Effect = "Allow"
        Action = [
          "ec2:StartInstances",
          "ec2:StopInstances",
          "ec2:CreateTags"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "ec2:ResourceTag/Role" = "AttackBox"
          }
        }
      },
      {
        Sid    = "AutoScalingAccess"
        Effect = "Allow"
        Action = [
          "autoscaling:DescribeAutoScalingGroups",
          "autoscaling:SetDesiredCapacity",
          "autoscaling:UpdateAutoScalingGroup"
        ]
        Resource = "*"
      },
      {
        Sid    = "SSMParameterAccess"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = "arn:aws:ssm:${var.aws_region}:*:parameter/${var.project_name}/${var.environment}/*"
      },
      {
        Sid    = "SecretsManagerAccess"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "arn:aws:secretsmanager:${var.aws_region}:*:secret:${var.project_name}/${var.environment}/*"
      }
    ]
  })
}

# X-Ray tracing policy (optional)
resource "aws_iam_role_policy_attachment" "lambda_xray" {
  count      = var.enable_xray_tracing ? 1 : 0
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# =============================================================================
# Lambda Layer for Common Code
# =============================================================================

resource "aws_lambda_layer_version" "common" {
  filename            = "${path.module}/lambda/layers/common.zip"
  layer_name          = "${local.function_name_prefix}-orchestrator-common"
  compatible_runtimes = ["python3.11", "python3.12"]
  description         = "Common utilities for orchestrator Lambda functions"

  source_code_hash = fileexists("${path.module}/lambda/layers/common.zip") ? filebase64sha256("${path.module}/lambda/layers/common.zip") : null
}

# =============================================================================
# CloudWatch Log Groups
# =============================================================================

resource "aws_cloudwatch_log_group" "create_session" {
  name              = "/aws/lambda/${local.function_name_prefix}-create-session"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "terminate_session" {
  name              = "/aws/lambda/${local.function_name_prefix}-terminate-session"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "get_session_status" {
  name              = "/aws/lambda/${local.function_name_prefix}-get-session-status"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "pool_manager" {
  name              = "/aws/lambda/${local.function_name_prefix}-pool-manager"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "get_usage" {
  name              = "/aws/lambda/${local.function_name_prefix}-get-usage"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "usage_history" {
  name              = "/aws/lambda/${local.function_name_prefix}-usage-history"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

# =============================================================================
# Lambda Functions
# =============================================================================

# Create Session Lambda
resource "aws_lambda_function" "create_session" {
  filename         = "${path.module}/lambda/packages/create-session.zip"
  function_name    = "${local.function_name_prefix}-create-session"
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.handler"
  runtime          = "python3.11"
  timeout          = 60
  memory_size      = 256

  source_code_hash = fileexists("${path.module}/lambda/packages/create-session.zip") ? filebase64sha256("${path.module}/lambda/packages/create-session.zip") : null

  layers = [aws_lambda_layer_version.common.arn]

  environment {
    variables = {
      SESSIONS_TABLE        = aws_dynamodb_table.sessions.name
      INSTANCE_POOL_TABLE   = aws_dynamodb_table.instance_pool.name
      USAGE_TABLE           = aws_dynamodb_table.usage.name
      ASG_NAME              = var.attackbox_asg_name
      GUACAMOLE_PRIVATE_IP  = var.guacamole_private_ip
      GUACAMOLE_PUBLIC_IP   = var.guacamole_public_ip
      GUACAMOLE_API_URL     = var.guacamole_api_url
      GUACAMOLE_ADMIN_USER  = var.guacamole_admin_username
      GUACAMOLE_ADMIN_PASS  = var.guacamole_admin_password
      RDP_USERNAME          = var.rdp_username
      RDP_PASSWORD          = var.rdp_password
      SESSION_TTL_HOURS     = tostring(var.session_ttl_hours)
      MAX_SESSIONS          = tostring(var.max_sessions_per_student)
      MOODLE_WEBHOOK_SECRET = var.moodle_webhook_secret
      REQUIRE_MOODLE_AUTH   = tostring(var.require_moodle_auth)
      ENVIRONMENT           = var.environment
      PROJECT_NAME          = var.project_name
      AWS_REGION_NAME       = var.aws_region
    }
  }

  dynamic "vpc_config" {
    for_each = var.enable_vpc_config ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = [var.lambda_security_group_id]
    }
  }

  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }

  depends_on = [aws_cloudwatch_log_group.create_session]

  tags = merge(
    local.common_tags,
    {
      Name = "${local.function_name_prefix}-create-session"
    }
  )
}

# Terminate Session Lambda
resource "aws_lambda_function" "terminate_session" {
  filename         = "${path.module}/lambda/packages/terminate-session.zip"
  function_name    = "${local.function_name_prefix}-terminate-session"
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.handler"
  runtime          = "python3.11"
  timeout          = 60
  memory_size      = 256

  source_code_hash = fileexists("${path.module}/lambda/packages/terminate-session.zip") ? filebase64sha256("${path.module}/lambda/packages/terminate-session.zip") : null

  layers = [aws_lambda_layer_version.common.arn]

  environment {
    variables = {
      SESSIONS_TABLE       = aws_dynamodb_table.sessions.name
      INSTANCE_POOL_TABLE  = aws_dynamodb_table.instance_pool.name
      USAGE_TABLE          = aws_dynamodb_table.usage.name
      GUACAMOLE_PRIVATE_IP = var.guacamole_private_ip
      GUACAMOLE_API_URL    = var.guacamole_api_url
      GUACAMOLE_ADMIN_USER = var.guacamole_admin_username
      GUACAMOLE_ADMIN_PASS = var.guacamole_admin_password
      ENVIRONMENT          = var.environment
      PROJECT_NAME         = var.project_name
      AWS_REGION_NAME      = var.aws_region
    }
  }

  dynamic "vpc_config" {
    for_each = var.enable_vpc_config ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = [var.lambda_security_group_id]
    }
  }

  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }

  depends_on = [aws_cloudwatch_log_group.terminate_session]

  tags = merge(
    local.common_tags,
    {
      Name = "${local.function_name_prefix}-terminate-session"
    }
  )
}

# Get Session Status Lambda
resource "aws_lambda_function" "get_session_status" {
  filename         = "${path.module}/lambda/packages/get-session-status.zip"
  function_name    = "${local.function_name_prefix}-get-session-status"
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.handler"
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 128

  source_code_hash = fileexists("${path.module}/lambda/packages/get-session-status.zip") ? filebase64sha256("${path.module}/lambda/packages/get-session-status.zip") : null

  layers = [aws_lambda_layer_version.common.arn]

  environment {
    variables = {
      SESSIONS_TABLE      = aws_dynamodb_table.sessions.name
      INSTANCE_POOL_TABLE = aws_dynamodb_table.instance_pool.name
      USAGE_TABLE         = aws_dynamodb_table.usage.name
      ENVIRONMENT         = var.environment
      PROJECT_NAME        = var.project_name
      AWS_REGION_NAME     = var.aws_region
    }
  }

  dynamic "vpc_config" {
    for_each = var.enable_vpc_config ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = [var.lambda_security_group_id]
    }
  }

  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }

  depends_on = [aws_cloudwatch_log_group.get_session_status]

  tags = merge(
    local.common_tags,
    {
      Name = "${local.function_name_prefix}-get-session-status"
    }
  )
}

# Pool Manager Lambda (scheduled cleanup and scaling)
resource "aws_lambda_function" "pool_manager" {
  filename         = "${path.module}/lambda/packages/pool-manager.zip"
  function_name    = "${local.function_name_prefix}-pool-manager"
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.handler"
  runtime          = "python3.11"
  timeout          = 120
  memory_size      = 256

  source_code_hash = fileexists("${path.module}/lambda/packages/pool-manager.zip") ? filebase64sha256("${path.module}/lambda/packages/pool-manager.zip") : null

  layers = [aws_lambda_layer_version.common.arn]

  environment {
    variables = {
      SESSIONS_TABLE      = aws_dynamodb_table.sessions.name
      INSTANCE_POOL_TABLE = aws_dynamodb_table.instance_pool.name
      USAGE_TABLE         = aws_dynamodb_table.usage.name
      ASG_NAME            = var.attackbox_asg_name
      ENVIRONMENT         = var.environment
      PROJECT_NAME        = var.project_name
      AWS_REGION_NAME     = var.aws_region
    }
  }

  dynamic "vpc_config" {
    for_each = var.enable_vpc_config ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = [var.lambda_security_group_id]
    }
  }

  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }

  depends_on = [aws_cloudwatch_log_group.pool_manager]

  tags = merge(
    local.common_tags,
    {
      Name = "${local.function_name_prefix}-pool-manager"
    }
  )
}

# Get Usage Lambda
resource "aws_lambda_function" "get_usage" {
  filename         = "${path.module}/lambda/packages/get-usage.zip"
  function_name    = "${local.function_name_prefix}-get-usage"
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.handler"
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 128

  source_code_hash = fileexists("${path.module}/lambda/packages/get-usage.zip") ? filebase64sha256("${path.module}/lambda/packages/get-usage.zip") : null

  layers = [aws_lambda_layer_version.common.arn]

  environment {
    variables = {
      USAGE_TABLE           = aws_dynamodb_table.usage.name
      MOODLE_WEBHOOK_SECRET = var.moodle_webhook_secret
      REQUIRE_MOODLE_AUTH   = tostring(var.require_moodle_auth)
      ENVIRONMENT           = var.environment
      PROJECT_NAME          = var.project_name
      AWS_REGION_NAME       = var.aws_region
    }
  }

  dynamic "vpc_config" {
    for_each = var.enable_vpc_config ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = [var.lambda_security_group_id]
    }
  }

  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }

  depends_on = [aws_cloudwatch_log_group.get_usage]

  tags = merge(
    local.common_tags,
    {
      Name = "${local.function_name_prefix}-get-usage"
    }
  )
}

# Usage History Lambda
resource "aws_lambda_function" "usage_history" {
  filename         = "${path.module}/lambda/packages/usage-history.zip"
  function_name    = "${local.function_name_prefix}-usage-history"
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.handler"
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 128

  source_code_hash = fileexists("${path.module}/lambda/packages/usage-history.zip") ? filebase64sha256("${path.module}/lambda/packages/usage-history.zip") : null

  layers = [aws_lambda_layer_version.common.arn]

  environment {
    variables = {
      SESSIONS_TABLE        = aws_dynamodb_table.sessions.name
      MOODLE_WEBHOOK_SECRET = var.moodle_webhook_secret
      REQUIRE_MOODLE_AUTH   = tostring(var.require_moodle_auth)
      ENVIRONMENT           = var.environment
      PROJECT_NAME          = var.project_name
      AWS_REGION_NAME       = var.aws_region
    }
  }

  dynamic "vpc_config" {
    for_each = var.enable_vpc_config ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = [var.lambda_security_group_id]
    }
  }

  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }

  depends_on = [aws_cloudwatch_log_group.usage_history]

  tags = merge(
    local.common_tags,
    {
      Name = "${local.function_name_prefix}-usage-history"
    }
  )
}

# =============================================================================
# Admin Sessions Lambda
# =============================================================================

resource "aws_cloudwatch_log_group" "admin_sessions" {
  name              = "/aws/lambda/${local.function_name_prefix}-admin-sessions"
  retention_in_days = var.log_retention_days

  tags = local.common_tags
}

resource "aws_lambda_function" "admin_sessions" {
  filename         = "${path.module}/lambda/packages/admin-sessions.zip"
  function_name    = "${local.function_name_prefix}-admin-sessions"
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.lambda_handler"
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 256

  source_code_hash = fileexists("${path.module}/lambda/packages/admin-sessions.zip") ? filebase64sha256("${path.module}/lambda/packages/admin-sessions.zip") : null

  layers = [aws_lambda_layer_version.common.arn]

  environment {
    variables = {
      SESSIONS_TABLE_NAME   = aws_dynamodb_table.sessions.name
      MOODLE_WEBHOOK_SECRET = var.moodle_webhook_secret
      REQUIRE_MOODLE_AUTH   = tostring(var.require_moodle_auth)
      ENVIRONMENT           = var.environment
      PROJECT_NAME          = var.project_name
    }
  }

  dynamic "vpc_config" {
    for_each = var.enable_vpc_config ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = [var.lambda_security_group_id]
    }
  }

  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }

  depends_on = [aws_cloudwatch_log_group.admin_sessions]

  tags = merge(
    local.common_tags,
    {
      Name = "${local.function_name_prefix}-admin-sessions"
    }
  )
}

# =============================================================================
# EventBridge Schedule for Pool Manager
# =============================================================================

resource "aws_cloudwatch_event_rule" "pool_manager_schedule" {
  name                = "${local.function_name_prefix}-pool-manager-schedule"
  description         = "Trigger pool manager every 1 minute for cleanup and scaling"
  schedule_expression = "rate(1 minute)"

  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "pool_manager" {
  rule      = aws_cloudwatch_event_rule.pool_manager_schedule.name
  target_id = "pool-manager"
  arn       = aws_lambda_function.pool_manager.arn
}

resource "aws_lambda_permission" "pool_manager_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.pool_manager.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.pool_manager_schedule.arn
}

# =============================================================================
# API Gateway
# =============================================================================

resource "aws_apigatewayv2_api" "orchestrator" {
  name          = "${local.function_name_prefix}-orchestrator-api"
  protocol_type = "HTTP"
  description   = "CyberLab Session Orchestrator API"

  cors_configuration {
    allow_origins     = var.allowed_origins
    allow_methods     = ["GET", "POST", "DELETE", "OPTIONS"]
    allow_headers     = ["Content-Type", "Authorization", "X-Api-Key", "X-Moodle-Token", "X-Moodle-Signature", "Accept"]
    expose_headers    = ["X-Request-Id"]
    max_age           = 3600
    allow_credentials = false
  }

  tags = local.common_tags
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.orchestrator.id
  name        = var.api_stage_name
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      responseLength = "$context.responseLength"
      integrationLatency = "$context.integrationLatency"
    })
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${local.function_name_prefix}-orchestrator"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

# =============================================================================
# API Gateway Integrations
# =============================================================================

# Create Session Integration
resource "aws_apigatewayv2_integration" "create_session" {
  api_id                 = aws_apigatewayv2_api.orchestrator.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.create_session.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "create_session" {
  api_id    = aws_apigatewayv2_api.orchestrator.id
  route_key = "POST /sessions"
  target    = "integrations/${aws_apigatewayv2_integration.create_session.id}"
}

resource "aws_lambda_permission" "create_session_apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.create_session.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.orchestrator.execution_arn}/*/*"
}

# Get Session Status Integration
resource "aws_apigatewayv2_integration" "get_session_status" {
  api_id                 = aws_apigatewayv2_api.orchestrator.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_session_status.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "get_session_status" {
  api_id    = aws_apigatewayv2_api.orchestrator.id
  route_key = "GET /sessions/{sessionId}"
  target    = "integrations/${aws_apigatewayv2_integration.get_session_status.id}"
}

resource "aws_apigatewayv2_route" "get_student_sessions" {
  api_id    = aws_apigatewayv2_api.orchestrator.id
  route_key = "GET /students/{studentId}/sessions"
  target    = "integrations/${aws_apigatewayv2_integration.get_session_status.id}"
}

resource "aws_lambda_permission" "get_session_status_apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_session_status.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.orchestrator.execution_arn}/*/*"
}

# Terminate Session Integration
resource "aws_apigatewayv2_integration" "terminate_session" {
  api_id                 = aws_apigatewayv2_api.orchestrator.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.terminate_session.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "terminate_session" {
  api_id    = aws_apigatewayv2_api.orchestrator.id
  route_key = "DELETE /sessions/{sessionId}"
  target    = "integrations/${aws_apigatewayv2_integration.terminate_session.id}"
}

resource "aws_lambda_permission" "terminate_session_apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.terminate_session.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.orchestrator.execution_arn}/*/*"
}

# Get Usage Integration
resource "aws_apigatewayv2_integration" "get_usage" {
  api_id                 = aws_apigatewayv2_api.orchestrator.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_usage.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "get_usage" {
  api_id    = aws_apigatewayv2_api.orchestrator.id
  route_key = "GET /usage"
  target    = "integrations/${aws_apigatewayv2_integration.get_usage.id}"
}

resource "aws_apigatewayv2_route" "get_user_usage" {
  api_id    = aws_apigatewayv2_api.orchestrator.id
  route_key = "GET /usage/{userId}"
  target    = "integrations/${aws_apigatewayv2_integration.get_usage.id}"
}

resource "aws_lambda_permission" "get_usage_apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_usage.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.orchestrator.execution_arn}/*/*"
}

# Usage History Integration
resource "aws_apigatewayv2_integration" "usage_history" {
  api_id                 = aws_apigatewayv2_api.orchestrator.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.usage_history.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "usage_history" {
  api_id    = aws_apigatewayv2_api.orchestrator.id
  route_key = "GET /sessions/history"
  target    = "integrations/${aws_apigatewayv2_integration.usage_history.id}"
}

resource "aws_apigatewayv2_route" "user_usage_history" {
  api_id    = aws_apigatewayv2_api.orchestrator.id
  route_key = "GET /sessions/history/{userId}"
  target    = "integrations/${aws_apigatewayv2_integration.usage_history.id}"
}

resource "aws_lambda_permission" "usage_history_apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.usage_history.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.orchestrator.execution_arn}/*/*"
}

# =============================================================================
# Admin Sessions API Routes
# =============================================================================

resource "aws_apigatewayv2_integration" "admin_sessions" {
  api_id           = aws_apigatewayv2_api.orchestrator.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.admin_sessions.invoke_arn
}

resource "aws_apigatewayv2_route" "admin_sessions" {
  api_id    = aws_apigatewayv2_api.orchestrator.id
  route_key = "GET /admin/sessions"
  target    = "integrations/${aws_apigatewayv2_integration.admin_sessions.id}"
}

resource "aws_lambda_permission" "admin_sessions_apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.admin_sessions.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.orchestrator.execution_arn}/*/*"
}

# =============================================================================
# SSM Parameters for Secrets
# =============================================================================

resource "aws_ssm_parameter" "guacamole_password" {
  count       = var.guacamole_admin_password != "" ? 1 : 0
  name        = "/${var.project_name}/${var.environment}/guacamole/admin-password"
  description = "Guacamole admin password"
  type        = "SecureString"
  value       = var.guacamole_admin_password

  tags = local.common_tags
}

resource "aws_ssm_parameter" "moodle_secret" {
  count       = var.moodle_webhook_secret != "" ? 1 : 0
  name        = "/${var.project_name}/${var.environment}/moodle/webhook-secret"
  description = "Moodle webhook authentication secret"
  type        = "SecureString"
  value       = var.moodle_webhook_secret

  tags = local.common_tags
}

