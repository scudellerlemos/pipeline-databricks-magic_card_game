# 🔄 CI/CD Pipeline - Magic Card Game

Este documento descreve o fluxo completo de CI/CD implementado para o pipeline de dados do Magic: The Gathering.

## 🎯 Objetivo

Implementar um fluxo de CI/CD que:
- ✅ Execute validações durante Pull Requests
- ✅ Faça deploy automático para o Databricks após aprovação da PR
- ✅ Só atue nas condições especificadas

## 🏗️ Arquitetura do Fluxo

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Pull Request  │───▶│   Validações    │───▶│   PR Aprovada   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │  Comentário na  │    │   Deploy Auto   │
                       │      PR         │    │   Databricks    │
                       └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │   Verificação   │
                                              │   do Deploy     │
                                              └─────────────────┘
```

## 📋 Condições de Execução

### Durante Pull Request
- **Triggers**: Mudanças em `src/**`, `.github/DAGs/**`, `.github/workflows/**`, `.github/scripts/**`
- **Ações**: Validações completas do pipeline
- **Resultado**: Comentário na PR com status das validações

### Após Aprovação da PR
- **Triggers**: Push na branch `main` (apenas após merge de PR aprovada)
- **Ações**: Deploy automático no Databricks
- **Resultado**: Pipeline em produção

## 🔧 Componentes do Sistema

### 1. Workflow Principal
**Arquivo**: `.github/workflows/validate-pipeline.yml`

**Jobs**:
- `validate`: Executa durante PR
- `deploy`: Executa após merge na main

### 2. Script de Deploy
**Arquivo**: `.github/scripts/deploy.py`

**Funcionalidades**:
- Validação de conexão com Databricks
- Conversão YAML → JSON
- Criação/atualização de jobs
- Verificação do deploy
- Logging detalhado

### 3. Configuração do Pipeline
**Arquivo**: `.github/DAGs/magic.yml`

**Conteúdo**:
- Definição do job MTG_PIPELINE
- Configuração de tasks e dependências
- Configuração do cluster
- Configuração Git

## ⚙️ Configuração Necessária

### 1. Secrets do GitHub
Configure no repositório:
```
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your-databricks-token
```

### 2. Environment
Crie o environment `Databricks` com:
- Proteção de branch
- Aprovação obrigatória
- Secrets configurados

### 3. Proteção de Branch
Configure a branch `main` com:
- Status checks obrigatórios
- Reviews obrigatórios
- Proteção contra force push

## 🚀 Fluxo Detalhado

### Fase 1: Validações (Durante PR)

1. **Checkout do código**
2. **Setup do ambiente Python**
3. **Instalação de dependências**
4. **Validações**:
   - Sintaxe YAML
   - Estrutura do pipeline
   - Caminhos dos notebooks
   - Configuração do cluster
   - Configuração Git
   - Sintaxe dos notebooks
5. **Geração de relatório**
6. **Comentário na PR**

### Fase 2: Deploy (Após Merge)

1. **Checkout do código**
2. **Setup do ambiente Python**
3. **Configuração do Databricks CLI**
4. **Validação de conexão**
5. **Deploy do pipeline**
6. **Verificação do deploy**
7. **Geração de relatório**

## 📊 Validações Implementadas

### Estruturais
- ✅ Sintaxe YAML válida
- ✅ Estrutura do job correta
- ✅ Dependências entre tasks válidas
- ✅ Campos obrigatórios presentes

### Notebooks
- ✅ Caminhos existem no repositório
- ✅ Sintaxe JSON válida
- ✅ Células de código presentes
- ✅ Estrutura correta

### Configuração
- ✅ Cluster configurado corretamente
- ✅ Git source válido
- ✅ Schedule configurado
- ✅ Permissões adequadas

## 🔍 Monitoramento e Logs

### Durante Validação
- Logs detalhados de cada step
- Comentário automático na PR
- Status checks no GitHub

### Durante Deploy
- Logs com timestamp
- Verificação de conexão
- Confirmação do job criado/atualizado
- Detalhes do job no Databricks

## 🛠️ Troubleshooting

### Problemas Comuns

1. **Notebook não encontrado**
   ```
   ❌ Missing notebooks:
     - src/01 - Ingestion/cards.ipynb
   ```
   **Solução**: Verificar se o arquivo existe e o caminho está correto

2. **Erro de conexão com Databricks**
   ```
   ❌ Erro na conexão com Databricks: Authentication failed
   ```
   **Solução**: Verificar secrets DATABRICKS_HOST e DATABRICKS_TOKEN

3. **Falha no deploy**
   ```
   ❌ Erro no deploy: Job configuration invalid
   ```
   **Solução**: Verificar configuração no magic.yml

### Debug
- Verificar logs do GitHub Actions
- Consultar output de cada step
- Verificar logs do script deploy.py
- Testar conexão manual com Databricks CLI

## 📈 Métricas e Relatórios

### Durante PR
- Status de cada validação
- Total de tasks no pipeline
- Breakdown por tipo de task
- Dependências identificadas

### Após Deploy
- Job ID criado/atualizado
- Status do schedule
- Total de tasks deployadas
- Timestamp do deploy

## 🔒 Segurança

### Proteções Implementadas
- Environment com aprovação obrigatória
- Secrets protegidos
- Validações antes do deploy
- Verificação pós-deploy
- Logs sem informações sensíveis

### Boas Práticas
- Não exposição de tokens nos logs
- Validação de permissões
- Verificação de integridade
- Rollback automático em caso de falha

## 📞 Suporte

Para problemas ou dúvidas:

1. **Verificar logs**: GitHub Actions → Actions → Workflow runs
2. **Consultar documentação**: Este README e `.github/workflows/README.md`
3. **Testar manualmente**: Executar script deploy.py localmente
4. **Contatar equipe**: Data Engineering

## 🔄 Próximos Passos

### Melhorias Futuras
- [ ] Testes unitários para notebooks
- [ ] Validação de dados de entrada
- [ ] Rollback automático
- [ ] Notificações em Slack/Teams
- [ ] Métricas de performance
- [ ] Backup automático de configurações

### Monitoramento
- [ ] Dashboard de status do pipeline
- [ ] Alertas de falha
- [ ] Métricas de execução
- [ ] Relatórios de performance

---

**Última atualização**: $(date '+%Y-%m-%d %H:%M:%S')
**Versão**: 1.0.0
**Responsável**: Data Engineering Team 