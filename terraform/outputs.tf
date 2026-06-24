# outputs.tf — valores usados pelos scripts Python (.env) após o apply.

output "openai_endpoint" {
  description = "Endpoint do Azure OpenAI (AZURE_OPENAI_ENDPOINT)."
  value       = azurerm_cognitive_account.openai.endpoint
}

output "search_endpoint" {
  description = "Endpoint do Azure AI Search (AZURE_SEARCH_ENDPOINT)."
  value       = "https://${azurerm_search_service.busca.name}.search.windows.net"
}

output "storage_name" {
  description = "Nome da Storage Account criada (com sufixo aleatório)."
  value       = azurerm_storage_account.dados.name
}

output "content_safety_endpoint" {
  description = "Endpoint Cognitive Services para Content Safety."
  value       = "https://${azurerm_cognitive_account.openai.custom_subdomain_name}.cognitiveservices.azure.com/"
}

output "key_vault_uri" {
  description = "URI do Key Vault com as chaves armazenadas."
  value       = azurerm_key_vault.cofre.vault_uri
}

# As chaves são sensíveis: leia com `terraform output -raw openai_api_key`.
output "openai_api_key" {
  description = "Chave primária do Azure OpenAI."
  value       = azurerm_cognitive_account.openai.primary_access_key
  sensitive   = true
}

output "search_api_key" {
  description = "Chave de admin do Azure AI Search."
  value       = azurerm_search_service.busca.primary_key
  sensitive   = true
}
