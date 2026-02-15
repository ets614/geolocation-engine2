# Production Environment - Detection API Infrastructure
# AWS EKS with HA PostgreSQL, full monitoring, and disaster recovery

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "detection-api-terraform-state"
    key            = "environments/prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "detection-api-terraform-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = "prod"
      ManagedBy   = "terraform"
      Team        = "platform-engineering"
    }
  }
}

# Replica region provider for cross-region DR
provider "aws" {
  alias  = "replica"
  region = var.replica_region
}

locals {
  environment  = "prod"
  cluster_name = "${var.project_name}-${local.environment}"

  tags = {
    Project     = var.project_name
    Environment = local.environment
    ManagedBy   = "terraform"
  }
}

# --------------------------------------------------------------------------
# VPC
# --------------------------------------------------------------------------

module "vpc" {
  source = "../../modules/vpc"

  project_name          = var.project_name
  environment           = local.environment
  vpc_cidr              = "10.0.0.0/16"
  public_subnet_cidrs   = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  private_subnet_cidrs  = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]
  database_subnet_cidrs = ["10.0.21.0/24", "10.0.22.0/24", "10.0.23.0/24"]
  cluster_name          = local.cluster_name
  enable_nat_gateway    = true
  single_nat_gateway    = false  # HA: one NAT per AZ
  enable_flow_logs      = true
  flow_log_retention_days = 90
  tags                  = local.tags
}

# --------------------------------------------------------------------------
# IAM
# --------------------------------------------------------------------------

module "iam" {
  source = "../../modules/iam"

  project_name      = var.project_name
  environment       = local.environment
  cluster_name      = local.cluster_name
  aws_region        = var.aws_region
  aws_account_id    = var.aws_account_id
  oidc_provider_arn = module.eks.oidc_provider_arn
  oidc_issuer       = replace(module.eks.cluster_oidc_issuer_url, "https://", "")
  backup_bucket_arn = module.s3.backup_bucket_arn
  kms_key_arns      = [module.s3.kms_key_arn]
  tags              = local.tags
}

# --------------------------------------------------------------------------
# EKS
# --------------------------------------------------------------------------

module "eks" {
  source = "../../modules/eks"

  cluster_name     = local.cluster_name
  cluster_version  = "1.29"
  vpc_id           = module.vpc.vpc_id
  vpc_cidr         = module.vpc.vpc_cidr
  private_subnet_ids = module.vpc.private_subnet_ids
  public_subnet_ids  = module.vpc.public_subnet_ids
  cluster_role_arn   = module.iam.eks_cluster_role_arn
  node_role_arn      = module.iam.eks_node_role_arn
  ebs_csi_role_arn   = module.iam.ebs_csi_role_arn

  # Production: private endpoint only
  endpoint_public_access = false

  # Application nodes: 3 AZ, auto-scale 3-10
  application_instance_types = ["m6i.xlarge"]
  application_desired_size   = 3
  application_min_size       = 3
  application_max_size       = 10
  application_disk_size      = 100

  # Monitoring nodes: 2 AZ, auto-scale 2-3
  monitoring_instance_types = ["m6i.large"]
  monitoring_desired_size   = 2
  monitoring_min_size       = 2
  monitoring_max_size       = 3
  monitoring_disk_size      = 200

  log_retention_days = 90
  tags               = local.tags
}

# --------------------------------------------------------------------------
# RDS (PostgreSQL HA)
# --------------------------------------------------------------------------

module "rds" {
  source = "../../modules/rds"

  project_name               = var.project_name
  environment                = local.environment
  vpc_id                     = module.vpc.vpc_id
  db_subnet_group_name       = module.vpc.database_subnet_group_name
  allowed_security_group_ids = [module.eks.cluster_security_group_id]

  engine_version        = "16.2"
  instance_class        = "db.r6g.large"
  allocated_storage     = 100
  max_allocated_storage = 500
  database_name         = "detection_api"
  master_username       = var.db_master_username
  master_password       = var.db_master_password
  max_connections       = "200"

  multi_az                = true
  backup_retention_period = 30
  create_read_replica     = true
  replica_instance_class  = "db.r6g.large"
  deletion_protection     = true

  monitoring_role_arn            = module.iam.rds_monitoring_role_arn
  performance_insights_retention = 7
  alarm_sns_topic_arns           = var.alarm_sns_topic_arns

  tags = local.tags
}

# --------------------------------------------------------------------------
# S3 (Backups and State)
# --------------------------------------------------------------------------

module "s3" {
  source = "../../modules/s3"

  project_name                    = var.project_name
  environment                     = local.environment
  aws_account_id                  = var.aws_account_id
  backup_retention_days           = 365
  audit_retention_days            = 2555  # 7 years
  enable_cross_region_replication = false  # Enable when replica provider is configured
  create_state_bucket             = false  # State bucket created separately
  tags                            = local.tags

  providers = {
    aws         = aws
    aws.replica = aws.replica
  }
}
