/* app.js — popula o dashboard estático do azure-ai-lab.
   Lê reports/azure_comparison.json (ao vivo) e usa dados de referência embutidos
   para as seções estáticas (Content Safety, custo, 15 dimensões, 3 nuvens). */

"use strict";

// ---- helpers de DOM -------------------------------------------------------
const el = (tag, cls, html) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html != null) e.innerHTML = html;
  return e;
};
const $ = (id) => document.getElementById(id);

// Barra horizontal proporcional ao valor (val) sobre o máximo (max).
function barra(label, val, max, cor, sufixo = "") {
  const row = el("div", "bar-row");
  row.appendChild(el("div", "label", label));
  const track = el("div", "bar-track");
  const pct = max > 0 ? Math.max(4, (val / max) * 100) : 0;
  const fill = el("div", `bar-fill ${cor}`, val + sufixo);
  fill.style.width = pct + "%";
  track.appendChild(fill);
  row.appendChild(track);
  row.appendChild(el("div", "val", val + sufixo));
  return row;
}

// ---- dados de referência (espelham os scripts Python) ---------------------
const SKILLS = ["Azure OpenAI", "Azure AI Search", "RAG vetorial (HNSW)",
  "Semantic Kernel", "Content Safety", "Terraform azurerm", "Multicloud AI",
  "Python", "GitHub Actions"];

// Custo: 1M in + 1M out (US$). GPT-4o-mini 0,15+0,60=0,75 · Haiku 0,25+1,25=1,50
// · Gemini Flash 0,075+0,30=0,375.
const CUSTO = [
  { label: "Claude 3 Haiku (AWS)", val: 1.5, cor: "aws" },
  { label: "GPT-4o-mini (Azure)", val: 0.75, cor: "azure" },
  { label: "Gemini 1.5 Flash (GCP)", val: 0.375, cor: "gcp" },
];

// Content Safety — severidade ilustrativa (0-6) de 4 textos representativos.
const SAFETY = [
  { label: "Runbook de health check do ALB", val: 0, cor: "azure" },
  { label: "\"Eu odeio quando o pipeline quebra\"", val: 2, cor: "azure" },
  { label: "\"incidente violento derrubou a API\"", val: 2, cor: "azure" },
  { label: "Tutorial de IAM least privilege", val: 0, cor: "azure" },
];

// 15 dimensões: [dimensão, Azure, AWS].
const DIMENSOES = [
  ["Modelos próprios/parceiros", "OpenAI, Llama, Mistral, Phi", "Claude, Llama, Titan, Mistral"],
  ["Modelo carro-chefe", "GPT-4o / 4o-mini", "Claude 3.5 / Haiku"],
  ["RAG gerenciado", "AI Search + on your data", "Bedrock Knowledge Bases"],
  ["Vetor / índice", "Azure AI Search (HNSW)", "OpenSearch Serverless / pgvector"],
  ["Agentes", "Semantic Kernel + Agent Service", "Bedrock Agents"],
  ["Fine-tuning", "GPT-4o-mini, 3.5…", "Titan, custom models"],
  ["Embeddings", "ada-002 / 3-small / 3-large", "Titan v2, Cohere"],
  ["Content safety ⭐", "Serviço dedicado", "Guardrails (acoplado)", true],
  ["Preço LLM rápido (1M in/out)", "$0,15 / $0,60", "$0,25 / $1,25 (Haiku)"],
  ["Free tier", "Trial $200 + AI Search F1", "sem free tier de inferência"],
  ["SDK", "openai (AzureOpenAI), azure-*", "boto3 (bedrock-runtime)"],
  ["IaC / Terraform", "azurerm (maduro)", "aws (bedrock_*) mais novo"],
  ["Identidade / segredos", "Entra ID + Key Vault", "IAM + Secrets Manager"],
  ["Enterprise SLA", "99,9% (Cognitive S0)", "99,9% (Bedrock)"],
  ["Multimodal", "GPT-4o (texto/visão/áudio)", "Claude (texto/visão), Titan Image"],
];

// Três nuvens (arquitetura de RAG): [dimensão, AWS, GCP, Azure].
const TRES = [
  ["Vetor", "OpenSearch / FAISS", "Vertex Vector Search", "Azure AI Search (HNSW)"],
  ["Embeddings", "Titan v2 (1536)", "text-embedding-004 (768)", "ada-002 (1536)"],
  ["LLM", "Claude 3 Haiku", "Gemini 1.5 Flash", "GPT-4o-mini"],
  ["RAG gerenciado", "Bedrock Knowledge Bases", "Vertex RAG Engine", "AI Search + on your data"],
];

// Matriz de recomendação: [cenário, escolha].
const MATRIZ = [
  ["Já é casa AWS, mínimo de código", "AWS Bedrock Knowledge Bases"],
  ["Dados no BigQuery / analytics", "GCP Vertex AI"],
  ["Stack Microsoft + compliance/moderação", "Azure AI Foundry"],
  ["Menor custo por token em chat", "Azure (GPT-4o-mini) ou GCP (Gemini Flash)"],
  ["Portabilidade / evitar lock-in", "Pipeline próprio (FAISS)"],
];

