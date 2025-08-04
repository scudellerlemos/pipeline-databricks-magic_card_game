# 🃏 Pipeline de Dados - Magic: The Gathering

<div align="center">

![Magic: The Gathering](https://static.wikia.nocookie.net/finalfantasy/images/9/9e/FFAB_Thundara_-_Vivi_SR.png)

> **Pipeline completo de dados para análise de mercado de cartas Magic: The Gathering**

</div>

[![CI/CD Pipeline](https://github.com/scudellerlemos/pipeline-databricks-magic_card_game/actions/workflows/validate-pipeline.yml/badge.svg)](https://github.com/scudellerlemos/pipeline-databricks-magic_card_game/actions/workflows/validate-pipeline.yml)
[![Databricks](https://img.shields.io/badge/Databricks-FF3621?style=flat&logo=databricks&logoColor=white)](https://databricks.com/)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Apache Spark](https://img.shields.io/badge/Apache%20Spark-E25A1C?style=flat&logo=apachespark&logoColor=white)](https://spark.apache.org/)

## 📋 **Visão Geral**

Este projeto implementa um **pipeline completo de dados** para análise de mercado de cartas Magic: The Gathering, utilizando múltiplas APIs especializadas e processando dados através de um pipeline ETL moderno no Databricks.

### 🎯 **Objetivos**

- 📊 **Análise de Mercado**: Monitoramento de preços e tendências
- 📈 **Métricas de Investimento**: Performance e ROI de cartas
- 🎮 **Insights Estratégicos**: Dados para decisões de negócio
- ⚡ **Automação Completa**: Pipeline CI/CD com deploy automático

## 🏗️ **Arquitetura**

<div align="center">

*Arquitetura do Pipeline ETL - Magic: The Gathering*

</div>

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MTG API       │    │                 │    │                 │
│   + Scryfall    │───▶│  Databricks     │───▶│  Analytics      │
│   (Extract)     │    │  (Transform)    │    │  (Load)         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Bronze Layer  │    │   Silver Layer  │    │   Gold Layer    │
│   (Raw Data)    │    │   (Cleaned)     │    │   (Analytics)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📁 **Estrutura do Projeto**

```
pipeline-databricks-magic_card_game/
├── 📁 src/
│   ├── 📁 01 - Ingestion/          # 🚀 Ingestão de dados da API
│   │   ├── cards.ipynb             # Cartas
│   │   ├── sets.ipynb              # Sets/Expansões
│   │   ├── formats.ipynb           # Formatos de jogo
│   │   ├── types.ipynb             # Tipos de carta
│   │   ├── subtypes.ipynb          # Subtipos
│   │   ├── supertypes.ipynb        # Supertipos
│   │   └── card_prices.ipynb       # Preços das cartas
│   │
│   ├── 📁 02 - Bronze/             # 🥉 Camada Bronze (Raw)
│   │   ├── 📁 Dev/
│   │   │   ├── TB_BRONZE_CARDS.ipynb
│   │   │   ├── TB_BRONZE_SETS.ipynb
│   │   │   ├── TB_BRONZE_FORMATS.ipynb
│   │   │   ├── TB_BRONZE_TYPES.ipynb
│   │   │   ├── TB_BRONZE_SUBTYPES.ipynb
│   │   │   ├── TB_BRONZE_SUPERTYPES.ipynb
│   │   │   └── TB_BRONZE_CARDPRICES.ipynb
│   │   └── 📁 Documentação/
│   │
│   ├── 📁 03 - Silver/             # 🥈 Camada Silver (Cleaned)
│   │   ├── 📁 Dev/
│   │   │   ├── TB_FATO_SILVER_CARDS.ipynb
│   │   │   ├── TB_FATO_SILVER_CARDPRICES.ipynb
│   │   │   ├── TB_REF_SILVER_SETS.ipynb
│   │   │   ├── TB_REF_SILVER_FORMATS.ipynb
│   │   │   ├── TB_REF_SILVER_TYPES.ipynb
│   │   │   ├── TB_REF_SILVER_SUBTYPES.ipynb
│   │   │   └── TB_REF_SILVER_SUPERTYPES.ipynb
│   │   └── 📁 Documentação/
│   │
│   └── 📁 04 - Gold/               # 🥇 Camada Gold (Analytics)
│       ├── 📁 Dev/
│       │   ├── TB_ANALISE_TEMPORAL.ipynb
│       │   ├── TB_ANALISE_MERCADO_CARTAS_EXECUTIVO.ipynb
│       │   ├── TB_METRICAS_PERFORMANCE_INVESTIMENTOS.ipynb
│       │   └── TB_REPORT_ALERTAS_EXECUTIVOS.ipynb
│       └── 📁 Documentação/
│
├── 📁 .github/
│   ├── 📁 workflows/
│   │   └── validate-pipeline.yml   # 🔄 CI/CD Pipeline
│   ├── 📁 scripts/
│   │   └── deploy.py               # 🚀 Script de Deploy
│   └── 📁 DAGs/
│       └── magic.yml               # 📋 Configuração do Job
│
└── 📄 README.md                    # 📖 Este arquivo
```

## 🚀 **Pipeline ETL**

### **1. Ingestão (Staging)**
- **Fontes**: 
  - **Magic: The Gathering API**: Cartas, Sets, Tipos, Formatos
  - **Scryfall API**: Preços de mercado (USD, EUR, TIX)
- **Dados**: Cartas, Sets, Formatos, Tipos, Preços
- **Formato**: Parquet
- **Frequência**: Diária (6h da manhã)

### **2. Bronze Layer**
- **Função**: Armazenamento raw dos dados
- **Partitioning**: Adequado para performance
- **Preservação**: Tipos de dados originais

### **3. Silver Layer**
- **Função**: Limpeza e padronização
- **Nomenclatura**: Prefixos padronizados (NME_, COD_, DESC_)
- **Qualidade**: Validações e transformações

### **4. Gold Layer**
- **Função**: Analytics e relatórios
- **Métricas**: Performance de investimentos
- **Dashboards**: Análise temporal e executiva

## 🔄 **CI/CD Pipeline**

### **Validações Automáticas**
- ✅ **Verificação de notebooks**: Existência e sintaxe
- ✅ **Validação de dependências**: DAG do pipeline
- ✅ **Teste de conexão**: Databricks
- ✅ **Comentários em PR**: Feedback automático

### **Deploy Automático**
- 🚀 **Trigger**: Merge na branch `main`
- 🔧 **Ambiente**: Databricks Production
- 📊 **Status**: Notificações de sucesso
- 🔄 **Rollback**: Automático em caso de falha

## 🛠️ **Tecnologias**

*Stack Tecnológico*

</div>

| Componente | Tecnologia | Versão |
|------------|------------|---------|
| **Cloud Platform** | AWS | - |
| **Data Platform** | Databricks | 14.3.x |
| **Processing** | Apache Spark | 3.5+ |
| **Language** | Python | 3.9+ |
| **Storage** | Delta Lake | - |
| **CI/CD** | GitHub Actions | - |
| **APIs** | MTG API + Scryfall |

## 🔗 **Fontes de Dados**

### **Magic: The Gathering API**
- **URL**: `https://api.magicthegathering.io/v1`
- **Dados**: Cartas, Sets, Tipos, Formatos, Metadados
- **Características**: API oficial, gratuita, completa
- **Rate Limiting**: Respeitado automaticamente

### **Scryfall API**
- **URL**: `https://api.scryfall.com`
- **Dados**: Preços de mercado (USD, EUR, TIX)
- **Características**: Especializada em dados de mercado
- **Rate Limiting**: 7 workers simultâneos


### **Entidades Principais**
- 🃏 **Cartas**: ~50,000+ cartas únicas
- 📦 **Sets**: Todas as expansões
- 🎮 **Formatos**: Standard, Modern, Legacy, etc.
- 💰 **Preços**: Histórico de preços
- 🏷️ **Tipos**: Categorização completa

### **Métricas Calculadas**
- 📈 **ROI**: Retorno sobre investimento
- 📊 **Volatilidade**: Análise de risco
- 🎯 **Tendências**: Movimentos de mercado
- ⚡ **Alertas**: Oportunidades de investimento


## 🚀 **Como Usar**

### **1. Configuração Inicial**
```bash
# Clone o repositório
git clone https://github.com/scudellerlemos/pipeline-databricks-magic_card_game.git
cd pipeline-databricks-magic_card_game

# Configure as variáveis de ambiente
export DATABRICKS_HOST="your-databricks-instance"
export DATABRICKS_TOKEN="your-token"
```

### **2. Deploy Automático**
O pipeline é deployado automaticamente quando:
- ✅ PR é aprovada e mergeada na `main`
- ✅ Validações passam com sucesso
- ✅ Conexão com Databricks está ativa

### **3. Monitoramento**
- 📊 **Databricks Jobs**: Monitoramento de execução
- 📈 **GitHub Actions**: Status do CI/CD
- 🔔 **Alertas**: Notificações de falhas


### **Executivo**
- 📊 **Visão Geral**: Métricas principais
- 📈 **Tendências**: Movimentos de mercado
- 💰 **ROI**: Performance de investimentos

### **Operacional**
- 🔍 **Análise Temporal**: Evolução de preços
- ⚠️ **Alertas**: Oportunidades identificadas
- 📋 **Relatórios**: Detalhamento por categoria

## 🔧 **Configuração Técnica**

### **Cluster Configuration**
```yaml
spark_version: "14.3.x-scala2.12"
node_type_id: "m5d.large"
num_workers: 1
aws_attributes:
  first_on_demand: 1
  zone_id: "us-west-1a"
  spot_bid_price_percent: 100
```

### **Schedule**
- ⏰ **Frequência**: Diária às 6h (Brasil)
- 🌍 **Timezone**: America/Sao_Paulo
- 🔄 **Status**: UNPAUSED

## 🤝 **Contribuição**

### **Fluxo de Desenvolvimento**
1. 🍴 **Fork** o projeto
2. 🌿 **Crie** uma branch para sua feature
3. 💾 **Commit** suas mudanças
4. 🔀 **Abra** um Pull Request
5. ✅ **Aguarde** as validações automáticas

### **Padrões de Código**
- 📝 **Documentação**: READMEs em cada pasta
- 🏷️ **Nomenclatura**: Prefixos padronizados
- 🔍 **Validação**: Notebooks testados
- 📊 **Logs**: Mensagens informativas


## 🙏 **Agradecimentos**

- 🎮 **Wizards of the Coast**: Magic: The Gathering
- 📊 **Magic: The Gathering API**: Dados oficiais das cartas
- 💰 **Scryfall**: API de preços e dados de mercado
- ☁️ **Databricks**: Plataforma de dados
- 🚀 **GitHub**: CI/CD e versionamento

---

<div align="center">

**🎉 Pipeline Magic: The Gathering - Transformando dados em insights estratégicos! 🎉**

[![Made with ❤️](https://img.shields.io/badge/Made%20with-❤️-red.svg)](https://github.com/scudellerlemos/pipeline-databricks-magic_card_game)

---

<img src="https://media1.tenor.com/m/yf2J9gTT3rQAAAAC/bye-bye.gif" alt="Bye Bye" width="200" height="150">

*Obrigado por explorar nosso pipeline! 👋*

</div> 