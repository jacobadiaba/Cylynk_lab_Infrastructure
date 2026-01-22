terraform {
  backend "s3" {
    bucket  = "cylynk-infra-prod-state-bucket"
    key     = "prod/terraform.tfstate"
    region  = "us-east-1"
    encrypt = true
  }
}

