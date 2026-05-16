# ADR-2026-0006: Human-on-the-Loop (HOTL) — Sem Remediação Autônoma

---

## Metadata

| Field            | Value                                                                    |
| ---------------- | ------------------------------------------------------------------------ |
| **ID**           | ADR-2026-0006                                                            |
| **Status**       | Accepted                                                                 |
| **Area**         | Architecture                                                             |
| **Author**       | Valdomiro Souza                                                          |
| **Reviewers**    | Orientador PPGCA/Unisinos                                                |
| **Created**      | 2026-05-14                                                               |
| **Approved**     | 2026-05-14                                                               |
| **Related spec** | SDD v1.7.0 §2.3 (Padrão HOTL), §4 (Ciclo PRAL — fase Act), §7.3          |
| **AI-assisted**  | Yes — Claude Sonnet 4.6, trade-off analysis, reviewed by Valdomiro Souza |

---

## 1. Context and Problem

O sistema analisa incidentes de TI com potencial de impacto crítico em produção. A questão central é: **qual deve ser o nível de autonomia do agente na fase Act do ciclo PRAL?**

Opções no espectro de autonomia:

- **Fully Autonomous**: agente executa remediação diretamente (ex: reiniciar serviços, escalar pods, fazer rollback)
- **Human-on-the-Loop (HOTL)**: agente analisa, gera recomendações e aguarda aprovação humana
- **Human-in-the-Loop (HITL)**: humano aprova cada passo individual da análise
- **Advisory-only**: agente gera relatório estático sem interação

**Driving forces:**

- **Risco de blast radius**: ações automáticas em produção (ex: rollback, escalar instâncias) podem agravar o incidente se baseadas em análise incorreta
- **Contexto organizacional não modelado**: o sistema não conhece janelas de manutenção, deploys em andamento, dependências de negócio — informação que só o engenheiro possui
- **OWASP LLM Top 10 (LLM06:2025 — Excessive Agency)**: conceder ações executáveis a um LLM sem supervisão humana é uma vulnerabilidade de segurança reconhecida
- **Contexto acadêmico**: dissertação pesquisa MTTD/MTTR — a métrica é a velocidade de diagnóstico, não de execução autônoma
- **Responsabilidade e accountability**: em sistemas críticos, a cadeia de responsabilidade deve incluir um humano que aprovou a ação

**Constraints:**

- Sistema opera em ambientes de produção simulados (dissertação) mas com post-mortems de incidentes reais como corpus
- Nenhuma integração com sistemas de orquestração (Kubernetes, Ansible, runbooks executáveis) está planejada

---

## 2. Decision

Adotamos o padrão **Human-on-the-Loop (HOTL)**: o agente executa análise completa e gera `IncidentReport` com diagnóstico e recomendações; **toda ação de remediação é executada exclusivamente pelo engenheiro humano**.

O sistema **nunca irá**:

- Reiniciar serviços, pods ou instâncias
- Executar scripts de remediação ou runbooks automaticamente
- Fazer chamadas a APIs de infraestrutura (AWS, GCP, Kubernetes) com efeito colateral
- Abrir tickets, enviar alertas ou notificações de forma autônoma

**Scope:**

- Applies to: Incident-Response-Agent (:8001), ciclo PRAL fase Act, toda saída de `IncidentReport`
- Does not apply to: coleta de métricas passivas (Log-Ingestion) — sem efeito colateral em infraestrutura

---

## 3. Alternatives Considered

| Alternative                                    | Pros                                                                                         | Cons                                                                                                               | Reason for Rejection                                                                  |
| ---------------------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| **HOTL — sem remediação autônoma (escolhido)** | Seguro por design; sem blast radius de LLM; alinhado com OWASP LLM06; responsabilidade clara | MTTR não reduzido pela execução, apenas pelo diagnóstico; requer engenheiro disponível                             | — Escolhido                                                                           |
| Fully Autonomous                               | MTTR máximo reduzido; sem intervenção humana para casos simples                              | Risco alto de ação incorreta; sem contexto organizacional; viola LLM06:2025; inaceitável para dissertação          | Violação de LLM06:2025 e princípios de segurança de sistemas críticos                 |
| Human-in-the-Loop (HITL)                       | Controle máximo; humano aprova cada ferramenta chamada                                       | Latência extrema; UX degradada; derrota o propósito de copiloto para acelerar diagnóstico                          | Granularidade excessiva; UX inaceitável para contexto de incidente                    |
| Semi-autônomo com aprovação por categoria      | Autonomia para ações "seguras" (ex: apenas leitura) com aprovação para destrutivas           | Complexidade de classificar "seguro vs destrutivo" é alta; qualquer erro de classificação tem consequências graves | Complexidade de implementação e riscos de classificação incorreta inaceitáveis        |
| Advisory-only (relatório estático)             | Zero risco; análise clara e documentada                                                      | Sem interatividade; sem tool use; sem recuperação de contexto similar (RAG); análise superficial                   | Perde as capacidades diferenciadoras do sistema (tool use, RAG, reasoning multi-step) |

