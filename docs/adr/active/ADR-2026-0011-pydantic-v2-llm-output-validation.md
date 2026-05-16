# ADR-2026-0011: Pydantic v2 para Validação de Output do LLM

---

## Metadata

| Field            | Value                                                                    |
| ---------------- | ------------------------------------------------------------------------ |
| **ID**           | ADR-2026-0011                                                            |
| **Status**       | Accepted                                                                 |
| **Area**         | Security                                                                 |
| **Author**       | Valdomiro Souza                                                          |
| **Reviewers**    | Orientador PPGCA/Unisinos                                                |
| **Created**      | 2026-05-15                                                               |
| **Approved**     | 2026-05-15                                                               |
| **Related spec** | SDD v1.7.0 §7.3.5 (LLM05:2025), §7.3.3 (LLM04:2025), §5.2 (SAST)         |
| **AI-assisted**  | Yes — Claude Sonnet 4.6, trade-off analysis, reviewed by Valdomiro Souza |

---

## 1. Context and Problem

O output da Anthropic API é texto não estruturado (ou JSON como string). Sem validação, o sistema pode:

- **Propagar hallucination estrutural**: Claude retorna JSON malformado ou com campos faltantes → `KeyError` em runtime
- **Aceitar severity inválida**: `severity: "CATASTROFICO"` em vez de `"low"|"medium"|"high"|"critical"`
- **Expor stack trace ao cliente**: `json.loads()` sem tratamento lança `JSONDecodeError` que pode vazar detalhes internos
- **Violar LLM05:2025 (Improper Output Handling)**: output LLM não sanitizado injetado diretamente na resposta da API

**Driving forces:**

- Pydantic v2 já é dependência obrigatória (FastAPI + ADR-2026-0002) — zero overhead de dependência extra
- `model_validate()` valida estrutura E tipos simultaneamente — uma linha de código protege contra toda classe de erros
- `ValidationError` de Pydantic lança exceção estruturada com campo inválido identificado — debugging eficiente
- OWASP LLM05:2025 recomenda explicitamente validação estrutural de output LLM antes de uso

**Constraints:**

- Output do Claude deve ser JSON parseable — `response_format={"type": "json_object"}` não disponível em todas as versões do SDK
- `OrchestratorResponse` deve ser validada antes de construir `IncidentReport` — dois modelos em cascata
- `SpecialistFinding` retornado por cada agente especialista deve ter `severity: Literal["low", "medium", "high", "critical"]`

---

## 2. Decision

Adotamos **Pydantic v2 `BaseModel` com `model_validate()`** para validação de todo output do LLM antes de uso. Os modelos `OrchestratorResponse` e `SpecialistFinding` definem o schema esperado; qualquer desvio lança `ValidationError` que ativa o fallback.

**Modelos de validação:**

| Modelo                 | Valida                                                                                                         |
| ---------------------- | -------------------------------------------------------------------------------------------------------------- |
| `SpecialistFinding`    | `signal`, `severity: Literal[...]`, `details: str`, `recommendations: list[str]`                               |
| `OrchestratorResponse` | `incident_id`, `severity`, `specialist_findings: list[SpecialistFinding]`, `root_cause`, `recommended_actions` |
| `IncidentReport`       | Construído a partir de `OrchestratorResponse` validado — nenhum campo não validado chega aqui                  |

**Scope:**

- Applies to: Incident-Response-Agent (:8001) — `orchestrator.py`, `models/`
- Does not apply to: input validation (também feita por Pydantic, mas é FastAPI responsability para request parsing)

---

## 3. Alternatives Considered

| Alternative                                  | Pros                                                                                 | Cons                                                                                                       | Reason for Rejection                                |
| -------------------------------------------- | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| **Pydantic v2 model_validate() (escolhido)** | Zero dependência extra, tipagem estática, ValidationError estruturado, Literal types | `model_validate()` pode ser lento para schemas muito aninhados (não é o caso aqui)                         | — Escolhido                                         |
| `json.loads()` + validação manual            | Simples, explícito                                                                   | `KeyError`/`TypeError` em runtime para campos faltantes; sem validação de tipos; sem mensagem de erro útil | Propenso a erros; viola LLM05:2025                  |
| `jsonschema` library                         | Schema JSON padrão, reutilizável fora de Python                                      | Dependência extra; sem tipagem estática; sem coerção automática de tipos                                   | Pydantic já disponível e mais integrado com FastAPI |
| `marshmallow`                                | Serialização bidirecional, maduro                                                    | Dependência extra; sem Literal types nativos; mais verboso que Pydantic v2                                 | Pydantic v2 superior para este caso de uso          |
| Sem validação (trust LLM output)             | Zero overhead                                                                        | Qualquer hallucination estrutural causa 500; viola LLM05:2025 e LLM04:2025; inaceitável                    | Inaceitável em sistema de produção                  |

