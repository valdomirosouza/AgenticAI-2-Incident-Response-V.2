# ADR-2026-0001: Arquitetura de 3 Microsserviços FastAPI Independentes

---

## Metadata

| Field            | Value                                                                    |
| ---------------- | ------------------------------------------------------------------------ |
| **ID**           | ADR-2026-0001                                                            |
| **Status**       | Accepted                                                                 |
| **Area**         | Architecture                                                             |
| **Author**       | Valdomiro Souza                                                          |
| **Reviewers**    | Orientador PPGCA/Unisinos                                                |
| **Created**      | 2026-05-14                                                               |
| **Approved**     | 2026-05-14                                                               |
| **Supersedes**   | —                                                                        |
| **Related spec** | SDD v1.7.0 §2 (Arquitetura), §3 (Componentes)                            |
| **AI-assisted**  | Yes — Claude Sonnet 4.6, trade-off analysis, reviewed by Valdomiro Souza |

---

## 1. Context and Problem

O sistema Agentic AI Copilot precisa coletar métricas de produção, executar análise de incidentes via LLM e consultar base de conhecimento histórica. Essas três responsabilidades têm ciclos de vida, dependências e requisitos de escalabilidade distintos:

- **Ingestão de logs** é de alta frequência (centenas de eventos/segundo) e deve ser desacoplada da análise
- **Análise via LLM** é latente (~10–60 s) e depende de Anthropic API Key (segredo isolado)
- **Knowledge Base** depende de modelos de embedding pesados (~800 MB) e Qdrant

Colocar tudo em um único serviço criaria acoplamento de deploy, vazamento de credenciais entre contextos e impossibilidade de escalar componentes de forma independente.

**Driving forces:**

- Separação de segredos: `ANTHROPIC_API_KEY` só deve existir no serviço de análise
- Escalabilidade independente: ingestão pode escalar horizontalmente sem arrastar o LLM
- Dissertação requer rastreabilidade clara de responsabilidades por componente (SDD §3)
- Equipe pequena (1 desenvolvedor): serviços devem ser simples e auto-contidos

**Constraints:**

- Orçamento de infraestrutura limitado (ambiente local + GitHub Actions)
- Python 3.12 como linguagem única para todos os serviços
- Tempo de desenvolvimento: 4 sprints (~2 semanas)

---

## 2. Decision

Adotamos arquitetura de **3 microsserviços FastAPI independentes**, cada um com seu próprio `Dockerfile`, `requirements.txt`, suite de testes e porta dedicada:

| Serviço                   | Porta | Responsabilidade                                                            |
| ------------------------- | ----- | --------------------------------------------------------------------------- |
| Log-Ingestion-and-Metrics | :8000 | Receber logs HAProxy, armazenar Golden Signals no Redis, expor métricas     |
| Incident-Response-Agent   | :8001 | Orquestrar 4 agentes especialistas, chamar Claude API, gerar IncidentReport |
| Knowledge-Base            | :8002 | Armazenar e recuperar post-mortems como vetores (Qdrant + embeddings)       |

**Scope:**

- Applies to: todos os componentes do sistema de análise de incidentes
- Does not apply to: infraestrutura de suporte (Redis, Qdrant, Prometheus, Grafana) — tratados como serviços externos

---

## 3. Alternatives Considered

| Alternative                      | Pros                                                                | Cons                                                                                                  | Reason for Rejection                                                                  |
| -------------------------------- | ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| **3 microsserviços (escolhido)** | Isolamento de segredos, deploy independente, responsabilidade única | Overhead de rede, 3 Dockerfiles/test suites para manter                                               | — Escolhido                                                                           |
| Monólito único FastAPI           | Simplicidade, zero latência entre componentes                       | ANTHROPIC_API_KEY exposta a todo o processo; impossível escalar ingestão independentemente            | Viola princípio de menor privilégio                                                   |
| 2 serviços (merge KB + IRA)      | Menos overhead de rede                                              | Modelo de embedding (~800 MB) no mesmo processo do LLM; conflito de dependências (torch vs anthropic) | Conflito de requirements; KB tem `requirements-test.txt` separado exatamente por isso |
| Serverless functions             | Escalabilidade automática                                           | Cold start inaceitável para análise LLM (~60 s); sem estado Redis local                               | Latência incompatível com SLO de análise                                              |

---

## 4. Consequences

### Positive

- `ANTHROPIC_API_KEY` isolada no IRA — LI e KB nunca a veem
- Cada serviço testável e deployável de forma independente (ci.yml cobre os 3 em paralelo)
- Falha em KB não bloqueia análise LLM (degradação graciosa: `similar_incidents=[]`)
- SDD §3 rastreia claramente qual componente implementa qual responsabilidade

### Negative / Trade-offs

- 3 Dockerfiles, 3 `pyproject.toml`, 3 suites de testes para manter em sincronia
- Latência de rede adicional: IRA chama LI (~2 ms) e KB (~5 ms) via HTTP interno
- `docker-compose.yml` cresce em complexidade com healthchecks, depends_on e networking

### Risks

| Risk                                          | Probability | Impact | Mitigation                                         |
| --------------------------------------------- | ----------- | ------ | -------------------------------------------------- |
| LI ou KB indisponíveis durante análise        | Médio       | Médio  | Circuit breaker + fallback rule-based no IRA       |
| Divergência de versões de bibliotecas comuns  | Baixo       | Médio  | Pinning explícito + pip-compile hashes por serviço |
| Overhead de manutenção com equipe de 1 pessoa | Alto        | Baixo  | CLAUDE.md documenta convenções compartilhadas      |

### Tech Debt Introduced

- Nenhum crítico; duplicação de middleware (SecurityHeaders, RequestLogging, RequestSizeLimit) entre os 3 serviços é intencional para isolamento

---

## 5. Future Review Criteria

Esta ADR deve ser revisitada se:

- [ ] Volume de logs ultrapassar 10.000 eventos/segundo (considerar message broker como Kafka)
- [ ] Necessidade de deploy em Kubernetes com autoscaling horizontal (HPA por serviço)
- [ ] Equipe crescer para 3+ engenheiros (considerar monorepo com Nx ou Turborepo)
- [ ] Após 2 anos sem revisão (2028-05-14)

---

## 6. References

- SDD v1.7.0 §2 — Visão Geral da Arquitetura
- SDD v1.7.0 §3 — Componentes e Responsabilidades
- `docker-compose.yml` — orquestração local dos 3 serviços
- `CLAUDE.md` — tabela de serviços, portas e diretórios

---

## 7. AI Assistance

| Field                      | Value                                                               |
| -------------------------- | ------------------------------------------------------------------- |
| **AI used**                | Claude Sonnet 4.6                                                   |
| **AI role**                | Análise de trade-offs, identificação de riscos, revisão do template |
| **Output reviewed by**     | Valdomiro Souza                                                     |
| **Final decision made by** | Valdomiro Souza                                                     |

---

## 8. Approval

| Role       | Name            | Date       | Decision   |
| ---------- | --------------- | ---------- | ---------- |
| Author     | Valdomiro Souza | 2026-05-14 | Proposes   |
| Tech Lead  | Valdomiro Souza | 2026-05-14 | ✅ Approve |
| Orientador | PPGCA/Unisinos  | 2026-05-14 | ✅ Approve |
