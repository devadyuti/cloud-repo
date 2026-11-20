# Design Document

## Overview

This design describes the AWS Landing Zone for the AnyCompany migration. The landing zone provides a multi-account structure using AWS Control Tower, with Terraform-defined infrastructure for networking, security, compute, and database resources. The target environment supports a lift-and-shift migration of 4 servers (2 web, 2 database) from on-premises to AWS using MGN and DMS over the public internet.

### Key Design Decisions

1. **AWS Control Tower** — Automates account factory, guardrails, and baseline security. Reduces landing zone build time from 3–4 weeks to 1.5–2 weeks.
2. **Internet-only connectivity** — No VPN or Direct Connect. MGN agents and DMS communicate over HTTPS/TLS. Simplifies networking significantly.
3. **Terraform for IaC** — All resources below the Control Tower layer are defined in Terraform. Control Tower itself is configured via the console (it manages its own CloudFormation stacks).
4. **Separate accounts for PRD and RC** — Blast radius isolation. SCPs can differ between Production and Non-Production OUs.
5. **eu-west-1 (Ireland)** — Single region deployment. SCPs deny all other regions.
6. **No bastion hosts** — EC2 management via SSM Session Manager. No SSH keys, no port 22.

## Architecture

```
AWS Organizations (Management Account)
│
├── Security OU
│   └── Log Archive Account
│       ├── S3: CloudTrail logs (all accounts)
│       ├── S3: Config snapshots (all accounts)
│       └── S3: VPC Flow Logs (all accounts)
│
├── Production OU
│   └── AnyCompany-Prod Account
│       └── VPC (10.1.0.0/16) — eu-west-1
│           ├── Public Subnet AZ-a (10.1.1.0/24) — ALB, NAT GW
│           ├── Public Subnet AZ-b (10.1.2.0/24) — ALB
│           ├── Private Subnet AZ-a (10.1.10.0/24) — EC2, RDS primary
│           └── Private Subnet AZ-b (10.1.11.0/24) — RDS standby (Multi-AZ)
│
└── Non-Production OU
    └── AnyCompany-RC Account
        └── VPC (10.2.0.0/16) — eu-west-1
            ├── Public Subnet AZ-a (10.2.1.0/24) — ALB, NAT GW
            ├── Public Subnet AZ-b (10.2.2.0/24) — ALB
            ├── Private Subnet AZ-a (10.2.10.0/24) — EC2, RDS
            └── Private Subnet AZ-b (10.2.11.0/24)
```

### Network Flow

```
Internet
  │
  ├──► ALB (public subnets, 80/443)
  │      │
  │      └──► EC2 Web Server (private subnets, SG: ALB only)
  │             │
  │             └──► RDS MySQL (private subnets, SG: EC2 only, port 3306)
  │
  ├──► MGN Agent (on-prem) ──HTTPS──► MGN Service Endpoint (internet)
  │
  └──► DMS Replication Instance (public subnet) ──► On-prem MySQL (internet, SSL)
         │
         └──► RDS MySQL (private subnet, SG: DMS SG, port 3306)
```

### Security Group Rules

| Security Group | Inbound | Source | Port |
|---------------|---------|--------|------|
| ALB-SG | HTTPS | 0.0.0.0/0 | 443 |
| ALB-SG | HTTP | 0.0.0.0/0 | 80 |
| EC2-SG | HTTP | ALB-SG | 80 |
| EC2-SG | HTTPS | ALB-SG | 443 |
| RDS-SG | MySQL | EC2-SG | 3306 |
| RDS-SG | MySQL | DMS-SG | 3306 |
| DMS-SG | (outbound only) | — | — |

### SCPs

| SCP | Effect | Applied To |
|-----|--------|-----------|
| Deny non-eu-west-1 regions | Deny all actions outside eu-west-1 (except global services: IAM, STS, Organizations, Billing) | All OUs |
| Deny root user actions | Deny all actions by root user in member accounts | Production OU, Non-Production OU |
| Deny CloudTrail disable | Deny `cloudtrail:StopLogging`, `cloudtrail:DeleteTrail` | All OUs |
| Deny GuardDuty disable | Deny `guardduty:DisableOrganizationAdminAccount`, `guardduty:DeleteDetector` | All OUs |

## Terraform Project Structure

