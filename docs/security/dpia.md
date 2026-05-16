# DPIA — Data Protection Impact Assessment

**Sistema:** AgenticAI-2 Incident Response
**Versão:** 1.0.0
**Data:** 2026-05-16
**Autor:** Valdomiro Souza
**Revisão:** Anual ou antes de mudança significativa no processamento de dados

Referência: LGPD (Lei 13.709/2018), GDPR (Regulamento UE 2016/679),
skills/security-by-design/privacy-by-design.md

---

## 1. Descrição do Sistema e do Processamento

### 1.1 Finalidade
Sistema acadêmico de Incident Response que analisa métricas de infraestrutura (HAProxy logs)
para recomendar ações de resolução de incidentes. Padrão Human-on-the-Loop — o sistema
recomenda, o humano decide.

### 1.2 Controlador
- **Organização:** PPGCA / Unisinos — Dissertação de Mestrado
- **Pesquisador:** Valdomiro Souza (valdomiro.souza@zsms.cloud)

### 1.3 Dados Processados

| Dado | Tipo | Classificação | Origem | Finalidade |
|------|------|---------------|--------|-----------|
| IPs de clientes em logs HAProxy | Dado pessoal (L3 Restrito) | Dado de navegação | Logs de infraestrutura | Cálculo de métricas de latência/erros |
| Paths de requisição | Potencialmente pessoal (L3) | Dado comportamental | Logs HAProxy | Métricas de tráfego |
| Timestamps de acesso | Dado comportamental (L3) | Dado de navegação | Logs HAProxy | Métricas temporais |
| Dados de métricas de infraestrutura | Dado técnico (L4 Público) | Não pessoal | Redis | Análise de incidentes |

**Dados NÃO processados:**
- CPF, nome, email, endereço (dados pessoais identificáveis)
- Dados financeiros ou de saúde
- Dados de menores

---

## 2. Necessidade e Proporcionalidade

### 2.1 Base Legal (LGPD Art. 7)
- **Legítimo interesse** (Art. 7, IX): processamento necessário para garantia de disponibilidade
  e segurança de sistemas de informação. Os IPs são processados exclusivamente para calcular
  métricas de desempenho, não para identificar pessoas.

### 2.2 Minimização de Dados
- Apenas logs necessários para Golden Signals são processados
- Nenhum dado de usuário final é persistido além do necessário para métricas
- Contadores e percentis são calculados; logs brutos não são armazenados de forma permanente

### 2.3 Anonimização / Pseudonimização
**IPs são anonimizados antes de qualquer processamento de log ou envio ao LLM:**

```python
# Log-Ingestion-and-Metrics/app/pii.py
_PATTERNS = [
    (r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "[IP_REDACTED]"),  # IPv4
    (r"\b[0-9a-fA-F:]{3,39}\b", "[IPv6_REDACTED]"),                  # IPv6
    ...
]
```

```python
# Incident-Response-Agent/app/agents/orchestrator.py
# IPs e FQDNs redactados antes de envio ao Claude (LLM02:2025)
result = _RE_IPV4.sub("[IP_REDACTED]", text)
```

---

## 3. Riscos Identificados e Mitigações

| Risco | Probabilidade | Impacto | Mitigação | Risco Residual |
|-------|--------------|---------|-----------|---------------|
| IP de usuário exposto em log estruturado | Médio | Baixo | `pii.py` anonimiza antes de logging | Baixo |
| IP enviado ao Claude (LLM externo) | Baixo | Alto | `_sanitize_finding_text()` redacta IPs/FQDNs antes do prompt | Baixo |
| Logs com PII persistidos no Redis | Baixo | Médio | Redis armazena apenas métricas agregadas, não logs brutos | Muito Baixo |
| Path de requisição com PII (ex: `/users/12345/cpf`) | Baixo | Médio | `pii.py` L2 patterns para CPF; paths agregados sem valores | Baixo |
| Acesso não autorizado à API | Baixo | Médio | HMAC API Key (timing-safe); `model_validator` em produção | Muito Baixo |
| Dados enviados à Anthropic sem DPA | Baixo | Alto | Apenas métricas anonimizadas de infra; sem PII confirmado | Baixo |

---

## 4. Transferência Internacional de Dados

**Anthropic API (Claude Sonnet 4.6):**
- Provedor: Anthropic PBC (EUA)
- Dados transferidos: findings de métricas de infraestrutura (IPs redactados, métricas numéricas)
- Dados pessoais enviados: **Nenhum confirmado** — IPs anonimizados antes do envio
- Base legal para transferência: Art. 33, II LGPD (país com nível adequado de proteção)
- Referência: [Anthropic Privacy Policy](https://www.anthropic.com/legal/privacy)

**Ação pendente:** Formalizar DPA com Anthropic se dados pessoais forem processados em produção.

---

## 5. Direitos dos Titulares (LGPD Art. 17-22)

| Direito | Aplicabilidade | Mecanismo |
|---------|---------------|-----------|
| Acesso | Limitado — dados anonimizados/agregados | Contato: valdomiro.souza@zsms.cloud |
| Correção | N/A — dados de infraestrutura | — |
| Eliminação | Sim — Redis TTL / `FLUSHDB` | Procedimento manual documentado |
| Portabilidade | Limitada — métricas numéricas | Export via `/metrics/*` endpoints |
| Oposição | Sim — opt-out de logs de IP | Configuração de anonimização |

---

## 6. Medidas de Segurança Implementadas

- **Criptografia em trânsito:** TLS 1.3 (via reverse proxy em produção)
- **Autenticação:** HMAC API Key (timing-safe `hmac.compare_digest`)
- **Anonimização:** `pii.py` e `_sanitize_finding_text()` (múltiplas camadas)
- **Controle de acesso:** `enable_docs=False` em produção; sem endpoints públicos além de /health
- **Logs seguros:** API keys apenas como SHA-256 truncado (8 chars); nenhum dado pessoal logado
- **Segurança de containers:** `USER appuser` (non-root) em todos os Dockerfiles
- **SAST/DAST:** bandit, semgrep, OWASP ZAP em CI

---

## 7. Conclusão

**Risco geral:** BAIXO

O sistema processa dados de infraestrutura com mínima exposição a dados pessoais.
Os IPs de clientes são o único dado pessoal relevante e são anonimizados em múltiplas camadas
antes de qualquer processamento, logging ou envio externo.

**Recomendação:** Não é necessário notificação à ANPD para este processamento.
Em caso de ampliação do escopo (ex: inclusão de dados de usuários finais), nova DPIA é obrigatória.

---

## 8. Aprovação

| Papel | Nome | Data | Assinatura |
|-------|------|------|-----------|
| Pesquisador / DPO informal | Valdomiro Souza | 2026-05-16 | Aprovado |
| Orientador (se aplicável) | — | — | Pendente |
