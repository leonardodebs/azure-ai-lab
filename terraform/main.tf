# main.tf — Infraestrutura do Azure AI Lab (Azure AI Foundry).
#
# Equivalente AWS (para o leitor vindo do Bedrock):
#   - Cognitive Services (Azure OpenAI)  ~ acesso a modelos do Bedrock
#   - Model deployments                  ~ provisioned throughput do Bedrock
#   - Azure AI Search                    ~ Bedrock Knowledge Bases (OpenSearch)
#   - Storage Account + container        ~ bucket S3 com os documentos-fonte
#   - Key Vault                          ~ AWS Secrets Manager
#
# Tudo em uma única região (var.location, padrão eastus) para caber no free trial.

data "azurerm_client_config" "atual" {}

# Sufixo aleatório para nomes globalmente únicos (Storage Account).
resource "random_string" "sufixo" {
  length  = 6
  special = false
  upper   = false
}

# ── 1. Resource Group ───────────────────────────────────────────────────────
resource "azurerm_resource_group" "lab" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

# ── 2. Azure OpenAI (Cognitive Services, kind=OpenAI, SKU S0) ───────────────
resource "azurerm_cognitive_account" "openai" {
  name                  = var.openai_account_name
  location              = azurerm_resource_group.lab.location
  resource_group_name   = azurerm_resource_group.lab.name
  kind                  = "OpenAI"
  sku_name              = "S0"
  custom_subdomain_name = var.openai_account_name # exigido p/ endpoint .openai.azure.com
  tags                  = var.tags
}

# ── 3. Model deployments dentro do recurso OpenAI ───────────────────────────
# gpt-4o-mini — chat/raciocínio. Capacidade em milhares de TPM (10 = 10K TPM).
resource "azurerm_cognitive_deployment" "gpt4o_mini" {
  name                 = "gpt-4o-mini"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-4o-mini"
    version = "2024-07-18"
  }

  scale {
    type     = "Standard"
    capacity = var.chat_capacity_tpm
  }
}

# text-embedding-ada-002 — embeddings de 1536 dims para o RAG (vetor HNSW).
resource "azurerm_cognitive_deployment" "ada_embedding" {
  name                 = "text-embedding-ada-002"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "text-embedding-ada-002"
    version = "2"
  }

  scale {
    type     = "Standard"
    capacity = var.embed_capacity_tpm
  }
}

# ── 4. Azure AI Search (free tier F1 — 1 índice, 50 MB) ─────────────────────
resource "azurerm_search_service" "busca" {
  name                = var.search_service_name
  resource_group_name = azurerm_resource_group.lab.name
  location            = azurerm_resource_group.lab.location
  sku                 = "free" # F1: 1 índice, 50 MB, sem réplicas/partições
  tags                = var.tags
}

# ── 5. Storage Account + container "runbooks" ───────────────────────────────
resource "azurerm_storage_account" "dados" {
  name                     = "stazurailab${random_string.sufixo.result}"
  resource_group_name      = azurerm_resource_group.lab.name
  location                 = azurerm_resource_group.lab.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
  tags                     = var.tags
}

resource "azurerm_storage_container" "runbooks" {
  name                  = "runbooks"
  storage_account_name  = azurerm_storage_account.dados.name
  container_access_type = "private"
}

# ── 6. Key Vault (guarda as chaves do OpenAI e do Search) ───────────────────
resource "azurerm_key_vault" "cofre" {
  name                       = var.key_vault_name
  location                   = azurerm_resource_group.lab.location
  resource_group_name        = azurerm_resource_group.lab.name
  tenant_id                  = data.azurerm_client_config.atual.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 7
  purge_protection_enabled   = false
  tags                       = var.tags
}

# Permissão para o principal que roda o Terraform gravar segredos.
resource "azurerm_key_vault_access_policy" "terraform" {
  key_vault_id = azurerm_key_vault.cofre.id
  tenant_id    = data.azurerm_client_config.atual.tenant_id
  object_id    = data.azurerm_client_config.atual.object_id

  secret_permissions = ["Get", "List", "Set", "Delete", "Purge"]
}

resource "azurerm_key_vault_secret" "openai_key" {
  name         = "openai-api-key"
  value        = azurerm_cognitive_account.openai.primary_access_key
  key_vault_id = azurerm_key_vault.cofre.id
  depends_on   = [azurerm_key_vault_access_policy.terraform]
}

resource "azurerm_key_vault_secret" "search_key" {
  name         = "search-api-key"
  value        = azurerm_search_service.busca.primary_key
  key_vault_id = azurerm_key_vault.cofre.id
  depends_on   = [azurerm_key_vault_access_policy.terraform]
}
