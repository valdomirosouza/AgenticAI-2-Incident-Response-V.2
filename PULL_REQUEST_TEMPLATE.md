## Descrição

<!-- Descreva o que foi implementado e por quê. -->

## Tipo de mudança

- [ ] Nova feature
- [ ] Bug fix
- [ ] Refactor
- [ ] Testes
- [ ] Documentação
- [ ] Infraestrutura / CI

## Checklist de Security Review

### Entradas e Validações
- [ ] Todo input externo é validado por Pydantic antes de ser processado?
- [ ] Campos de texto são truncados antes de serem inseridos em prompts LLM?
- [ ] Novos endpoints têm autenticação e rate limiting?

### Secrets e Configuração
- [ ] Nenhum secret hardcoded (API keys, passwords, tokens)?
- [ ] Novos campos de configuração têm valores padrão seguros para produção?
- [ ] Nenhum dado sensível é logado em nível INFO ou superior?

### Tratamento de Erros
- [ ] Exceções são capturadas e retornam mensagens sem detalhes internos?
- [ ] Novos caminhos de código têm testes de falha (não só happy path)?

### LLM-Específico
- [ ] Dados externos inseridos em prompts são sanitizados?
- [ ] Output do LLM é validado por schema Pydantic antes de uso?
- [ ] Prompts novos ou modificados têm testes de regressão?

## Checklist de Qualidade

- [ ] `pytest --cov` ≥ 85% nos serviços alterados
- [ ] `bandit -ll` sem HIGH ou CRITICAL findings
- [ ] `mypy` sem erros
- [ ] `ruff` e `black` sem issues
- [ ] CUJs afetados passando

## Referências

<!-- Issues, seções do SDD, papers da RSL relacionados. -->
