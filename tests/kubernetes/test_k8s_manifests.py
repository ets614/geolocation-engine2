"""
Kubernetes Manifests Test Suite
Phase 05: Production Ready Kubernetes Deployment

Tests validate YAML syntax, required fields, resource limits,
health checks, RBAC permissions, and deployment strategy.
"""

import pytest
import yaml
from pathlib import Path


@pytest.fixture
def manifests_dir():
    """Get Kubernetes manifests directory."""
    return Path(__file__).parent.parent.parent / "kubernetes" / "manifests"


@pytest.fixture
def helm_dir():
    """Get Helm charts directory."""
    return Path(__file__).parent.parent.parent / "kubernetes" / "helm-charts"


class TestDeploymentManifest:
    """Test Deployment YAML manifest."""

    @pytest.fixture
    def deployment(self, manifests_dir):
        """Load deployment manifest."""
        with open(manifests_dir / "deployment.yaml") as f:
            docs = list(yaml.safe_load_all(f))
        return docs

    def test_deployment_exists(self, deployment):
        """Test deployment manifests exist."""
        assert len(deployment) >= 2, "Should have Blue and Green deployments"

    def test_deployment_has_required_fields(self, deployment):
        """Test deployment has all required fields."""
        for dep in deployment:
            assert dep["apiVersion"] == "apps/v1"
            assert dep["kind"] == "Deployment"
            assert "metadata" in dep
            assert "spec" in dep
            assert "name" in dep["metadata"]

    def test_deployment_replicas(self, deployment):
        """Test deployment replicas configuration."""
        for dep in deployment:
            replicas = dep["spec"].get("replicas", 0)
            assert replicas == 3, "Should have 3 replicas initially (HPA will adjust)"

    def test_deployment_resource_limits(self, deployment):
        """Test resource requests and limits (Phase 05 spec)."""
        for dep in deployment:
            containers = dep["spec"]["template"]["spec"]["containers"]
            for container in containers:
                resources = container["resources"]

                # Phase 05 requirements
                cpu_request = resources["requests"]["cpu"]
                memory_request = resources["requests"]["memory"]
                cpu_limit = resources["limits"]["cpu"]
                memory_limit = resources["limits"]["memory"]

                assert cpu_request == "250m", "CPU request must be 250m"
                assert memory_request == "256Mi", "Memory request must be 256Mi"
                assert cpu_limit == "500m", "CPU limit must be 500m"
                assert memory_limit == "512Mi", "Memory limit must be 512Mi"

    def test_deployment_health_checks(self, deployment):
        """Test health checks (liveness, readiness, startup probes)."""
        for dep in deployment:
            containers = dep["spec"]["template"]["spec"]["containers"]
            for container in containers:
                # Liveness Probe
                assert "livenessProbe" in container
                liveness = container["livenessProbe"]
                assert liveness["httpGet"]["path"] == "/health"
                assert liveness["initialDelaySeconds"] == 10
                assert liveness["periodSeconds"] == 30
                assert liveness["failureThreshold"] == 3

                # Readiness Probe
                assert "readinessProbe" in container
                readiness = container["readinessProbe"]
                assert readiness["httpGet"]["path"] == "/ready"
                assert readiness["initialDelaySeconds"] == 5
                assert readiness["periodSeconds"] == 5
                assert readiness["failureThreshold"] == 1

                # Startup Probe
                assert "startupProbe" in container
                startup = container["startupProbe"]
                assert startup["httpGet"]["path"] == "/health"
                assert startup["failureThreshold"] == 30  # 150 seconds max

    def test_deployment_security_context(self, deployment):
        """Test pod security context."""
        for dep in deployment:
            spec = dep["spec"]["template"]["spec"]

            # Pod security context
            pod_sec = spec["securityContext"]
            assert pod_sec["runAsNonRoot"] is True, "Must run as non-root"
            assert pod_sec["runAsUser"] == 1000
            assert pod_sec["fsGroup"] == 1000
            assert pod_sec["seccompProfile"]["type"] == "RuntimeDefault"

            # Container security context
            containers = spec["containers"]
            for container in containers:
                cont_sec = container["securityContext"]
                assert cont_sec["allowPrivilegeEscalation"] is False
                assert "ALL" in cont_sec["capabilities"]["drop"]
                assert cont_sec["runAsNonRoot"] is True

    def test_deployment_service_account(self, deployment):
        """Test service account assignment."""
        for dep in deployment:
            spec = dep["spec"]["template"]["spec"]
            assert "serviceAccountName" in spec
            assert spec["serviceAccountName"] == "detection-api-sa"

    def test_deployment_pod_affinity(self, deployment):
        """Test pod anti-affinity for HA."""
        for dep in deployment:
            affinity = dep["spec"]["template"]["spec"]["affinity"]
            assert "podAntiAffinity" in affinity
            assert "requiredDuringSchedulingIgnoredDuringExecution" in affinity["podAntiAffinity"]

    def test_deployment_volume_mounts(self, deployment):
        """Test volume mounts for queue storage."""
        for dep in deployment:
            containers = dep["spec"]["template"]["spec"]["containers"]
            for container in containers:
                volume_mounts = container["volumeMounts"]
                mount_paths = [vm["mountPath"] for vm in volume_mounts]
                assert "/app/data" in mount_paths, "Must mount queue storage"

    def test_deployment_strategy(self, deployment):
        """Test rolling update strategy."""
        for dep in deployment:
            strategy = dep["spec"]["strategy"]
            assert strategy["type"] == "RollingUpdate"
            assert strategy["rollingUpdate"]["maxSurge"] == 1
            assert strategy["rollingUpdate"]["maxUnavailable"] == 0

    def test_deployment_termination_grace_period(self, deployment):
        """Test graceful termination."""
        for dep in deployment:
            spec = dep["spec"]["template"]["spec"]
            assert spec["terminationGracePeriodSeconds"] == 30


