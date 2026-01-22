terraform {
  backend "s3" {
    bucket  = "cylynk-infra-dev-state-bucket-1"
    key     = "dev/terraform.tfstate"
    region  = "us-west-2"
    encrypt = true

  }
}