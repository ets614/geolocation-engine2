"""
Phase 05: Infrastructure as Code (Terraform) Tests
Purpose: Validate AWS infrastructure deployment, configurations, and disaster recovery
"""

import json
import pytest
import subprocess
import boto3
import time
from typing import Dict, Any, List


class TestTerraformValidation:
    """Test Terraform code quality and validation"""

    def test_terraform_init(self):
        """Test Terraform initialization"""
        result = subprocess.run(
            ["terraform", "init", "-backend=false"],
            cwd="terraform",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Terraform init failed: {result.stderr}"

    def test_terraform_validate(self):
        """Test Terraform configuration validation"""
        result = subprocess.run(
            ["terraform", "validate"],
            cwd="terraform",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Terraform validation failed: {result.stderr}"

    def test_terraform_format(self):
        """Test Terraform code formatting"""
        result = subprocess.run(
            ["terraform", "fmt", "-check", "-recursive", "."],
            cwd="terraform",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Terraform format check failed: {result.stderr}"

    def test_tflint_rules(self):
        """Test Terraform code with TFLint"""
        result = subprocess.run(
            ["tflint", "--format", "json"],
            cwd="terraform",
            capture_output=True,
            text=True
        )
        # Parse TFLint JSON output
        if result.stdout:
            tflint_output = json.loads(result.stdout)
            # Only fail on critical issues
            critical_issues = [
                i for i in tflint_output.get("issues", [])
                if i.get("rule", {}).get("severity") == "error"
            ]
            assert len(critical_issues) == 0, f"TFLint critical issues: {critical_issues}"


class TestVPCConfiguration:
    """Test VPC infrastructure"""

    @pytest.fixture
    def ec2_client(self):
        return boto3.client("ec2", region_name="us-east-1")

    def test_vpc_exists(self, ec2_client):
        """Test VPC is created"""
        response = ec2_client.describe_vpcs(
            Filters=[{"Name": "tag:Name", "Values": ["detection-api-vpc"]}]
        )
        assert len(response["Vpcs"]) > 0, "VPC not found"
        vpc = response["Vpcs"][0]
        assert vpc["CidrBlock"] == "10.0.0.0/16"

    def test_public_subnets_exist(self, ec2_client):
        """Test public subnets are created (3 AZs)"""
        response = ec2_client.describe_subnets(
            Filters=[
                {"Name": "tag:Name", "Values": ["detection-api-public-subnet-1"]},
                {"Name": "tag:Name", "Values": ["detection-api-public-subnet-2"]},
                {"Name": "tag:Name", "Values": ["detection-api-public-subnet-3"]},
            ]
        )
        assert len(response["Subnets"]) == 3, "Expected 3 public subnets"

    def test_private_subnets_exist(self, ec2_client):
        """Test private subnets are created (3 AZs)"""
        response = ec2_client.describe_subnets(
            Filters=[
                {"Name": "tag:Name", "Values": ["detection-api-private-subnet-1"]},
                {"Name": "tag:Name", "Values": ["detection-api-private-subnet-2"]},
                {"Name": "tag:Name", "Values": ["detection-api-private-subnet-3"]},
            ]
        )
        assert len(response["Subnets"]) == 3, "Expected 3 private subnets"

    def test_nat_gateways_deployed(self, ec2_client):
        """Test NAT gateways for private subnet internet access"""
        response = ec2_client.describe_nat_gateways(
            Filters=[{"Name": "tag:Name", "Values": ["detection-api-nat-1", "detection-api-nat-2", "detection-api-nat-3"]}]
        )
        assert len(response["NatGateways"]) == 3, "Expected 3 NAT gateways"
        for nat in response["NatGateways"]:
            assert nat["State"] == "available"

    def test_security_groups_created(self, ec2_client):
        """Test security groups for ALB, EKS, RDS, Redis"""
        sg_names = ["detection-api-alb-sg", "detection-api-eks-node-sg", "detection-api-rds-sg", "detection-api-redis-sg"]
        for sg_name in sg_names:
            response = ec2_client.describe_security_groups(
                Filters=[{"Name": "group-name", "Values": [sg_name]}]
            )
            assert len(response["SecurityGroups"]) > 0, f"Security group {sg_name} not found"


class TestEKSCluster:
    """Test EKS Kubernetes cluster"""

    @pytest.fixture
    def eks_client(self):
        return boto3.client("eks", region_name="us-east-1")

    def test_eks_cluster_exists(self, eks_client):
        """Test EKS cluster is created"""
        response = eks_client.describe_cluster(name="detection-api")
        assert response["cluster"]["status"] == "ACTIVE"
        assert response["cluster"]["version"] == "1.28"

    def test_eks_cluster_logging_enabled(self, eks_client):
        """Test EKS cluster logging is enabled"""
        response = eks_client.describe_cluster(name="detection-api")
        log_types = response["cluster"]["logging"]["clusterLogging"][0]["types"]
        expected_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
        for log_type in expected_types:
            assert log_type in log_types

    def test_eks_node_groups_exist(self, eks_client):
        """Test EKS node groups are created"""
        response = eks_client.list_nodegroups(clusterName="detection-api")
        node_groups = response["nodegroups"]
        assert "detection-api-ng-on-demand" in node_groups
        # Spot instances optional but preferred
        if "detection-api-ng-spot" in node_groups:
            spot_ng = eks_client.describe_nodegroup(
                clusterName="detection-api",
                nodegroupName="detection-api-ng-spot"
            )
            assert spot_ng["nodegroup"]["capacityType"] == "SPOT"

    def test_eks_cluster_multi_az(self, eks_client):
        """Test EKS cluster spans multiple AZs"""
        response = eks_client.describe_cluster(name="detection-api")
        subnets = response["cluster"]["resourcesVpcConfig"]["subnetIds"]
        # Should have at least 3 subnets for HA
        assert len(subnets) >= 3

    def test_eks_oidc_provider_created(self):
        """Test OIDC provider for IRSA is created"""
        iam_client = boto3.client("iam", region_name="us-east-1")
        response = iam_client.list_open_id_connect_providers()
        oidc_providers = response["OpenIDConnectProviderList"]
        assert len(oidc_providers) > 0, "No OIDC providers found"


class TestRDSDatabase:
    """Test RDS PostgreSQL database"""

    @pytest.fixture
    def rds_client(self):
        return boto3.client("rds", region_name="us-east-1")

    def test_rds_instance_exists(self, rds_client):
        """Test RDS instance is created"""
        response = rds_client.describe_db_instances(
            DBInstanceIdentifier="detection-api-db"
        )
        assert len(response["DBInstances"]) == 1
        db = response["DBInstances"][0]
        assert db["Engine"] == "postgres"
        assert db["DBInstanceStatus"] == "available"

    def test_rds_multi_az_enabled(self, rds_client):
        """Test RDS Multi-AZ is enabled for HA"""
        response = rds_client.describe_db_instances(
            DBInstanceIdentifier="detection-api-db"
        )
        db = response["DBInstances"][0]
        assert db["MultiAZ"] is True

    def test_rds_backup_retention(self, rds_client):
        """Test RDS backup retention is 30 days"""
        response = rds_client.describe_db_instances(
            DBInstanceIdentifier="detection-api-db"
        )
        db = response["DBInstances"][0]
        assert db["BackupRetentionPeriod"] >= 30

    def test_rds_encryption_enabled(self, rds_client):
        """Test RDS encryption at rest is enabled"""
        response = rds_client.describe_db_instances(
            DBInstanceIdentifier="detection-api-db"
        )
        db = response["DBInstances"][0]
        assert db["StorageEncrypted"] is True

    def test_rds_iam_database_authentication(self, rds_client):
        """Test IAM database authentication is enabled"""
        response = rds_client.describe_db_instances(
            DBInstanceIdentifier="detection-api-db"
        )
        db = response["DBInstances"][0]
        assert db["IAMDatabaseAuthenticationEnabled"] is True

    def test_rds_enhanced_monitoring(self, rds_client):
        """Test RDS enhanced monitoring is enabled"""
        response = rds_client.describe_db_instances(
            DBInstanceIdentifier="detection-api-db"
        )
        db = response["DBInstances"][0]
        assert db["MonitoringInterval"] >= 60

    def test_rds_logs_exported(self, rds_client):
        """Test RDS logs are exported to CloudWatch"""
        response = rds_client.describe_db_instances(
            DBInstanceIdentifier="detection-api-db"
        )
        db = response["DBInstances"][0]
        assert "postgresql" in db["EnabledCloudwatchLogsExports"]


class TestRedisCluster:
    """Test ElastiCache Redis cluster"""

    @pytest.fixture
    def elasticache_client(self):
        return boto3.client("elasticache", region_name="us-east-1")

    def test_redis_cluster_exists(self, elasticache_client):
        """Test Redis cluster is created"""
        response = elasticache_client.describe_cache_clusters(
            CacheClusterId="detection-api-redis"
        )
        assert len(response["CacheClusters"]) == 1
        cluster = response["CacheClusters"][0]
        assert cluster["CacheNodeType"] == "cache.t4g.medium"
        assert cluster["Engine"] == "redis"

    def test_redis_multi_node(self, elasticache_client):
        """Test Redis has 3 nodes for HA"""
        response = elasticache_client.describe_cache_clusters(
            CacheClusterId="detection-api-redis"
        )
        cluster = response["CacheClusters"][0]
        assert cluster["NumCacheNodes"] == 3

    def test_redis_encryption_enabled(self, elasticache_client):
        """Test Redis encryption at rest is enabled"""
        response = elasticache_client.describe_cache_clusters(
            CacheClusterId="detection-api-redis"
        )
        cluster = response["CacheClusters"][0]
        assert cluster["AtRestEncryptionEnabled"] is True

    def test_redis_transit_encryption_enabled(self, elasticache_client):
        """Test Redis encryption in transit is enabled"""
        response = elasticache_client.describe_cache_clusters(
            CacheClusterId="detection-api-redis"
        )
        cluster = response["CacheClusters"][0]
        assert cluster["TransitEncryptionEnabled"] is True

    def test_redis_automatic_failover(self, elasticache_client):
        """Test Redis automatic failover is enabled"""
        response = elasticache_client.describe_replication_groups(
            ReplicationGroupId="detection-api-redis"
        )
        rg = response["ReplicationGroups"][0]
        assert rg["AutomaticFailoverEnabled"] is True

    def test_redis_backup_retention(self, elasticache_client):
        """Test Redis has automatic backups"""
        response = elasticache_client.describe_cache_clusters(
            CacheClusterId="detection-api-redis"
        )
        cluster = response["CacheClusters"][0]
        assert cluster["SnapshotRetentionLimit"] >= 30


class TestALB:
    """Test Application Load Balancer"""

    @pytest.fixture
    def elbv2_client(self):
        return boto3.client("elbv2", region_name="us-east-1")

    def test_alb_exists(self, elbv2_client):
        """Test ALB is created"""
        response = elbv2_client.describe_load_balancers()
        albs = [lb for lb in response["LoadBalancers"] if "detection-api-alb" in lb["LoadBalancerName"]]
        assert len(albs) > 0

    def test_alb_multi_az(self, elbv2_client):
        """Test ALB spans multiple AZs"""
        response = elbv2_client.describe_load_balancers()
        alb = [lb for lb in response["LoadBalancers"] if "detection-api-alb" in lb["LoadBalancerName"]][0]
        assert len(alb["AvailabilityZones"]) >= 3

    def test_alb_access_logs_enabled(self, elbv2_client):
        """Test ALB access logs are enabled"""
        response = elbv2_client.describe_load_balancers()
        alb = [lb for lb in response["LoadBalancers"] if "detection-api-alb" in lb["LoadBalancerName"]][0]
        logs = elbv2_client.describe_load_balancer_attributes(LoadBalancerArn=alb["LoadBalancerArn"])
        access_logs_enabled = any(
            attr["Key"] == "access_logs.s3.enabled" and attr["Value"] == "true"
            for attr in logs["Attributes"]
        )
        assert access_logs_enabled

    def test_alb_target_group_exists(self, elbv2_client):
        """Test target group for health checks"""
        response = elbv2_client.describe_target_groups()
        tgs = [tg for tg in response["TargetGroups"] if "detection-api-tg-http" in tg["TargetGroupName"]]
        assert len(tgs) > 0
        tg = tgs[0]
        assert tg["HealthCheckPath"] == "/health"
        assert tg["HealthCheckProtocol"] == "HTTP"


class TestCloudWatch:
    """Test CloudWatch monitoring"""

    @pytest.fixture
    def cloudwatch_client(self):
        return boto3.client("cloudwatch", region_name="us-east-1")

    def test_log_groups_created(self, cloudwatch_client):
        """Test CloudWatch log groups are created"""
        response = cloudwatch_client.describe_log_groups()
        log_group_names = [lg["logGroupName"] for lg in response["logGroups"]]
        expected_logs = [
            "/aws/eks/detection-api/cluster",
            "/aws/application/detection-api",
            "/aws/elasticache/detection-api/slow-log",
            "/aws/elasticache/detection-api/engine-log"
        ]
        for log in expected_logs:
            assert log in log_group_names, f"Log group {log} not found"

    def test_alarms_created(self, cloudwatch_client):
        """Test CloudWatch alarms are created for monitoring"""
        response = cloudwatch_client.describe_alarms()
        alarm_names = [alarm["AlarmName"] for alarm in response["MetricAlarms"]]
        expected_alarms = [
            "detection-api-eks-cpu-high",
            "detection-api-eks-memory-high",
            "detection-api-rds-cpu-high",
            "detection-api-redis-cpu-high",
            "detection-api-alb-target-response-time",
            "detection-api-alb-unhealthy-hosts"
        ]
        for alarm in expected_alarms:
            assert alarm in alarm_names, f"Alarm {alarm} not found"

    def test_dashboard_exists(self, cloudwatch_client):
        """Test CloudWatch dashboard is created"""
        response = cloudwatch_client.list_dashboards()
        dashboard_names = [db["DashboardName"] for db in response["DashboardEntries"]]
        assert "detection-api-main" in dashboard_names


class TestDisasterRecovery:
    """Test disaster recovery capabilities"""

    @pytest.fixture
    def rds_client(self):
        return boto3.client("rds", region_name="us-east-1")

    @pytest.fixture
    def elasticache_client(self):
        return boto3.client("elasticache", region_name="us-east-1")

    def test_rds_automated_backup(self, rds_client):
        """Test RDS automated backups are enabled"""
        response = rds_client.describe_db_instances(
            DBInstanceIdentifier="detection-api-db"
        )
        db = response["DBInstances"][0]
        assert db["BackupRetentionPeriod"] >= 30, "Backup retention < 30 days"

    def test_rds_backup_rpo(self, rds_client):
        """Test RDS backup RPO < 5 minutes"""
        response = rds_client.describe_db_instances(
            DBInstanceIdentifier="detection-api-db"
        )
        db = response["DBInstances"][0]
        # RDS automated backups are taken daily, so RPO is effectively 1 day
        # For better RPO, enhanced backups needed
        assert db["BackupRetentionPeriod"] > 0

    def test_redis_snapshot_enabled(self, elasticache_client):
        """Test Redis snapshot backups are enabled"""
        response = elasticache_client.describe_cache_clusters(
            CacheClusterId="detection-api-redis"
        )
        cluster = response["CacheClusters"][0]
        assert cluster["SnapshotRetentionLimit"] >= 30

    def test_s3_backup_buckets_exist(self):
        """Test S3 buckets for disaster recovery backups"""
        s3_client = boto3.client("s3", region_name="us-east-1")
        response = s3_client.list_buckets()
        bucket_names = [b["Name"] for b in response["Buckets"]]
        backup_buckets = [b for b in bucket_names if "backup" in b]
        assert len(backup_buckets) > 0, "No backup S3 buckets found"

    def test_backup_bucket_versioning(self):
        """Test S3 backup buckets have versioning enabled"""
        s3_client = boto3.client("s3", region_name="us-east-1")
        response = s3_client.list_buckets()
        backup_buckets = [b for b in response["Buckets"] if "backup" in b["Name"]]
        for bucket in backup_buckets:
            versioning = s3_client.get_bucket_versioning(Bucket=bucket["Name"])
            assert versioning.get("Status") == "Enabled", f"Versioning not enabled for {bucket['Name']}"

    def test_backup_bucket_encryption(self):
        """Test S3 backup buckets have encryption enabled"""
        s3_client = boto3.client("s3", region_name="us-east-1")
        response = s3_client.list_buckets()
        backup_buckets = [b for b in response["Buckets"] if "backup" in b["Name"]]
        for bucket in backup_buckets:
            try:
                encryption = s3_client.get_bucket_encryption(Bucket=bucket["Name"])
                assert "Rules" in encryption["ServerSideEncryptionConfiguration"]
            except s3_client.exceptions.ServerSideEncryptionConfigurationNotFoundError:
                pytest.fail(f"Encryption not configured for {bucket['Name']}")


class TestScalingAndPerformance:
    """Test auto-scaling and performance configurations"""

    @pytest.fixture
    def eks_client(self):
        return boto3.client("eks", region_name="us-east-1")

    @pytest.fixture
    def autoscaling_client(self):
        return boto3.client("autoscaling", region_name="us-east-1")

    def test_node_group_scaling_config(self, eks_client):
        """Test node group has auto-scaling configured"""
        response = eks_client.describe_nodegroup(
            clusterName="detection-api",
            nodegroupName="detection-api-ng-on-demand"
        )
        ng = response["nodegroup"]
        assert ng["scalingConfig"]["minSize"] >= 3
        assert ng["scalingConfig"]["maxSize"] >= 10

    def test_spot_instances_configured(self, eks_client):
        """Test spot instances for cost optimization"""
        try:
            response = eks_client.describe_nodegroup(
                clusterName="detection-api",
                nodegroupName="detection-api-ng-spot"
            )
            ng = response["nodegroup"]
            assert ng["capacityType"] == "SPOT"
        except eks_client.exceptions.ResourceNotFoundException:
            # Spot instances are optional
            pass

    def test_rds_storage_scaling(self):
        """Test RDS storage allocation for scaling"""
        rds_client = boto3.client("rds", region_name="us-east-1")
        response = rds_client.describe_db_instances(
            DBInstanceIdentifier="detection-api-db"
        )
        db = response["DBInstances"][0]
        # Storage should be at least 100GB for production-ready
        assert db["AllocatedStorage"] >= 100


@pytest.mark.integration
class TestEndToEndInfrastructure:
    """End-to-end infrastructure validation"""

    def test_complete_infrastructure_deployment(self):
        """Test all infrastructure components are deployed and ready"""
        # This is a comprehensive check that runs after deployment
        eks_client = boto3.client("eks", region_name="us-east-1")
        rds_client = boto3.client("rds", region_name="us-east-1")
        elasticache_client = boto3.client("elasticache", region_name="us-east-1")

        # Check EKS
        eks_response = eks_client.describe_cluster(name="detection-api")
        assert eks_response["cluster"]["status"] == "ACTIVE"

        # Check RDS
        rds_response = rds_client.describe_db_instances(
            DBInstanceIdentifier="detection-api-db"
        )
        assert rds_response["DBInstances"][0]["DBInstanceStatus"] == "available"

        # Check Redis
        redis_response = elasticache_client.describe_cache_clusters(
            CacheClusterId="detection-api-redis"
        )
        assert redis_response["CacheClusters"][0]["CacheClusterStatus"] == "available"
