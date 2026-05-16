# Branch Protection Rules — AgenticAI-2 Incident Response

Documentação das regras de proteção de branch conforme `skills/cicd-pipeline/`.

> Estas regras devem ser configuradas manualmente no GitHub:
> Settings → Branches → Add branch protection rule → Branch name pattern: `main`

---

## Branch `main` — Proteção Completa

| Regra | Status | Configuração |
|-------|--------|-------------|
| Require pull request | ✅ Obrigatório | Sem push direto; toda mudança via PR |
| Required approvals | ✅ Obrigatório | Mínimo 1 aprovação de reviewer |
| Dismiss stale reviews | ✅ Obrigatório | Novas mudanças invalidam aprovações anteriores |
| Require status checks | ✅ Obrigatório | CI, SAST, SBOM devem estar verdes |
| Require branches up to date | ✅ Obrigatório | Branch deve estar atualizada com `main` antes do merge |
| No force push | ✅ Obrigatório | `git push --force` bloqueado em `main` |
| No deletions | ✅ Obrigatório | Branch `main` não pode ser deletada |
| Require linear history | ✅ Recomendado | Squash or rebase merge apenas |

---

## Status Checks Obrigatórios

Para que um PR seja mergeável em `main`, todos estes checks devem passar:

```
✅ test-log-ingestion       (CI — pytest Log-Ingestion ≥85% coverage)
✅ test-incident-agent      (CI — pytest IRA ≥85% coverage)
✅ test-knowledge-base      (CI — pytest KB ≥85% coverage)
✅ docker-build             (CI — docker compose build)
✅ sast / sast              (SAST — bandit + semgrep + pip-audit + checkov)
✅ trivy / Trivy FS scan    (SAST — CVEs críticos bloqueantes)
✅ secrets / TruffleHog     (SAST — detecção de secrets no histórico)
✅ sbom / sbom              (SBOM — syft + grype + cosign)
```

---

## Estratégia de Branches

```
main ─────────────────────────────────────── (production — proteção total)
  └── release/YYYY-MM-DD ─────────────────── (staging)
        └── feature/SPEC-NNN-description ─── (desenvolvimento)
        └── fix/SPEC-NNN-description ──────── (bugfix)
        └── hotfix/SPEC-NNN-description ───── (hotfix crítico — merge direto em main)
```

### Convenção de Nomes

| Tipo | Padrão | Exemplo |
|------|--------|---------|
| Feature | `feature/SPEC-NNN-descricao` | `feature/SPEC-2026-005-chaos-testing` |
| Bugfix | `fix/DEBT-NNN-descricao` | `fix/DEBT-2026-001-slo-yaml` |
| Hotfix | `hotfix/INC-NNN-descricao` | `hotfix/INC-004-redis-oom` |
| Release | `release/YYYY-MM-DD` | `release/2026-06-01` |

---

## Change Type por PR

Toda PR deve ter uma label indicando o tipo de mudança (ver `skills/cicd-pipeline/`):

| Label | Tipo | Aprovação | Restrição de deploy |
|-------|------|-----------|---------------------|
| `standard-change` | Standard | Automático se CI verde | Mon-Thu 10:00-17:00 |
| `normal-change` | Normal | RFC aprovado pelo CAB | Sem deploy em freeze |
| `emergency-change` | Emergency | TL + SecOps async | Postmortem obrigatório |

---

## Deploy Freeze

Deploys em `main` são bloqueados nos seguintes períodos:

- Error budget < 10% (bloqueado automaticamente pelo pipeline)
- SEV-1 ativo (bloqueio manual)
- Períodos de freeze declarados no #eng-announcements

---

## Configuração GitHub CLI

```bash
# Configurar branch protection via GitHub CLI (requer permissão de admin)
gh api repos/OWNER/REPO/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["test-log-ingestion","test-incident-agent","test-knowledge-base","docker-build"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
  --field restrictions=null \
  --field allow_force_pushes=false \
  --field allow_deletions=false
```
