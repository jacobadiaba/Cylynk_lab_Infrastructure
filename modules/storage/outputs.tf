# modules/storage/outputs.tf

output "configs_bucket_name" {
  description = "Name of the configs S3 bucket"
  value       = aws_s3_bucket.configs.bucket
}

output "configs_bucket_id" {
  description = "ID of the configs S3 bucket"
  value       = aws_s3_bucket.configs.id
}

output "configs_bucket_arn" {
  description = "ARN of the configs S3 bucket"
  value       = aws_s3_bucket.configs.arn
}

output "configs_bucket_domain_name" {
  description = "Domain name of the configs S3 bucket"
  value       = aws_s3_bucket.configs.bucket_domain_name
}

output "logs_bucket_name" {
  description = "Name of the logs S3 bucket"
  value       = aws_s3_bucket.logs.bucket
}

output "logs_bucket_id" {
  description = "ID of the logs S3 bucket"
  value       = aws_s3_bucket.logs.id
}

output "logs_bucket_arn" {
  description = "ARN of the logs S3 bucket"
  value       = aws_s3_bucket.logs.arn
}

output "logs_bucket_domain_name" {
  description = "Domain name of the logs S3 bucket"
  value       = aws_s3_bucket.logs.bucket_domain_name
}

output "amis_bucket_id" {
  description = "ID of the AMIs S3 bucket"
  value       = aws_s3_bucket.amis.id
}

output "amis_bucket_arn" {
  description = "ARN of the AMIs S3 bucket"
  value       = aws_s3_bucket.amis.arn
}

output "amis_bucket_domain_name" {
  description = "Domain name of the AMIs S3 bucket"
  value       = aws_s3_bucket.amis.bucket_domain_name
}

output "all_bucket_ids" {
  description = "List of all S3 bucket IDs"
  value = [
    aws_s3_bucket.configs.id,
    aws_s3_bucket.logs.id,
    aws_s3_bucket.amis.id
  ]
}

output "all_bucket_arns" {
  description = "List of all S3 bucket ARNs"
  value = [
    aws_s3_bucket.configs.arn,
    aws_s3_bucket.logs.arn,
    aws_s3_bucket.amis.arn
  ]
}