variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "aws_account_id" {
  description = "AWS account ID for globally unique bucket names"
  type        = string
}

variable "backup_retention_days" {
  description = "Number of days to retain database backups"
  type        = number
  default     = 365
}

variable "audit_retention_days" {
  description = "Number of days to retain audit logs"
  type        = number
  default     = 2555  # ~7 years for compliance
}

variable "enable_cross_region_replication" {
  description = "Enable cross-region S3 replication for DR"
  type        = bool
  default     = false
}

variable "create_state_bucket" {
  description = "Create S3 bucket for Terraform state"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
