# ADR-2026-0009: API Key com hmac.compare_digest para Autenticação

---

## Metadata

| Field            | Value                                                                    |
| ---------------- | ------------------------------------------------------------------------ |
| **ID**           | ADR-2026-0009                                                            |
| **Status**       | Accepted                                                                 |
| **Area**         | Security                                                                 |
| **Author**       | Valdomiro Souza                                                          |
| **Reviewers**    | Orientador PPGCA/Unisinos                                                |
| **Created**      | 2026-05-14                                                               |
| **Approved**     | 2026-05-14                                                               |
| **Related spec** | SDD v1.7.0 §5 (SAST), §7.3.1 (LLM01/A01), §7.3.2 (A05)                   |
| **AI-assisted**  | Yes — Claude Sonnet 4.6, trade-off analysis, reviewed by Valdomiro Souza |

---

## 1. Context and Problem

Os serviços HTTP (IRA :8001, KB :8002, Prometheus endpoint :8000) precisam de autenticação para proteger endpoints de acesso não autorizado. Os requisitos são:

- **Proteção de endpoints sensíveis**: `/analyze` (IRA), `/documents/*` (KB), `/prometheus/metrics` (LI)
- **Sem overhead de sessão**: serviços são stateless — sem necessidade de session tokens ou refresh
- **Timing-safe comparison**: comparação direta de strings (`==`) é vulnerável a timing attacks — mede tempo de execução para inferir prefixo correto da chave
- **Obrigatório em produção e staging**: API_KEY ausente deve bloquear startup (A01/A05)
- **Log seguro**: API key nunca deve aparecer em logs — apenas hash truncado SHA-256 (8 chars)

**Driving forces:**

- `hmac.compare_digest` da stdlib Python garante comparação em tempo constante — previne timing attacks sem dependência extra
- API Key transmitida via `X-API-Key` header — compatível com Schemathesis DAST fuzzing
- Dependência apenas de `hmac` da stdlib — zero overhead de biblioteca externa
- `hash_key()` com SHA-256 truncado (8 chars) permite auditoria de uso sem expor a chave

**Constraints:**

- Sem autenticação OAuth2/OIDC — sem provedor de identidade externo no escopo da dissertação
- API keys armazenadas em variáveis de ambiente (`.env`) — sem secret manager (Vault, AWS Secrets Manager)
- Serviços chamam uns aos outros internamente via Docker network — autenticação interna via mesmo mecanismo

---

## 2. Decision

Adotamos **API Key com `hmac.compare_digest`** como mecanismo de autenticação para todos os endpoints protegidos dos 3 serviços. A chave é transmitida via header `X-API-Key`, comparada em tempo constante, e nunca logada em texto claro.

**Implementação:**

```python
async def require_api_key(key: str | None = Security(api_key_header)) -> None:
    if not settings.api_key:
        return  # development: sem autenticação
    if not key or not hmac.compare_digest(key.encode(), settings.api_key.encode()):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
```

**Scope:**

- Applies to: IRA (:8001) `/analyze`, KB (:8002) `/documents/*`, LI (:8000) `/prometheus/metrics`
- Does not apply to: endpoints públicos (`/health`, `/metrics/slo-status`, `/openapi.json` em dev)

---

## 3. Alternatives Considered

| Alternative                                   | Pros                                                                  | Cons                                                                                                         | Reason for Rejection                                                    |
| --------------------------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| **API Key + hmac.compare_digest (escolhido)** | Timing-safe, stdlib pura, stateless, sem dependência externa, simples | Sem expiração automática; revogação requer restart do serviço; sem auditoria granular por usuário            | — Escolhido; simplicidade + segurança para escopo da dissertação        |
| JWT (Bearer Token)                            | Expiração nativa, payload claims, padrão amplo                        | Requer biblioteca (`python-jose` ou `PyJWT`); verificação de assinatura; sem vantagem para serviço-a-serviço | Overhead desnecessário para comunicação interna entre microsserviços    |
| OAuth2 / OIDC                                 | Padrão industrial, integração com IdP, scopes granulares              | Requer IdP externo (Keycloak, Auth0); complexidade incompatível com equipe de 1 pessoa                       | Dependência de infraestrutura não disponível no ambiente de dissertação |
| mTLS (mutual TLS)                             | Autenticação bidirecional, sem segredo compartilhado                  | Gerenciamento de certificados complexo; sem suporte nativo simples no FastAPI                                | Complexidade operacional desproporcional para escopo local              |
| Autenticação HTTP Basic                       | Simples, suportada por todo cliente HTTP                              | Credenciais em Base64 (não criptografado); sem timing-safe comparison nativo                                 | Menos seguro que API Key + hmac.compare_digest                          |
| "Do nothing" (sem autenticação)               | Zero overhead, máxima simplicidade                                    | Endpoints expostos sem proteção; qualquer acesso à rede Docker pode chamar `/analyze`                        | Inaceitável para dissertação com requisitos de segurança documentados   |