```
anycompany-landing-zone/
├── README.md
├── docs/
│   ├── architecture.md
│   ├── access-guide.md
│   ├── runbook.md
│   └── migration-readiness.md
├── terraform/
│   ├── backend.tf              # S3 + DynamoDB state backend config
│   ├── providers.tf            # AWS provider config with assume role
│   ├── variables.tf            # Global variables (region, account IDs, project tags)
│   ├── outputs.tf              # Key outputs (VPC IDs, subnet IDs, RDS endpoints)
│   ├── main.tf                 # Root module — calls child modules
│   ├── environments/
│   │   ├── prod.tfvars         # PRD-specific values (instance sizes, CIDR, Multi-AZ)
│   │   └── rc.tfvars           # RC-specific values (smaller instances, Single-AZ)
│   └── modules/
│       ├── networking/
│       │   ├── main.tf         # VPC, subnets, IGW, NAT GW, route tables
│       │   ├── variables.tf
│       │   └── outputs.tf
│       ├── security/
│       │   ├── main.tf         # Security groups, NACLs, GuardDuty, Config rules
│       │   ├── variables.tf
│       │   └── outputs.tf
│       ├── compute/
│       │   ├── main.tf         # EC2 instance, ALB, target group, SSM role
│       │   ├── variables.tf
│       │   └── outputs.tf
│       ├── database/
│       │   ├── main.tf         # RDS MySQL, subnet group, parameter group
│       │   ├── variables.tf
│       │   └── outputs.tf
│       ├── monitoring/
│       │   ├── main.tf         # CloudWatch dashboards, alarms, SNS topic
│       │   ├── variables.tf
│       │   └── outputs.tf
│       └── migration/
│           ├── main.tf         # MGN IAM roles, DMS IAM roles, DMS security group
│           ├── variables.tf
│           └── outputs.tf
```

### Terraform Module Interfaces

#### networking module

```hcl
# Input variables
variable "vpc_cidr"           {}  # e.g., "10.1.0.0/16"
variable "public_subnet_cidrs" {} # e.g., ["10.1.1.0/24", "10.1.2.0/24"]
variable "private_subnet_cidrs" {} # e.g., ["10.1.10.0/24", "10.1.11.0/24"]
variable "availability_zones"  {} # e.g., ["eu-west-1a", "eu-west-1b"]
variable "environment"         {} # "prod" or "rc"
variable "project_tags"        {} # Common tags

# Outputs
output "vpc_id"              {}
output "public_subnet_ids"   {}
output "private_subnet_ids"  {}
output "nat_gateway_id"      {}
```

#### security module

```hcl
# Input variables
variable "vpc_id"             {}
variable "environment"        {}
variable "project_tags"       {}

# Outputs
output "alb_security_group_id" {}
output "ec2_security_group_id" {}
output "rds_security_group_id" {}
output "dms_security_group_id" {}
```

#### compute module

```hcl
# Input variables
variable "instance_type"       {} # e.g., "m6i.xlarge"
variable "ami_id"              {} # Amazon Linux 2023
variable "public_subnet_ids"   {}
variable "private_subnet_ids"  {}
variable "alb_security_group_id" {}
variable "ec2_security_group_id" {}
variable "vpc_id"              {}
variable "environment"         {}
variable "project_tags"        {}

# Outputs
output "ec2_instance_id"     {}
output "alb_dns_name"        {}
output "alb_arn"             {}
```

#### database module

```hcl
# Input variables
variable "instance_class"     {} # e.g., "db.m6i.2xlarge"
variable "multi_az"           {} # true for prod, false for RC
variable "private_subnet_ids" {}
variable "rds_security_group_id" {}
variable "backup_retention"   {} # 7 for prod, 1 for RC
variable "environment"        {}
variable "project_tags"       {}

# Outputs
output "rds_endpoint"        {}
output "rds_port"            {}
output "rds_instance_id"     {}
```

#### monitoring module

```hcl
# Input variables
variable "ec2_instance_id"   {}
variable "rds_instance_id"   {}
variable "alb_arn"           {}
variable "sns_email"         {} # Alert recipient
variable "environment"       {}
variable "project_tags"      {}

# Outputs
output "dashboard_url"       {}
output "sns_topic_arn"       {}
```

#### migration module

```hcl
# Input variables
variable "rds_security_group_id" {}
variable "vpc_id"                {}
variable "public_subnet_ids"     {}
variable "environment"           {}
variable "project_tags"          {}

# Outputs
output "mgn_role_arn"        {}
output "dms_role_arn"        {}
output "dms_security_group_id" {}
```

### Environment-Specific Variables

#### prod.tfvars

