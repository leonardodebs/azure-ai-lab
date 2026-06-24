# Investigação de Pico de Custo na Cloud

## Objetivo
Procedimento para investigar e mitigar um aumento inesperado na fatura da cloud,
aplicável a AWS, Azure e GCP.

## 1. Identificando a origem
1. Abra o Cost Explorer (AWS), Cost Management (Azure) ou Billing Reports (GCP).
2. Agrupe os custos por serviço e por tag/projeto no período do pico.
3. Compare com a baseline da semana anterior para isolar o delta.

## 2. Causas comuns de pico
- Recursos órfãos: volumes EBS/discos não anexados, IPs elásticos ociosos
- Auto Scaling disparado por loop de erro (tasks reiniciando sem parar)
- Transferência de dados entre regiões/zonas (egress) não prevista
- Ambiente de teste esquecido ligado (clusters, bancos, GPUs)
- Logs ou métricas em volume excessivo (CloudWatch, Log Analytics)

## 3. Mitigação imediata
1. Pare ou reduza os recursos identificados como causadores.
2. Configure um Budget com alerta (ex: 80% do orçamento mensal).
3. Aplique tags de governança para rastrear donos de cada recurso.
4. Habilite políticas de ciclo de vida em storage (mover para tier frio/expirar).

## 4. Prevenção
Use orçamentos com alertas automáticos, revise recomendações de rightsizing e
adote tags obrigatórias por política para todo recurso provisionado.
