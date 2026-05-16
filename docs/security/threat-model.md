# Threat Model — AgenticAI-2-Incident-Response

**Versão:** 1.0.0  
**Data:** 2026-05-16  
**Autor:** Valdomiro Souza  
**Referências:** SDD §5 (SAST/DAST), ADR-2026-0009 (authn), skills/security-by-design/threat-modeling.md  
**Próxima revisão:** 2026-11-16 (a cada major release)

---

## 1. Escopo e Fronteiras

### Ativos em Escopo

| Serviço                       | Porta | Dados sensíveis                                                  |
| ----------------------------- | ----- | ---------------------------------------------------------------- |
| Log-Ingestion-and-Metrics     | :8000 | Logs de aplicação (potencial PII L3), métricas de Golden Signals |
| Incident-Response-Agent (IRA) | :8001 | API key Anthropic, findings de incidentes, prompts LLM           |
| Knowledge-Base                | :8002 | Post-mortems históricos (potencial PII L3 em logs)               |

### Ativos fora de Escopo

- Infraestrutura cloud (provedor de responsabilidade compartilhada)
- Endpoint do usuário final (HOTL — humano decide e executa)
- Sistema de produção monitorado (apenas recebe observabilidade, não é gerenciado pelo sistema)

### Diagrama de Fluxo de Dados (DFD)

```
[SRE / Analista]
       │ HTTPS (UI/API)
       ▼
[Incident-Response-Agent :8001] ──── API Key ────► [Knowledge-Base :8002]
       │                                                    │
       │ HTTP interno (Docker bridge)                       │ Qdrant :6333
       │                                                    ▼
       ▼                                            [Vector DB — post-mortems]
[Log-Ingestion-and-Metrics :8000]
       │
       ▼ Redis :6379
[Golden Signals Store]
       │
       ▼ Prometheus scrape
[Prometheus :9090] ──► [Grafana :3000]
       │
       ▼ Anthropic API (externa)
[Claude claude-sonnet-4-6]
```

**Fronteiras de confiança:**

- `B1`: Internet → IRA (requer API Key via header `X-API-Key`)
- `B2`: IRA → Log-Ingestion (HTTP interno Docker — sem TLS — ver ADR-2026-0013)
- `B3`: IRA → Knowledge-Base (HTTP interno Docker + API Key)
- `B4`: IRA → Anthropic API (HTTPS externo + API Key)
- `B5`: Prometheus → serviços (scrape interno protegido por `PROMETHEUS_API_KEY`)

---

## 2. Análise STRIDE

### 2.1 Spoofing (Falsificação de Identidade)

| ID  | Componente        | Ameaça                                  | Controle implementado                                              | Residual |
| --- | ----------------- | --------------------------------------- | ------------------------------------------------------------------ | -------- |
| S01 | IRA `:8001`       | Atacante forja requisição sem API Key   | `hmac.compare_digest` em `auth.py` (ADR-2026-0009)                 | Baixo    |
| S02 | IRA → Anthropic   | Chave ANTHROPIC_API_KEY exposta/roubada | Key só no env var; `hash_key()` SHA-256 nos logs; TruffleHog no CI | Médio    |
| S03 | IRA → KB          | KB não valida que chamada vem do IRA    | KB valida API Key; rede interna Docker isola acesso externo        | Baixo    |
| S04 | Prometheus scrape | Scraper não autorizado lê métricas      | `PROMETHEUS_API_KEY` obrigatório em staging/prod                   | Baixo    |

### 2.2 Tampering (Adulteração)

| ID  | Componente        | Ameaça                                       | Controle implementado                                                                      | Residual |
| --- | ----------------- | -------------------------------------------- | ------------------------------------------------------------------------------------------ | -------- |
| T01 | Log entries → IRA | Dados de log adulterados para injetar prompt | `_sanitize_finding_text()`: trunca (500 chars), remove tags `<system>/<human>/<assistant>` | Baixo    |
| T02 | Resposta LLM      | Output do Claude adulterado em trânsito      | TLS 1.3 no canal IRA→Anthropic                                                             | Baixo    |
| T03 | KB → Vector DB    | Documento malicioso inserido no Qdrant       | Auth API Key + `score_threshold=0.70` filtra resultados irrelevantes                       | Médio    |
| T04 | Git history       | Commit com secret ou código malicioso        | TruffleHog CI + gitleaks pre-commit + Semgrep SAST                                         | Baixo    |

### 2.3 Repudiation (Repúdio)

| ID  | Componente                | Ameaça                                        | Controle implementado                                                   | Residual |
| --- | ------------------------- | --------------------------------------------- | ----------------------------------------------------------------------- | -------- |
| R01 | IRA — decisões de análise | Sem rastreabilidade de qual análise foi feita | `audit.py`: log JSON de cada análise com timestamp, key hash, resultado | Baixo    |
| R02 | Admin endpoints           | Rotação de chave sem rastreabilidade          | `POST /admin/rotate-key` logado com hash da chave anterior              | Baixo    |
| R03 | LLM calls                 | Sem log de qual prompt/versão foi enviado     | `PROMPT_VERSION` logado em cada análise (prompts.py)                    | Baixo    |

### 2.4 Information Disclosure (Divulgação de Informação)

