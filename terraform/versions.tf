# versions.tf — versões mínimas do Terraform e dos providers.
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.110"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      # Permite recriar o Key Vault em laboratório sem purga manual.
      purge_soft_delete_on_destroy = true
    }
  }
}
