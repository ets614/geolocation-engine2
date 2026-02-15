output "primary_endpoint" {
  description = "Primary RDS endpoint"
  value       = aws_db_instance.primary.endpoint
}

output "primary_address" {
  description = "Primary RDS address (hostname only)"
  value       = aws_db_instance.primary.address
}

output "replica_endpoint" {
  description = "Read replica RDS endpoint"
  value       = var.create_read_replica ? aws_db_instance.replica[0].endpoint : null
}

output "replica_address" {
  description = "Read replica RDS address (hostname only)"
  value       = var.create_read_replica ? aws_db_instance.replica[0].address : null
}

output "database_name" {
  description = "Name of the database"
  value       = aws_db_instance.primary.db_name
}

output "port" {
  description = "RDS port"
  value       = aws_db_instance.primary.port
}

output "security_group_id" {
  description = "Security group ID for RDS"
  value       = aws_security_group.rds.id
}

output "primary_arn" {
  description = "ARN of the primary RDS instance"
  value       = aws_db_instance.primary.arn
}

output "kms_key_arn" {
  description = "ARN of the KMS key used for encryption"
  value       = aws_kms_key.rds.arn
}
