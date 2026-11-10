# Run ONCE, from your laptop, with your own AWS profile. Creates what the pipelines need before they
# can run: the image registry, the Terraform state bucket, and the IAM role GitHub Actions assumes.
# State stays local (bootstrap/terraform.tfstate): keep it until you destroy, don't commit it.

terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region  = var.region
  profile = var.aws_profile
  default_tags {
    tags = { owner = var.name, workshop = "csk-w10-cicd" }
  }
}

data "aws_caller_identity" "current" {}

data "aws_eks_cluster" "this" {
  name = var.cluster_name
}

# ECR: where service-code's main workflow pushes hello:<version>. IMMUTABLE: forget the version bump
# and the push fails, instead of silently replacing the image that is running.
resource "aws_ecr_repository" "hello" {
  name                 = "${var.name}/hello"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = true
}

# S3: infra-code's Terraform state. Your laptop and the runners must see the same state, so it
# can't stay local. Locking is a lock file next to the state (use_lockfile), no DynamoDB needed.
resource "aws_s3_bucket" "state" {
  bucket        = "${var.name}-infra-code-tfstate-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration {
    status = "Enabled"
  }
}

# OIDC: GitHub signs a token for every workflow run, AWS checks the signature and the token's `sub`
# (which repo, which branch or event) and hands out short-lived credentials. No access keys stored.
# The provider exists once per account and is already there, so we only look it up.
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

data "aws_iam_policy_document" "trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:${var.github_owner}/service-code:ref:refs/heads/main", # push the image
        "repo:${var.github_owner}/infra-code:pull_request",          # plan on a PR
        "repo:${var.github_owner}/infra-code:ref:refs/heads/main",   # plan + apply after merge
      ]
    }
  }
}

resource "aws_iam_role" "gha" {
  name               = "${var.name}-gha"
  assume_role_policy = data.aws_iam_policy_document.trust.json
}

data "aws_iam_policy_document" "gha" {
  statement {
    sid       = "EcrLogin"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }
  statement {
    sid = "EcrPush"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:CompleteLayerUpload",
      "ecr:GetDownloadUrlForLayer",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart",
    ]
    resources = [aws_ecr_repository.hello.arn]
  }
  statement {
    sid       = "TerraformState"
    actions   = ["s3:ListBucket", "s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = [aws_s3_bucket.state.arn, "${aws_s3_bucket.state.arn}/*"]
  }
  statement {
    sid       = "EksToken"
    actions   = ["eks:DescribeCluster"]
    resources = [data.aws_eks_cluster.this.arn]
  }
}

resource "aws_iam_role_policy" "gha" {
  name   = "gha"
  role   = aws_iam_role.gha.id
  policy = data.aws_iam_policy_document.gha.json
}

# IAM gets the role into AWS; this access entry gets it into Kubernetes. Needs the cluster's
# authentication mode to be API or API_AND_CONFIG_MAP.
resource "aws_eks_access_entry" "gha" {
  cluster_name  = var.cluster_name
  principal_arn = aws_iam_role.gha.arn
}

resource "aws_eks_access_policy_association" "gha" {
  cluster_name  = var.cluster_name
  principal_arn = aws_eks_access_entry.gha.principal_arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
  access_scope {
    type = "cluster"
  }
}
