terraform {
  backend "s3" {
    bucket  = "cylynk-infra-dev-state-bucket"
    key     = "dev/terraform.tfstate"
    region  = "us-east-1"
    encrypt = true

  }
}