---

## 4. Consequences

### Positive

- **LLM06:2025 (Excessive Agency) mitigado por design**: sistema estruturalmente incapaz de executar remediação
- `IncidentReport` contém `recommended_actions` como lista de strings — semântica de recomendação, não de comando
- Fase Act do ciclo PRAL documenta claramente: "Act phase is always executed by the engineer (HOTL)"
- Auditabilidade total: cada análise gera relatório persistente sem efeitos colaterais
- Dissertação mensura impacto de HOTL em MTTD/MTTR via Wheel of Misfortune (§9.13)

### Negative / Trade-offs

- MTTR inclui tempo de decisão e execução humana — métrica não captura o ganho pleno se o engenheiro for lento
- Sem feedback loop automático: engenheiro deve manualmente reportar resultado da ação (fase Learn do PRAL)
- Usuários avançados podem querer automação para casos repetitivos — não suportado por design

### Risks

| Risk                                                        | Probability | Impact | Mitigation                                                                          |
| ----------------------------------------------------------- | ----------- | ------ | ----------------------------------------------------------------------------------- |
| Pressão para adicionar remediação autônoma em versão futura | Médio       | Alto   | Esta ADR documenta a decisão; qualquer mudança requer nova ADR com análise de risco |
| Engenheiro ignora recomendações do copiloto                 | Médio       | Baixo  | Fora do escopo do sistema — problema organizacional, não técnico                    |
| LLM gera recomendação incorreta                             | Médio       | Médio  | HOTL garante revisão humana antes de execução; circuit breaker para fallback        |

### Tech Debt Introduced

- Nenhum — padrão HOTL é a decisão mais simples e segura disponível

---

## 5. Future Review Criteria

Esta ADR deve ser revisitada se:

- [ ] Requisito explícito de remediação autônoma emergir com análise de risco formal (ex: apenas em ambientes de staging isolados)
- [ ] OWASP LLM06:2025 for revisado e o guidance mudar substancialmente
- [ ] Sistema for integrado a plataforma de runbooks com aprovação formal (ex: PagerDuty, OpsGenie) — considerar aprovação com 1 clique
- [ ] Após 2 anos sem revisão (2028-05-14)

---

## 6. References

- SDD v1.7.0 §2.3 — Padrão Human-on-the-Loop
- SDD v1.7.0 §4 — Ciclo PRAL (fase Act: always executed by engineer)
- SDD v1.7.0 §7.3.6 — OWASP LLM06:2025 (Excessive Agency)
- SDD v1.7.0 §9.13 — Wheel of Misfortune (validação do padrão HOTL)
- `Incident-Response-Agent/app/models/` — `IncidentReport.recommended_actions: list[str]`

---

## 7. AI Assistance

| Field                      | Value                                                                      |
| -------------------------- | -------------------------------------------------------------------------- |
| **AI used**                | Claude Sonnet 4.6                                                          |
| **AI role**                | Análise do espectro de autonomia, identificação de riscos OWASP LLM06:2025 |
| **Output reviewed by**     | Valdomiro Souza                                                            |
| **Final decision made by** | Valdomiro Souza                                                            |

---

## 8. Approval

| Role       | Name            | Date       | Decision   |
| ---------- | --------------- | ---------- | ---------- |
| Author     | Valdomiro Souza | 2026-05-14 | Proposes   |
| Tech Lead  | Valdomiro Souza | 2026-05-14 | ✅ Approve |
| Orientador | PPGCA/Unisinos  | 2026-05-14 | ✅ Approve |
