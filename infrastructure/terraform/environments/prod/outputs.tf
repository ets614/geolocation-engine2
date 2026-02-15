output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
  sensitive   = true
}

output "rds_primary_endpoint" {
  description = "RDS primary endpoint"
  value       = module.rds.primary_endpoint
  sensitive   = true
}

output "rds_replica_endpoint" {
  description = "RDS read replica endpoint"
  value       = module.rds.replica_endpoint
  sensitive   = true
}

output "backup_bucket" {
  description = "S3 backup bucket name"
  value       = module.s3.backup_bucket_id
}

output "detection_api_role_arn" {
  description = "IAM role ARN for detection API pods"
  value       = module.iam.detection_api_role_arn
}
