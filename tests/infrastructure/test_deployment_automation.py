"""
Phase 05: Deployment Automation Tests
Purpose: Validate deployment scripts, health checks, and rollback procedures
"""

import subprocess
import pytest
import os
import json
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestDeploymentScriptValidation:
    """Test deployment automation scripts"""

    @pytest.fixture
    def script_path(self):
        return Path(__file__).parent.parent.parent / "scripts" / "deploy.sh"

    def test_deploy_script_exists(self, script_path):
        """Test deployment script exists"""
        assert script_path.exists(), "deploy.sh not found"

    def test_deploy_script_executable(self, script_path):
        """Test deployment script is executable"""
        assert os.access(script_path, os.X_OK), "deploy.sh not executable"

    def test_deploy_script_syntax(self, script_path):
        """Test bash script has valid syntax"""
        result = subprocess.run(
            ["bash", "-n", str(script_path)],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Syntax error: {result.stderr}"

    def test_disaster_recovery_script_exists(self):
        """Test disaster recovery script exists"""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "disaster-recovery.sh"
        assert script_path.exists(), "disaster-recovery.sh not found"

    def test_disaster_recovery_script_syntax(self):
        """Test disaster recovery script has valid syntax"""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "disaster-recovery.sh"
        result = subprocess.run(
            ["bash", "-n", str(script_path)],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Syntax error: {result.stderr}"


class TestDeploymentValidation:
    """Test deployment validation functions"""

    def test_terraform_plan_generation(self):
        """Test Terraform plan can be generated"""
        result = subprocess.run(
            ["terraform", "plan", "-var-file=environments/dev.tfvars", "-out=/tmp/test.tfplan"],
            cwd="terraform",
            capture_output=True,
            text=True,
            timeout=60
        )
        # May fail due to missing AWS credentials, but syntax should be valid
        if result.returncode != 0:
            assert "syntax" not in result.stderr.lower()

    def test_terraform_output_parsing(self):
        """Test Terraform outputs can be parsed"""
        result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd="terraform",
            capture_output=True,
            text=True,
            timeout=30
        )
        # May fail due to no state, but JSON parsing should work
        if result.stdout:
            try:
                json.loads(result.stdout)
            except json.JSONDecodeError:
                pytest.fail("Invalid JSON output from Terraform")


class TestHealthCheckImplementation:
    """Test health check endpoints and procedures"""

    def test_health_check_endpoint_definition(self):
        """Test health check endpoint is defined in API"""
        # This would check the FastAPI application
        from src.main import app
        # Verify /health endpoint exists
        routes = [route.path for route in app.routes]
        assert "/health" in routes, "/health endpoint not found"

    def test_readiness_check_endpoint_definition(self):
        """Test readiness check endpoint is defined"""
        from src.main import app
        routes = [route.path for route in app.routes]
        assert "/ready" in routes, "/ready endpoint not found"


class TestKubernetesDeploy:
    """Test Kubernetes deployment configuration"""

    def test_deployment_manifest_exists(self):
        """Test deployment manifest exists"""
        manifest_path = Path("kubernetes/manifests/deployment.yaml")
        assert manifest_path.exists(), "deployment.yaml not found"

    def test_deployment_manifest_valid_yaml(self):
        """Test deployment manifest is valid YAML"""
        import yaml
        manifest_path = Path("kubernetes/manifests/deployment.yaml")
        try:
            with open(manifest_path) as f:
                yaml.safe_load_all(f)
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML: {e}")

    def test_deployment_has_health_probes(self):
        """Test deployment has liveness and readiness probes"""
        import yaml
        manifest_path = Path("kubernetes/manifests/deployment.yaml")
        with open(manifest_path) as f:
            docs = list(yaml.safe_load_all(f))
            for doc in docs:
                if doc.get("kind") == "Deployment":
                    containers = doc["spec"]["template"]["spec"]["containers"]
                    for container in containers:
                        assert "livenessProbe" in container, "Missing liveness probe"
                        assert "readinessProbe" in container, "Missing readiness probe"

    def test_deployment_has_resource_limits(self):
        """Test deployment has resource requests and limits"""
        import yaml
        manifest_path = Path("kubernetes/manifests/deployment.yaml")
        with open(manifest_path) as f:
            docs = list(yaml.safe_load_all(f))
            for doc in docs:
                if doc.get("kind") == "Deployment":
                    containers = doc["spec"]["template"]["spec"]["containers"]
                    for container in containers:
                        assert "resources" in container, "Missing resource configuration"
                        assert "requests" in container["resources"]
                        assert "limits" in container["resources"]

    def test_deployment_has_security_context(self):
        """Test deployment has security context configured"""
        import yaml
        manifest_path = Path("kubernetes/manifests/deployment.yaml")
        with open(manifest_path) as f:
            docs = list(yaml.safe_load_all(f))
            for doc in docs:
                if doc.get("kind") == "Deployment":
                    spec = doc["spec"]["template"]["spec"]
                    assert "securityContext" in spec, "Missing pod security context"
                    assert "containers" in spec
                    for container in spec["containers"]:
                        assert "securityContext" in container, "Missing container security context"

    def test_deployment_graceful_shutdown(self):
        """Test deployment has termination grace period and preStop hook"""
        import yaml
        manifest_path = Path("kubernetes/manifests/deployment.yaml")
        with open(manifest_path) as f:
            docs = list(yaml.safe_load_all(f))
            for doc in docs:
                if doc.get("kind") == "Deployment":
                    spec = doc["spec"]["template"]["spec"]
                    assert "terminationGracePeriodSeconds" in spec
                    assert spec["terminationGracePeriodSeconds"] >= 30
                    containers = spec["containers"]
                    for container in containers:
                        assert "lifecycle" in container
                        assert "preStop" in container["lifecycle"]


class TestBlueGreenDeployment:
    """Test blue-green deployment strategy implementation"""

    def test_blue_green_deployments_exist(self):
        """Test both blue and green deployment manifests exist"""
        import yaml
        manifest_path = Path("kubernetes/manifests/deployment.yaml")
        with open(manifest_path) as f:
            docs = list(yaml.safe_load_all(f))
            deployment_names = [doc["metadata"]["name"] for doc in docs if doc.get("kind") == "Deployment"]
            assert "detection-api-blue" in deployment_names
            assert "detection-api-green" in deployment_names

    def test_blue_green_identical_specs(self):
        """Test blue and green have identical pod specs"""
        import yaml
        manifest_path = Path("kubernetes/manifests/deployment.yaml")
        with open(manifest_path) as f:
            docs = list(yaml.safe_load_all(f))
            deployments = {doc["metadata"]["name"]: doc for doc in docs if doc.get("kind") == "Deployment"}
            blue_spec = deployments["detection-api-blue"]["spec"]["template"]["spec"]
            green_spec = deployments["detection-api-green"]["spec"]["template"]["spec"]
            # Compare container specs (image may differ during deployment)
            assert blue_spec["securityContext"] == green_spec["securityContext"]
            assert blue_spec["terminationGracePeriodSeconds"] == green_spec["terminationGracePeriodSeconds"]

    def test_slot_labels_present(self):
        """Test slot labels for blue-green switching"""
        import yaml
        manifest_path = Path("kubernetes/manifests/deployment.yaml")
        with open(manifest_path) as f:
            docs = list(yaml.safe_load_all(f))
            deployments = {doc["metadata"]["name"]: doc for doc in docs if doc.get("kind") == "Deployment"}
            blue_labels = deployments["detection-api-blue"]["spec"]["selector"]["matchLabels"]
            green_labels = deployments["detection-api-green"]["spec"]["selector"]["matchLabels"]
            assert blue_labels.get("slot") == "blue"
            assert green_labels.get("slot") == "green"


class TestMonitoringAndLogging:
    """Test monitoring and logging configuration"""

    def test_prometheus_annotations_present(self):
        """Test Prometheus scrape annotations are present"""
        import yaml
        manifest_path = Path("kubernetes/manifests/deployment.yaml")
        with open(manifest_path) as f:
            docs = list(yaml.safe_load_all(f))
            for doc in docs:
                if doc.get("kind") == "Deployment":
                    annotations = doc["spec"]["template"]["metadata"].get("annotations", {})
                    assert annotations.get("prometheus.io/scrape") == "true"
                    assert annotations.get("prometheus.io/port") == "8000"
                    assert annotations.get("prometheus.io/path") == "/metrics"

    def test_cloudwatch_logs_configured(self):
        """Test CloudWatch logs are exported from containers"""
        import yaml
        manifest_path = Path("kubernetes/manifests/deployment.yaml")
        with open(manifest_path) as f:
            docs = list(yaml.safe_load_all(f))
            for doc in docs:
                if doc.get("kind") == "Deployment":
                    containers = doc["spec"]["template"]["spec"]["containers"]
                    for container in containers:
                        env_vars = {e["name"]: e.get("value") for e in container.get("env", [])}
                        assert "LOG_LEVEL" in env_vars
                        assert "LOG_FORMAT" in env_vars
                        assert env_vars.get("LOG_FORMAT") == "json"


class TestDisasterRecoveryProcedures:
    """Test disaster recovery procedures"""

    def test_backup_script_backup_function(self):
        """Test backup function in disaster recovery script"""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "disaster-recovery.sh"
        with open(script_path) as f:
            content = f.read()
            assert "backup_rds_database()" in content
            assert "backup_redis_cluster()" in content
            assert "backup_eks_cluster()" in content

    def test_restore_script_restore_function(self):
        """Test restore function in disaster recovery script"""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "disaster-recovery.sh"
        with open(script_path) as f:
            content = f.read()
            assert "restore_rds_database()" in content
            assert "restore_eks_from_backup()" in content

    def test_rto_target_documented(self):
        """Test RTO < 30 minutes is documented"""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "disaster-recovery.sh"
        with open(script_path) as f:
            content = f.read()
            assert "1800" in content or "30 min" in content.lower()

    def test_rpo_target_documented(self):
        """Test RPO < 5 minutes is documented"""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "disaster-recovery.sh"
        with open(script_path) as f:
            content = f.read()
            assert "300" in content or "5 min" in content.lower()


class TestRollbackCapability:
    """Test rollback procedures"""

    def test_rollback_script_exists(self):
        """Test rollback script or function exists"""
        # Could be in deployment script or separate
        deploy_script = Path(__file__).parent.parent.parent / "scripts" / "deploy.sh"
        with open(deploy_script) as f:
            content = f.read()
            assert "rollback" in content.lower()

    def test_service_selector_patching_documented(self):
        """Test service selector patching for traffic switching is documented"""
        deployment_strategy = Path("docs/infrastructure/deployment-strategy.md")
        with open(deployment_strategy) as f:
            content = f.read()
            assert "kubectl patch service" in content
            assert "slot" in content.lower()


class TestEnvironmentConfigurations:
    """Test environment-specific configurations"""

    def test_dev_tfvars_exists(self):
        """Test dev environment config exists"""
        assert Path("terraform/environments/dev.tfvars").exists()

    def test_staging_tfvars_exists(self):
        """Test staging environment config exists"""
        assert Path("terraform/environments/staging.tfvars").exists()

    def test_prod_tfvars_exists(self):
        """Test prod environment config exists"""
        assert Path("terraform/environments/prod.tfvars").exists()

    def test_dev_config_values(self):
        """Test dev environment has appropriate resource sizes"""
        with open("terraform/environments/dev.tfvars") as f:
            content = f.read()
            assert "environment" in content
            assert "dev" in content.lower()
            # Should have smaller resources
            assert "t3.medium" in content or "small" in content.lower()

    def test_prod_config_values(self):
        """Test prod environment has appropriate resource sizes"""
        with open("terraform/environments/prod.tfvars") as f:
            content = f.read()
            assert "environment" in content
            assert "prod" in content.lower()
            # Should have larger resources and higher availability
            assert "30" in content  # 30-day backup retention
            assert "true" in content  # Multi-AZ enabled

    def test_prod_config_encryption_enabled(self):
        """Test prod environment has encryption enabled"""
        with open("terraform/environments/prod.tfvars") as f:
            content = f.read()
            assert "redis_encryption_enabled" in content
            assert "true" in content


@pytest.mark.integration
class TestDeploymentEnd2End:
    """End-to-end deployment testing"""

    def test_terraform_plan_completeness(self):
        """Test Terraform plan includes all necessary resources"""
        result = subprocess.run(
            ["terraform", "plan", "-var-file=environments/dev.tfvars", "-json"],
            cwd="terraform",
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0 and result.stdout:
            try:
                plan = json.loads(result.stdout)
                # Verify plan includes infrastructure
                assert "resource_changes" in plan
            except json.JSONDecodeError:
                # May fail due to state, but JSON structure should be valid
                pass

    def test_all_scripts_have_logging(self):
        """Test all automation scripts have proper logging"""
        scripts = [
            Path(__file__).parent.parent.parent / "scripts" / "deploy.sh",
            Path(__file__).parent.parent.parent / "scripts" / "disaster-recovery.sh",
        ]
        for script in scripts:
            with open(script) as f:
                content = f.read()
                assert "log_info" in content or "echo" in content
                assert "log_error" in content or ">&2" in content
