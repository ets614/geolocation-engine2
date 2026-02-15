# EKS Cluster Configuration - Phase 05
# Features: Multi-AZ, auto-scaling, spot instances, monitoring

# IAM Role for EKS Cluster
resource "aws_iam_role" "eks_cluster" {
  name = "${var.project_name}-eks-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "eks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster.name
}

resource "aws_iam_role_policy_attachment" "eks_vpc_resource_controller" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSVPCResourceController"
  role       = aws_iam_role.eks_cluster.name
}

# EKS Cluster
resource "aws_eks_cluster" "main" {
  name     = var.project_name
  version  = var.kubernetes_version
  role_arn = aws_iam_role.eks_cluster.arn

  vpc_config {
    subnet_ids              = concat(aws_subnet.public[*].id, aws_subnet.private[*].id)
    security_group_ids      = [aws_security_group.eks_node.id]
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = ["0.0.0.0/0"]
  }

  enabled_cluster_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler"
  ]

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_vpc_resource_controller
  ]

  tags = {
    Name = "${var.project_name}-eks-cluster"
  }
}

# IAM Role for EKS Node Group
resource "aws_iam_role" "eks_node" {
  name = "${var.project_name}-eks-node-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "eks_node_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_node.name
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_node.name
}

resource "aws_iam_role_policy_attachment" "eks_registry_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_node.name
}

# SSM access for debugging
resource "aws_iam_role_policy_attachment" "eks_ssm_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  role       = aws_iam_role.eks_node.name
}

# CloudWatch Logs access
resource "aws_iam_role_policy_attachment" "eks_cloudwatch_policy" {
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
  role       = aws_iam_role.eks_node.name
}

# EKS Node Group - On-Demand Instances
resource "aws_eks_node_group" "on_demand" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.project_name}-ng-on-demand"
  node_role_arn   = aws_iam_role.eks_node.arn
  version         = var.kubernetes_version

  subnet_ids = aws_subnet.private[*].id

  scaling_config {
    desired_size = var.eks_node_count_min
    max_size     = var.eks_node_count_max
    min_size     = var.eks_node_count_min
  }

  instance_types = var.eks_node_instance_types

  capacity_type = "ON_DEMAND"

  disk_size = 50

  labels = {
    Environment = var.environment
    NodeType    = "on-demand"
  }

  tags = {
    Name = "${var.project_name}-ng-on-demand"
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_registry_policy,
    aws_iam_role_policy_attachment.eks_ssm_policy,
    aws_iam_role_policy_attachment.eks_cloudwatch_policy
  ]

  lifecycle {
    create_before_destroy = true
  }
}

# EKS Node Group - Spot Instances (cost optimization)
resource "aws_eks_node_group" "spot" {
  count           = var.enable_spot_instances ? 1 : 0
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.project_name}-ng-spot"
  node_role_arn   = aws_iam_role.eks_node.arn
  version         = var.kubernetes_version

  subnet_ids = aws_subnet.private[*].id

  scaling_config {
    desired_size = max(1, var.eks_node_count_min - 1)
    max_size     = var.eks_node_count_max
    min_size     = 0
  }

  instance_types = var.eks_node_instance_types

  capacity_type = "SPOT"

  spot_price = var.spot_max_price != "" ? var.spot_max_price : null

  disk_size = 50

  labels = {
    Environment = var.environment
    NodeType    = "spot"
    Preemptible = "true"
  }

  taints {
    key    = "spot"
    value  = "true"
    effect = "NoSchedule"
  }

  tags = {
    Name = "${var.project_name}-ng-spot"
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_registry_policy,
    aws_iam_role_policy_attachment.eks_ssm_policy,
    aws_iam_role_policy_attachment.eks_cloudwatch_policy
  ]

  lifecycle {
    create_before_destroy = true
  }
}

# OIDC Provider for IRSA (IAM Roles for Service Accounts)
data "tls_certificate" "cluster" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "cluster" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.cluster.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer

  tags = {
    Name = "${var.project_name}-irsa-provider"
  }
}

