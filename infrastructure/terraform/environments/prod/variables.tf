variable "project_name" {
  description = "Project name"
  type        = string
  default     = "detection-api"
}

variable "aws_region" {
  description = "AWS region for production"
  type        = string
  default     = "us-east-1"
}

variable "replica_region" {
  description = "AWS region for DR replication"
  type        = string
  default     = "us-west-2"
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
}

variable "db_master_username" {
  description = "RDS master username"
  type        = string
  sensitive   = true
}

variable "db_master_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}

variable "alarm_sns_topic_arns" {
  description = "SNS topic ARNs for alarms"
  type        = list(string)
  default     = []
}
