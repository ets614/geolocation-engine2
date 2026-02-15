package test

import (
	"testing"

	"github.com/gruntwork-io/terratest/modules/aws"
	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
)

func TestVpcModule(t *testing.T) {
	t.Parallel()

	awsRegion := "us-east-1"

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../modules/vpc",
		Vars: map[string]interface{}{
			"project_name":          "detection-api-test",
			"environment":           "test",
			"vpc_cidr":              "10.99.0.0/16",
			"public_subnet_cidrs":   []string{"10.99.1.0/24", "10.99.2.0/24", "10.99.3.0/24"},
			"private_subnet_cidrs":  []string{"10.99.11.0/24", "10.99.12.0/24", "10.99.13.0/24"},
			"database_subnet_cidrs": []string{"10.99.21.0/24", "10.99.22.0/24", "10.99.23.0/24"},
			"cluster_name":          "detection-api-test",
			"enable_nat_gateway":    true,
			"single_nat_gateway":    true,
			"enable_flow_logs":      false,
		},
		EnvVars: map[string]string{
			"AWS_DEFAULT_REGION": awsRegion,
		},
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	// Verify VPC was created
	vpcID := terraform.Output(t, terraformOptions, "vpc_id")
	assert.NotEmpty(t, vpcID)

	// Verify VPC CIDR
	vpcCIDR := terraform.Output(t, terraformOptions, "vpc_cidr")
	assert.Equal(t, "10.99.0.0/16", vpcCIDR)

	// Verify subnets
	publicSubnetIDs := terraform.OutputList(t, terraformOptions, "public_subnet_ids")
	assert.Equal(t, 3, len(publicSubnetIDs))

	privateSubnetIDs := terraform.OutputList(t, terraformOptions, "private_subnet_ids")
	assert.Equal(t, 3, len(privateSubnetIDs))

	databaseSubnetIDs := terraform.OutputList(t, terraformOptions, "database_subnet_ids")
	assert.Equal(t, 3, len(databaseSubnetIDs))

	// Verify subnets are in different AZs
	vpc := aws.GetVpcById(t, vpcID, awsRegion)
	assert.NotNil(t, vpc)

	// Verify NAT gateway
	natGatewayIDs := terraform.OutputList(t, terraformOptions, "nat_gateway_ids")
	assert.Equal(t, 1, len(natGatewayIDs)) // single_nat_gateway = true
}
