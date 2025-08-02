# 🥇 Camada Gold - Magic: The Gathering

<div align="center">

<!-- Imagem ilustrativa da tabela (adicione o link abaixo) -->
![Jace, the Mind Sculptor](https://cdn11.bigcommerce.com/s-3b5vpig99v/images/stencil/500x659/products/587617/1128758/JaceTheMindSculptor8001__01242.1671568738.jpg?c=2)

*"Na forja sagrada da Gold, insights lapidados se transformam em visões estratégicas para decisões executivas."* - Nicol Bolas, Magic: The Gathering

</div>

## 📋 Visão Geral

Esta pasta contém os notebooks responsáveis pela **camada Gold** do pipeline de dados do Magic: The Gathering. A camada Gold realiza o processo **AL (Analyze & Load)**, criando análises executivas, métricas de negócio e insights estratégicos prontos para consumo executivo e tomada de decisão.

## 🎯 Objetivo

Transformar dados enriquecidos da Silver em análises executivas, métricas de performance e insights estratégicos na Gold (Unity Catalog/Delta), garantindo:
- **Analyze**: Análises pré-computadas e métricas de negócio
- **Load**: Carregamento incremental com merge inteligente
- **Governança**: Controle e rastreabilidade via Unity Catalog
- **Performance**: Otimização com Delta Lake
- **Prontidão Executiva**: Insights prontos para tomada de decisão

## 🔄 Processo AL (Analyze & Load)

### **Analyze - Análises Executivas e Métricas**
```python
# Exemplo de análise executiva típica
df_analise = df_silver.groupBy("DATA_REF", "NME_SET", "NME_CARD_TYPE", "NME_RARITY") \
    .agg(
        sum("VLR_USD").cast("decimal(10,2)").alias("VALOR_TOTAL_MERCADO"),
        countDistinct("NME_CARD").cast("int").alias("QTD_CARTAS_ATIVAS"),
        avg("VLR_USD").cast("decimal(10,2)").alias("VALOR_MEDIO_CARTA"),
        expr("percentile_approx(VLR_USD, 0.5)").cast("decimal(10,2)").alias("TICKET_MEDIANA")
    )

# Cálculo de market share
window_set = Window.partitionBy("DATA_REF")
df_analise = df_analise.withColumn(
    "MARKET_SHARE_SET",
    (col("VALOR_TOTAL_MERCADO") / sum("VALOR_TOTAL_MERCADO").over(window_set)).cast("decimal(10,4)")
)
```

### **Load - Carregamento na Gold**
```python
def load_to_gold_unity_incremental(df, table_name):
    # Merge incremental com Delta Lake
    delta_table.alias("gold").merge(
        df.alias("novo"),
        "gold.DATA_REF = novo.DATA_REF AND gold.NME_CARD = novo.NME_CARD"
    ).whenMatchedUpdateAll() \
     .whenNotMatchedInsertAll() \
     .execute()
```

## 📁 Estrutura dos Notebooks

### 📊 `TB_ANALISE_MERCADO_CARTAS_EXECUTIVO.ipynb`
- **Fonte**: Dados de cartas e preços da Silver
- **Chave**: `DATA_REF`, `NME_CARD`
- **Características**: 
  - Análise executiva de mercado
  - Agregações por segmento (set, tipo, raridade)
  - Cálculo de market share e valorização
  - Categorizações automáticas
  - Particionamento otimizado para consultas executivas
- **Tipo**: 📊 Executive Analysis (análises pré-computadas)

### 📈 `TB_METRICAS_PERFORMANCE_INVESTIMENTOS.ipynb`
- **Fonte**: Dados de cartas e preços da Silver
- **Chave**: `DATA_REF`, `NME_CARD`
- **Características**:
  - KPIs de performance e ROI
  - Análise de risco e volatilidade
  - Métricas de liquidez
  - Indicadores de investimento
  - Particionamento por período e set
- **Tipo**: 📈 Investment KPIs (métricas financeiras)

### ⏰ `TB_ANALISE_TEMPORAL.ipynb`
- **Fonte**: Dados de cartas e preços da Silver
- **Chave**: `DATA_REF`, `NME_CARD`
- **Características**:
  - Análise de padrões temporais e sazonalidade
  - Tendências de longo prazo
  - Indicadores de momentum
  - Extração de componentes temporais
  - Particionamento por período e set
- **Tipo**: ⏰ Temporal Analysis (padrões temporais)

### 🚨 `TB_REPORT_ALERTAS_EXECUTIVOS.ipynb`
- **Fonte**: Dados de cartas e preços da Silver
- **Chave**: `DATA_REF`, `NME_CARD`
- **Características**:
  - Sistema de alertas executivos
  - Detecção de oportunidades e riscos
  - Priorização de ações
  - Recomendações automáticas
  - Particionamento por período e set
- **Tipo**: 🚨 Executive Alerts (sistema de alertas)

## ⚙️ Configurações Necessárias

### 🔐 Segredos do Databricks
Configure os seguintes segredos no scope `mtg-pipeline`:
```python
catalog_name           # Nome do catálogo Unity
s3_bucket             # Bucket S3 para armazenamento
s3_gold_prefix        # Prefixo da camada gold
```

### Estrutura Unity Catalog
```
{catalog_name}/
└── gold/
    ├── TB_ANALISE_MERCADO_CARTAS_EXECUTIVO
    ├── TB_METRICAS_PERFORMANCE_INVESTIMENTOS
    ├── TB_ANALISE_TEMPORAL
    └── TB_REPORT_ALERTAS_EXECUTIVOS
```

## 🔄 Fluxo de Execução

### 1. **Setup Unity Catalog**
- Criação do catálogo e schema
- Configuração de permissões
- Verificação de estrutura

### 2. **Análise Gold**
- Agregações executivas e métricas
- Cálculo de KPIs e indicadores
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
*"Como um oráculo que transforma dados em visões de lucro, a camada Gold revela os segredos do mercado de cartas, oferecendo insights lapidados para decisões estratégicas."*

## 🛡️ Controle de Qualidade

### **Validações Implementadas**
- ✅ **Verificação de dados vazios**
- ✅ **Remoção de duplicatas**
- ✅ **Compatibilidade de schema**
- ✅ **Merge incremental**
- ✅ **Arredondamento preciso** (2-4 casas decimais)
- ✅ **Validação de métricas**

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
- **Validação de métricas**: Verificação de cálculos

## 📊 Características dos Dados

### **Análises Executivas (TB_ANALISE_MERCADO_CARTAS_EXECUTIVO)**
- **Filtro**: Baseado em RELEASE_YEAR e RELEASE_MONTH
- **Merge**: Incremental por DATA_REF + NME_CARD
- **Particionamento**: Por DATA_REF, NME_SET, NME_CARD_TYPE, NME_RARITY
- **Arredondamento**: 2 casas para valores, 4 para percentuais
- **Tipo**: 📊 Executive Analysis (análises pré-computadas)

### **Métricas de Performance (TB_METRICAS_PERFORMANCE_INVESTIMENTOS)**
- **Filtro**: Baseado em RELEASE_YEAR e RELEASE_MONTH
- **Merge**: Incremental por DATA_REF + NME_CARD
- **Particionamento**: Por DATA_REF, NME_SET
- **Arredondamento**: 2 casas para valores, 4 para percentuais
- **Tipo**: 📈 Investment KPIs (métricas financeiras)

### **Análises Temporais (TB_ANALISE_TEMPORAL)**
- **Filtro**: Baseado em RELEASE_YEAR e RELEASE_MONTH
- **Merge**: Incremental por DATA_REF + NME_CARD
- **Particionamento**: Por DATA_REF, NME_SET
- **Arredondamento**: 2 casas para valores, 4 para percentuais
- **Tipo**: ⏰ Temporal Analysis (padrões temporais)

### **Alertas Executivos (TB_REPORT_ALERTAS_EXECUTIVOS)**
- **Filtro**: Baseado em RELEASE_YEAR e RELEASE_MONTH
- **Merge**: Incremental por DATA_REF + NME_CARD
- **Particionamento**: Por DATA_REF, NME_SET
- **Arredondamento**: 2 casas para valores, 4 para percentuais
- **Tipo**: 🚨 Executive Alerts (sistema de alertas)

### 🎴 **Flavor Text dos Dados**
*"Na Gold, cada métrica é uma joia lapidada, cada insight uma visão estratégica, pronta para iluminar o caminho das decisões executivas."*

## 🔧 Funcionalidades Avançadas

### **Modularização com gold_utils.ipynb**
```python
# Importação do módulo utilitário
%run ./gold_utils

# Configuração via módulo
config = create_manual_config(
    catalog_name="magic_the_gathering",
    s3_bucket=get_secret("s3_bucket"),
    s3_gold_prefix="magic_the_gathering/gold"
)

# Uso do processador modularizado
processor = GoldTableProcessor(TABLE_NAME, config)
dfs = processor.load_silver_data(['cards', 'prices'])
```

### **Merge Incremental Inteligente**
```python
delta_table.alias("gold").merge(
    df.alias("novo"),
    merge_condition
).whenMatchedUpdate(set=update_actions) \
 .whenNotMatchedInsert(values=insert_actions) \
 .execute()
```

### **Compatibilidade e Análises de Schema**
- Detecção automática de diferenças de schema
- Cálculos precisos com arredondamento controlado
- Agregações otimizadas para performance
- Preservação de dados existentes

### **Metadados e Propriedades das Tabelas**
- **`gold_layer`**: Identificação da camada
- **`data_source`**: Origem dos dados (silver_layer)
- **`last_processing_date`**: Data/hora do último processamento
- **`table_type`**: Tipo da tabela (gold)
- **`load_mode`**: Modo de carregamento (incremental_merge_analysis)
- **`partitioning`**: Estratégia de particionamento utilizada

### **Particionamento das Tabelas**
- **Análises Executivas**: Particionamento por DATA_REF e dimensões de negócio
- **Métricas de Performance**: Particionamento por DATA_REF e NME_SET
- **Análises Temporais**: Particionamento por DATA_REF e NME_SET
- **Alertas**: Particionamento por DATA_REF e NME_SET

## 🔗 Próximos Passos

Após o processamento na Gold, os dados estarão disponíveis para:
1. **Dashboards Executivos**: Visualizações e relatórios
3. **Tomada de Decisão**: Insights estratégicos

## 📊 Expansão Futura - Tabelas Silver Restantes

### 🎯 **Potencial de Análises Adicionais**

Atualmente, a camada Gold utiliza apenas as tabelas `TB_FATO_SILVER_CARDS` e `TB_FATO_SILVER_CARDPRICES` da Silver. Existem **5 tabelas Silver adicionais** que podem expandir significativamente as capacidades analíticas:

#### **Tabelas Silver Disponíveis para Expansão:**
- **TB_REF_SILVER_SETS** - Metadados de coleções e expansões
- **TB_REF_SILVER_TYPES** - Tipos de cartas (Criatura, Feitiço, Artefato, etc.)
- **TB_REF_SILVER_SUPERTYPES** - Supertipos (Lendário, Básico, etc.)
- **TB_REF_SILVER_SUBTYPES** - Subtipos (Humano, Dragão, Goblin, etc.)
- **TB_REF_SILVER_FORMATS** - Formatos de jogo (Standard, Modern, Commander, etc.)

### 🏗️ **Análises Futuras Possíveis**

#### **Análises por Formato de Jogo:**
- Performance de cartas por formato (Standard vs Modern vs Commander)
- Análise de metagame e tendências por formato
- Valorização específica por formato de jogo
- Alertas de banimentos e restrições por formato

#### **Análises por Tipo e Subtipo:**
- Performance de Criaturas vs Feitiços vs Artefatos
- Análise de tribos (Humano, Dragão, Goblin, etc.)
- Valorização por tipo de carta
- Tendências de design e poder por tipo

#### **Análises por Coleção/Set:**
- Performance de cartas por set de lançamento
- Análise de power creep ao longo do tempo
- Valorização de cartas por raridade dentro de sets
- Sazonalidade de lançamentos de novos sets

### 🗄️ **Data Warehouse Completo**

Com todas as tabelas Silver disponíveis, é possível construir um **Data Warehouse completo** seguindo o modelo Star Schema:

#### **Dimensões (DIM):**
- **DIM_CARTAS** - Dimensão de cartas com todos os atributos
- **DIM_SETS** - Dimensão de coleções e expansões
- **DIM_TEMPO** - Dimensão temporal (ano, mês, trimestre)
- **DIM_FORMATOS** - Dimensão de formatos de jogo
- **DIM_TIPOS** - Dimensão de tipos e subtipos

#### **Fatos (FATO):**
- **FATO_PRECOS** - Fato central com preços e métricas
- **FATO_PERFORMANCE** - Fato de performance e ROI
- **FATO_MERCADO** - Fato de métricas de mercado

#### **Tabelas Bridge:**
- **BRIDGE_CARTA_FORMATO** - Relacionamento M:N entre cartas e formatos
- **BRIDGE_CARTA_TIPO** - Relacionamento M:N entre cartas e tipos

### 🎴 **Flavor Text da Expansão**
*"Como um bibliotecário arcano descobrindo novos grimórios, a expansão da camada Gold revelará segredos ocultos do multiverso de dados, transformando cada tabela Silver em insights estratégicos de valor inestimável."*


## 🏗️ Engenharia de Dados

### 🎴 **Flavor Text da Engenharia**
*"Como um ourives mestre lapidando diamantes, a engenharia da Gold transforma dados em insights estratégicos, cada métrica uma joia de valor inestimável para as decisões executivas."*

### 🎯 Princípios da Camada Gold

#### **1. Análise Executiva**
- ✅ Transformação de dados em insights estratégicos
- ✅ Métricas de negócio e KPIs
- ✅ Agregações otimizadas para consultas executivas
- ✅ Categorizações automáticas

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

#### **Regra #1: Análises Executivas**
```python
# Agregações otimizadas para consultas executivas
df_analise = df.groupBy("DATA_REF", "NME_SET", "NME_CARD_TYPE", "NME_RARITY") \
    .agg(
        sum("VLR_USD").cast("decimal(10,2)").alias("VALOR_TOTAL_MERCADO"),
        countDistinct("NME_CARD").cast("int").alias("QTD_CARTAS_ATIVAS")
    )
```

#### **Regra #2: Merge Incremental**
```python
delta_table.merge(df, "gold.DATA_REF = novo.DATA_REF AND gold.NME_CARD = novo.NME_CARD")
```

#### **Regra #3: Arredondamento Preciso**
```python
# 2 casas para valores monetários, 4 para percentuais
sum("VLR_USD").cast("decimal(10,2)").alias("VALOR_TOTAL_MERCADO")
(col("VALOR_TOTAL_MERCADO") / sum("VALOR_TOTAL_MERCADO").over(window)).cast("decimal(10,4)")
```

#### **Regra #4: Logs Estruturados**
```python
print(f"Análises executivas aplicadas: {analyses}")
print(f"Merge executado com sucesso")
```

## 🎴 Galeria Visual - Camada Gold

### 🏗️ Elementos da Camada Gold
```
💎 Análise Executiva    🔄 Incrementalidade    🛡️ Governança    📊 Qualidade
```

### 👑 Personagens da Gold
```
👑 Nicol Bolas    🏛️ Ugin    🐉 Dragon Lords    🧙‍♂️ Planeswalkers
```

### 🔧 Ferramentas do Ourives
```
💎 Diamond Cutter    🏺 Insight Vessel    🔮 Oracle Crystal    ⚖️ Strategy Scales
```

### 🎯 Metodologias da Gold
```
💎 Executive Analysis    🔄 Merge Mastery    🛡️ Quality Shield    📊 Metrics Crystal
```

### 🌟 Propriedades Mágicas
```
✨ Gold Layer    🔗 Data Source    ⏰ Processing Time    🎮 Load Mode
```

### 🏛️ Arquitetura da Gold
```
🏛️ Unity Catalog    🗄️ Delta Lake    📁 Schema Gold    🔐 Governance
```

### 🎴 Tipos de Análises Processadas
```
📊 Executive Analysis    📈 Investment KPIs    ⏰ Temporal Analysis    🚨 Executive Alerts
```

### 🔄 Operações de Merge
```
🔄 Incremental Merge    📊 Schema Compatibility    🛡️ Quality Validation
⚡ Performance Optimization    📈 Data Monitoring    🔍 Error Handling
```

## 📚 Documentação Completa

### 🎯 **Documentação Detalhada das Tabelas**
Para informações completas sobre cada tabela da camada Gold, incluindo schema detalhado, regras de implementação, particionamento e linhagem de dados, consulte nossa **documentação completa**:


### 📋 **O que você encontrará na documentação:**
- **Schema detalhado** de todas as 4 tabelas de análise
- **Regras de cálculo** e agregações
- **Estratégias de particionamento** específicas
- **Linhagem de dados** e fluxo de processamento
- **Regras de implementação** e métricas de negócio
- **Exemplos de uso** e casos específicos

### 🎴 **Flavor Text da Documentação**
*"Como um grimório sagrado que contém todos os segredos da magia executiva, a documentação completa da camada Gold revela os mistérios de cada análise, permitindo que os magos dos negócios dominem completamente o poder dos insights estratégicos."*

## 🚀 Como Executar

### Execução Individual
```python
# Executar notebook específico
TB_ANALISE_MERCADO_CARTAS_EXECUTIVO_MODULAR.py
TB_METRICAS_PERFORMANCE_INVESTIMENTOS_MODULAR.py
TB_ANALISE_TEMPORAL.py
TB_REPORT_ALERTAS_EXECUTIVOS_MODULAR.py
```

### Execução Sequencial
```python
# Executar todos os notebooks em ordem
TB_ANALISE_MERCADO_CARTAS_EXECUTIVO_MODULAR.py
TB_METRICAS_PERFORMANCE_INVESTIMENTOS_MODULAR.py
TB_ANALISE_TEMPORAL.py
TB_REPORT_ALERTAS_EXECUTIVOS_MODULAR.py
```

## 📋 Checklist de Execução

- [ ] Segredos configurados no Databricks
- [ ] Permissões Unity Catalog verificadas
- [ ] Cluster Spark disponível
- [ ] Dados da Silver disponíveis
- [ ] Espaço em disco suficiente
- [ ] gold_utils.py configurado

## 📞 Suporte

Para dúvidas ou problemas:
- Verificar logs de execução
- Consultar histórico do Delta Lake
- Revisar configurações de segredos
- Verificar permissões Unity Catalog