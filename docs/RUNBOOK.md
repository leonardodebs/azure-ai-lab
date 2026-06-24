# Runbook Operacional — azure-ai-lab

Procedimentos operacionais e troubleshooting do laboratório. Use junto com o
[README](../README.md) e a [Documentação de Arquitetura](ARQUITETURA.md).

---

## 1. Pré-requisitos

| Ferramenta | Versão mínima | Verificar |
|------------|---------------|-----------|
| Azure CLI | 2.50+ | `az version` |
| Terraform | 1.5+ | `terraform version` |
| Python | 3.12 | `python3 --version` |
| Conta Azure | trial US$200 ativo | `az account show` |

---

## 2. Setup inicial (do zero)

```bash
cd fase3-multicloud/azure-openai

# 1. Ambiente Python isolado
python3 -m venv .venv && source .venv/bin/activate
make install                 # pip install -r requirements.txt

# 2. Autenticar e registrar providers
az login
az account set --subscription "SUA_SUBSCRIPTION_ID"
az provider register --namespace Microsoft.CognitiveServices
az provider register --namespace Microsoft.MachineLearningServices

# 3. Provisionar a infra
make tf-init
make tf-plan                 # revise o plano
make tf-apply                # confirme com "yes"

# 4. Configurar o .env (ver docs/VARIAVEIS-DE-AMBIENTE.md)
cp .env.example .env
# preencha com os outputs do Terraform (passo 3 abaixo)

# 5. Verificar conexão e indexar
make check                   # → "Azure AI Foundry: OK"
make rag-index               # indexa os runbooks (rodar uma vez)
```

---

## 3. Obter os valores do `.env` a partir do Terraform

```bash
cd terraform
terraform output openai_endpoint            # → AZURE_OPENAI_ENDPOINT
terraform output -raw openai_api_key        # → AZURE_OPENAI_API_KEY
terraform output search_endpoint            # → AZURE_SEARCH_ENDPOINT
terraform output -raw search_api_key        # → AZURE_SEARCH_API_KEY
terraform output content_safety_endpoint    # → AZURE_CONTENT_SAFETY_ENDPOINT
terraform output storage_name               # nome da Storage Account
cd ..
```

> `-raw` imprime o valor puro (sem aspas), ideal para colar no `.env`.
> Outputs marcados como `sensitive` só aparecem com `-raw`.

---

## 4. Operações do dia a dia

| Tarefa | Comando |
|--------|---------|
| Verificar ambiente | `make check` |
| Comparar modelos | `make compare` |
| (Re)indexar runbooks | `make rag-index` |
| Perguntar ao RAG | `make rag Q="Como resolver erro 502 no ALB?"` |
| RAG interativo | `python src/azure_rag.py --interactive` |
| Moderação de conteúdo | `make safety` |
| Demo Semantic Kernel | `make sk-demo` |
| Relatório 3 nuvens | `make compare-3` |
| Todos os relatórios | `make report` |
| Testes (sem nuvem) | `make test` |
| Formatar/validar IaC | `make fmt` |

---

## 5. Teste local sem nuvem (grátis)

Valida ~90% do código sem autenticar na Azure:

```bash
make test          # 25 testes (APIs mockadas)
make fmt           # terraform fmt + validate
make compare-3     # gera o .md em modo stub
```

---

## 6. Encerramento (IMPORTANTE)

Para **não consumir os créditos do trial**, destrua a infra ao terminar:

```bash
make tf-destroy    # confirme com "yes"
```

Confirme no portal que `rg-azure-ai-lab-eastus` foi removido.

---

## 7. Troubleshooting

### `make check` falha em "Sessão autenticada"
- **Causa**: `az login` não foi feito ou a sessão expirou.
- **Correção**: `az login && az account set --subscription "SUA_SUBSCRIPTION_ID"`.

### `make check` falha em "Resource Providers"
- **Causa**: providers não registrados (estado `NotRegistered`/`Registering`).
- **Correção**:
  ```bash
  az provider register --namespace Microsoft.CognitiveServices
  az provider register --namespace Microsoft.MachineLearningServices
  # o registro leva alguns minutos; acompanhe:
  az provider show -n Microsoft.CognitiveServices --query registrationState -o tsv
  ```

### `make check` falha em "Conexão AzureOpenAI client"
- **Causas comuns**:
  - `.env` não preenchido ou com `your_key_here` → cole os outputs reais.
  - Deployment `gpt-4o-mini` ainda não criado → `make tf-apply`.
  - `AZURE_OPENAI_ENDPOINT` errado → deve terminar em `.openai.azure.com/`.
  - Versão de API incompatível → use `AZURE_OPENAI_API_VERSION=2024-02-01`.

### `terraform apply` — "DeploymentModelNotAvailable" / cota
- **Causa**: o modelo/versão não está disponível na região ou falta cota de TPM.
- **Correção**: confirme disponibilidade do `gpt-4o-mini` em eastus; reduza
  `chat_capacity_tpm` ou solicite aumento de cota no portal (Quotas → Azure OpenAI).

### `terraform apply` — Key Vault "name already exists / soft-deleted"
- **Causa**: Key Vault com soft-delete de uma execução anterior.
- **Correção**: `az keyvault purge --name kv-azure-ai-lab` e reaplique. (O provider
  está com `purge_soft_delete_on_destroy = true` para mitigar isso.)

### `terraform apply` — Storage Account "name not available"
- **Causa**: o nome global já existe (raro, há sufixo aleatório).
- **Correção**: rode `terraform apply` de novo — o `random_string` gera novo sufixo.

### RAG retorna "Falha ao falar com Azure OpenAI / AI Search"
- **Causa**: índice não criado ou chaves do Search ausentes.
- **Correção**: rode `make rag-index` antes de consultar; confira
  `AZURE_SEARCH_ENDPOINT`/`AZURE_SEARCH_API_KEY` no `.env`.

### RAG indexa mas retorna 0 resultados
- **Causa**: o índice ficou vazio ou o nome do índice no `.env` diverge.
- **Correção**: garanta que `AZURE_SEARCH_INDEX` é o mesmo usado no `--index`;
  rode `make rag-index` novamente.

### `make safety` falha
- **Causa**: `AZURE_CONTENT_SAFETY_ENDPOINT`/chave ausentes.
- **Correção**: use o `content_safety_endpoint` do Terraform; a chave pode ser a
  mesma do recurso Cognitive Services (`AZURE_OPENAI_API_KEY`).

### `make sk-demo` falha em import
- **Causa**: `semantic-kernel` não instalado.
- **Correção**: `pip install semantic-kernel` (ou `make install`).

### `make compare` mostra tudo como "stub"
- **Esperado** quando não há credenciais. Para o modo "real", preencha o `.env`
  (Azure obrigatório; AWS/GCP opcionais e só ativados se houver credenciais).

---

## 8. Escalonamento

Se um erro de provisionamento persistir após as correções acima:
1. Capture a saída completa: `terraform apply 2>&1 | tee /tmp/tf-apply.log`.
2. Verifique o estado dos providers e cotas no portal Azure.
3. Para problemas de modelo/cota, abra um chamado em **Azure Support** (categoria
   Azure OpenAI / Quotas).