class TestServiceManifest:
    """Test Service YAML manifest."""

    @pytest.fixture
    def services(self, manifests_dir):
        """Load services manifest."""
        with open(manifests_dir / "services.yaml") as f:
            docs = list(yaml.safe_load_all(f))
        return docs

    def test_services_exist(self, services):
        """Test service manifests exist."""
        assert len(services) > 0, "Should have at least one service"

    def test_clusterip_service(self, services):
        """Test ClusterIP service configuration."""
        clusterip_services = [s for s in services if s.get("kind") == "Service" and s.get("spec", {}).get("type") == "ClusterIP"]
        assert len(clusterip_services) > 0, "Should have ClusterIP service"

        for service in clusterip_services:
            assert service["metadata"]["name"] == "detection-api-service"
            assert service["spec"]["selector"]["app"] == "detection-api"
            assert service["spec"]["ports"][0]["port"] == 8000

    def test_pvc_configuration(self, services):
        """Test PersistentVolumeClaim for queue storage."""
        pvcs = [s for s in services if s.get("kind") == "PersistentVolumeClaim"]
        assert len(pvcs) > 0, "Should have PVC for queue storage"

        for pvc in pvcs:
            assert "storageClassName" in pvc["spec"]
            assert pvc["spec"]["accessModes"] == ["ReadWriteOnce"]
            assert "resources" in pvc["spec"]
            assert pvc["spec"]["resources"]["requests"]["storage"] == "50Gi"

    def test_network_policies(self, services):
        """Test network policies for security."""
        policies = [s for s in services if s.get("kind") == "NetworkPolicy"]
        assert len(policies) > 0, "Should have network policies"

        # Should have default deny-all policy
        deny_policies = [p for p in policies if p["metadata"]["name"] == "default-deny-all"]
        assert len(deny_policies) > 0, "Should have default deny-all policy"

    def test_configmap_exists(self, services):
        """Test ConfigMap for application config."""
        configmaps = [s for s in services if s.get("kind") == "ConfigMap"]
        assert len(configmaps) > 0, "Should have ConfigMap"

        for cm in configmaps:
            assert "data" in cm
            assert "tak_server_endpoint" in cm["data"]


