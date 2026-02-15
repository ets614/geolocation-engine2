variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "db_subnet_group_name" {
  description = "Name of the DB subnet group"
  type        = string
}

variable "allowed_security_group_ids" {
  description = "Security group IDs allowed to connect to RDS"
  type        = list(string)
}

variable "engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "16.2"
}

variable "engine_major_version" {
  description = "PostgreSQL major version for parameter group"
  type        = string
  default     = "16"
}

variable "instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.r6g.large"
}

variable "allocated_storage" {
  description = "Allocated storage in GB"
  type        = number
  default     = 100
}

variable "max_allocated_storage" {
  description = "Maximum auto-scaled storage in GB"
  type        = number
  default     = 500
}

variable "database_name" {
  description = "Name of the default database"
  type        = string
  default     = "detection_api"
}

variable "master_username" {
  description = "Master username for RDS"
  type        = string
  default     = "detection_admin"
  sensitive   = true
}

variable "master_password" {
  description = "Master password for RDS"
  type        = string
  sensitive   = true
}

variable "max_connections" {
  description = "Maximum number of database connections"
  type        = string
  default     = "200"
}

variable "multi_az" {
  description = "Enable Multi-AZ deployment"
  type        = bool
  default     = true
}

variable "backup_retention_period" {
  description = "Backup retention period in days"
  type        = number
  default     = 30
}

variable "create_read_replica" {
  description = "Create a read replica"
  type        = bool
  default     = true
}

variable "replica_instance_class" {
  description = "Instance class for read replica"
  type        = string
  default     = "db.r6g.large"
}

variable "monitoring_role_arn" {
  description = "ARN of the IAM role for enhanced monitoring"
  type        = string
}

variable "performance_insights_retention" {
  description = "Performance Insights retention period in days"
  type        = number
  default     = 7
}

variable "deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = true
}

variable "alarm_sns_topic_arns" {
  description = "SNS topic ARNs for CloudWatch alarms"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
