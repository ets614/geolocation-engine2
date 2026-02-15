variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
}

variable "oidc_provider_arn" {
  description = "ARN of the OIDC provider for IRSA"
  type        = string
  default     = ""
}

variable "oidc_issuer" {
  description = "OIDC issuer URL (without https://)"
  type        = string
  default     = ""
}

variable "backup_bucket_arn" {
  description = "ARN of the S3 backup bucket"
  type        = string
  default     = ""
}

variable "kms_key_arns" {
  description = "ARNs of KMS keys the API role can use"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
