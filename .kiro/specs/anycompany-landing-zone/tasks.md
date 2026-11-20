# Implementation Plan: AnyCompany Landing Zone

## Overview

Build an AWS Landing Zone for the AnyCompany migration using AWS Control Tower and Terraform. The landing zone provides multi-account governance, networking, security, compute, database, and migration readiness for a 4-server lift-and-shift from on-premises to AWS (eu-west-1, internet-only connectivity).

## Tasks

- [ ] 1. Project scaffold and Terraform backend
  - [ ] 1.1 Create `anycompany-landing-zone/` directory structure with `terraform/`, `terraform/modules/`, `terraform/environments/`, and `docs/` folders
    - _Requirements: 8.1_
  - [ ] 1.2 Create `terraform/backend.tf` with S3 state backend and DynamoDB locking configuration (Management Account)
    - _Requirements: 8.2_
  - [ ] 1.3 Create `terraform/providers.tf` with AWS provider for eu-west-1 and assume role configuration for cross-account deployment
    - _Requirements: 8.1_
  - [ ] 1.4 Create `terraform/variables.tf` with global variables: region, account IDs, project tags, environment name
    - _Requirements: 8.4_
  - [ ] 1.5 Create `terraform/outputs.tf` with key outputs: VPC IDs, subnet IDs, RDS endpoints, ALB DNS names
    - _Requirements: 8.1_
  - [ ] 1.6 Create `terraform/environments/prod.tfvars` and `terraform/environments/rc.tfvars` with environment-specific values (CIDRs, instance sizes, Multi-AZ settings)
    - _Requirements: 8.4_

- [ ] 2. Networking module
  - [ ] 2.1 Create `terraform/modules/networking/variables.tf` with inputs: vpc_cidr, public_subnet_cidrs, private_subnet_cidrs, availability_zones, environment, project_tags
    - _Requirements: 2.1, 2.2_
  - [ ] 2.2 Create `terraform/modules/networking/main.tf` with: VPC, 2 public subnets, 2 private subnets, Internet Gateway, NAT Gateway (single AZ), public and private route tables with correct routing
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  - [ ] 2.3 Create `terraform/modules/networking/outputs.tf` exposing vpc_id, public_subnet_ids, private_subnet_ids, nat_gateway_id
    - _Requirements: 2.1_
  - [ ] 2.4 Enable VPC Flow Logs on the VPC, delivering to CloudWatch Logs group (cross-account delivery to Log Archive handled in monitoring module)
    - _Requirements: 3.4_

- [ ] 3. Security module
  - [ ] 3.1 Create `terraform/modules/security/variables.tf` with inputs: vpc_id, environment, project_tags
    - _Requirements: 3.1_
  - [ ] 3.2 Create `terraform/modules/security/main.tf` with security groups: ALB-SG (80/443 from 0.0.0.0/0), EC2-SG (80/443 from ALB-SG only), RDS-SG (3306 from EC2-SG and DMS-SG), DMS-SG (outbound only)
    - _Requirements: 7.3, 9.3_
  - [ ] 3.3 Add AWS Config rules to security module: encrypted-volumes, rds-multi-az (prod only), restricted-ssh, required-tags
    - _Requirements: 3.3_
  - [ ] 3.4 Create `terraform/modules/security/outputs.tf` exposing all security group IDs
    - _Requirements: 3.2_

- [ ] 4. Compute module
  - [ ] 4.1 Create `terraform/modules/compute/variables.tf` with inputs: instance_type, ami_id, subnet IDs, security group IDs, vpc_id, environment, project_tags
    - _Requirements: 7.1, 7.2_
  - [ ] 4.2 Create `terraform/modules/compute/main.tf` with: EC2 instance (Amazon Linux 2023, SSM IAM role, no key pair), Application Load Balancer (public subnets, HTTP/HTTPS listeners), target group, and ALB-to-EC2 registration
    - _Requirements: 7.1, 7.2, 7.5_
  - [ ] 4.3 Create IAM instance profile for EC2 with AmazonSSMManagedInstanceCore policy
    - _Requirements: 7.5_
  - [ ] 4.4 Create `terraform/modules/compute/outputs.tf` exposing ec2_instance_id, alb_dns_name, alb_arn
    - _Requirements: 7.1_

- [ ] 5. Database module
  - [ ] 5.1 Create `terraform/modules/database/variables.tf` with inputs: instance_class, multi_az, private_subnet_ids, rds_security_group_id, backup_retention, environment, project_tags
    - _Requirements: 7.1, 7.2_
  - [ ] 5.2 Create `terraform/modules/database/main.tf` with: RDS MySQL 8.0 instance, DB subnet group, custom parameter group, gp3 storage with autoscaling, encryption at rest, automated backups, SSL enforcement
    - _Requirements: 7.1, 7.2, 7.4_
  - [ ] 5.3 Create `terraform/modules/database/outputs.tf` exposing rds_endpoint, rds_port, rds_instance_id
    - _Requirements: 7.1_

