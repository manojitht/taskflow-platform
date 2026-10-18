terraform {
  required_version = ">= 1.6"
  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 5.80" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
  # Step 6 exercise: move state to S3 + DynamoDB locking
  # backend "s3" { bucket = "..." key = "taskflow/terraform.tfstate" region = "..." dynamodb_table = "..." }
}

variable "region" { default = "ap-south-1" }
variable "name"   { default = "taskflow" }

provider "aws" { region = var.region }
data "aws_availability_zones" "az" { state = "available" }

locals { azs = slice(data.aws_availability_zones.az.names, 0, 2) }

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.16"

  name            = var.name
  cidr            = "10.0.0.0/16"
  azs             = local.azs
  public_subnets  = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnets = ["10.0.11.0/24", "10.0.12.0/24"]
  database_subnets = ["10.0.21.0/24", "10.0.22.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = true # cost saving for learning; use one per AZ in prod
  enable_dns_hostnames = true
  public_subnet_tags   = { "kubernetes.io/role/elb" = 1 }
  private_subnet_tags  = { "kubernetes.io/role/internal-elb" = 1 }
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.31"

  cluster_name                             = var.name
  cluster_version                          = "1.31"
  vpc_id                                   = module.vpc.vpc_id
  subnet_ids                               = module.vpc.private_subnets
  cluster_endpoint_public_access           = true
  enable_cluster_creator_admin_permissions = true

  eks_managed_node_groups = {
    default = {
      instance_types = ["t3.medium"]
      min_size       = 2
      max_size       = 3
      desired_size   = 2
    }
  }
}

resource "aws_ecr_repository" "app" {
  name                 = var.name
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
}

resource "random_password" "db" {
  length  = 24
  special = false
}

resource "aws_security_group" "db" {
  name_prefix = "${var.name}-db-"
  vpc_id      = module.vpc.vpc_id
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id] # only the cluster nodes can reach Postgres
  }
}

resource "aws_db_subnet_group" "db" {
  name       = var.name
  subnet_ids = module.vpc.database_subnets
}

resource "aws_db_instance" "postgres" {
  identifier              = var.name
  engine                  = "postgres"
  engine_version          = "16"
  instance_class          = "db.t4g.micro"
  allocated_storage       = 20
  db_name                 = "taskflow"
  username                = "taskflow"
  password                = random_password.db.result
  db_subnet_group_name    = aws_db_subnet_group.db.name
  vpc_security_group_ids  = [aws_security_group.db.id]
  storage_encrypted       = true
  backup_retention_period = 7
  skip_final_snapshot     = true # learning only; set false in prod
  publicly_accessible     = false
}

output "ecr_url"      { value = aws_ecr_repository.app.repository_url }
output "cluster_name" { value = module.eks.cluster_name }
output "database_url" {
  value     = "postgresql+psycopg://taskflow:${random_password.db.result}@${aws_db_instance.postgres.address}:5432/taskflow"
  sensitive = true
}
