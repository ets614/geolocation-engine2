# Infrastructure Cost Estimate - Detection API

## Production Environment (Monthly)

| Resource                     | Spec                    | Qty | Unit Cost  | Monthly     |
|------------------------------|-------------------------|-----|------------|-------------|
| **EKS Cluster**              | Control plane            | 1   | $73        | $73         |
| **App Node Group**           | m6i.xlarge (4c/16GB)    | 3   | $138       | $414        |
| **Monitoring Node Group**    | m6i.large (2c/8GB)      | 2   | $69        | $138        |
| **RDS PostgreSQL Primary**   | db.r6g.large Multi-AZ   | 1   | $196       | $196        |
| **RDS Read Replica**         | db.r6g.large             | 1   | $98        | $98         |
| **RDS Storage**              | gp3, 100GB              | 1   | $12        | $12         |
| **NAT Gateway**              | Per AZ                  | 3   | $32        | $96         |
| **NAT Gateway Data**         | ~100GB/mo estimated     | 3   | $15        | $45         |
| **S3 Backup Storage**        | ~50GB estimated         | 1   | $1         | $1          |
| **CloudWatch Logs**          | ~20GB/mo estimated      | 1   | $10        | $10         |
| **EBS (PVCs)**               | gp3, ~200GB total       | 1   | $16        | $16         |
| **KMS Keys**                 | 3 keys                  | 3   | $1         | $3          |
| **Load Balancer (ALB)**      | Application LB          | 1   | $22        | $22         |
| **Data Transfer**            | ~50GB/mo estimated      | 1   | $5         | $5          |
|                              |                         |     | **Total:** | **$1,129**  |

## Environment Comparison

| Environment | Estimated Monthly Cost |
|-------------|----------------------|
| Dev         | ~$350                |
| Staging     | ~$650                |
| Production  | ~$1,129              |
| **Total**   | **~$2,129**          |

## Cost Optimization Notes

1. **Dev**: t3.large instances, single NAT, no Multi-AZ, no read replica
2. **Staging**: m6i.large instances, single NAT, Multi-AZ (mirrors prod config), no replica
3. **Production**: Full HA with Multi-AZ, 3 NAT gateways, read replica
4. **Reserved Instances**: 1-year RI for production nodes could save ~30% (~$340/mo)
5. **Spot Instances**: Dev/staging app nodes could use spot for ~60% savings
6. **Scale-to-zero**: Dev cluster can be scheduled off during non-business hours (saves ~$200/mo)

## Scaling Cost Projections

| Load Level          | App Nodes | Est. Monthly |
|---------------------|-----------|--------------|
| Low (current)       | 3         | $1,129       |
| Medium (10x)        | 5         | $1,405       |
| High (50x)          | 8         | $1,819       |
| Peak (100x)         | 10        | $2,095       |

Auto-scaling from 3 to 10 nodes adds ~$966/mo at peak.
