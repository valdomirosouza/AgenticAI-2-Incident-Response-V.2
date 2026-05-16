# ADR-2026-0012: Docker Compose como Orquestração (não Kubernetes)

---

## Metadata

| Field            | Value                                                                    |
| ---------------- | ------------------------------------------------------------------------ |
| **ID**           | ADR-2026-0012                                                            |
| **Status**       | Accepted                                                                 |
| **Area**         | Infra                                                                    |
| **Author**       | Valdomiro Souza                                                          |
| **Reviewers**    | Orientador PPGCA/Unisinos                                                |
| **Created**      | 2026-05-14                                                               |
| **Approved**     | 2026-05-14                                                               |
| **Related spec** | SDD v1.7.0 §3.4 (Infraestrutura), §8 (Deploy), §9.6 (Stack)              |
| **AI-assisted**  | Yes — Claude Sonnet 4.6, trade-off analysis, reviewed by Valdomiro Souza |

---

## 1. Context and Problem

O sistema precisa de orquestração para subir e conectar 7 componentes simultaneamente (3 serviços FastAPI + Redis + Qdrant + Prometheus + Grafana) em um único ambiente de desenvolvimento e CI. As questões são:

- **Reprodutibilidade**: ambiente deve ser idêntico entre máquina do desenvolvedor, CI (GitHub Actions) e avaliação da banca
- **Networking**: serviços precisam se comunicar por nome (ex: `http://log-ingestion:8000`) sem hardcode de IP
- **Healthchecks e dependências**: KB deve aguardar Qdrant estar pronto; IRA deve aguardar Redis e LI
- **Simplicidade operacional**: equipe de 1 pessoa; comandos devem ser memoráveis

**Driving forces:**

- `docker compose up -d --wait` com um único comando sobe toda a stack e aguarda healthchecks
- Docker Compose é o padrão de facto para desenvolvimento local multi-container
- GitHub Actions tem Docker Compose nativo — sem configuração adicional de CI
- Orquestração Kubernetes seria overhead para corpus de dissertação (~7 containers, 1 réplica cada)

**Constraints:**

- Ambiente de execução: laptop local + GitHub Actions (sem cluster Kubernetes disponível)
- Equipe: 1 desenvolvedor, 4 sprints de ~2 semanas
- Orçamento: zero para infraestrutura cloud

---

## 2. Decision

Adotamos **Docker Compose v2** (plugin `docker compose`) como único orquestrador para desenvolvimento local e CI. Kubernetes não será usado no escopo da dissertação.

**Estrutura do `docker-compose.yml`:**

| Serviço          | Imagem/Build                  | Porta | `depends_on`                      |
| ---------------- | ----------------------------- | ----- | --------------------------------- |
| `redis`          | `redis:7-alpine`              | 6379  | —                                 |
| `qdrant`         | `qdrant/qdrant:v1.18.0`       | 6333  | —                                 |
| `log-ingestion`  | `./Log-Ingestion-and-Metrics` | 8000  | `redis`                           |
| `ira`            | `./Incident-Response-Agent`   | 8001  | `log-ingestion`, `knowledge-base` |
| `knowledge-base` | `./Knowledge-Base`            | 8002  | `qdrant`                          |
| `prometheus`     | `prom/prometheus`             | 9090  | `log-ingestion`                   |
| `grafana`        | `grafana/grafana`             | 3000  | `prometheus`                      |

**Scope:**

- Applies to: todos os componentes do sistema em desenvolvimento local e CI
- Does not apply to: ambiente de avaliação da banca (pode usar `docker compose` ou subir serviços individualmente)

---

## 3. Alternatives Considered