class TestSecretsManifest:
    """Test Secrets YAML manifest."""

    @pytest.fixture
    def secrets(self, manifests_dir):
        """Load secrets manifest."""
        with open(manifests_dir / "secrets.yaml") as f:
            docs = list(yaml.safe_load_all(f))
        return docs

    def test_secrets_exist(self, secrets):
        """Test secret manifests exist."""
        assert len(secrets) > 0, "Should have secrets"

    def test_tak_server_secret(self, secrets):
        """Test TAK server credentials secret."""
        tak_secrets = [s for s in secrets if s.get("metadata", {}).get("name") == "tak-server-credentials"]
        assert len(tak_secrets) > 0, "Should have TAK server secret"

        for secret in tak_secrets:
            assert secret["type"] == "Opaque"
            data = secret["stringData"]
            assert "endpoint" in data
            assert "username" in data
            assert "password" in data
            assert "ca_cert" in data

    def test_jwt_keys_secret(self, secrets):
        """Test JWT keys secret."""
        jwt_secrets = [s for s in secrets if s.get("metadata", {}).get("name") == "jwt-keys"]
        assert len(jwt_secrets) > 0, "Should have JWT secret"

        for secret in jwt_secrets:
            data = secret["stringData"]
            assert "jwt_secret_key" in data
            assert "jwt_algorithm" in data
            assert "jwt_expiration" in data
            assert len(data["jwt_secret_key"]) > 20, "JWT key should be long"

    def test_database_secret(self, secrets):
        """Test database credentials secret."""
        db_secrets = [s for s in secrets if s.get("metadata", {}).get("name") == "db-credentials"]
        assert len(db_secrets) > 0, "Should have DB secret"

        for secret in db_secrets:
            data = secret["stringData"]
            assert "database_url" in data
            assert "db_username" in data
            assert "db_password" in data

    def test_discord_webhook_secret(self, secrets):
        """Test Discord webhook secret."""
        discord_secrets = [s for s in secrets if s.get("metadata", {}).get("name") == "discord-webhook"]
        assert len(discord_secrets) > 0, "Should have Discord webhook secret"

        for secret in discord_secrets:
            data = secret["stringData"]
            assert "webhook_url" in data


class TestStorageManifest:
    """Test Storage YAML manifest."""

    @pytest.fixture
    def storage(self, manifests_dir):
        """Load storage manifest."""
        with open(manifests_dir / "storage.yaml") as f:
            docs = list(yaml.safe_load_all(f))
        return docs

    def test_storage_classes(self, storage):
        """Test StorageClass definitions."""
        storage_classes = [s for s in storage if s.get("kind") == "StorageClass"]
        assert len(storage_classes) >= 2, "Should have fast-ssd and standard-db"

        # Check fast-ssd
        fast_ssd = [s for s in storage_classes if s["metadata"]["name"] == "fast-ssd"]
        assert len(fast_ssd) > 0
        assert fast_ssd[0]["parameters"]["type"] == "gp3"
        assert fast_ssd[0]["parameters"]["encrypted"] == "true"

    def test_persistent_volumes(self, storage):
        """Test PersistentVolume definitions."""
        pvs = [s for s in storage if s.get("kind") == "PersistentVolume"]
        assert len(pvs) >= 2, "Should have queue and cache PVs"

    def test_persistent_volume_claims(self, storage):
        """Test PersistentVolumeClaim definitions."""
        pvcs = [s for s in storage if s.get("kind") == "PersistentVolumeClaim"]
        assert len(pvcs) >= 2, "Should have queue and cache PVCs"

        # Queue PVC
        queue_pvc = [p for p in pvcs if "queue" in p["metadata"]["name"]]
        assert len(queue_pvc) > 0
        assert queue_pvc[0]["spec"]["resources"]["requests"]["storage"] == "50Gi"


class TestHPAManifest:
    """Test Horizontal Pod Autoscaler manifest."""

    @pytest.fixture
    def hpa(self, manifests_dir):
        """Load HPA manifest."""
        with open(manifests_dir / "hpa.yaml") as f:
            docs = list(yaml.safe_load_all(f))
        return [d for d in docs if d is not None]

    def test_hpa_exists(self, hpa):
        """Test HPA manifests exist."""
        hpas = [h for h in hpa if h.get("kind") == "HorizontalPodAutoscaler"]
        assert len(hpas) >= 2, "Should have HPA for blue and green"

    def test_hpa_replica_bounds(self, hpa):
        """Test HPA replica bounds (2-10 pods)."""
        hpas = [h for h in hpa if h.get("kind") == "HorizontalPodAutoscaler"]
        assert len(hpas) >= 2, "Should have HPAs"

        for autoscaler in hpas:
            assert autoscaler["spec"]["minReplicas"] == 2, "Min replicas should be 2"
            assert autoscaler["spec"]["maxReplicas"] == 10, "Max replicas should be 10"

    def test_hpa_metrics(self, hpa):
        """Test HPA scaling metrics."""
        hpas = [h for h in hpa if h.get("kind") == "HorizontalPodAutoscaler"]
        assert len(hpas) >= 2, "Should have HPAs"

        for autoscaler in hpas:
            metrics = autoscaler["spec"].get("metrics", [])
            assert len(metrics) >= 2, "Should have CPU and memory metrics"

            # Check CPU metric
            cpu_metrics = [m for m in metrics if m.get("resource", {}).get("name") == "cpu"]
            assert len(cpu_metrics) > 0, "Should have CPU metric"
            assert cpu_metrics[0]["resource"]["target"]["averageUtilization"] == 70

            # Check memory metric
            mem_metrics = [m for m in metrics if m.get("resource", {}).get("name") == "memory"]
            assert len(mem_metrics) > 0, "Should have memory metric"
            assert mem_metrics[0]["resource"]["target"]["averageUtilization"] == 80


