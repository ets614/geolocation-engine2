# Staging Environment - Detection API Infrastructure
# Production-like but reduced capacity for cost efficiency

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
    key            = "environments/staging/terraform.tfstate"
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
      Environment = "staging"
      ManagedBy   = "terraform"
      Team        = "platform-engineering"
    }
  }
}

provider "aws" {
  alias  = "replica"
  region = var.aws_region
}

locals {
  environment  = "staging"
  cluster_name = "${var.project_name}-${local.environment}"

  tags = {
    Project     = var.project_name
    Environment = local.environment
    ManagedBy   = "terraform"
  }
}

module "vpc" {
  source = "../../modules/vpc"

  project_name          = var.project_name
  environment           = local.environment
  vpc_cidr              = "10.20.0.0/16"
  public_subnet_cidrs   = ["10.20.1.0/24", "10.20.2.0/24", "10.20.3.0/24"]
  private_subnet_cidrs  = ["10.20.11.0/24", "10.20.12.0/24", "10.20.13.0/24"]
  database_subnet_cidrs = ["10.20.21.0/24", "10.20.22.0/24", "10.20.23.0/24"]
  cluster_name          = local.cluster_name
  enable_nat_gateway    = true
  single_nat_gateway    = true  # Single NAT to save costs
  enable_flow_logs      = true
  flow_log_retention_days = 60
  tags                  = local.tags
}

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

  endpoint_public_access = true  # For CI/CD access

  application_instance_types = ["m6i.large"]
  application_desired_size   = 2
  application_min_size       = 2
  application_max_size       = 6
  application_disk_size      = 80

  monitoring_instance_types = ["t3.large"]
  monitoring_desired_size   = 1
  monitoring_min_size       = 1
  monitoring_max_size       = 2
  monitoring_disk_size      = 150

  log_retention_days = 60
  tags               = local.tags
}

module "rds" {
  source = "../../modules/rds"

  project_name               = var.project_name
  environment                = local.environment
  vpc_id                     = module.vpc.vpc_id
  db_subnet_group_name       = module.vpc.database_subnet_group_name
  allowed_security_group_ids = [module.eks.cluster_security_group_id]

  engine_version        = "16.2"
  instance_class        = "db.r6g.medium"
  allocated_storage     = 50
  max_allocated_storage = 200
  database_name         = "detection_api"
  master_username       = var.db_master_username
  master_password       = var.db_master_password

  multi_az                = true   # Mirrors prod for validation
  backup_retention_period = 14
  create_read_replica     = false  # No replica in staging
  deletion_protection     = true

  monitoring_role_arn = module.iam.rds_monitoring_role_arn

  tags = local.tags
}

module "s3" {
  source = "../../modules/s3"

  project_name          = var.project_name
  environment           = local.environment
  aws_account_id        = var.aws_account_id
  backup_retention_days = 90
  audit_retention_days  = 365

  providers = {
    aws         = aws
    aws.replica = aws.replica
  }

  tags = local.tags
}
