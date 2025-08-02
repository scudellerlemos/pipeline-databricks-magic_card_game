# 🏗️ Data Lake - Magic: The Gathering

<div align="center">

![Jace, the Mind Sculptor](https://repositorio.sbrauble.com/arquivos/in/magic/480738/68250850dd567-7s4u3-8loi0-bd6caeb231d828e67d6e2c1b6abc7239.jpg)

*"Como um mágico negro que busca entender sua própria existência, cada camada do Data Lake é um passo na jornada de transformação, onde dados brutos ganham consciência e se tornam insights de poder inestimável."* - Vivi Ornitier, Final Fantasy IX - Magic The Gathering

</div>

## 📋 Visão Geral do Data Lake

Este repositório contém o **pipeline completo de dados** do Magic: The Gathering, implementado como um Data Lake moderno no Databricks. O pipeline segue a arquitetura **Medallion** com três camadas principais: **Bronze** (dados brutos), **Silver** (dados limpos) e **Gold** (análises executivas).

### 🎯 **Objetivo Principal**

Transformar dados brutos da API do Magic: The Gathering em insights estratégicos e análises executivas, seguindo as melhores práticas de Data Engineering:

- **Extract & Load** (Bronze) - Carregamento de dados brutos
- **Transform & Load** (Silver) - Limpeza e enriquecimento
- **Analyze & Load** (Gold) - Análises executivas e métricas

## 🏛️ Arquitetura do Data Lake

```
┌─────────────────────────────────────────────────────────────┐
│                    🎮 MAGIC: THE GATHERING                  │
│                            DATA LAKE                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   🥉 BRONZE     │    │   🥈 SILVER    │    │   🥇 GOLD       │
│                 │    │                 │    │                 │
│ • Extract       │───▶│ • Transform     │───▶│ • Analyze       │
│ • Load          │    │ • Load          │    │ • Load          │
│ • Raw Data      │    │ • Clean Data    │    │ • Insights      │
│ • Staging       │    │ • Enriched      │    │ • Metrics       │
│ • Delta Lake    │    │ • Delta Lake    │    │ • Delta Lake    │
└─────────────────┘    └─────────────────┘    └─────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    🏛️ UNITY CATALOG                         │
│              magic_the_gathering.{bronze|silver|gold}       │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Estrutura das Camadas

### 🥉 **Camada Bronze** - Dados Brutos
**Localização**: `src/01 - Ingestion/` → `src/02 - Bronze/`

**Processo**: **EL (Extract & Load)**
- **Extract**: Leitura de dados Parquet da staging (S3)
- **Load**: Carregamento incremental no Unity Catalog
- **Dados**: 7 tabelas principais (Cards, Sets, Types, SuperTypes, SubTypes, Formats, CardPrices)

**Características**:
- ✅ Dados brutos preservados
- ✅ Merge incremental por chaves específicas
- ✅ Particionamento temporal
- ✅ Governança via Unity Catalog
- ✅ Histórico completo via Delta Lake

**Tabelas**:
- 🃏 **TB_BRONZE_CARDS** - Cartas com 25+ campos
- 📦 **TB_BRONZE_SETS** - Expansões e coleções
- 🏷️ **TB_BRONZE_TYPES** - Tipos de cartas
- ⭐ **TB_BRONZE_SUPERTYPES** - Supertipos
- 🔖 **TB_BRONZE_SUBTYPES** - Subtipos
- 🎮 **TB_BRONZE_FORMATS** - Formatos de jogo
- 💰 **TB_BRONZE_CARDPRICES** - Preços em tempo real

### 🥈 **Camada Silver** - Dados Limpos
**Localização**: `src/03 - Silver/`

**Processo**: **TL (Transform & Load)**
- **Transform**: Limpeza, padronização e enriquecimento
- **Load**: Carregamento incremental com dados refinados
- **Dados**: 7 tabelas enriquecidas e padronizadas

**Características**:
- ✅ Dados limpos e padronizados
- ✅ Enriquecimento com categorias e métricas
- ✅ Nomenclatura consistente (NME_, COD_, DESC_)
- ✅ Particionamento otimizado
- ✅ Qualidade de dados garantida

**Tabelas**:
- 🃏 **TB_FATO_SILVER_CARDS** - Cartas enriquecidas
- 📦 **TB_REF_SILVER_SETS** - Expansões com metadados
- 🏷️ **TB_REF_SILVER_TYPES** - Tipos padronizados
- ⭐ **TB_REF_SILVER_SUPERTYPES** - Supertipos limpos
- 🔖 **TB_REF_SILVER_SUBTYPES** - Subtipos organizados
- 🎮 **TB_REF_SILVER_FORMATS** - Formatos de jogo
- 💰 **TB_FATO_SILVER_CARDPRICES** - Preços processados

### 🥇 **Camada Gold** - Análises Executivas
**Localização**: `src/04 - Gold/`

**Processo**: **AL (Analyze & Load)**
- **Analyze**: Análises pré-computadas e métricas de negócio
- **Load**: Carregamento incremental de insights estratégicos
- **Dados**: 4 tabelas de análise executiva

**Características**:
- ✅ Análises pré-computadas
- ✅ Métricas de negócio e KPIs
- ✅ Insights estratégicos
- ✅ Categorizações automáticas
- ✅ Prontidão executiva

**Tabelas**:
- 📊 **TB_ANALISE_MERCADO_CARTAS_EXECUTIVO** - Análise executiva de mercado
- 📈 **TB_METRICAS_PERFORMANCE_INVESTIMENTOS** - KPIs de performance
- ⏰ **TB_ANALISE_TEMPORAL** - Padrões temporais
- 🚨 **TB_REPORT_ALERTAS_EXECUTIVOS** - Sistema de alertas

## 🔄 Fluxo de Dados Completo

### **1. Ingestão (01 - Ingestion)**
```python
# Extração da API MTG
api_data = extract_from_mtg_api()
# Salvamento em Parquet na staging
save_to_staging(api_data, "cards.parquet")
```

### **2. Bronze (02 - Bronze)**
```python
# Carregamento da staging
df_staging = spark.read.parquet("s3://bucket/staging/cards.parquet")
# Merge incremental na Bronze
load_to_bronze_unity_merge(df_staging, "TB_BRONZE_CARDS")
```

### **3. Silver (03 - Silver)**
```python
# Transformação e enriquecimento
df_silver = transform_bronze_data(df_bronze)
# Carregamento incremental na Silver
load_to_silver_unity_incremental(df_silver, "TB_FATO_SILVER_CARDS")
```

### **4. Gold (04 - Gold)**
```python
# Análises executivas
df_gold = create_executive_analysis(df_silver)
# Carregamento incremental na Gold
load_to_gold_unity_incremental(df_gold, "TB_ANALISE_MERCADO_CARTAS_EXECUTIVO")
```

## 🛠️ Tecnologias Utilizadas

### **Plataforma Principal**
- **Databricks** - Plataforma unificada de analytics
- **Unity Catalog** - Governança de dados
- **Delta Lake** - Storage layer ACID
- **Apache Spark** - Processamento distribuído

### **Linguagens e APIs**
- **PySpark** - DataFrame API
- **Python** - Scripts de automação
- **SQL** - Consultas e análises

### **Infraestrutura**
- **AWS S3** - Storage de staging
- **Databricks Secrets** - Gerenciamento de credenciais
- **Databricks Clusters** - Computação escalável

## 📊 Métricas e KPIs do Pipeline

### **Performance**
- **Ingestão**: 100 páginas por execução (demonstração)
- **Processamento**: Incremental por chaves específicas
- **Tempo de Execução**: <50 minutos para pipeline completo

### **Qualidade**
- **Bronze**: Preservação de dados originais
- **Silver**: Dados limpos e válidos
- **Gold**: Análises com métricas validadas

## 🎯 Casos de Uso

### **Análises de Mercado**
- Valorização de cartas por set e raridade
- Análise de tendências temporais
- Identificação de oportunidades de investimento

### **Análises de Jogo**
- Performance de cartas por formato
- Análise de metagame e tendências
- Estatísticas de uso e popularidade

### **Análises Executivas**
- KPIs de performance de investimentos
- Alertas de oportunidades e riscos
- Relatórios estratégicos para tomada de decisão

## 🔧 Configuração e Execução

### **Pré-requisitos**
- Databricks Workspace configurado
- Unity Catalog habilitado
- Cluster Spark disponível
- Segredos configurados no scope `mtg-pipeline`

### **Segredos Necessários**
```python
catalog_name           # Nome do catálogo Unity
s3_bucket             # Bucket S3 para staging
s3_bronze_prefix      # Prefixo da camada bronze
s3_silver_prefix      # Prefixo da camada silver
s3_gold_prefix        # Prefixo da camada gold
```

### **Ordem de Execução**
1. **Ingestão**: `src/01 - Ingestion/` (extração da API)
2. **Bronze**: `src/02 - Bronze/` (carregamento de dados brutos)
3. **Silver**: `src/03 - Silver/` (transformação e limpeza)
4. **Gold**: `src/04 - Gold/` (análises executivas)


## 🚀 Próximos Passos

### **Expansão Imediata**
- Implementação de todas as tabelas Silver restantes
- Criação de Data Warehouse completo (Star Schema)
- Análises por formato de jogo (Standard, Modern, Commander)

### **Melhorias Futuras**
- Análises de sentimento de cartas
- Integração com dados de torneios
- Dashboard executivo em tempo real

### **Otimizações**
- Particionamento avançado por múltiplas dimensões
- Cache inteligente para consultas frequentes
- Otimização de queries com Z-Order
- Monitoramento avançado de performance

## 🎴 Flavor Text do Data Lake

*"Como um multiverso de dados que se expande infinitamente, este Data Lake transforma a magia bruta da informação em insights estratégicos de poder inestimável. Cada camada é um plano de existência, cada tabela uma criatura mágica, cada análise um feitiço de poder executivo."*

---

## 📞 Suporte e Contato

Para dúvidas, sugestões ou problemas:
- Verificar documentação específica de cada camada
- Consultar logs de execução no Databricks
- Revisar configurações de segredos e permissões
- Verificar status do Unity Catalog e Delta Lake

**🎮 Que a magia dos dados esteja sempre com você!** 
