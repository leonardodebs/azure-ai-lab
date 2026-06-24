# variables.tf — parâmetros do Azure AI Lab.

variable "location" {
  description = "Região do Azure para todos os recursos do laboratório."
  type        = string
  default     = "eastus"
}

variable "resource_group_name" {
  description = "Nome do Resource Group."
  type        = string
  default     = "rg-azure-ai-lab-eastus"
}

variable "openai_account_name" {
  description = "Nome da conta Cognitive Services (Azure OpenAI)."
  type        = string
  default     = "oai-azure-ai-lab"
}

variable "search_service_name" {
  description = "Nome do serviço Azure AI Search."
  type        = string
  default     = "srch-azure-ai-lab"
}

variable "key_vault_name" {
  description = "Nome do Key Vault."
  type        = string
  default     = "kv-azure-ai-lab"
}

variable "chat_capacity_tpm" {
  description = "Capacidade do deployment gpt-4o-mini, em milhares de TPM (10 = 10K)."
  type        = number
  default     = 10
}

variable "embed_capacity_tpm" {
  description = "Capacidade do text-embedding-ada-002, em milhares de TPM (10 = 10K)."
  type        = number
  default     = 10
}

variable "tags" {
  description = "Tags aplicadas a todos os recursos."
  type        = map(string)
  default = {
    projeto    = "azure-ai-lab"
    fase       = "fase3-multicloud"
    ambiente   = "lab"
    gerenciado = "terraform"
  }
}
