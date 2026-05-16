# ADR-2026-0013 — Modelo de Confiança Inter-Serviço

| Campo             | Valor                                                                                          |
| ----------------- | ---------------------------------------------------------------------------------------------- |
| **ID**            | ADR-2026-0013                                                                                  |
| **Status**        | Accepted                                                                                       |
| **Área**          | Security / Architecture                                                                        |
| **Data**          | 2026-05-16                                                                                     |
| **Autor**         | Valdomiro Souza                                                                                |
| **AI assistance** | Claude Sonnet 4.6 (rascunho); revisado pelo autor                                              |
| **Refs**          | ADR-2026-0009 (API Key auth), ADR-2026-0012 (Docker Compose), docs/security/threat-model.md B2 |

---

## 1. Contexto e Problema

O sistema é composto por três microsserviços FastAPI (Log-Ingestion :8000, IRA :8001, Knowledge-Base :8002) que se comunicam via HTTP dentro de uma rede Docker bridge. A rede interna não usa TLS — todo tráfego é plaintext entre os contêineres.

**Forças em tensão:**

- **Segurança:** A skill `security-by-design` exige mTLS ou TLS 1.3 em toda comunicação inter-serviço.
- **Escopo:** O projeto é uma dissertação de mestrado executada em Docker Compose, sem service mesh (Istio/Linkerd) nem PKI interna.
- **Praticidade:** Implementar mTLS em Docker Compose requer: CA interna, geração e rotação de certificados, configuração de uvicorn com SSL, clientes httpx com verificação de cert — custo operacional alto para ambiente de pesquisa.
- **Compensação existente:** A rede Docker bridge `agentic_network` é privada; nenhuma porta interna é exposta ao host. O IRA autentica chamadas via `API_KEY` para o KB. O log-ingestion não tem autenticação interna (único consumidor é o IRA).

---

## 2. Decisão

**Aceitar HTTP plaintext na comunicação interna Docker em ambiente de desenvolvimento/dissertação, com controles compensatórios explícitos. Em qualquer deployment de produção real, mTLS via service mesh é mandatório.**

**Controles compensatórios implementados:**

| Controle                             | Implementação                                                                                                                                                                           |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Isolamento de rede                   | `agentic_network` bridge — nenhum contêiner interno exposto ao host sem `ports:` explícito                                                                                              |
| Autenticação IRA → KB                | `X-API-Key` validado com `hmac.compare_digest` em `auth.py`                                                                                                                             |
| Sem autenticação IRA → Log-Ingestion | Log-Ingestion aceita chamadas de qualquer cliente na rede interna; compensado por: (a) nenhuma porta 8000 exposta ao host em prod, (b) dados de métricas são somente-leitura para o IRA |
| Segmentação futura                   | Em Kubernetes: NetworkPolicy deny-all + allow apenas IRA → KB e IRA → Log-Ingestion                                                                                                     |

---

## 3. Alternativas Consideradas

| Alternativa                                   | Prós                                     | Contras                                                                                                              | Decisão                                                               |
| --------------------------------------------- | ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| **mTLS com certificados self-signed**         | Criptografia in-transit                  | CA interna, rotação manual, uvicorn SSL config, httpx cert verify — +3-4 dias de eng sem valor acadêmico incremental | Rejeitada (escopo)                                                    |
| **nginx TLS termination**                     | TLS externo ao código Python             | Adiciona componente de infra; mTLS entre nginx e upstream ainda plaintext                                            | Rejeitada (complexidade sem ganho de segurança real no Docker bridge) |
| **Service mesh (Istio)**                      | mTLS automático, zero-config no app      | Requer Kubernetes — incompatível com Docker Compose                                                                  | Rejeitada (fora do escopo)                                            |
| **HTTP plaintext + controles compensatórios** | Simples, viável no escopo da dissertação | Tráfego inter-serviço não cifrado (risco aceitável em rede privada Docker)                                           | **Escolhida**                                                         |

---

## 4. Consequências

**Positivas:**

- Implementação direta sem overhead operacional.
- Foco do projeto mantido em contribuições de pesquisa (MTTD/MTTR, PRAL cycle, LLM para SRE).

**Negativas / Trade-offs:**

- Tráfego inter-serviço não cifrado: um atacante com acesso à rede Docker (e.g., via container comprometido) pode interceptar chamadas.
- Não atende ao requisito da PRR checklist: `mTLS or TLS 1.3 on all inter-service communication`.

**Tabela de risco:**

| Ameaça                              | Probabilidade                            | Impacto                       | Controle compensatório                                 |
| ----------------------------------- | ---------------------------------------- | ----------------------------- | ------------------------------------------------------ |
| Sniffing de tráfego interno         | Baixa (acesso físico ao host necessário) | Médio (dados de métricas SRE) | Rede bridge isolada                                    |
| Container escape → lateral movement | Muito Baixa                              | Alto                          | USER appuser (non-root); sem privilégios Docker extras |

---

## 5. Critérios de Revisão

Esta ADR deve ser revisitada se:

- O sistema for deployado em Kubernetes (mTLS via Istio/Linkerd torna-se viável sem custo adicional).
- O sistema processar dados de PII L1/L2 reais (requisito de mTLS passa a ser mandatório).
- A rede Docker deixar de ser privada (exposição de porta interna ao host).

---

## 6. Referências

- `skills/security-by-design/SKILL.md` — Secure by Default, mTLS requirement
- `docs/security/threat-model.md` — fronteira B2, risco residual RR-01
- `ADR-2026-0009` — autenticação API Key (controle compensatório)
- `ADR-2026-0012` — decisão Docker Compose vs Kubernetes