| ID  | Componente                | Ameaça                                      | Controle implementado                                                                           | Residual |
| --- | ------------------------- | ------------------------------------------- | ----------------------------------------------------------------------------------------------- | -------- |
| I01 | IRA logs                  | API Key logada em plaintext                 | `hash_key()` SHA-256 truncado — nunca chave completa                                            | Baixo    |
| I02 | Sistema prompts           | System prompt exposto via erro ou response  | `PROMPT_CLASSIFICATION = "SENSITIVE"` — nunca exposto em respostas; `enable_docs=False` em prod | Baixo    |
| I03 | Log entries com PII       | PII L1/L2 (CPF, email) em logs de incidente | `PIIAnonymizer` mascara L1-L3 antes de armazenar/logar                                          | Médio    |
| I04 | Stack traces em respostas | Erro expõe detalhes internos                | FastAPI error handlers retornam apenas mensagem genérica                                        | Baixo    |
| I05 | Documentação Swagger      | Expõe schema completo da API                | `enable_docs=False` em produção (model_validator)                                               | Baixo    |
| I06 | Dados enviados ao Claude  | PII em findings enviados ao LLM             | `_sanitize_finding_text()` anonimiza IPs/hostnames; PII não deve constar em métricas            | Médio    |

### 2.5 Denial of Service (Negação de Serviço)

| ID  | Componente    | Ameaça                             | Controle implementado                                                        | Residual |
| --- | ------------- | ---------------------------------- | ---------------------------------------------------------------------------- | -------- |
| D01 | IRA `:8001`   | Flood de requisições `/analyze`    | Rate limiting `slowapi` (10/min por IP)                                      | Baixo    |
| D02 | Anthropic API | Chamadas excessivas esgotam budget | Circuit breaker (3 falhas → OPEN 60s); rate limiting no endpoint             | Baixo    |
| D03 | Redis         | OOM — memória Redis saturada       | Alerta Prometheus `redis_memory_usage > 80%`; `maxmemory-policy` configurado | Baixo    |
| D04 | Log-Ingestion | Payload excessivamente grande      | `RequestSizeLimitMiddleware` bloqueia body > limite                          | Baixo    |
| D05 | Qdrant        | Query de alta cardinalidade        | `score_threshold=0.70` + `limit=5` na busca KB                               | Baixo    |

### 2.6 Elevation of Privilege (Elevação de Privilégio)

| ID  | Componente          | Ameaça                                | Controle implementado                                                    | Residual |
| --- | ------------------- | ------------------------------------- | ------------------------------------------------------------------------ | -------- |
| E01 | Containers          | Processo root dentro do container     | `USER appuser` em todos os Dockerfiles (não-root)                        | Baixo    |
| E02 | Admin endpoints     | Acesso admin com API Key comum        | `ADMIN_KEY` separado da `API_KEY`; endpoints `/admin/*` exigem ADMIN_KEY | Baixo    |
| E03 | Anthropic API scope | LLM executa ação de produção autônoma | Padrão HOTL: LLM só recomenda, humano decide; sem tool use de remediação | Baixo    |
| E04 | Redis               | Acesso arbitrário ao Redis sem senha  | `REDIS_PASSWORD` + rede interna Docker; redis não exposto externamente   | Baixo    |

---

## 3. Análise LINDDUN — Privacy Threats (PII em logs/dados)

| Threat          | Componente                                        | Risco | Controle                                                                         |
| --------------- | ------------------------------------------------- | ----- | -------------------------------------------------------------------------------- |
| Linkability     | Log-Ingestion: logs correlacionáveis por IP       | Médio | `PIIAnonymizer` mascara IPs (L3)                                                 |
| Identifiability | Logs com email/CPF de usuário final               | Alto  | `PIIAnonymizer` mascara L1/L2; revisão manual antes de armazenar post-mortems    |
| Non-repudiation | Audit logs vinculados a identidade                | Baixo | Apenas hash de API Key — sem PII do operador                                     |
| Detectability   | Padrão de acesso revela incidente em curso        | Médio | Métricas agregadas — sem granularidade de usuário individual                     |
| Disclosure      | Dados LLM enviados ao Anthropic                   | Médio | Sanitização pre-LLM; Anthropic DPA deve ser verificado pela organização          |
| Unawareness     | Usuários não sabem que logs são analisados por IA | Médio | HOTL: humano revisa; contexto de SRE interno — sem PII de cliente final previsto |
| Non-compliance  | Retenção de logs sem política definida            | Médio | **DEBT-2026-003** — política de retenção pendente                                |

---

## 4. Riscos Residuais Aceitos

| ID    | Risco                                  | Justificativa                                                                                                                          | Responsável     |
| ----- | -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | --------------- |
| RR-01 | HTTP sem TLS entre microsserviços (B2) | Rede bridge Docker isola tráfego; mTLS requer service mesh (Kubernetes — fora do escopo da dissertação). Ver ADR-2026-0013             | Valdomiro Souza |
| RR-02 | PII L3 (IPs) em métricas Prometheus    | Métricas agregadas por path/status — sem IP individual. IPs só aparecem em logs de request, mascarados pelo PIIAnonymizer              | Valdomiro Souza |
| RR-03 | Sem DPIA formal                        | Sistema de pesquisa/dissertação; sem processamento de PII de clientes reais. DPIA obrigatório antes de qualquer deploy com dados reais | Valdomiro Souza |

---

## 5. Aprovação

| Revisor         | Papel              | Data       | Status                          |
| --------------- | ------------------ | ---------- | ------------------------------- |
| Valdomiro Souza | Engenheiro / Autor | 2026-05-16 | Aprovado                        |
| —               | SecOps             | —          | Pendente (contexto dissertação) |
| —               | DPO                | —          | N/A (sem PII de clientes reais) |
