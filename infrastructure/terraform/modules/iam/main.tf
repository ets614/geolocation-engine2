# IAM Module for Detection API Infrastructure
# Provides roles for EKS cluster, nodes, IRSA, and monitoring

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# --------------------------------------------------------------------------
# EKS Cluster Role
# --------------------------------------------------------------------------

resource "aws_iam_role" "eks_cluster" {
  name = "${var.project_name}-${var.environment}-eks-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "eks.amazonaws.com"
      }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster.name
}

resource "aws_iam_role_policy_attachment" "eks_vpc_resource_controller" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSVPCResourceController"
  role       = aws_iam_role.eks_cluster.name
}

# --------------------------------------------------------------------------
# EKS Node Role
# --------------------------------------------------------------------------

resource "aws_iam_role" "eks_node" {
  name = "${var.project_name}-${var.environment}-eks-node-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "eks_worker_node_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_node.name
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_node.name
}

resource "aws_iam_role_policy_attachment" "ecr_read_only" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_node.name
}

resource "aws_iam_role_policy_attachment" "ssm_managed_instance" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  role       = aws_iam_role.eks_node.name
}

# --------------------------------------------------------------------------
# EBS CSI Driver Role (IRSA)
# --------------------------------------------------------------------------

resource "aws_iam_role" "ebs_csi" {
  name = "${var.project_name}-${var.environment}-ebs-csi-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRoleWithWebIdentity"
      Effect = "Allow"
      Principal = {
        Federated = var.oidc_provider_arn
      }
      Condition = {
        StringEquals = {
          "${var.oidc_issuer}:sub" = "system:serviceaccount:kube-system:ebs-csi-controller-sa"
          "${var.oidc_issuer}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "ebs_csi" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
  role       = aws_iam_role.ebs_csi.name
}

# --------------------------------------------------------------------------
# Detection API Service Account Role (IRSA)
# --------------------------------------------------------------------------

resource "aws_iam_role" "detection_api" {
  name = "${var.project_name}-${var.environment}-detection-api-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRoleWithWebIdentity"
      Effect = "Allow"
      Principal = {
        Federated = var.oidc_provider_arn
      }
      Condition = {
        StringEquals = {
          "${var.oidc_issuer}:sub" = "system:serviceaccount:default:detection-api-sa"
          "${var.oidc_issuer}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "detection_api" {
  name = "${var.project_name}-${var.environment}-detection-api-policy"
  role = aws_iam_role.detection_api.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3BackupAccess"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.backup_bucket_arn,
          "${var.backup_bucket_arn}/*"
        ]
      },
      {
        Sid    = "SecretsManagerAccess"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:${var.project_name}/${var.environment}/*"
        ]
      },
      {
        Sid    = "KMSDecrypt"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = var.kms_key_arns
      }
    ]
  })
}

# --------------------------------------------------------------------------
# RDS Enhanced Monitoring Role
# --------------------------------------------------------------------------

resource "aws_iam_role" "rds_monitoring" {
  name = "${var.project_name}-${var.environment}-rds-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "monitoring.rds.amazonaws.com"
      }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
  role       = aws_iam_role.rds_monitoring.name
}

# --------------------------------------------------------------------------
# Cluster Autoscaler Role (IRSA)
# --------------------------------------------------------------------------

resource "aws_iam_role" "cluster_autoscaler" {
  name = "${var.project_name}-${var.environment}-cluster-autoscaler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRoleWithWebIdentity"
      Effect = "Allow"
      Principal = {
        Federated = var.oidc_provider_arn
      }
      Condition = {
        StringEquals = {
          "${var.oidc_issuer}:sub" = "system:serviceaccount:kube-system:cluster-autoscaler"
          "${var.oidc_issuer}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "cluster_autoscaler" {
  name = "${var.project_name}-${var.environment}-cluster-autoscaler-policy"
  role = aws_iam_role.cluster_autoscaler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "autoscaling:DescribeAutoScalingGroups",
          "autoscaling:DescribeAutoScalingInstances",
          "autoscaling:DescribeLaunchConfigurations",
          "autoscaling:DescribeScalingActivities",
          "autoscaling:DescribeTags",
          "ec2:DescribeImages",
          "ec2:DescribeInstanceTypes",
          "ec2:DescribeLaunchTemplateVersions",
          "ec2:GetInstanceTypesFromInstanceRequirements",
          "eks:DescribeNodegroup"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "autoscaling:SetDesiredCapacity",
          "autoscaling:TerminateInstanceInAutoScalingGroup"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:ResourceTag/k8s.io/cluster-autoscaler/${var.cluster_name}" = "owned"
          }
        }
      }
    ]
  })
}