---

## 4. Consequences

### Positive

- `hmac.compare_digest` previne timing attacks — tempo de comparação é constante independente de quantos caracteres coincidem
- `hash_key()` com SHA-256 truncado permite logging de auditoria: `"API key used: abc12345"` sem exposição
- `@model_validator` bloqueia startup em produção/staging sem `API_KEY` — fail-fast em configuração incorreta
- Bandit B105/B106/B107 — sem hardcoded passwords; pip-audit não detecta vulnerabilidade em `hmac` stdlib

### Negative / Trade-offs

- Sem expiração de chave: rotação requer atualização da variável de ambiente + restart do serviço
- Única chave compartilhada entre todos os clientes — sem auditoria granular por serviço chamador
- Em caso de comprometimento, mesma chave protege todos os endpoints do serviço

### Risks

| Risk                                   | Probability | Impact | Mitigation                                                                                 |
| -------------------------------------- | ----------- | ------ | ------------------------------------------------------------------------------------------ |
| API_KEY vaza em logs                   | Baixo       | Alto   | `hash_key()` obrigatório; Semgrep rule detecta logging direto de `api_key`                 |
| Força bruta de API Key                 | Baixo       | Alto   | `hmac.compare_digest` não ajuda aqui — mitigar com rate limiting (não implementado no MVP) |
| Chave comprometida em `.env` commitado | Baixo       | Alto   | TruffleHog CI scan com `--only-verified`; `.env` no `.gitignore`                           |

### Tech Debt Introduced

- Sem rate limiting nos endpoints autenticados — risco de força bruta em produção real (aceitável para dissertação)
- Chave única compartilhada — ideal seria chave por serviço chamador para auditoria granular

---

## 5. Future Review Criteria

Esta ADR deve ser revisitada se:

- [ ] Requisito de auditoria por cliente emergir (considerar JWT com `sub` claim)
- [ ] Sistema for exposto à internet (considerar rate limiting + key rotation automática)
- [ ] Integração com IdP externo for adicionada (considerar OAuth2/OIDC)
- [ ] Após 2 anos sem revisão (2028-05-14)

---

## 6. References

- SDD v1.7.0 §7.3.1 — OWASP LLM01/A01 (Broken Access Control)
- SDD v1.7.0 §7.3.2 — OWASP A05 (Security Misconfiguration)
- `Incident-Response-Agent/app/auth.py` — `require_api_key()`, `hash_key()`
- `Knowledge-Base/app/auth.py` — `require_api_key()`
- `Log-Ingestion-and-Metrics/app/auth.py` — `require_prometheus_key()`
- Python docs: `hmac.compare_digest` — constant-time comparison

---

## 7. AI Assistance

| Field                      | Value                                                                                     |
| -------------------------- | ----------------------------------------------------------------------------------------- |
| **AI used**                | Claude Sonnet 4.6                                                                         |
| **AI role**                | Análise de mecanismos de autenticação, riscos de timing attack, trade-offs JWT vs API Key |
| **Output reviewed by**     | Valdomiro Souza                                                                           |
| **Final decision made by** | Valdomiro Souza                                                                           |

---

## 8. Approval

| Role       | Name            | Date       | Decision   |
| ---------- | --------------- | ---------- | ---------- |
| Author     | Valdomiro Souza | 2026-05-14 | Proposes   |
| Tech Lead  | Valdomiro Souza | 2026-05-14 | ✅ Approve |
| Orientador | PPGCA/Unisinos  | 2026-05-14 | ✅ Approve |