| Alternative                               | Pros                                                                                     | Cons                                                                                          | Reason for Rejection                                                     |
| ----------------------------------------- | ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| **Docker Compose v2 (escolhido)**         | Zero config de CI, networking por nome, healthchecks nativos, 1 comando, padrão de facto | Sem autoscaling, sem rolling deploy, sem service mesh; estado perdido em `down`               | — Escolhido; simplicidade supera limitações para escopo de dissertação   |
| Kubernetes (minikube/kind)                | Padrão de produção, HPA, rolling deploys, probes nativas                                 | Overhead de 3–5 GB RAM para cluster local; curva de aprendizado; sem vantagem para 1 réplica  | Overhead desproporcional para equipe de 1 pessoa e corpus de dissertação |
| Docker Swarm                              | Simples como Compose, suporta múltiplos nós                                              | Sem suporte a Compose v3 completo; deprecated de facto em favor de Kubernetes                 | Declínio de adoção; sem vantagem sobre Compose para 1 nó                 |
| Podman Compose                            | Rootless containers, sem daemon                                                          | Compatibilidade com `docker-compose.yml` parcial; CI GitHub Actions usa Docker nativo         | Compatibilidade incompleta com CI                                        |
| Scripts bash + docker run                 | Zero overhead de ferramenta, controle total                                              | Sem healthcheck automático, sem networking por nome, sem `depends_on`, manutenção exponencial | Inaceitável para 7 serviços com dependências                             |
| "Do nothing" (subir serviços manualmente) | Zero dependência                                                                         | Impossível de reproduzir em CI; cada execução manual é propensa a erro de ordem               | Inaceitável para dissertação com CI obrigatório                          |

---

## 4. Consequences

### Positive

- `docker compose up -d --wait` aguarda todos os healthchecks antes de retornar — sem race conditions entre serviços
- Networking interno via `service_name:port` (ex: `redis:6379`) — sem hardcode de IP no código
- `docker-compose.yml` serve como documentação executável da arquitetura — banca pode subir a stack sem configuração adicional
- CI GitHub Actions: `docker compose -f docker-compose.yml up -d --wait` em 1 linha no workflow

### Negative / Trade-offs

- Sem autoscaling: se ingestão de logs aumentar, IRA não escala automaticamente
- `docker compose down` remove volumes — dados do Qdrant e Redis perdidos (aceitável: dados de desenvolvimento)
- Versão do Compose plugin pode diferir entre máquinas — `docker compose version` deve ser ≥ v2.20.0

### Risks

| Risk                                           | Probability | Impact | Mitigation                                                                    |
| ---------------------------------------------- | ----------- | ------ | ----------------------------------------------------------------------------- |
| Healthcheck Qdrant falha (sem curl na imagem)  | Já ocorreu  | Médio  | Resolvido: `bash -c 'exec 3<>/dev/tcp/localhost/6333'` (documentado ADR-0004) |
| `docker compose up --wait` timeout em CI lento | Baixo       | Médio  | `timeout: 120s` no healthcheck; CI usa `ubuntu-latest` com Docker nativo      |
| Volume de dados corrupto após falha            | Baixo       | Baixo  | `docker compose down -v` limpa volumes; dados reindexados via `seed_kb.py`    |

### Tech Debt Introduced

- `docker-compose.yml` não tem profiles (dev/test/prod) — todos os serviços sobem sempre, incluindo Prometheus e Grafana desnecessários para testes unitários

---

## 5. Future Review Criteria

Esta ADR deve ser revisitada se:

- [ ] Requisito de deploy em cluster emergir (considerar Helm + Kubernetes)
- [ ] CI migrar para plataforma sem Docker nativo (considerar Testcontainers ou similar)
- [ ] Número de serviços ultrapassar 12 (Compose `depends_on` não suporta grafos complexos bem)
- [ ] Após 2 anos sem revisão (2028-05-14)

---

## 6. References

- SDD v1.7.0 §3.4 — Infraestrutura e Orquestração
- SDD v1.7.0 §8 — Deploy e Operações
- `docker-compose.yml` — configuração completa dos 7 serviços
- `.github/workflows/ci.yml` — uso de `docker compose` em CI
- ADR-2026-0004 — healthcheck Qdrant via `bash /dev/tcp`

---

## 7. AI Assistance

| Field                      | Value                                                                     |
| -------------------------- | ------------------------------------------------------------------------- |
| **AI used**                | Claude Sonnet 4.6                                                         |
| **AI role**                | Comparação de orquestradores, análise de trade-offs Compose vs Kubernetes |
| **Output reviewed by**     | Valdomiro Souza                                                           |
| **Final decision made by** | Valdomiro Souza                                                           |

---

## 8. Approval

| Role       | Name            | Date       | Decision   |
| ---------- | --------------- | ---------- | ---------- |
| Author     | Valdomiro Souza | 2026-05-14 | Proposes   |
| Tech Lead  | Valdomiro Souza | 2026-05-14 | ✅ Approve |
| Orientador | PPGCA/Unisinos  | 2026-05-14 | ✅ Approve |