---

## 4. Consequences

### Positive

- `OrchestratorResponse.model_validate(json.loads(llm_output))` — uma linha valida estrutura completa
- `severity: Literal["low", "medium", "high", "critical"]` — mypy detecta uso incorreto em tempo de análise estática
- `ValidationError` ativa fallback rule-based graciosamente — cliente nunca recebe 500 por hallucination LLM
- `response_model=IncidentReportResponse` no router FastAPI valida também o output final da API — double validation
- Bandit/ruff não reportam issues em código que usa `model_validate` corretamente

### Negative / Trade-offs

- LLM precisa gerar JSON exato que corresponde ao schema — `temperature=0.1` reduz criatividade para aumentar conformidade estrutural
- `model_validate()` lança `ValidationError` mas não tenta reparar JSON parcialmente válido — fallback rule-based ativado mesmo para erros pequenos (ex: campo extra ignorado com `model_config = ConfigDict(extra="ignore")`)
- Schema evolution (adicionar campo obrigatório) quebra validação de outputs cached/antigos

### Risks

| Risk                                            | Probability | Impact | Mitigation                                                               |
| ----------------------------------------------- | ----------- | ------ | ------------------------------------------------------------------------ |
| Claude retorna JSON inválido (não parseable)    | Baixo       | Alto   | `try/except json.JSONDecodeError` antes de `model_validate()` → fallback |
| Claude retorna JSON válido mas schema incorreto | Médio       | Médio  | `model_validate()` captura; fallback ativado; log com `severity=WARNING` |
| Schema change quebra análises em curso          | Baixo       | Médio  | Versioning de schema via `PROMPT_VERSION` em `prompts.py`                |

### Tech Debt Introduced

- `model_config = ConfigDict(extra="ignore")` é necessário para tolerar campos extras do Claude — pode mascarar mudanças no output do modelo que adicionam campos novos

---

## 5. Future Review Criteria

Esta ADR deve ser revisitada se:

- [ ] Anthropic lançar modo `structured_output` nativo (tipo OpenAI) — pode substituir validação manual
- [ ] Pydantic v3 lançado com breaking changes em `model_validate()` API
- [ ] Taxa de `ValidationError` em produção ultrapassar 5% das análises — rever schema ou prompt
- [ ] Após 2 anos sem revisão (2028-05-14)

---

## 6. References

- SDD v1.7.0 §7.3.5 — LLM05:2025 (Improper Output Handling)
- SDD v1.7.0 §7.3.3 — LLM04:2025 (Model DoS via malformed output)
- `Incident-Response-Agent/app/models/` — `OrchestratorResponse`, `SpecialistFinding`, `IncidentReport`
- `Incident-Response-Agent/app/agents/orchestrator.py` — `model_validate()` call site
- Pydantic v2 docs: `model_validate`, `ConfigDict`, `Literal` types

---

## 7. AI Assistance

| Field                      | Value                                                                                |
| -------------------------- | ------------------------------------------------------------------------------------ |
| **AI used**                | Claude Sonnet 4.6                                                                    |
| **AI role**                | Análise de alternativas de validação de output LLM, mapeamento para LLM05/LLM04:2025 |
| **Output reviewed by**     | Valdomiro Souza                                                                      |
| **Final decision made by** | Valdomiro Souza                                                                      |

---

## 8. Approval

| Role       | Name            | Date       | Decision   |
| ---------- | --------------- | ---------- | ---------- |
| Author     | Valdomiro Souza | 2026-05-15 | Proposes   |
| Tech Lead  | Valdomiro Souza | 2026-05-15 | ✅ Approve |
| Orientador | PPGCA/Unisinos  | 2026-05-15 | ✅ Approve |