- [ ] 6. Monitoring module
  - [ ] 6.1 Create `terraform/modules/monitoring/variables.tf` with inputs: ec2_instance_id, rds_instance_id, alb_arn, sns_email, environment, project_tags
    - _Requirements: 5.1_
  - [ ] 6.2 Create `terraform/modules/monitoring/main.tf` with: SNS topic for alerts, CloudWatch alarms (root login, unauthorized API calls, billing threshold), CloudWatch dashboard (EC2 CPU/memory, RDS CPU/connections/storage)
    - _Requirements: 5.3, 5.4_
  - [ ] 6.3 Add S3 bucket configuration for centralized logging (Log Archive Account): lifecycle policy (Glacier after 90 days, delete after 365 days), SSE-S3 encryption, bucket policy for cross-account CloudTrail/Config/Flow Log delivery
    - _Requirements: 5.1, 5.2_
  - [ ] 6.4 Create `terraform/modules/monitoring/outputs.tf` exposing dashboard_url, sns_topic_arn
    - _Requirements: 5.3_

- [ ] 7. Migration module
  - [ ] 7.1 Create `terraform/modules/migration/variables.tf` with inputs: rds_security_group_id, vpc_id, public_subnet_ids, environment, project_tags
    - _Requirements: 9.1_
  - [ ] 7.2 Create `terraform/modules/migration/main.tf` with: MGN IAM role (AWSApplicationMigrationServiceRole), DMS IAM roles (dms-vpc-role, dms-cloudwatch-logs-role), DMS replication subnet group, DMS security group allowing outbound internet
    - _Requirements: 9.1, 9.2, 9.3_
  - [ ] 7.3 Create `terraform/modules/migration/outputs.tf` exposing mgn_role_arn, dms_role_arn, dms_security_group_id
    - _Requirements: 9.1_

- [ ] 8. Root module wiring
  - [ ] 8.1 Create `terraform/main.tf` that calls all child modules (networking, security, compute, database, monitoring, migration) with correct variable passing and dependency ordering
    - _Requirements: 8.1, 8.3_
  - [ ] 8.2 Verify `terraform fmt -check` and `terraform validate` pass
    - _Requirements: 8.1_

- [ ] 9. Checkpoint — Terraform plan review
  - Run `terraform plan -var-file=environments/prod.tfvars` and `terraform plan -var-file=environments/rc.tfvars`. Review the plan output for correctness. Ask the user if questions arise.

- [ ] 10. SCPs and Organization Policies (documentation only — applied via Control Tower console)
  - [ ] 10.1 Create `terraform/scps/deny-non-approved-regions.json` — deny all actions outside eu-west-1 (except global services)
    - _Requirements: 3.5_
  - [ ] 10.2 Create `terraform/scps/deny-root-user.json` — deny all actions by root user in member accounts
    - _Requirements: 3.5_
  - [ ] 10.3 Create `terraform/scps/deny-security-disable.json` — deny disabling CloudTrail and GuardDuty
    - _Requirements: 3.5_

- [ ] 11. Documentation
  - [ ] 11.1 Create `docs/architecture.md` with architecture diagram (account structure, VPC layout, security boundaries, network flows)
    - _Requirements: 10.1_
  - [ ] 11.2 Create `docs/access-guide.md` documenting SSO login, account switching, and permission sets
    - _Requirements: 10.2_
  - [ ] 11.3 Create `docs/runbook.md` with operational procedures: CloudTrail log review, GuardDuty findings, RDS backup/restore, EC2 management via SSM
    - _Requirements: 10.3_
  - [ ] 11.4 Create `docs/migration-readiness.md` with pre-migration checklist for MGN and DMS
    - _Requirements: 10.4, 9.4_
  - [ ] 11.5 Create `anycompany-landing-zone/README.md` with project overview, prerequisites, Terraform init/plan/apply instructions, and links to docs
    - _Requirements: 8.5_

- [ ] 12. Billing and cost management
  - [ ] 12.1 Add cost allocation tag definitions to `terraform/variables.tf` and ensure all modules apply tags consistently
    - _Requirements: 6.1, 6.4_
  - [ ] 12.2 Add AWS Budget resource to monitoring module with 80% and 100% threshold alerts (~$1,200/month)
    - _Requirements: 6.2_

- [ ] 13. Final checkpoint — Full review
  - Verify all Terraform files pass fmt and validate. Review documentation completeness. Confirm migration readiness checklist covers all MGN/DMS prerequisites. Ask the user if questions arise.

## Notes

- Control Tower setup (Requirement 1) is done via the AWS Console, not Terraform. The spec covers the Terraform-managed resources that sit within the Control Tower-governed accounts.
- IAM Identity Center (Requirement 4) is configured via the Console/CLI after Control Tower setup. Permission set definitions are documented in `docs/access-guide.md`.
- SCPs (Requirement 3.5) are defined as JSON files in the repo but applied via the Control Tower console or AWS Organizations CLI.
- All file paths are relative to `anycompany-landing-zone/`
- Terraform state backend (S3 + DynamoDB) must be created manually before first `terraform init`
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
