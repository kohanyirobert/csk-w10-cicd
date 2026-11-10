variable "name" {
  description = "Your short name, lowercase, e.g. robi. Prefixes everything this creates."
  type        = string
}

variable "github_owner" {
  description = "Your GitHub user name: the owner of the service-code and infra-code repos."
  type        = string
}

variable "cluster_name" {
  description = "Your existing EKS cluster."
  type        = string
}

variable "aws_profile" {
  description = "Your AWS CLI profile."
  type        = string
  default     = "default"
}

variable "region" {
  type    = string
  default = "eu-central-1"
}
