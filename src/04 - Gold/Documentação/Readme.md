# 📚 Documentação da Camada Gold
<br>
<br>
<div align="center">
<!-- Imagem ilustrativa da tabela (adicione o link abaixo) -->
<img src="https://i.postimg.cc/1t61LYFb/doc.png" alt="Imagem de documentação" width="400"/>
</div>
<br>

## 📋 Visão Geral

Esta pasta contém a **documentação completa** de todas as tabelas da camada Gold do pipeline de dados do Magic: The Gathering. A camada Gold representa o nível mais refinado de dados, contendo análises pré-computadas, métricas executivas e insights de negócio prontos para consumo.

## 🎯 Objetivo

Fornecer documentação executiva e técnica de todas as tabelas Gold, permitindo:
- **Visão geral rápida** das análises e métricas disponíveis
- **Acesso direto** à documentação detalhada de cada tabela
- **Entendimento da arquitetura** de dados da camada Gold
- **Referência técnica** para desenvolvimento, análise e manutenção

## 🃏 Tabelas Documentadas

### 📊 **TB_ANALISE_MERCADO_CARTAS_EXECUTIVO** - Análise Executiva de Mercado
- **Descrição**: Análise executiva do mercado de cartas Magic com métricas de valor, market share e categorização
- **Chave Primária**: `DATA_REF`, `NME_CARD`
- **Particionamento**: `DATA_REF`, `NME_SET`, `NME_CARD_TYPE`, `NME_RARITY`
- **Filtro Temporal**: Baseado em `RELEASE_YEAR` e `RELEASE_MONTH`
- **Schema**: 15+ colunas (métricas executivas)
- **Características**: 
  - Agregações por segmento de mercado
  - Categorização por valor e market share
  - Análise de valorização temporal
  - Rankings de performance

### 📈 **TB_METRICAS_PERFORMANCE_INVESTIMENTOS** - KPIs de Performance
- **Descrição**: Métricas de performance e ROI para análise de investimentos em cartas
- **Chave Primária**: `DATA_REF`, `NME_CARD`
- **Particionamento**: `DATA_REF`, `NME_SET`
- **Filtro Temporal**: Baseado em `RELEASE_YEAR` e `RELEASE_MONTH`
- **Schema**: 12+ colunas (métricas financeiras)
- **Características**:
  - Cálculo de ROI e retornos
  - Análise de risco e volatilidade
  - Métricas de liquidez
  - Indicadores de performance

### 🚨 **TB_REPORT_ALERTAS_EXECUTIVOS** - Alertas Executivos
- **Descrição**: Sistema de alertas para mudanças significativas no mercado de cartas
- **Chave Primária**: `DATA_REF`, `NME_CARD`
- **Particionamento**: `DATA_REF`, `NME_SET`
- **Filtro Temporal**: Baseado em `RELEASE_YEAR` e `RELEASE_MONTH`
- **Schema**: 10+ colunas (alertas e notificações)
- **Características**:
  - Detecção de variações significativas
  - Alertas de oportunidades
  - Notificações de risco
  - Priorização de ações

## 🔄 Categorização das Tabelas

### 📊 **Tabelas de Análise Executiva** (Análises Pré-computadas)
| Tabela | Tipo de Análise | Particionamento | Característica |
|--------|----------------|-----------------|----------------|
| TB_ANALISE_MERCADO_CARTAS_EXECUTIVO | Mercado | DATA_REF, NME_SET, NME_CARD_TYPE, NME_RARITY | Agregações executivas |
| TB_METRICAS_PERFORMANCE_INVESTIMENTOS | Performance | DATA_REF, NME_SET | KPIs financeiros |
| TB_REPORT_ALERTAS_EXECUTIVOS | Alertas | DATA_REF, NME_SET | Sistema de alertas |

## 🎴 **Flavor Text da Documentação**
*"Como um oráculo que transforma dados brutos em visões de lucro, a camada Gold revela os segredos do mercado de cartas, oferecendo insights lapidados para decisões estratégicas e investimentos sagazes."*

## 📈 Estatísticas da Camada Gold

### **Volume de Dados**
- **3 tabelas** documentadas
- **3 tipos de análise** especializados
- **Total estimado**: ~40+ colunas de métricas
- **Granularidade**: Por carta, set, tipo e raridade

### **Padrões de Nomenclatura**
- **NME_**: Nomes e identificadores
- **COD_**: Códigos e chaves
- **VLR_**: Valores monetários
- **DT_**: Datas e timestamps
- **FLG_**: Flags booleanos
- **QTD_**: Quantidades
- **CATEGORIA_**: Categorizações
- **RANK_**: Rankings e posições

### **Estratégias de Particionamento**
- **Análises Executivas**: Particionamento por DATA_REF e dimensões de negócio
- **Métricas de Performance**: Particionamento por DATA_REF e NME_SET
- **Alertas**: Particionamento por DATA_REF e NME_SET

## 🔍 Como Usar Esta Documentação

### **Para Executivos**
1. **Visão Geral**: Comece por este README para entender as análises disponíveis
2. **Métricas Executivas**: Foque em TB_ANALISE_MERCADO_CARTAS_EXECUTIVO
3. **Performance**: Consulte TB_METRICAS_PERFORMANCE_INVESTIMENTOS
4. **Alertas**: Monitore TB_REPORT_ALERTAS_EXECUTIVOS

### **Para Analistas de Dados**
1. **Linhagem de Dados**: Entenda a origem das métricas (Silver)
2. **Particionamento**: Otimize consultas usando partições
3. **Regras de Negócio**: Compreenda cálculos e agregações
4. **Relacionamentos**: Identifique chaves para joins

### **Para Desenvolvedores**
1. **Configuração**: Verifique segredos e configurações necessárias
2. **Monitoramento**: Acompanhe logs e métricas de processamento
3. **Manutenção**: Entenda estratégias de atualização
4. **Modularização**: Use gold_utils para desenvolvimento

## 🛡️ Controle de Qualidade

### **Validações Implementadas**
- ✅ **Schema Padronizado**: Nomenclatura consistente
- ✅ **Particionamento Adequado**: Otimização de performance
- ✅ **Métricas Validadas**: Cálculos verificados
- ✅ **Arredondamento Correto**: 2 casas para valores, 4 para percentuais
- ✅ **Merge Incremental**: Atualização inteligente

### **Monitoramento**
- 📊 **Contagem de Registros**: Antes e depois do processamento
- 🔄 **Taxa de Atualização**: Frequência de mudanças
- ⚡ **Performance**: Tempo de processamento por tabela
- 🎯 **Qualidade**: Validação de integridade dos dados
- 🚨 **Alertas**: Detecção de anomalias

## 🏗️ Arquitetura da Camada Gold

### **Dependências**
- **Fonte**: Tabelas Silver (TB_FATO_SILVER_CARDS, TB_FATO_SILVER_CARDPRICES)
- **Utilitários**: gold_utils.py (módulo compartilhado)
- **Configuração**: Unity Catalog (mtg_dev.gold)

### **Padrões de Implementação**
- **Modularização**: 1 script por tabela
- **Reutilização**: gold_utils para funções comuns
- **Configuração**: Secrets para parâmetros sensíveis
- **Logging**: Mensagens detalhadas de processamento
- **Tratamento de Erros**: Fallbacks e validações

### **Performance**
- **Particionamento**: Otimizado para consultas executivas
- **Window Functions**: Com partições adequadas
- **Arredondamento**: Precisão controlada (2-4 casas decimais)
- **Incremental**: Atualização eficiente de dados 