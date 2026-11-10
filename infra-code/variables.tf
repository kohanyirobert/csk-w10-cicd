variable "cluster_name" {
  description = "Your existing EKS cluster."
  type        = string
}

variable "region" {
  type    = string
  default = "eu-central-1"
}
