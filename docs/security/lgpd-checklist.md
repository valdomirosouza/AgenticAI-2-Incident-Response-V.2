# Checklist de Conformidade — LGPD / GDPR / CCPA

**Sistema:** AgenticAI-2 Incident Response
**Data:** 2026-05-16 | **Revisão:** Anual
**Referência:** LGPD Lei 13.709/2018, GDPR 2016/679, skills/security-by-design/privacy-by-design.md

---

## 1. Princípios LGPD (Art. 6)

| Princípio | Status | Implementação |
|-----------|--------|---------------|
| Finalidade | ✅ | Dados de infra usados exclusivamente para análise de incidentes |
| Adequação | ✅ | Apenas métricas necessárias para Golden Signals |
| Necessidade | ✅ | Minimização: IPs não persistidos; apenas métricas agregadas |
| Livre acesso | ⚠️ | Mecanismo manual via email — sem portal self-service |
| Qualidade | ✅ | Métricas calculadas de logs em tempo real |
| Transparência | ✅ | DPIA disponível em docs/security/dpia.md |
| Segurança | ✅ | TLS, HMAC, anonimização, SAST/DAST |
| Prevenção | ✅ | Privacy by design; múltiplas camadas de anonimização |
| Não discriminação | ✅ | Sistema não toma decisões sobre pessoas |
| Responsabilização | ✅ | DPIA documentada; auditoria via logs estruturados |

---

## 2. Base Legal para Processamento (Art. 7)

- [x] Base legal identificada: **Legítimo interesse** (Art. 7, IX) — garantia de disponibilidade
- [x] Base legal documentada na DPIA (docs/security/dpia.md §2.2)
- [ ] Aviso de privacidade publicado *(N/A — sistema interno/acadêmico)*
- [x] Sem processamento de dados sensíveis (Art. 11)

---

## 3. Direitos dos Titulares (Art. 17-22)

| Direito | Implementado | Mecanismo |
|---------|-------------|-----------|
| Confirmação de existência | ✅ | DPIA §5 |
| Acesso | ⚠️ | Manual (email) — sem portal |
| Correção | N/A | Dados de infra, não dados pessoais de titulares |
| Anonimização / bloqueio | ✅ | Processo documentado na DPIA |
| Portabilidade | ⚠️ | Export via API /metrics; sem formato padronizado |
| Eliminação | ✅ | `FLUSHDB` Redis; procedimento documentado |
| Oposição | ✅ | Configurável via env vars de anonimização |
| Revogação de consentimento | N/A | Base = legítimo interesse, não consentimento |

---

## 4. Transferência Internacional

- [x] Transferência para Anthropic API (EUA) identificada
- [x] Dados anonimizados antes da transferência (IPs/hostnames redactados)
- [x] Base legal: Art. 33, II LGPD (nível adequado de proteção)
- [ ] DPA formal com Anthropic *(pendente para produção real)*
- [x] Anthropic Privacy Policy revisada

---

## 5. Medidas Técnicas de Proteção

### 5.1 Anonimização de Dados

- [x] IPs (IPv4/IPv6) anonimizados em `pii.py` (L3 — Log-Ingestion)
- [x] IPs anonimizados em `orchestrator.py` antes de envio ao LLM (L3 — IRA)
- [x] CPF mascarado via regex em `pii.py` (L2 — caso presente em paths)
- [x] Email mascarado via regex em `pii.py` (L2)
- [x] Hostname/FQDN redactado em `orchestrator.py` (L3)

### 5.2 Segurança de Dados

- [x] Criptografia em trânsito: TLS 1.3 (reverse proxy em produção)
- [x] Criptografia em repouso: responsabilidade do provider de cloud
- [x] Controle de acesso: HMAC API Key (timing-safe)
- [x] Logs sem dados pessoais: API keys como SHA-256 truncado
- [x] Containers non-root: `USER appuser` em todos os Dockerfiles
- [x] SAST: bandit + semgrep em CI
- [x] DAST: OWASP ZAP em CI/CD
- [x] Secret detection: gitleaks + detect-secrets (pre-commit + CI)

### 5.3 Retenção de Dados

- [x] Redis: dados efêmeros de sessão; sem TTL explícito obrigatório
- [ ] Política de retenção formal definida por SLA *(pendente — DEBT-2026-008)*
- [x] Logs estruturados: sem PII confirmado; retenção conforme política de logs

---

## 6. Incidentes de Dados Pessoais

**Procedimento em caso de violação de dados (LGPD Art. 48):**

1. Identificar dados expostos e escopo da exposição
2. Conter o incidente (revogar credenciais, isolar serviço)
3. Avaliar se envolve dados pessoais de titulares identificáveis
4. Se sim: notificar ANPD em até 72h (ou conforme regulamentação vigente)
5. Notificar titulares afetados se houver risco relevante
6. Abrir postmortem: `docs/post-mortems/` seguindo template `POSTMORTEM_TEMPLATE.md`

**Contato DPO:** valdomiro.souza@zsms.cloud

---

## 7. Gaps Identificados e Plano de Ação

| Gap | Severidade | Status | Ação |
|-----|-----------|--------|------|
| DPA formal com Anthropic ausente | Médio | Pendente | Formalizar antes de produção com dados reais |
| Mecanismo self-service para direitos dos titulares | Baixo | Backlog | DEBT-2026-008 |
| Política de retenção formal | Baixo | Backlog | DEBT-2026-008 |
| Aviso de privacidade público | N/A | N/A | Sistema acadêmico interno |

---

## Histórico de Revisões

| Versão | Data | Autor | Mudanças |
|--------|------|-------|---------|
| 1.0.0 | 2026-05-16 | Valdomiro Souza | Criação inicial |