# Autoscaling Group Tags for cluster autoscaler discovery
resource "aws_autoscaling_group_tag" "cluster_autoscaler_enabled" {
  for_each = toset(
    concat(
      [aws_eks_node_group.on_demand.resources[0].autoscaling_groups[0].name],
      var.enable_spot_instances ? [aws_eks_node_group.spot[0].resources[0].autoscaling_groups[0].name] : []
    )
  )

  autoscaling_group_name = each.value

  tag {
    key                 = "k8s.io/cluster-autoscaler/${var.project_name}"
    value               = "owned"
    propagate_at_launch = false
  }
}

# Kubernetes Service Account for ALB Controller
resource "kubernetes_service_account" "alb_controller" {
  depends_on = [aws_eks_cluster.main]

  metadata {
    name      = "aws-load-balancer-controller"
    namespace = "kube-system"
  }
}

# IAM Role for ALB Controller
resource "aws_iam_role" "alb_controller" {
  name = "${var.project_name}-alb-controller-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRoleWithWebIdentity"
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.cluster.arn
        }
        Condition = {
          StringEquals = {
            "${replace(aws_iam_openid_connect_provider.cluster.url, "https://", "")}:sub" = "system:serviceaccount:kube-system:aws-load-balancer-controller"
          }
        }
      }
    ]
  })
}

# ALB Controller Policy
data "aws_iam_policy_document" "alb_controller" {
  statement {
    actions = [
      "elbv2:CreateLoadBalancer",
      "elbv2:CreateTargetGroup",
      "elbv2:CreateListener",
      "elbv2:DeleteLoadBalancer",
      "elbv2:DeleteTargetGroup",
      "elbv2:DeleteListener",
      "elbv2:DescribeLoadBalancers",
      "elbv2:DescribeTargetGroups",
      "elbv2:DescribeListeners",
      "elbv2:DescribeLoadBalancerAttributes",
      "elbv2:DescribeTargetGroupAttributes",
      "elbv2:ModifyLoadBalancerAttributes",
      "elbv2:ModifyTargetGroupAttributes",
      "elbv2:RegisterTargets",
      "elbv2:DeregisterTargets"
    ]
    resources = ["*"]
  }

  statement {
    actions = [
      "ec2:DescribeSecurityGroups",
      "ec2:DescribeSubnets",
      "ec2:DescribeNetworkInterfaces",
      "ec2:DescribeInstances"
    ]
    resources = ["*"]
  }

  statement {
    actions = [
      "ec2:CreateSecurityGroup",
      "ec2:AuthorizeSecurityGroupIngress",
      "ec2:RevokeSecurityGroupIngress",
      "ec2:DeleteSecurityGroup",
      "ec2:CreateTags",
      "ec2:DeleteTags"
    ]
    resources = ["*"]
  }

  statement {
    actions = [
      "acm:DescribeCertificate",
      "acm:ListCertificates",
      "route53:ChangeResourceRecordSets"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "alb_controller" {
  name   = "${var.project_name}-alb-controller-policy"
  policy = data.aws_iam_policy_document.alb_controller.json
}

resource "aws_iam_role_policy_attachment" "alb_controller" {
  policy_arn = aws_iam_policy.alb_controller.arn
  role       = aws_iam_role.alb_controller.name
}

# Patch service account with IAM role annotation
resource "kubernetes_patch" "alb_controller_annotation" {
  api_version = "v1"
  kind        = "ServiceAccount"
  name        = kubernetes_service_account.alb_controller.metadata[0].name
  namespace   = kubernetes_service_account.alb_controller.metadata[0].namespace

  patch = jsonencode({
    metadata = {
      annotations = {
        "eks.amazonaws.com/role-arn" = aws_iam_role.alb_controller.arn
      }
    }
  })

  depends_on = [kubernetes_service_account.alb_controller]
}

# Output cluster details
output "eks_cluster_endpoint" {
  description = "EKS cluster API endpoint"
  value       = aws_eks_cluster.main.endpoint
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = aws_eks_cluster.main.name
}

output "eks_cluster_certificate_authority" {
  description = "Base64 encoded certificate authority"
  value       = aws_eks_cluster.main.certificate_authority[0].data
  sensitive   = true
}

output "oidc_provider_arn" {
  description = "ARN of OIDC provider"
  value       = aws_iam_openid_connect_provider.cluster.arn
}
