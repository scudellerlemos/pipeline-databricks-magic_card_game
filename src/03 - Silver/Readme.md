# 🥈 Camada Silver - Magic: The Gathering

<div align="center">

<!-- Imagem ilustrativa da tabela (adicione o link abaixo) -->
![RED XIII - Proud Warrior](https://img.mypcards.com/img/1/137/magic_ddajvc_001/magic_ddajvc_001_en.jpg)


*"Na forja alquímica da Silver, dados brutos ganham forma, clareza e poder analítico."* - Jace Beleren, Magic: The Gathering

</div>

## 📋 Visão Geral

Esta pasta contém os notebooks responsáveis pela **camada Silver** do pipeline de dados do Magic: The Gathering. A camada Silver realiza o processo **TL (Transform & Load)**, refinando, limpando e enriquecendo os dados da Bronze para análises avançadas e modelagem de negócio.

## 🎯 Objetivo

Transformar dados estruturados da Bronze em dados limpos, padronizados e enriquecidos na Silver (Unity Catalog/Delta), garantindo:
- **Transform**: Limpeza, padronização e enriquecimento
- **Load**: Carregamento incremental com merge inteligente
- **Governança**: Controle e rastreabilidade via Unity Catalog
- **Performance**: Otimização com Delta Lake
- **Prontidão Analítica**: Dados prontos para análises e camadas superiores

## 🔄 Processo TL (Transform & Load)

### **Transform - Limpeza e Enriquecimento**
```python
# Exemplo de transformação típica
cards = cards.withColumn("NME_CARD", initcap(trim(col("NME_CARD"))))
cards = cards.withColumn("MANA_COST", coalesce(col("MANA_COST"), lit(0)))
cards = cards.withColumn("NME_COLOR_CATEGORY", when(col("COD_COLORS") == "Colorless", "Colorless")
    .when(size(split(col("COD_COLORS"), ",")) == 1, "Mono")
    .when(size(split(col("COD_COLORS"), ",")) == 2, "Dual Color")
    .otherwise("Multicolor"))
```

### **Load - Carregamento na Silver**
```python
def load_to_silver_unity_incremental(df, table_name):
    # Merge incremental com Delta Lake
    delta_table.alias("silver").merge(
        df.alias("novo"),
        "silver.id = novo.id"  # ou chave específica
    ).whenMatchedUpdateAll() \
     .whenNotMatchedInsertAll() \
     .execute()
```

## 📁 Estrutura dos Notebooks

### 🃏 `Cards.ipynb`
- **Fonte**: Dados de cartas da Bronze
- **Chave**: `ID_CARD`
- **Características**: 
  - Merge incremental por ID
  - Filtro temporal de 5 anos
  - Enriquecimento de tipos, cores, categorias
  - Padronização de nomes, custos, textos
  - Particionamento por ano/mês de ingestão
- **Tipo**: 🎴 Creature/Spell/Artifact (dados temporais)

### 📦 `Sets.ipynb`
- **Fonte**: Dados de expansões da Bronze
- **Chave**: `COD_SET`
- **Características**:
  - Merge incremental por código
  - Filtro temporal de 5 anos
  - Enriquecimento de metadados
  - Particionamento por ano/mês de lançamento
- **Tipo**: 📦 Expansion Set (dados temporais)

### 🏷️ `Types.ipynb`, ⭐ `SuperTypes.ipynb`, 🔖 `SubTypes.ipynb`, 🎮 `Formats.ipynb`
- **Fonte**: Dados de referência da Bronze
- **Chave**: Nome do tipo/supertipo/subtipo/formato
- **Características**:
  - Dados de referência estáticos
  - Padronização e limpeza
  - Particionamento por ano/mês de ingestão
- **Tipo**: 🏷️/⭐/🔖/🎮 Reference Card (dados estáticos)

### 💰 `Card_Prices.ipynb`
- **Fonte**: Dados de preços da Bronze
- **Chave**: `NME_CARD`
- **Características**:
  - Preços em tempo real (USD, EUR, TIX)
  - Merge incremental por nome da carta
  - Particionamento por ano/mês de ingestão
  - Dependência: requer dados de cards já processados
- **Tipo**: 💰 Market Data (dados dinâmicos)

## ⚙️ Configurações Necessárias

### 🔐 Segredos do Databricks
Configure os seguintes segredos no scope `mtg-pipeline`:
```python
catalog_name           # Nome do catálogo Unity
s3_bucket             # Bucket S3 para armazenamento
s3_silver_prefix      # Prefixo da camada silver
```

### Estrutura Unity Catalog
```
{catalog_name}/
└── silver/
    ├── cards
    ├── sets
    ├── types
    ├── supertypes
    ├── subtypes
    ├── formats
    └── card_prices
```

## 🔄 Fluxo de Execução

### 1. **Setup Unity Catalog**
- Criação do catálogo e schema
- Configuração de permissões
- Verificação de estrutura

### 2. **Transformação Silver**
- Limpeza, padronização e enriquecimento
- Aplicação de regras de negócio
- Validação de dados

### 3. **Preparação para Merge**
- Remoção de duplicatas
- Compatibilidade de schema
- Preparação de chaves de merge

### 4. **Load Incremental**
- Verificação de tabela existente
- Merge incremental com Delta Lake
- Criação/atualização da tabela Unity Catalog

### 5. **Validação e Monitoramento**
- Contagem de registros
- Verificação de integridade
- Logs de processamento

### 🎴 **Flavor Text do Processamento**
*"Como um alquimista, a camada Silver transmuta dados brutos em informação valiosa, pronta para ser utilizada nas estratégias mais complexas do multiverso analítico."*

## 🛡️ Controle de Qualidade

### **Validações Implementadas**
- ✅ **Verificação de dados vazios**
- ✅ **Remoção de duplicatas**
- ✅ **Compatibilidade de schema**
- ✅ **Merge incremental**
- ✅ **Padronização e enriquecimento**

### **Tratamento de Erros e Recuperação**
- **Verificação de existência**: Antes de criar/atualizar tabelas
- **Preservação de modificações**: Não sobrescreve alterações customizadas
- **Rollback automático**: Em caso de falha no merge
- **Logs detalhados**: Para debugging e auditoria

### **Logs e Monitoramento**
- **Contagem de registros**: Antes e depois do processamento
- **Duplicatas removidas**: Quantidade e chave utilizada
- **Schema compatível**: Colunas utilizadas no merge
- **Tempo de execução**: Performance do processamento

## 📊 Características dos Dados

### **Dados Temporais (Cards e Sets)**
- **Filtro**: Últimos 5 anos por padrão
- **Merge**: Incremental por ID/código
- **Particionamento**: Por ano/mês baseado em `DT_INGESTION` ou `RELEASE_DATE`
- **Histórico**: Mantido no Delta Lake
- **Tipo**: 🃏 Creature/Spell/Artifact (dinâmicos)

### **Dados de Referência (Types, SuperTypes, SubTypes, Formats)**
- **Filtro**: Sem filtro temporal (dados estáticos)
- **Merge**: Incremental por nome
- **Particionamento**: Por ano/mês baseado em `DT_INGESTION`
- **Frequência**: Atualização ocasional
- **Compatibilidade**: Suporte a schemas antigos
- **Tipo**: 🏷️ Reference Card (estáticos)

### **Dados de Preços (Card Prices)**
- **Filtro**: Baseado em cards existentes (sem filtro temporal direto)
- **Merge**: Incremental por nome da carta
- **Particionamento**: Por ano/mês baseado em `DT_INGESTION`
- **Frequência**: Atualização frequente (preços dinâmicos)
- **Fonte**: Scryfall API (diferente da MTG API)
- **Dependência**: Requer dados de cards já processados
- **Tipo**: 💰 Market Data (dados dinâmicos)

### 🎴 **Flavor Text dos Dados**
*"Na Silver, cada dado é polido como uma joia, revelando seu verdadeiro valor para as estratégias do plano."*

## 🔧 Funcionalidades Avançadas

### **Merge Incremental Inteligente**
```python
delta_table.alias("silver").merge(
    df.alias("novo"),
    merge_condition
).whenMatchedUpdate(set=update_actions) \
 .whenNotMatchedInsert(values=insert_actions) \
 .execute()
```

### **Compatibilidade e Enriquecimento de Schema**
- Detecção automática de diferenças de schema
- Renomeação e padronização de colunas
- Enriquecimento com colunas derivadas (ex: categorias, flags, métricas)
- Preservação de dados existentes

### **Metadados e Propriedades das Tabelas**
- **`silver_layer`**: Identificação da camada
- **`data_source`**: Origem dos dados (mtg_api)
- **`last_processing_date`**: Data/hora do último processamento
- **`table_type`**: Tipo da tabela (silver)
- **`load_mode`**: Modo de carregamento (incremental_merge_enriched)
- **`partitioning`**: Estratégia de particionamento utilizada

### **Particionamento das Tabelas**
- **Dados Temporais**: Particionamento por ano/mês de referência
- **Dados de Referência**: Particionamento por ano/mês de ingestão
- **Dados de Preços**: Particionamento por ano/mês de ingestão

## 🔗 Próximos Passos

Após o processamento na Silver, os dados estarão disponíveis para:
1. **Camada Gold**: Modelos de dados finais e métricas
2. **Análises**: Consultas e dashboards avançados

## 🏗️ Engenharia de Dados

### 🎴 **Flavor Text da Engenharia**
*"Como um ourives lapidando gemas raras, a engenharia da Silver transforma dados em insights valiosos, prontos para brilhar nas análises mais exigentes."*

### 🎯 Princípios da Camada Silver

#### **1. Enriquecimento**
- ✅ Transformação de dados em informação
- ✅ Colunas derivadas e métricas
- ✅ Padronização e limpeza
- ✅ Metadados organizados

#### **2. Incrementalidade**
- ✅ Merge inteligente de dados
- ✅ Preservação de histórico
- ✅ Performance otimizada
- ✅ Recuperação de falhas

#### **3. Governança**
- ✅ Unity Catalog para controle
- ✅ Permissões granulares
- ✅ Rastreabilidade completa
- ✅ Auditoria de mudanças

#### **4. Qualidade**
- ✅ Validação de integridade
- ✅ Remoção de duplicatas
- ✅ Compatibilidade de schema
- ✅ Logs estruturados

### 📐 Regras da Camada

#### **Regra #1: Enriquecimento e Padronização**
```python
# Exemplo de enriquecimento
cards = cards.withColumn("NME_COLOR_CATEGORY", ...)
cards = cards.withColumn("QTY_COLORS", ...)
```

#### **Regra #2: Merge Incremental**
```python
delta_table.merge(df, "silver.id = novo.id")
```

#### **Regra #3: Compatibilidade de Schema**
```python
# Verificação de compatibilidade antes do merge
compatible_columns = [col for col in df.columns if col in target_schema]
```

#### **Regra #4: Logs Estruturados**
```python
print(f"Transformações aplicadas: {transformations}")
print(f"Merge executado com sucesso")
```

## 🎴 Galeria Visual - Camada Silver

### 🏗️ Elementos da Camada Silver
```
💎 Enriquecimento    🔄 Incrementalidade    🛡️ Governança    📊 Qualidade
```

### 🧙‍♂️ Personagens da Silver
```
🧙‍♂️ Jace Beleren    🦉 Narset    🦅 Teferi    🦋 Tamiyo
```

### 🔧 Ferramentas do Alquimista
```
⚗️ Alembic    🧪 Elixir of Data    🔬 Insight Lens    🏺 Data Vessel
```

### 🎯 Metodologias da Silver
```
💎 Data Enrichment    🔄 Merge Mastery    🛡️ Quality Shield    📊 Metrics Crystal
```

### 🌟 Propriedades Mágicas
```
✨ Silver Layer    🔗 Data Source    ⏰ Processing Time    🎮 Load Mode
```

### 🏛️ Arquitetura da Silver
```
🏛️ Unity Catalog    🗄️ Delta Lake    📁 Schema Silver    🔐 Governance
```

### 🎴 Tipos de Dados Processados
```
🃏 Cards (Temporais)    📦 Sets (Temporais)    🏷️ Types (Referência)
⭐ SuperTypes (Referência)    🔖 SubTypes (Referência)    🎮 Formats (Referência)
💰 Card Prices (Market Data)
```

### 🔄 Operações de Merge
```
🔄 Incremental Merge    📊 Schema Compatibility    🛡️ Quality Validation
⚡ Performance Optimization    📈 Data Monitoring    🔍 Error Handling
```

## 📞 Suporte

Para dúvidas ou problemas:
- Verificar logs de execução
- Consultar histórico do Delta Lake
- Revisar configurações de segredos
- Verificar permissões Unity Catalog
- Consultar este README para referência 📚 
