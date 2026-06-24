# Exemplos de Variáveis de Ambiente — azure-ai-lab

Template e referência para configurar o arquivo `.env` (e os `.tfvars` do
Terraform). O `.env` real **nunca é versionado** (bloqueado pelo `.gitignore`);
use o `.env.example` na raiz como ponto de partida.

```bash
cp .env.example .env   # depois preencha com os outputs do Terraform
```

---

## 1. Azure OpenAI (obrigatório)

| Variável | Exemplo | Origem | Obrigatória |
|----------|---------|--------|-------------|
| `AZURE_OPENAI_ENDPOINT` | `https://oai-azure-ai-lab.openai.azure.com/` | `terraform output openai_endpoint` | ✅ |
| `AZURE_OPENAI_API_KEY` | `a1b2c3...` (32+ chars) | `terraform output -raw openai_api_key` | ✅ |
| `AZURE_OPENAI_API_VERSION` | `2024-02-01` | fixa (compatível com os scripts) | ✅ |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | `gpt-4o-mini` | nome do deployment (Terraform) | ✅ |
| `AZURE_OPENAI_EMBED_DEPLOYMENT` | `text-embedding-ada-002` | nome do deployment (Terraform) | ✅ |

> O endpoint **deve terminar em `.openai.azure.com/`** (vem do
> `custom_subdomain_name`). Use a versão de API `2024-02-01`.

---

## 2. Azure AI Search (obrigatório para o RAG)

| Variável | Exemplo | Origem | Obrigatória |
|----------|---------|--------|-------------|
| `AZURE_SEARCH_ENDPOINT` | `https://srch-azure-ai-lab.search.windows.net` | `terraform output search_endpoint` | ✅ (RAG) |
| `AZURE_SEARCH_API_KEY` | `XYZ...` (chave admin) | `terraform output -raw search_api_key` | ✅ (RAG) |
| `AZURE_SEARCH_INDEX` | `runbooks-index` | escolha sua (default do script) | ✅ (RAG) |

> A `AZURE_SEARCH_INDEX` precisa ser **a mesma** na indexação (`--index`) e na
> consulta. O default no código é `runbooks-index`.

---

## 3. Azure AI Content Safety (obrigatório para `make safety`)

| Variável | Exemplo | Origem | Obrigatória |
|----------|---------|--------|-------------|
| `AZURE_CONTENT_SAFETY_ENDPOINT` | `https://oai-azure-ai-lab.cognitiveservices.azure.com/` | `terraform output content_safety_endpoint` | ✅ (safety) |
| `AZURE_CONTENT_SAFETY_API_KEY` | `a1b2c3...` | mesma chave do Cognitive Services | ⚠️ (cai para `AZURE_OPENAI_API_KEY`) |

> O endpoint de Content Safety usa o domínio `*.cognitiveservices.azure.com/`
> (diferente do `*.openai.azure.com/`). Se a chave dedicada não for informada, o
> script reaproveita `AZURE_OPENAI_API_KEY`.

---

## 4. Comparação multicloud (opcional)

Só são chamados se as credenciais existirem; ausência → modo stub.

| Variável | Exemplo | Usado por |
|----------|---------|-----------|
| `AWS_ACCESS_KEY_ID` | `AKIA...` | `compare_models.py` (Claude Haiku via Bedrock) |
| `AWS_SECRET_ACCESS_KEY` | `wJalr...` | idem |
| `AWS_DEFAULT_REGION` | `us-east-1` | idem |
| `GOOGLE_CLOUD_PROJECT` | `meu-projeto-gcp` | `compare_models.py` (Gemini via Vertex) |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` | idem |

---

## 5. Template completo do `.env`

```bash
# ── Azure OpenAI ──────────────────────────────────────────────────────────
AZURE_OPENAI_ENDPOINT=https://oai-azure-ai-lab.openai.azure.com/
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_EMBED_DEPLOYMENT=text-embedding-ada-002

# ── Azure AI Search ───────────────────────────────────────────────────────
AZURE_SEARCH_ENDPOINT=https://srch-azure-ai-lab.search.windows.net
AZURE_SEARCH_API_KEY=your_key_here
AZURE_SEARCH_INDEX=runbooks-index

# ── Azure AI Content Safety ───────────────────────────────────────────────
AZURE_CONTENT_SAFETY_ENDPOINT=https://oai-azure-ai-lab.cognitiveservices.azure.com/
AZURE_CONTENT_SAFETY_API_KEY=your_key_here

# ── Comparação multicloud (opcional) ──────────────────────────────────────
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_key_here
AWS_DEFAULT_REGION=us-east-1
GOOGLE_CLOUD_PROJECT=your_project
GOOGLE_CLOUD_LOCATION=us-central1
```

---

## 6. Variáveis do Terraform (`terraform.tfvars`)

Opcional — todas têm default. Copie de `terraform/terraform.tfvars.example`.
O `terraform.tfvars` real é ignorado pelo `.gitignore`.

| Variável | Default | Descrição |
|----------|---------|-----------|
| `location` | `eastus` | Região de todos os recursos |
| `resource_group_name` | `rg-azure-ai-lab-eastus` | Nome do Resource Group |
| `openai_account_name` | `oai-azure-ai-lab` | Conta Cognitive Services (OpenAI) |
| `search_service_name` | `srch-azure-ai-lab` | Serviço Azure AI Search |
| `key_vault_name` | `kv-azure-ai-lab` | Key Vault |
| `chat_capacity_tpm` | `10` | Capacidade do gpt-4o-mini (milhares de TPM → 10K) |
| `embed_capacity_tpm` | `10` | Capacidade do ada-002 (milhares de TPM → 10K) |

```hcl
# terraform/terraform.tfvars
location            = "eastus"
chat_capacity_tpm   = 10
embed_capacity_tpm  = 10
```

---

## 7. Boas práticas de segurança

- **Nunca commitar** `.env`, `*.tfvars` (exceto `*.example`) ou `*.tfstate` — já
  bloqueados pelo `.gitignore`.
- Em **produção**, ler segredos do **Key Vault via Managed Identity**, não de
  arquivos `.env`.
- **Rotacionar** as chaves do OpenAI e do Search periodicamente (portal → Keys).
- Usar a **chave secundária** durante a rotação para não derrubar o serviço.
- Restringir o acesso ao recurso por **rede/Private Endpoint** quando aplicável.