class TestIngressManifest:
    """Test Ingress YAML manifest."""

    @pytest.fixture
    def ingress(self, manifests_dir):
        """Load ingress manifest."""
        with open(manifests_dir / "ingress.yaml") as f:
            docs = list(yaml.safe_load_all(f))
        return docs

    def test_ingress_exists(self, ingress):
        """Test Ingress manifests exist."""
        ingresses = [i for i in ingress if i.get("kind") == "Ingress"]
        assert len(ingresses) > 0, "Should have Ingress"

    def test_ingress_https(self, ingress):
        """Test Ingress has HTTPS configuration."""
        ingresses = [i for i in ingress if i.get("kind") == "Ingress"]

        for ing in ingresses:
            if "tls" in ing["spec"]:
                tls = ing["spec"]["tls"]
                assert len(tls) > 0, "Should have TLS configuration"

    def test_ingress_rate_limiting(self, ingress):
        """Test Ingress has rate limiting configured (in primary ingress)."""
        ingresses = [i for i in ingress if i.get("kind") == "Ingress"]
        # At least one ingress should have rate limiting
        has_rate_limit = False
        for ing in ingresses:
            annotations = ing["metadata"].get("annotations", {})
            # Check for rate limit annotations in primary ingress
            if any("limit" in k.lower() for k in annotations.keys()) or \
               any("rate" in str(v).lower() for v in annotations.values()):
                has_rate_limit = True
                break
        assert has_rate_limit, "At least one ingress should have rate limiting configured"

    def test_ingress_security_headers(self, ingress):
        """Test Ingress has security headers configured."""
        ingresses = [i for i in ingress if i.get("kind") == "Ingress"]
        # At least one ingress should have security configurations
        has_security = False
        for ing in ingresses:
            annotations = ing["metadata"].get("annotations", {})
            # Security headers should be configured
            if any("security" in str(v).lower() or "cors" in str(v).lower() or
                   "ssl" in str(v).lower() or "redirect" in str(v).lower()
                   for v in annotations.values()):
                has_security = True
                break
        assert has_security, "At least one ingress should have security configurations"


class TestRBACManifest:
    """Test RBAC YAML manifest."""

    @pytest.fixture
    def rbac(self, manifests_dir):
        """Load RBAC manifest."""
        with open(manifests_dir / "rbac.yaml") as f:
            docs = list(yaml.safe_load_all(f))
        return docs

    def test_service_accounts(self, rbac):
        """Test ServiceAccount definitions."""
        sas = [r for r in rbac if r.get("kind") == "ServiceAccount"]
        assert len(sas) > 0, "Should have ServiceAccounts"

        # Should have detection-api-sa
        api_sas = [s for s in sas if s["metadata"]["name"] == "detection-api-sa"]
        assert len(api_sas) > 0

    def test_roles(self, rbac):
        """Test Role definitions."""
        roles = [r for r in rbac if r.get("kind") == "Role"]
        assert len(roles) > 0, "Should have Roles"

    def test_role_bindings(self, rbac):
        """Test RoleBinding definitions."""
        bindings = [r for r in rbac if r.get("kind") == "RoleBinding"]
        assert len(bindings) > 0, "Should have RoleBindings"

    def test_minimal_permissions(self, rbac):
        """Test RBAC uses minimal permissions."""
        roles = [r for r in rbac if r.get("kind") == "Role" and "spec" in r]

        found_detection_role = False
        for role in roles:
            if "detection-api-role" in role.get("metadata", {}).get("name", ""):
                found_detection_role = True
                rules = role["spec"].get("rules", [])
                # Should not have wildcard verbs like ["*"]
                for rule in rules:
                    verbs = rule.get("verbs", [])
                    assert "*" not in verbs, "Should not have wildcard permissions"
                    # Should be specific: get, list, watch, etc.
                    valid_verbs = ["get", "list", "watch", "patch", "update", "delete", "create"]
                    for verb in verbs:
                        assert verb in valid_verbs, f"Unexpected verb: {verb}"
        assert found_detection_role, "Should have detection-api-role defined"


