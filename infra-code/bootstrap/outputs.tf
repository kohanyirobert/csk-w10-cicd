output "ecr_repository_url" {
  description = "service-code repo variable ECR_REPOSITORY_URL, and the image in k8s/deployment.yaml"
  value       = aws_ecr_repository.hello.repository_url
}

output "state_bucket" {
  description = "bucket in infra-code's backend.tf"
  value       = aws_s3_bucket.state.bucket
}

output "role_arn" {
  description = "repo variable AWS_ROLE_ARN in both repos"
  value       = aws_iam_role.gha.arn
}