```hcl
environment          = "prod"
vpc_cidr             = "10.1.0.0/16"
public_subnet_cidrs  = ["10.1.1.0/24", "10.1.2.0/24"]
private_subnet_cidrs = ["10.1.10.0/24", "10.1.11.0/24"]
ec2_instance_type    = "m6i.xlarge"
rds_instance_class   = "db.m6i.2xlarge"
rds_multi_az         = true
rds_backup_retention = 7
```

#### rc.tfvars

```hcl
environment          = "prod"
vpc_cidr             = "10.2.0.0/16"
public_subnet_cidrs  = ["10.2.1.0/24", "10.2.2.0/24"]
private_subnet_cidrs = ["10.2.10.0/24", "10.2.11.0/24"]
ec2_instance_type    = "m6i.xlarge"
rds_instance_class   = "db.t3.xlarge"
rds_multi_az         = false
rds_backup_retention = 1
```

## Data Models

### Tagging Standard

All resources receive these tags:

```hcl
tags = {
  Project     = "AnyCompany"
  Environment = var.environment  # "prod" or "rc"
  Owner       = "AnyCompany"
  ManagedBy   = "Terraform"
}
```

### CIDR Allocation

| Account | VPC CIDR | Public AZ-a | Public AZ-b | Private AZ-a | Private AZ-b |
|---------|----------|-------------|-------------|--------------|--------------|
| PRD | 10.1.0.0/16 | 10.1.1.0/24 | 10.1.2.0/24 | 10.1.10.0/24 | 10.1.11.0/24 |
| RC | 10.2.0.0/16 | 10.2.1.0/24 | 10.2.2.0/24 | 10.2.10.0/24 | 10.2.11.0/24 |

### RDS Configuration

| Parameter | PRD | RC |
|-----------|-----|-----|
| Instance class | db.m6i.2xlarge | db.t3.xlarge |
| Multi-AZ | Yes | No |
| Engine | MySQL 8.0 | MySQL 8.0 |
| Storage | gp3, 100 GB, autoscaling to 500 GB | gp3, 50 GB, autoscaling to 200 GB |
| Backup retention | 7 days | 1 day |
| Encryption | Yes (aws/rds KMS key) | Yes (aws/rds KMS key) |
| SSL enforced | Yes | Yes |

### EC2 Configuration

| Parameter | PRD | RC |
|-----------|-----|-----|
| Instance type | m6i.xlarge (4 vCPU, 16 GB) | m6i.xlarge (4 vCPU, 16 GB) |
| AMI | Amazon Linux 2023 (latest) | Amazon Linux 2023 (latest) |
| Root volume | gp3, 30 GB | gp3, 30 GB |
| Management | SSM Session Manager | SSM Session Manager |
| Key pair | None (SSM only) | None (SSM only) |

## Error Handling

### Terraform State Locking

Terraform state is stored in S3 with DynamoDB locking. If a lock conflict occurs (concurrent applies), Terraform will fail with a lock error. Resolution: wait for the other operation to complete or force-unlock if the lock is stale.

### Control Tower Guardrail Violations

If a Terraform apply attempts an action blocked by an SCP (e.g., creating a resource in us-east-1), the AWS API will return an `AccessDeniedException`. The Terraform plan should catch this before apply by validating the region in the provider configuration.

### RDS Provisioning Failures

If the requested RDS instance class is not available in the selected AZ, Terraform will fail at apply time. The `database` module should use `aws_rds_orderable_db_instance` data source to validate availability before provisioning.

## Testing Strategy

### Terraform Validation

1. `terraform fmt -check` — Ensure consistent formatting
2. `terraform validate` — Syntax and reference validation
3. `terraform plan -var-file=environments/prod.tfvars` — Dry-run for PRD
4. `terraform plan -var-file=environments/rc.tfvars` — Dry-run for RC

### Post-Apply Verification

After each environment is applied, verify:
- VPC and subnets exist with correct CIDRs
- Internet Gateway and NAT Gateway are functional
- Security groups have correct rules
- EC2 instance is reachable via ALB
- RDS instance is accessible from EC2 (MySQL connection test)
- CloudTrail is logging to Log Archive S3 bucket
- GuardDuty is enabled
- SSM Session Manager can connect to EC2

### Migration Readiness Checks

- MGN IAM role exists and has correct permissions
- DMS IAM role exists and can access RDS
- DMS security group allows outbound to internet (for on-prem MySQL)
- RDS security group allows inbound from DMS security group