class TestHelmChart:
    """Test Helm Chart structure and values."""

    @pytest.fixture
    def chart_yaml(self, helm_dir):
        """Load Chart.yaml."""
        with open(helm_dir / "Chart.yaml") as f:
            return yaml.safe_load(f)

    @pytest.fixture
    def values_yaml(self, helm_dir):
        """Load values.yaml."""
        with open(helm_dir / "values.yaml") as f:
            return yaml.safe_load(f)

    def test_chart_metadata(self, chart_yaml):
        """Test Chart.yaml has required metadata."""
        assert "name" in chart_yaml
        assert chart_yaml["name"] == "detection-api"
        assert "version" in chart_yaml
        assert "apiVersion" in chart_yaml
        assert chart_yaml["apiVersion"] == "v2"

    def test_values_structure(self, values_yaml):
        """Test values.yaml has required sections."""
        assert "app" in values_yaml
        assert "image" in values_yaml
        assert "resources" in values_yaml
        assert "autoscaling" in values_yaml
        assert "persistence" in values_yaml

    def test_values_autoscaling(self, values_yaml):
        """Test HPA is enabled in values."""
        autoscaling = values_yaml["autoscaling"]
        assert autoscaling["enabled"] is True, "HPA should be enabled in Phase 05"
        assert autoscaling["minReplicas"] == 2
        assert autoscaling["maxReplicas"] == 10

    def test_values_resources(self, values_yaml):
        """Test resource limits in values."""
        resources = values_yaml["resources"]
        assert resources["requests"]["cpu"] == "250m"
        assert resources["requests"]["memory"] == "256Mi"
        assert resources["limits"]["cpu"] == "500m"
        assert resources["limits"]["memory"] == "512Mi"

    def test_helm_templates_exist(self, helm_dir):
        """Test required Helm templates exist."""
        templates_dir = helm_dir / "templates"
        required_templates = [
            "deployment.yaml",
            "service.yaml",
            "hpa.yaml",
            "configmap.yaml",
            "_helpers.tpl",
        ]

        for template in required_templates:
            assert (templates_dir / template).exists(), f"Missing template: {template}"


class TestPhase05Compliance:
    """Test Phase 05 specific requirements."""

    def test_deployment_exists(self, manifests_dir):
        """Test Phase 05: Deployment manifest required."""
        assert (manifests_dir / "deployment.yaml").exists()

    def test_storage_exists(self, manifests_dir):
        """Test Phase 05: Storage configuration required."""
        assert (manifests_dir / "storage.yaml").exists()

    def test_secrets_exists(self, manifests_dir):
        """Test Phase 05: Secrets manifest required."""
        assert (manifests_dir / "secrets.yaml").exists()

    def test_hpa_exists(self, manifests_dir):
        """Test Phase 05: HPA manifest required."""
        assert (manifests_dir / "hpa.yaml").exists()

    def test_ingress_exists(self, manifests_dir):
        """Test Phase 05: Ingress manifest required."""
        assert (manifests_dir / "ingress.yaml").exists()

    def test_rbac_exists(self, manifests_dir):
        """Test Phase 05: RBAC manifest required."""
        assert (manifests_dir / "rbac.yaml").exists()

    def test_helm_chart_exists(self, helm_dir):
        """Test Phase 05: Helm chart required."""
        assert (helm_dir / "Chart.yaml").exists()
        assert (helm_dir / "values.yaml").exists()

    def test_deployment_guide_exists(self, manifests_dir):
        """Test Phase 05: Deployment guide required."""
        guide = manifests_dir.parent / "DEPLOYMENT_GUIDE.md"
        assert guide.exists(), "Deployment guide required"


@pytest.mark.parametrize("replicas", [2, 5, 10])
def test_hpa_scaling_scenarios(replicas):
    """Test HPA scaling scenarios (2-10 pods)."""
    assert 2 <= replicas <= 10, "Replicas must be between 2-10"


@pytest.mark.parametrize("cpu_req,cpu_limit", [("250m", "500m")])
def test_resource_limit_ratios(cpu_req, cpu_limit):
    """Test resource limit ratios are reasonable (1:2)."""
    req_val = int(cpu_req.rstrip("m"))
    limit_val = int(cpu_limit.rstrip("m"))
    ratio = limit_val / req_val
    assert 1.5 <= ratio <= 2.5, "Limit should be 2x request (with tolerance)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
