# Requirements Document

## Introduction

This document defines the requirements for building an AWS Landing Zone for the AnyCompany migration project. The landing zone provides the foundational AWS account structure, networking, security, identity, and governance controls needed before migrating the AnyCompany application (4 servers: PRD-WEB, PRD-DB, RC-WEB, RC-DB) from on-premises to AWS. The migration uses internet-only connectivity (no VPN or Direct Connect), with EC2 for web servers and RDS MySQL for databases. Infrastructure is defined as code using Terraform to ensure repeatability across environments.

## Glossary

- **Landing_Zone**: The foundational AWS environment including account structure, networking, security baselines, identity management, and governance controls.
- **Control_Tower**: AWS Control Tower — the managed service used to set up and govern a multi-account AWS environment with pre-configured guardrails.
- **PRD_Account**: The AWS account hosting the AnyCompany production workload (PRD-WEB EC2 and PRD-DB RDS).
- **RC_Account**: The AWS account hosting the AnyCompany release candidate / staging workload (RC-WEB EC2 and RC-DB RDS).
- **Management_Account**: The AWS Organizations management account used for billing, SCPs, and Control Tower administration.
- **Log_Archive_Account**: The centralized account for CloudTrail, Config, and VPC Flow Log storage.
- **IaC**: Infrastructure as Code — Terraform is used to define all landing zone resources declaratively.
- **SCP**: Service Control Policy — organization-level policies that restrict actions across member accounts.
- **SSO**: AWS IAM Identity Center (formerly AWS SSO) — centralized identity and access management for all accounts.

## Requirements

### Requirement 1: AWS Account Structure

**User Story:** As a cloud engineer, I want a well-structured multi-account setup using AWS Organizations and Control Tower, so that workloads are isolated and governed from day one.

#### Acceptance Criteria

1. THE Landing_Zone SHALL use AWS Control Tower to create and manage the multi-account structure.
2. THE Landing_Zone SHALL include the following accounts: Management_Account, Log_Archive_Account, PRD_Account, and RC_Account.
3. THE account structure SHALL use Organizational Units (OUs): Security OU (containing Log_Archive_Account), Production OU (containing PRD_Account), and Non-Production OU (containing RC_Account).
4. THE Management_Account SHALL NOT host any application workloads — it is reserved for billing, SCPs, and Control Tower administration only.

### Requirement 2: Networking (VPC, Subnets, Internet Access)

**User Story:** As a cloud engineer, I want a VPC in each workload account with public and private subnets across two Availability Zones, so that web servers are publicly accessible and databases are isolated in private subnets.

#### Acceptance Criteria

1. EACH workload account (PRD_Account, RC_Account) SHALL have a VPC with a CIDR block that does not overlap between accounts.
2. EACH VPC SHALL contain public subnets (2 AZs) and private subnets (2 AZs) in the eu-west-1 region.
3. EACH VPC SHALL have an Internet Gateway attached for public subnet internet access.
4. EACH VPC SHALL have a NAT Gateway in one public subnet for private subnet outbound internet access (required for RDS patching, DMS, and MGN agent communication).
5. Route tables SHALL route public subnet traffic to the Internet Gateway and private subnet traffic to the NAT Gateway.
6. THERE SHALL be no VPN or Direct Connect — all connectivity is over the public internet.

### Requirement 3: Security Baseline

**User Story:** As a security engineer, I want foundational security services enabled across all accounts, so that threats are detected, configurations are tracked, and API activity is logged from the start.

#### Acceptance Criteria

1. AWS CloudTrail SHALL be enabled in all accounts with logs delivered to the Log_Archive_Account S3 bucket.
2. AWS GuardDuty SHALL be enabled in all accounts for threat detection.
3. AWS Config SHALL be enabled in all accounts with a set of managed rules for baseline compliance (e.g., encrypted-volumes, rds-multi-az, restricted-ssh).
4. VPC Flow Logs SHALL be enabled on all VPCs and delivered to the Log_Archive_Account.
5. SCPs SHALL be applied to the Organization to: deny usage of non-approved regions (allow only eu-west-1), prevent root account usage in member accounts, and deny disabling of CloudTrail or GuardDuty.

### Requirement 4: Identity and Access Management

**User Story:** As a cloud engineer, I want centralized identity management using IAM Identity Center, so that team members can access the right accounts with the right permissions using SSO.

#### Acceptance Criteria

1. AWS IAM Identity Center (SSO) SHALL be configured in the Management_Account.
2. THE Landing_Zone SHALL define the following permission sets: AdministratorAccess (full access), ReadOnlyAccess (read-only for monitoring/troubleshooting), and DatabaseAdminAccess (RDS management permissions).
3. MFA SHALL be enforced for all SSO users.
4. IAM roles within workload accounts SHALL follow least-privilege principles — no wildcard (`*`) resource permissions in production.

### Requirement 5: Logging and Monitoring