// ---- render ---------------------------------------------------------------
function renderSkills() {
  const c = $("skills");
  SKILLS.forEach((s) => c.appendChild(el("span", null, s)));
}

function renderCusto() {
  const max = Math.max(...CUSTO.map((d) => d.val));
  const c = $("custo-bars");
  CUSTO.forEach((d) => c.appendChild(barra(d.label, d.val, max, d.cor, " US$")));
}

function renderSafety() {
  const c = $("safety-cats");
  SAFETY.forEach((d) => c.appendChild(barra(d.label, d.val, 6, d.cor)));
}

function renderDimensoes() {
  const tbl = el("table");
  tbl.innerHTML =
    "<thead><tr><th>#</th><th>Dimensão</th><th>Azure AI Foundry</th><th>AWS Bedrock</th></tr></thead>";
  const tb = el("tbody");
  DIMENSOES.forEach((d, i) => {
    const tr = el("tr");
    if (d[3]) tr.style.background = "rgba(245,197,24,.08)";
    tr.appendChild(el("td", null, String(i + 1)));
    tr.appendChild(el("td", null, d[0]));
    tr.appendChild(el("td", "azure-col", d[1]));
    tr.appendChild(el("td", "aws-col", d[2]));
    tb.appendChild(tr);
  });
  tbl.appendChild(tb);
  $("tabela-dim").appendChild(tbl);
}

function renderTresNuvens() {
  const tbl = el("table");
  tbl.innerHTML =
    "<thead><tr><th>Dimensão</th><th>AWS</th><th>GCP</th><th>Azure</th></tr></thead>";
  const tb = el("tbody");
  TRES.forEach((d) => {
    const tr = el("tr");
    tr.appendChild(el("td", null, d[0]));
    tr.appendChild(el("td", "aws-col", d[1]));
    tr.appendChild(el("td", "gcp-col", d[2]));
    tr.appendChild(el("td", "azure-col", d[3]));
    tb.appendChild(tr);
  });
  tbl.appendChild(tb);
  $("tabela-3").appendChild(tbl);

  const m = el("table");
  m.innerHTML = "<thead><tr><th>Cenário</th><th>Escolha recomendada</th></tr></thead>";
  const mb = el("tbody");
  MATRIZ.forEach((d) => {
    const tr = el("tr");
    tr.appendChild(el("td", null, d[0]));
    tr.appendChild(el("td", "azure-col", d[1]));
    mb.appendChild(tr);
  });
  m.appendChild(mb);
  $("matriz-3").appendChild(m);
}

// Tabela de modelos: carrega o JSON ao vivo (com fallback amigável).
async function renderModelos() {
  const alvo = $("tabela-modelos");
  try {
    const resp = await fetch("../reports/azure_comparison.json", { cache: "no-store" });
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    const data = await resp.json();

    const algumStub = data.resultados.some((r) =>
      r.modelos.some((m) => m.modo === "stub")
    );
    $("modo-aviso").innerHTML = algumStub
      ? '<span class="tag stub">modo stub</span> — rode <code>make compare</code> ' +
        "com o .env configurado para preencher latência, tokens e custo reais."
      : '<span class="tag real">modo real</span> — métricas obtidas das APIs.';

    const cor = (m) =>
      m.startsWith("gpt") ? "azure-col" : m.startsWith("claude") ? "aws-col" : "gcp-col";

    const tbl = el("table");
    tbl.innerHTML =
      "<thead><tr><th>Prompt</th><th>Modelo</th><th>Modo</th><th>Latência (ms)</th>" +
      "<th>Tokens</th><th>Custo US$</th><th>Qual.</th></tr></thead>";
    const tb = el("tbody");
    data.resultados.forEach((item) => {
      item.modelos.forEach((m) => {
        const tr = el("tr");
        const cel = (v) => el("td", null, v == null ? "—" : v);
        tr.appendChild(el("td", null, item.prompt.slice(0, 44) + "…"));
        tr.appendChild(el("td", cor(m.modelo), m.modelo));
        tr.appendChild(
          Object.assign(el("td"), {
            innerHTML: `<span class="tag ${m.modo}">${m.modo}</span>`,
          })
        );
        tr.appendChild(cel(m.latencia_ms));
        tr.appendChild(cel(m.tokens_total));
        tr.appendChild(cel(m.custo_usd != null ? m.custo_usd.toFixed(6) : null));
        tr.appendChild(cel(m.qualidade));
        tb.appendChild(tr);
      });
    });
    tbl.appendChild(tb);
    alvo.innerHTML = "";
    alvo.appendChild(tbl);
  } catch (e) {
    alvo.innerHTML =
      '<p class="muted" style="padding:16px">Não foi possível carregar ' +
      "<code>reports/azure_comparison.json</code> (" +
      e.message +
      "). Sirva o projeto via <code>python3 -m http.server</code> na raiz " +
      "(o protocolo <code>file://</code> bloqueia o fetch) e rode " +
      "<code>make compare</code> antes.</p>";
    $("modo-aviso").textContent = "";
  }
}

// ---- init -----------------------------------------------------------------
renderSkills();
renderSafety();
renderCusto();
renderDimensoes();
renderTresNuvens();
renderModelos();
