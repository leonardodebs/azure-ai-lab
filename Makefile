# Makefile — azure-ai-lab
# Carrega variáveis do .env (se existir) para os comandos.
ifneq (,$(wildcard .env))
include .env
export
endif

PY ?= python3
TF ?= terraform
TFDIR ?= terraform
Q ?= Como resolver erro 502 no ALB?

.PHONY: help install check compare rag rag-index safety sk-demo compare-3 report \
        tf-init tf-plan tf-apply tf-destroy test fmt clean

help:  ## Lista os alvos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	 awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n",$$1,$$2}'

install:  ## Instala dependências do requirements.txt
	$(PY) -m pip install -r requirements.txt

# ── Verificação de ambiente ────────────────────────────────────────────────
check:  ## Verifica conexão com o Azure AI Foundry (setup_check.py)
	$(PY) scripts/setup_check.py

# ── Terraform ──────────────────────────────────────────────────────────────
tf-init:  ## terraform init
	cd $(TFDIR) && $(TF) init

tf-plan:  ## terraform plan
	cd $(TFDIR) && $(TF) plan

tf-apply:  ## terraform apply (provisiona a infra no Azure)
	cd $(TFDIR) && $(TF) apply

tf-destroy:  ## terraform destroy (remove tudo — evita gastar créditos)
	cd $(TFDIR) && $(TF) destroy

fmt:  ## terraform fmt + validate
	cd $(TFDIR) && $(TF) fmt && $(TF) validate

# ── Scripts Python ─────────────────────────────────────────────────────────
compare:  ## Compara GPT-4o-mini vs Claude Haiku vs Gemini nos 5 prompts
	$(PY) src/compare_models.py

rag-index:  ## Cria o índice no Azure AI Search e indexa os runbooks (rodar uma vez)
	$(PY) src/azure_rag.py --index

rag:  ## RAG sobre runbooks. Uso: make rag Q="sua pergunta"
	$(PY) src/azure_rag.py "$(Q)"

safety:  ## Analisa 10 textos com Azure Content Safety
	$(PY) src/azure_content_safety.py

sk-demo:  ## Demo do Semantic Kernel (InfraPlugin + RunbookPlugin)
	$(PY) src/semantic_kernel_demo.py

compare-3:  ## RAG comparado nas três nuvens (gera o .md)
	$(PY) src/three_clouds_rag_comparison.py

report: compare compare-3  ## Gera os relatórios de comparação (modelos + 3 nuvens)
	@echo "Relatórios em reports/"

# ── Testes ─────────────────────────────────────────────────────────────────
test:  ## Roda a suíte de testes (pytest) — mocka as APIs Azure, sem chamadas reais
	$(PY) -m pytest

clean:  ## Remove relatórios gerados
	rm -f reports/azure_comparison.json reports/three_clouds_rag_comparison.md
