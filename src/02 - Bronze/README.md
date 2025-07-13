# 🥉 Camada Bronze - Magic: The Gathering

<div align="center">

![RED XIII - Proud Warrior](https://repositorio.sbrauble.com/arquivos/in/magic/480717/6824dbcfba786-4us35-hj5ls-0e0603650198f950cad99859423dd8cf.jpg)

*"Through the fires of transformation, raw data emerges as structured wisdom."* - RED XIII, Magic: The Gathering - FF Edition

</div>

## 📋 Visão Geral

Esta pasta contém os notebooks responsáveis pela **camada Bronze** do pipeline de dados do Magic: The Gathering. A camada Bronze realiza o processo **EL (Extract & Load)**, carregando dados brutos da staging em dados estruturados e organizados no Unity Catalog com Delta Lake.

## 🎯 Objetivo

Carregar dados da camada de staging (S3/Parquet) em dados estruturados na camada Bronze (Unity Catalog/Delta), garantindo:
- **Extract**: Leitura eficiente dos dados de staging
- **Load**: Carregamento incremental com merge inteligente
- **Governança**: Controle através do Unity Catalog
- **Performance**: Otimização com Delta Lake
- **Rastreabilidade**: Histórico completo de mudanças

## 🔄 Processo EL (Extract & Load)

### **Extract - Extração da Staging**
```python
def extract_from_staging(table_name):
    stage_path = f"{S3_STAGE_PATH}/*_{table_name}.parquet"
    df = spark.read.parquet(stage_path)
    return df
```

### **Load - Carregamento na Bronze**
```python
def load_to_bronze_unity_merge(df, table_name):
    # Merge incremental com Delta Lake
    delta_table.alias("bronze").merge(
        df.alias("novo"),
        "bronze.id = novo.id"  # ou chave específica
    ).whenMatchedUpdateAll() \
     .whenNotMatchedInsertAll() \
     .execute()
```

## 📁 Estrutura dos Notebooks

### 🃏 `Cards.ipynb`
- **Fonte**: Dados de cartas da staging
- **Chave**: `id` (identificador único da carta)
- **Características**: 
  - Merge incremental por ID
  - Filtro temporal de 5 anos
  - Schema complexo com 25+ campos
  - Tratamento de arrays JSON
- **Tipo**: 🎴 Creature/Spell/Artifact (dados temporais)

### 🎴 `Sets.ipynb`
- **Fonte**: Dados de expansões da staging
- **Chave**: `code` (código da expansão)
- **Características**:
  - Merge incremental por código
  - Filtro temporal de 5 anos
  - Campo booster explodido em múltiplas colunas
  - Metadados de lançamento
- **Tipo**: 📦 Expansion Set (dados temporais)

### 🏷️ `Types.ipynb`
- **Fonte**: Dados de tipos da staging
- **Chave**: `type_name` (nome do tipo)
- **Características**:
  - Dados de referência estáticos
  - Sem filtro temporal
  - Schema simples (1 campo principal)
  - Compatibilidade com schemas antigos
- **Tipo**: 🏷️ Reference Card (dados estáticos)

### ⭐ `SuperTypes.ipynb`
- **Fonte**: Dados de super tipos da staging
- **Chave**: `supertype_name` (nome do super tipo)
- **Características**:
  - Dados de referência estáticos
  - Sem filtro temporal
  - Schema simples (1 campo principal)
- **Tipo**: ⭐ Reference Card (dados estáticos)

### 🔖 `SubTypes.ipynb`
- **Fonte**: Dados de sub tipos da staging
- **Chave**: `subtype_name` (nome do sub tipo)
- **Características**:
  - Dados de referência estáticos
  - Sem filtro temporal
  - Schema simples (1 campo principal)
- **Tipo**: 🔖 Reference Card (dados estáticos)

### 🎮 `Formats.ipynb`
- **Fonte**: Dados de formatos da staging
- **Chave**: `format_name` (nome do formato)
- **Características**:
  - Dados de referência estáticos
  - Sem filtro temporal
  - Schema simples (1 campo principal)
- **Tipo**: 🎮 Reference Card (dados estáticos)

### 💰 `Card_Prices.ipynb`
- **Fonte**: Dados de preços da staging (Scryfall API)
- **Chave**: `name` (nome da carta)
- **Características**:
  - Dados de preços em tempo real (USD, EUR, TIX)
  - Merge incremental por nome da carta
  - Particionamento por `ingestion_timestamp`
  - Dependência: Requer dados de cards já processados
  - Fonte de dados: Scryfall API (diferente da MTG API)
- **Tipo**: 💰 Market Data (dados dinâmicos)

## ⚙️ Configurações Necessárias

### 🔐 Segredos do Databricks
Configure os seguintes segredos no scope `mtg-pipeline`:

```python
# Unity Catalog Configuration
catalog_name           # Nome do catálogo Unity
s3_bucket             # Bucket S3 para armazenamento
s3_stage_prefix       # Prefixo da camada staging
s3_bronze_prefix      # Prefixo da camada bronze

# Temporal Configuration
years_back            # Anos para trás no filtro temporal (padrão: 5)
```

### Estrutura Unity Catalog
```
{catalog_name}/
└── bronze/
    ├── cards
    ├── sets
    ├── types
    ├── supertypes
    ├── subtypes
    └── formats
```

## 🔄 Fluxo de Execução

### 1. **Setup Unity Catalog**
- Criação do catálogo e schema
- Configuração de permissões
- Verificação de estrutura

### 2. **Extract da Staging**
- Leitura de arquivos Parquet da staging
- Aplicação de filtros temporais
- Validação de dados de entrada

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
*"Como um ferreiro forjando armas lendárias, a camada Bronze transforma dados brutos em estruturas refinadas, preparando-os para as batalhas analíticas que virão."*

## 🛡️ Controle de Qualidade

### **Validações Implementadas**
- ✅ **Verificação de dados vazios**: Validação antes do processamento
- ✅ **Remoção de duplicatas**: Baseada em chaves específicas
- ✅ **Compatibilidade de schema**: Verificação de colunas
- ✅ **Merge incremental**: Atualização inteligente de dados

### 🎴 **Flavor Text da Qualidade**
*"Como um guardião vigilante, a camada Bronze protege a integridade dos dados com escudos de validação e espadas de verificação, garantindo que apenas informações puras avancem para as próximas camadas."*

### **Tratamento de Erros e Recuperação**
```python
# Verificação de tabela Delta existente
def check_delta_table_exists(delta_path):
    delta_log_path = f"{delta_path}/_delta_log"
    files = dbutils.fs.ls(delta_log_path)
    return len(files) > 0

# Preparação para merge
def prepare_dataframe_for_merge(df, table_name, target_schema=None):
    # Remoção de duplicatas
    # Compatibilidade de schema
    # Filtros temporais

# Preservação de modificações Unity Catalog
def create_or_update_unity_catalog(full_table_name, delta_path):
    table_exists = check_unity_table_exists(full_table_name)
    
    if not table_exists:
        # Criar tabela pela primeira vez
        create_table_sql = f"CREATE TABLE {full_table_name} USING DELTA LOCATION '{delta_path}'"
        spark.sql(create_table_sql)
    else:
        # Tabela já existe, apenas atualizar propriedades de pipeline
        # (preservando modificações customizadas existentes)
        print("Atualizando apenas propriedades de pipeline")
```

#### **Estratégias de Recuperação**
- **Verificação de existência**: Antes de criar/atualizar tabelas
- **Preservação de modificações**: Não sobrescreve alterações customizadas
- **Rollback automático**: Em caso de falha no merge
- **Logs detalhados**: Para debugging e auditoria

### **Logs e Monitoramento**
- **Contagem de registros**: Antes e depois do processamento
- **Duplicatas removidas**: Quantidade e chave utilizada
- **Schema compatível**: Colunas utilizadas no merge
- **Tempo de execução**: Performance do processamento

### **Monitoramento de Particionamento**
```python
# Consulta de partições por volume de dados
partition_query = f"""
SELECT 
    partition_year,
    partition_month,
    COUNT(*) as records
FROM {table_name}
GROUP BY partition_year, partition_month
ORDER BY partition_year DESC, partition_month DESC, records DESC
LIMIT 10
"""
```

#### **Métricas de Particionamento**
- **Distribuição de dados**: Registros por partição
- **Performance**: Tempo de consulta por partição
- **Otimização**: Identificação de partições desbalanceadas
- **Manutenção**: Limpeza de partições antigas

### **Funções de Monitoramento e Validação**

#### **Verificação de Tabelas**
```python
def check_delta_table_exists(delta_path):
    # Verifica se a tabela Delta existe e tem dados
    delta_log_path = f"{delta_path}/_delta_log"
    files = dbutils.fs.ls(delta_log_path)
    if files:
        df = spark.read.format("delta").load(delta_path)
        count = df.count()
        return True, count > 0
    return False, False

def check_unity_table_exists(full_table_name):
    # Verifica se a tabela Unity Catalog existe
    tables_df = spark.sql(f"SHOW TABLES IN {CATALOG_NAME}.{SCHEMA_NAME}")
    tables_list = [row.tableName for row in tables_df.collect()]
    return TABLE_NAME in tables_list
```

#### **Informações de Processamento**
```python
def show_delta_info(table_name):
    # Mostra histórico de versões Delta
    delta_table = DeltaTable.forPath(spark, delta_path)
    history = delta_table.history()
    print(f"Versões Delta: {history.count()}")

def show_sample_data(table_name):
    # Mostra dados de exemplo da tabela
    sample_query = f"SELECT * FROM {full_table_name} LIMIT 5"
    spark.sql(sample_query).show(truncate=False)
```

## 📊 Características dos Dados

### **Dados Temporais (Cards e Sets)**
- **Filtro**: Últimos 5 anos por padrão
- **Merge**: Incremental por ID/código
- **Particionamento**: Por ano/mês baseado em `releaseDate`
- **Histórico**: Mantido no Delta Lake
- **Tipo**: 🃏 Creature/Spell/Artifact (dinâmicos)

### **Dados de Referência (Types, SuperTypes, SubTypes, Formats)**
- **Filtro**: Sem filtro temporal (dados estáticos)
- **Merge**: Incremental por nome
- **Particionamento**: Por ano/mês baseado em `ingestion_timestamp`
- **Frequência**: Atualização ocasional
- **Compatibilidade**: Suporte a schemas antigos
- **Tipo**: 🏷️ Reference Card (estáticos)

### **Dados de Preços (Card Prices)**
- **Filtro**: Baseado em cards existentes (sem filtro temporal direto)
- **Merge**: Incremental por nome da carta
- **Particionamento**: Por ano/mês baseado em `ingestion_timestamp`
- **Frequência**: Atualização frequente (preços dinâmicos)
- **Fonte**: Scryfall API (diferente da MTG API)
- **Dependência**: Requer dados de cards já processados
- **Tipo**: 💰 Market Data (dados dinâmicos)

### 🎴 **Flavor Text dos Dados**
*"Como um bibliotecário organizando grimórios antigos e novos, a camada Bronze separa conhecimento temporal de sabedoria eterna, cada um com sua própria estratégia de preservação."*

## 🔧 Funcionalidades Avançadas

### 🎴 **Flavor Text das Funcionalidades**
*"Como um arcanista dominando feitiços complexos, a camada Bronze utiliza magias avançadas de merge, particionamento e compatibilidade para forjar dados de qualidade superior."*

### **Merge Incremental Inteligente**
```python
# Merge com colunas específicas
delta_table.alias("bronze").merge(
    df.alias("novo"),
    merge_condition
).whenMatchedUpdate(set=update_actions) \
 .whenNotMatchedInsert(values=insert_actions) \
 .execute()
```

### **Compatibilidade de Schema Avançada**
```python
# Detecção automática de schema para merge
def get_delta_schema_for_merge(delta_path):
    df = spark.read.format("delta").load(delta_path)
    schema_fields = [field.name for field in df.schema.fields]
    # Excluir colunas de particionamento
    partition_columns = ['partition_year', 'partition_month']
    merge_schema = [col for col in schema_fields if col not in partition_columns]
    return merge_schema

# Preparação de dados para merge
def prepare_dataframe_for_merge(df, table_name, target_schema=None):
    # Determinar chave baseada na tabela
    if table_name == "types":
        key_column = 'type_name'
    else:
        key_column = 'name'
    
    # Remoção de duplicatas
    df = df.dropDuplicates([key_column])
    
    # Filtro de colunas compatíveis
    if target_schema:
        compatible_columns = [col for col in df.columns if col in target_schema]
        df = df.select(compatible_columns)
    
    return df
```

### **Compatibilidade de Schema**
- **Detecção automática** de diferenças de schema
- **Renomeação de colunas** para compatibilidade
- **Filtro de colunas** compatíveis
- **Preservação** de dados existentes

### **Metadados e Propriedades das Tabelas**
```python
# Propriedades automáticas configuradas
spark.sql(f"""
ALTER TABLE {full_table_name} SET TBLPROPERTIES (
    'bronze_layer' = 'true',
    'data_source' = 'mtg_api',
    'last_processing_date' = '{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
    'table_type' = 'bronze',
    'load_mode' = 'incremental_merge_fixed',
    'temporal_window_years' = '{YEARS_BACK}',
    'partitioning' = 'ingestion_timestamp_year_month'
)
""")
```

#### **Propriedades Configuradas**
- **`bronze_layer`**: Identificação da camada
- **`data_source`**: Origem dos dados (mtg_api)
- **`last_processing_date`**: Data/hora do último processamento
- **`table_type`**: Tipo da tabela (bronze)
- **`load_mode`**: Modo de carregamento (incremental_merge_fixed)
- **`temporal_window_years`**: Janela temporal configurada
- **`partitioning`**: Estratégia de particionamento utilizada

### **Filtros Temporais**
- **Configurável**: Anos para trás ajustável
- **Seletivo**: Aplicado apenas em dados temporais
- **Performance**: Otimização de consultas
- **Flexibilidade**: Diferentes estratégias por tabela

### **Particionamento das Tabelas**
```python
# Dados Temporais (Cards e Sets) - Particionamento por releaseDate
df_with_partition = df.withColumn("partition_year", 
                  when(col("releaseDate").isNotNull(), 
                       year(col("releaseDate")))
                  .otherwise(year(col("ingestion_timestamp")))) \
       .withColumn("partition_month", 
                  when(col("releaseDate").isNotNull(), 
                       month(col("releaseDate")))
                  .otherwise(month(col("ingestion_timestamp"))))

# Dados de Referência (Types, SuperTypes, SubTypes, Formats) - Particionamento por ingestion_timestamp
df_with_partition = df.withColumn("partition_year", 
                  year(col("ingestion_timestamp"))) \
       .withColumn("partition_month", 
                  month(col("ingestion_timestamp")))

# Dados de Preços (Card Prices) - Particionamento por ingestion_timestamp
df_with_partition = df.withColumn("partition_year", 
                  year(col("ingestion_timestamp"))) \
       .withColumn("partition_month", 
                  month(col("ingestion_timestamp")))

# Aplicação do particionamento
df_with_partition.write.format("delta") \
       .partitionBy("partition_year", "partition_month") \
       .save(delta_path)

#### **Campos de Particionamento**
- **`partition_year`**: Ano extraído da data de referência
- **`partition_month`**: Mês extraído da data de referência
- **Estratégia**: 
  - **Dados temporais**: Prioriza `releaseDate`, fallback para `ingestion_timestamp`
  - **Dados de referência**: Usa `ingestion_timestamp` (data de ingestão)
  - **Dados de preços**: Usa `ingestion_timestamp` (data de ingestão)

## 🚀 Como Executar

### Execução Individual
```python
# Executar notebook específico
Cards.ipynb
Sets.ipynb
Types.ipynb
SuperTypes.ipynb
SubTypes.ipynb
Formats.ipynb
Card_Prices.ipynb
```

### Execução Sequencial
```python
# Executar todos os notebooks em ordem
Types.ipynb
SuperTypes.ipynb
SubTypes.ipynb
Formats.ipynb
Sets.ipynb
Cards.ipynb
Card_Prices.ipynb  # Deve ser executado após Cards.ipynb
```

## 📋 Checklist de Execução

- [ ] Segredos configurados no Databricks
- [ ] Permissões Unity Catalog verificadas
- [ ] Cluster Spark disponível
- [ ] Dados de staging disponíveis
- [ ] Espaço em disco suficiente
- [ ] Limitações de demonstração compreendidas

## 🔗 Próximos Passos

Após o processamento na Bronze, os dados estarão disponíveis para:
1. **Camada Silver**: Transformações e enriquecimento
2. **Camada Gold**: Modelos de dados finais
3. **Análises**: Consultas diretas no Unity Catalog

## 🏗️ Engenharia de Dados

### 🎴 **Flavor Text da Engenharia**
*"Como um mestre ferreiro forjando armas lendárias, a engenharia da camada Bronze combina arte e ciência para criar estruturas de dados que resistem ao teste do tempo."*

### 🎯 Princípios da Camada Bronze

#### **1. Estruturação**
- ✅ Transformação de dados brutos em estruturados
- ✅ Schema explícito e validado
- ✅ Tipos de dados apropriados
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

#### **Regra #1: Merge Incremental**
```python
# ✅ CORRETO - Merge com chave específica
delta_table.merge(df, "bronze.id = novo.id")

# ❌ INCORRETO - Overwrite completo
df.write.mode("overwrite").save(delta_path)
```

#### **Regra #2: Compatibilidade de Schema**
```python
# Verificação de compatibilidade antes do merge
target_schema = get_delta_schema_for_merge(delta_path)
compatible_columns = [col for col in df.columns if col in target_schema]
```

#### **Regra #3: Remoção de Duplicatas**
```python
# Remoção baseada em chave específica
df = df.dropDuplicates([key_column])
```

#### **Regra #4: Logs Estruturados**
```python
print(f"Extraídos {df.count()} registros de staging")
print(f"Removidas {duplicates} duplicatas")
print(f"Merge executado com sucesso")
```

## 🎴 Galeria Visual - Camada Bronze

### 🏗️ Elementos da Camada Bronze
```
🏗️ Estruturação    🔄 Incrementalidade    🛡️ Governança    📊 Qualidade
```

### 🐉 Criaturas da Bronze
```
🐉 Bronze Dragon    🛡️ Bronze Golem    ⚔️ Bronze Sphinx    🏰 Bronze Guardian
```

### 🔧 Ferramentas da Forja
```
🔥 Forge Hammer    ⚒️ Anvil of Data    🔨 Refinement Tools    🏭 Processing Plant
```

### 🎯 Metodologias da Bronze
```
📐 Schema Forge    🔄 Merge Mastery    🛡️ Quality Shield    📊 Metrics Crystal
```

### 🌟 Propriedades Mágicas
```
✨ Bronze Layer    🔗 Data Source    ⏰ Processing Time    🎮 Load Mode
```

### 🏛️ Arquitetura da Bronze
```
🏛️ Unity Catalog    🗄️ Delta Lake    📁 Schema Bronze    🔐 Governance
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

## 📚 Documentação Completa

### 🎯 **Documentação Detalhada das Tabelas**
Para informações completas sobre cada tabela da camada Bronze, incluindo schema detalhado, regras de implementação, particionamento e linhagem de dados, consulte nossa **documentação completa**:

**[📖 Ver Documentação Completa da Camada Bronze](./Documentação/README.md)**

### 📋 **O que você encontrará na documentação:**
- **Schema detalhado** de todas as 7 tabelas
- **Regras de renomeação**
- **Estratégias de particionamento** específicas
- **Linhagem de dados** e fluxo de processamento
- **Regras de implementação** e filtros temporais
- **Exemplos de uso** e casos específicos

### 🎴 **Flavor Text da Documentação**
*"Como um grimório sagrado que contém todos os segredos da magia, a documentação completa da camada Bronze revela os mistérios de cada tabela, permitindo que os magos da engenharia de dados dominem completamente o poder dos dados estruturados."*

## 📞 Suporte

Para dúvidas ou problemas:
- Verificar logs de execução
- Consultar histórico do Delta Lake
- Revisar configurações de segredos
- Verificar permissões Unity Catalog
- Para detalhes técnicos: Acessar [Documentação Completa](./Documentação/README.md) 

