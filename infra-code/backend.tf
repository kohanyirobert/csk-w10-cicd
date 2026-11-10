terraform {
  backend "s3" {
    bucket       = "CHANGE-ME" # bootstrap output: state_bucket
    key          = "infra-code/terraform.tfstate"
    region       = "eu-central-1"
    use_lockfile = true
  }
}
