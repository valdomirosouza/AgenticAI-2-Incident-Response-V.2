# Postmortem Template — [INC-NNN] [Título do Incidente]

> INSTRUÇÃO: Copie este arquivo para `INC-NNN-titulo.md`, preencha todas as seções.
> Postmortems são **blameless** — foco em sistemas, processos e ferramentas, não em pessoas.
> Completar em até 72h após resolução do incidente.

---

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | INC-NNN |
| **Data/Hora início** | YYYY-MM-DDTHH:MM:SSZ |
| **Data/Hora resolução** | YYYY-MM-DDTHH:MM:SSZ |
| **Duração total** | Xh Ymin |
| **Severidade** | SEV-1 / SEV-2 / SEV-3 |
| **Incident Commander** | [nome] |
| **Autor do postmortem** | [nome] |
| **Revisores** | [nomes] |
| **Status** | Draft / Review / Final |
| **Data de publicação** | YYYY-MM-DD |

---

## Resumo Executivo

*2-3 frases descrevendo o incidente, impacto e resolução para leitura rápida pelo Incident Commander.*

Exemplo: "Redis OOM em produção causou degradação total da ingestão de logs por 2h15min.
Detectado via alerta Prometheus; resolvido com flush de chaves expiradas e ajuste de maxmemory.
Nenhum dado perdido; SLO de disponibilidade violado em 0.3%."

---

## Impacto

| Dimensão | Detalhe |
|----------|---------|
| **Usuários afetados** | [N usuários / % da base] |
| **Serviços impactados** | [lista de serviços] |
| **Receita/SLA** | [impacto financeiro ou SLA breach] |
| **SLO breach** | [SLO violado + quanto do error budget consumido] |
| **Dados** | [perda de dados? sim/não] |

---

## Timeline

*Todas as entradas em UTC. Seja preciso — timestamps exatos são fundamentais para a análise.*

| Timestamp (UTC) | Evento |
|-----------------|--------|
| HH:MM:SS | [Primeiro sinal de problema — log, alerta, report de usuário] |
| HH:MM:SS | [Alerta Prometheus disparado / Pagerduty notificado] |
| HH:MM:SS | [On-call assume como Incident Commander] |
| HH:MM:SS | [Canal de incidente criado (#inc-NNN)] |
| HH:MM:SS | [Primeira hipótese levantada] |
| HH:MM:SS | [Diagnóstico correto identificado] |
| HH:MM:SS | [Ação de mitigação iniciada] |
| HH:MM:SS | [Serviço estabilizado / incidente mitigado] |
| HH:MM:SS | [Resolução completa] |
| HH:MM:SS | [All-clear declarado] |

**MTTD (Mean Time to Detect):** Xmin
**MTTI (Mean Time to Investigate):** Xmin
**MTTR (Mean Time to Recover):** Xmin

---

## Análise da Causa Raiz

### O que aconteceu?
*Narrativa técnica detalhada. O que exatamente falhou e como se propagou?*

### Por que aconteceu? (5 Whys)

1. **Por quê** o serviço falhou?
   → [resposta]
2. **Por quê** [resposta 1] aconteceu?
   → [resposta]
3. **Por quê** [resposta 2] aconteceu?
   → [resposta]
4. **Por quê** [resposta 3] aconteceu?
   → [resposta]
5. **Por quê** [resposta 4] aconteceu?
   → **Root Cause:** [causa raiz sistêmica]

### Root Cause vs Trigger

| | Descrição |
|-|-----------|
| **Root Cause** | [Vulnerabilidade sistêmica pré-existente que tornava o sistema frágil] |
| **Trigger** | [Evento ambiental que ativou a vulnerabilidade no momento do incidente] |

---

## O que Foi Bem

*Reconhecer o que funcionou — ajuda a replicar em futuros incidentes. Seja específico.*

- Alerta Prometheus detectou o problema antes de reports de usuários
- [...]
- [...]

---

## O que Poderia Ter Sido Melhor

*Sem culpa — foco em sistemas e processos. O que tornaria a resposta mais rápida ou eficaz?*

- Runbook estava desatualizado — dificultou diagnóstico inicial
- [...]
- [...]

---

## Ações Corretivas

*Cada ação deve ter owner e prazo. Ações sem dono não existem.*

| ID | Ação | Tipo | Owner | Prazo | Status |
|----|------|------|-------|-------|--------|
| ACT-NNN-01 | [Ação preventiva específica] | Preventiva | [nome] | YYYY-MM-DD | Pendente |
| ACT-NNN-02 | [Melhoria de detecção] | Detective | [nome] | YYYY-MM-DD | Pendente |
| ACT-NNN-03 | [Melhoria de runbook] | Corretiva | [nome] | YYYY-MM-DD | Pendente |

**Dívida Técnica gerada:** [DEBT-2026-NNN se aplicável]

---

## Lições Aprendidas

*O que este incidente ensina sobre o sistema, processo ou organização?*

1. [Lição 1]
2. [Lição 2]
3. [Lição 3]

---

## Métricas do Incidente

| Métrica | Valor |
|---------|-------|
| MTTD | Xmin |
| MTTI | Xmin |
| MTTR | Xmin |
| SLO error budget consumido | X% |
| Usuários impactados | N |

---

## Referências

- Runbook utilizado: [link]
- Alerta Prometheus: [nome do alerta]
- Dashboard Grafana: [link]
- Ticket/Issue relacionado: [link]
- ADR relacionado: [se decisão arquitetural for revisada]

---

*Postmortem aprovado por: [Incident Commander] em [data]*
*Publicado em: docs/post-mortems/INC-NNN-titulo.md*