**User Story:** As an operations engineer, I want centralized logging and basic CloudWatch dashboards, so that I can monitor the landing zone health and troubleshoot issues.

#### Acceptance Criteria

1. CloudTrail logs, Config snapshots, and VPC Flow Logs SHALL be stored in a dedicated S3 bucket in the Log_Archive_Account with server-side encryption (SSE-S3 or SSE-KMS).
2. The Log_Archive S3 bucket SHALL have a lifecycle policy to transition logs to S3 Glacier after 90 days and delete after 365 days.
3. CloudWatch alarms SHALL be configured for: root account login attempts, unauthorized API calls, and billing threshold alerts.
4. EACH workload account SHALL have a basic CloudWatch dashboard showing EC2 and RDS key metrics (CPU, memory, disk, connections).

### Requirement 6: Billing and Cost Management

**User Story:** As a project manager, I want cost allocation tags, budgets, and alerts configured, so that AnyCompany has visibility into AWS spend from day one.

#### Acceptance Criteria

1. Cost allocation tags SHALL be defined: `Project: AnyCompany`, `Environment: Production | RC`, `Owner: AnyCompany`.
2. AWS Budgets SHALL be configured with a monthly budget alert at 80% and 100% of the estimated monthly spend (~$1,200/month based on the cost estimate).
3. Cost Explorer SHALL be enabled in the Management_Account.
4. ALL IaC-provisioned resources SHALL include the required cost allocation tags.

### Requirement 7: Application Infrastructure (EC2 + RDS)

**User Story:** As a cloud engineer, I want the target EC2 and RDS instances provisioned in each workload account, so that the migration tools (MGN, DMS) have a target to replicate into.

#### Acceptance Criteria

1. THE PRD_Account SHALL contain: one EC2 instance (m6i.xlarge, 4 vCPU, 16 GB) in a public subnet behind an Application Load Balancer, and one RDS MySQL instance (db.m6i.2xlarge, Multi-AZ) in private subnets.
2. THE RC_Account SHALL contain: one EC2 instance (m6i.xlarge) in a public subnet behind an ALB, and one RDS MySQL instance (db.t3.xlarge, Single-AZ) in private subnets.
3. Security groups SHALL restrict: ALB ingress to 80/443 from 0.0.0.0/0, EC2 ingress to ALB security group only, RDS ingress to EC2 security group only (port 3306).
4. RDS instances SHALL have automated backups enabled (7-day retention for PRD, 1-day for RC), encryption at rest, and SSL enforced for connections.
5. EC2 instances SHALL use Amazon Linux 2023 AMI with SSM Agent for management (no SSH key pairs needed).

### Requirement 8: Infrastructure as Code (Terraform)

**User Story:** As a cloud engineer, I want all landing zone resources defined in Terraform, so that the infrastructure is repeatable, version-controlled, and auditable.

#### Acceptance Criteria

1. ALL landing zone resources (VPCs, subnets, security groups, IAM roles, RDS, EC2, ALB, CloudWatch) SHALL be defined in Terraform configuration files.
2. Terraform state SHALL be stored in an S3 backend with DynamoDB locking in the Management_Account.
3. THE Terraform code SHALL be organized into reusable modules: `networking`, `security`, `compute`, `database`, `monitoring`.
4. THE Terraform code SHALL use variables for environment-specific values (instance sizes, CIDR blocks, account IDs) to support both PRD and RC deployments from the same codebase.
5. A `README.md` SHALL document how to initialize, plan, and apply the Terraform configuration.

### Requirement 9: Migration Readiness

**User Story:** As a migration engineer, I want the landing zone pre-configured for MGN and DMS, so that migration can begin immediately after the landing zone is built.

#### Acceptance Criteria

1. IAM roles for AWS MGN (AWSApplicationMigrationServiceRole) SHALL be created in each workload account.
2. IAM roles for AWS DMS SHALL be created in each workload account with permissions to access the target RDS instances.
3. Security groups SHALL allow inbound HTTPS (443) from the internet for MGN agent communication and inbound MySQL (3306) from the DMS replication instance to RDS.
4. THE Landing_Zone documentation SHALL include a migration readiness checklist confirming all prerequisites for MGN and DMS are met.

### Requirement 10: Documentation and Handover

**User Story:** As a project manager, I want clear documentation of the landing zone architecture, access procedures, and operational runbooks, so that AnyCompany can operate the environment independently.

#### Acceptance Criteria

1. A `docs/architecture.md` SHALL include an architecture diagram showing the account structure, VPC layout, and security boundaries.
2. A `docs/access-guide.md` SHALL document how to log in via SSO, switch accounts, and use the defined permission sets.
3. A `docs/runbook.md` SHALL document common operational procedures: checking CloudTrail logs, responding to GuardDuty findings, RDS backup/restore, and EC2 instance management via SSM.
4. A `docs/migration-readiness.md` SHALL include the pre-migration checklist for MGN and DMS setup.
