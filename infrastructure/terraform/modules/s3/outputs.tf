output "backup_bucket_id" {
  description = "ID of the backup S3 bucket"
  value       = aws_s3_bucket.backup.id
}

output "backup_bucket_arn" {
  description = "ARN of the backup S3 bucket"
  value       = aws_s3_bucket.backup.arn
}

output "backup_bucket_domain" {
  description = "Domain name of the backup S3 bucket"
  value       = aws_s3_bucket.backup.bucket_domain_name
}

output "kms_key_arn" {
  description = "ARN of the S3 KMS key"
  value       = aws_kms_key.s3.arn
}

output "terraform_state_bucket_id" {
  description = "ID of the Terraform state bucket"
  value       = var.create_state_bucket ? aws_s3_bucket.terraform_state[0].id : null
}

output "terraform_lock_table_name" {
  description = "Name of the DynamoDB lock table"
  value       = var.create_state_bucket ? aws_dynamodb_table.terraform_lock[0].name : null
}
