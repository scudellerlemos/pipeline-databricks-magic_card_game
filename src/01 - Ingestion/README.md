# 📥 Pipeline de Ingestão - Magic: The Gathering

<div align="center">

![Shuko - Artifact Equipment](https://repositorio.sbrauble.com/arquivos/in/magic/199/5f424341cf64f-dzpnm7-nvfmuq-140f6969d5213fd0ece03148e62e461e.jpg)

*"A simple tool in the hands of a master becomes a deadly weapon."* - Shuko, Betrayers of Kamigawa

</div>

## 📋 Visão Geral

Esta pasta contém os notebooks responsáveis pela **ingestão de dados brutos** da API do Magic: The Gathering para o ambiente de staging no S3. Os dados são coletados, processados e salvos em formato Parquet para posterior processamento na camada Bronze.

## 🔗 APIs Utilizadas

### **Magic: The Gathering API**
- **URL Base**: `https://api.magicthegathering.io/v1`
- **Documentação**: [https://docs.magicthegathering.io](https://docs.magicthegathering.io)
- **Tipo**: REST API pública e gratuita
- **Rate Limiting**: Sim (respeitado automaticamente)
- **Formato de Resposta**: JSON
- **Dados**: Cartas, sets, tipos, formatos e metadados

### **Scryfall API**
- **URL Base**: `https://api.scryfall.com`
- **Documentação**: [https://scryfall.com/docs/api](https://scryfall.com/docs/api)
- **Tipo**: REST API pública e gratuita
- **Rate Limiting**: Sim (respeitado com 7 workers simultâneos)
- **Formato de Resposta**: JSON
- **Dados**: Preços atualizados de cartas (USD, EUR, TIX)
- **Especialização**: Dados de mercado e preços em tempo real

### **Endpoints Utilizados**

#### **Magic: The Gathering API**
```
GET /cards          # Lista de cartas (com paginação)
GET /sets           # Lista de expansões/coleções
GET /types          # Tipos de cartas
GET /supertypes     # Super tipos
GET /subtypes       # Sub tipos  
GET /formats        # Formatos de jogo
```

#### **Scryfall API**
```
GET /cards/named?exact={card_name}  # Preços de cartas específicas
```

### **Características das APIs**

#### **Magic: The Gathering API**
- ✅ **Gratuita**: Sem necessidade de API key
- ✅ **Completa**: Dados de todas as cartas já lançadas
- ✅ **Atualizada**: Mantida pela comunidade
- ✅ **Estável**: Alta disponibilidade
- ✅ **Bem documentada**: Exemplos e guias disponíveis

#### **Scryfall API**
- ✅ **Gratuita**: Sem necessidade de API key
- ✅ **Preços em Tempo Real**: Dados de mercado atualizados
- ✅ **Múltiplas Moedas**: USD, EUR e TIX (MTGO)
- ✅ **Alta Performance**: Otimizada para consultas rápidas
- ✅ **Rate Limiting Inteligente**: Respeitado automaticamente
- ✅ **Dados de Mercado**: Especializada em preços e valores

### **Exemplo de Resposta - Magic: The Gathering API**
```json
{
  "cards": [
    {
      "name": "Black Lotus",
      "manaCost": "{0}",
      "cmc": 0,
      "colors": [],
      "type": "Artifact",
      "rarity": "Rare",
      "set": "LEA",
      "setName": "Limited Edition Alpha",
      "text": "{T}, Sacrifice Black Lotus: Add three mana of any one color.",
      "artist": "Christopher Rush",
      "number": "232",
      "power": null,
      "toughness": null,
      "layout": "normal",
      "multiverseid": 3,
      "imageUrl": "http://gatherer.wizards.com/Handlers/Image.ashx?multiverseid=3&type=card",
      "id": "b7c199d8-7c42-4c0f-8c1a-0c3b0c3b0c3b"
    }
  ]
}
```

### **Exemplo de Resposta - Scryfall API**
```json
{
  "name": "Black Lotus",
  "set": "lea",
  "rarity": "rare",
  "prices": {
    "usd": "25000.00",
    "usd_foil": "50000.00",
    "eur": "22000.00",
    "eur_foil": "45000.00",
    "tix": null
  },
  "scryfall_uri": "https://scryfall.com/card/lea/232/black-lotus",
  "image_uris": {
    "normal": "https://c1.scryfall.com/file/scryfall-images/normal/front/0/9/09b7c199d8-7c42-4c0f-8c1a-0c3b0c3b0c3b.jpg"
  }
}
```

## 🎯 Objetivo

Ingerir dados completos e atualizados da API oficial do Magic: The Gathering e da API Scryfall, garantindo:
- **Dados brutos**: Preservação da estrutura original da API
- **Formato Parquet**: Otimizado para consultas analíticas
- **Particionamento**: Por ano e mês para performance
- **Incremental**: Evita reprocessamento desnecessário
- **Tolerância a falhas**: Retry automático e tratamento de erros

## 📁 Estrutura dos Notebooks

### 🃏 `cards.ipynb`
- **API**: MTG API
- **Endpoint**: `/cards`
- **Tipo**: Dados paginados com filtro temporal
- **Características**: 
  - Filtro de 5 anos para otimização
  - Paginação automática
  - Schema complexo com múltiplos campos
  - Tratamento de arrays JSON

### 🎴 `sets.ipynb`
- **API**: MTG API
- **Endpoint**: `/sets`
- **Tipo**: Dados paginados com filtro temporal
- **Características**:
  - Filtro de 5 anos
  - Informações de expansões/coleções
  - Metadados de lançamento

### 🏷️ `types.ipynb`
- **API**: MTG API
- **Endpoint**: `/types`
- **Tipo**: Tabela de referência (sem filtro temporal)
- **Características**:
  - Tipos de cartas (Creature, Instant, Sorcery, etc.)
  - Dados estáticos de referência

### 🏷️ `supertypes.ipynb`
- **API**: MTG API
- **Endpoint**: `/supertypes`
- **Tipo**: Tabela de referência (sem filtro temporal)
- **Características**:
  - Super tipos (Basic, Legendary, Snow, etc.)
  - Dados estáticos de referência

### 🏷️ `subtypes.ipynb`
- **API**: MTG API
- **Endpoint**: `/subtypes`
- **Tipo**: Tabela de referência (sem filtro temporal)
- **Características**:
  - Sub tipos (Human, Warrior, Equipment, etc.)
  - Dados estáticos de referência

### 🎮 `formats.ipynb`
- **API**: MTG API
- **Endpoint**: `/formats`
- **Tipo**: Tabela de referência (sem filtro temporal)
- **Características**:
  - Formatos de jogo (Standard, Modern, Legacy, etc.)
  - Dados estáticos de referência

### 💰 `card_prices.ipynb`
- **API**: Scryfall API
- **Endpoint**: `/cards/named?exact={card_name}`
- **Tipo**: Dados de preços baseados em cards existentes
- **Características**:
  - Preços em USD, EUR e TIX
  - Processamento baseado em arquivos de cards existentes
  - Execução paralela com ThreadPoolExecutor
  - Rate limiting respeitado (7 workers simultâneos)
  - Dependência: Requer arquivos de cards já ingeridos

## ⚙️ Configurações Necessárias

### Segredos do Databricks
Configure os seguintes segredos no scope `mtg-pipeline`:

```python
# API Configuration
api_base_url          # URL base da API MTG
scryfall_api_url      # URL base da Scryfall API
batch_size           # Tamanho do lote (padrão: 100)
max_retries          # Máximo de tentativas (padrão: 3)

# S3 Configuration
s3_bucket            # Bucket S3 para armazenamento
s3_prefix            # Prefixo do caminho S3
s3_stage_prefix      # Prefixo específico para staging

# Temporal Configuration (cards, sets e card_prices)
years_back           # Anos para trás no filtro temporal (padrão: 5)
```

### Estrutura de Pastas S3
```
s3://{bucket}/{prefix}/
├── {year}_{month}_{day}_cards.parquet   # dia da execução no nome (AUD-04)
├── {year}_{month}_card_prices.parquet
├── {year}_{month}_{day}_sets.parquet    # dia da execução no nome (AUD-04)
├── {year}_{month}_types.parquet
├── {year}_{month}_supertypes.parquet
├── {year}_{month}_subtypes.parquet
└── {year}_{month}_formats.parquet
```

## 🔄 Fluxo de Execução

### 1. **Configuração Inicial**
- Importação de bibliotecas
- Configuração de segredos
- Setup do Spark e S3

### 2. **Funções Utilitárias**
- Compartilhadas via `ingestion_utils.py` (`%run ./ingestion_utils`): `get_secret()`, `setup_s3_storage()`,
  `save_to_parquet()`
- issue #129: `cards.ipynb`/`sets.ipynb`/`card_prices.ipynb` usam só a Scryfall API — sem mais chamadas
  à magicthegathering.io (`make_api_request()`/`get_filtered_set_codes()` foram removidas)
- `clean_sets_data()`: limpeza específica de schema complexo, mantida em `sets.ipynb`
- issue #129: `cards.ipynb` não tem mais `clean_cards_data()` — a landing zone captura o dado bruto
  da Scryfall (via `_to_card_record`) e só filtra por coleção, sem tratamento/coerção de tipo adicional

### 3. **Ingestão**
- Coleta de dados da API
- Limpeza e estruturação
- Salvamento em Parquet
- Verificação de duplicatas

## 📊 Características dos Dados

### Dados Temporais (Cards e Sets)
- **Filtro**: Últimos `years_back` anos (secret, padrão 5), lido de forma consistente por cards/sets/card_prices
- **Por coleção**: `cards.ipynb` busca a lista de sets dentro da janela na Scryfall (`fetch_valid_set_codes`,
  `/sets`) e filtra o catálogo inteiro da Bulk Data API em memória (issue #129)
- **Particionamento**: Ano/Mês, com o dia da execução no nome do arquivo (AUD-04: evita pular o mês inteiro
  a partir da 2ª execução)
- **Incremental**: Evita reprocessar o mesmo dia duas vezes

### Dados de Referência (Types, SuperTypes, SubTypes, Formats)
- **Completo**: Sem filtro temporal
- **Estático**: Raramente alterado
- **Particionamento**: Ano/Mês atual
- **Único**: Sem paginação

### Dados de Preços (Card Prices)
- **Dependente**: Baseado em arquivos de cards existentes
- **Dinâmico**: Preços atualizados da Scryfall API
- **Particionamento**: Ano/Mês correspondente aos cards
- **Paralelo**: Processamento com ThreadPoolExecutor (7 workers)
- **Rate Limiting**: Respeitado para não sobrecarregar a API

## 🛡️ Tratamento de Erros

### Rate Limiting
- Detecção automática (HTTP 429)
- Backoff exponencial
- Aguardar até 60 segundos

### Timeouts
- Timeout de 30 segundos por requisição
- Retry automático
- Logs detalhados

### Falhas de Rede
- Retry com backoff
- Logs de erro estruturados
- Continuação do processamento

## 📈 Monitoramento

### Logs Estruturados
- Status de cada requisição
- Contagem de registros processados
- Tempo de execução
- Erros e warnings

### Métricas
- Registros processados por tabela
- Arquivos Parquet criados
- Tempo total de execução
- Taxa de sucesso

## 🚀 Como Executar

### Execução Individual
```python
# Executar notebook específico
cards.ipynb
sets.ipynb
types.ipynb
# etc...
```

### Execução Sequencial
```python
# Executar todos os notebooks em ordem
types.ipynb
supertypes.ipynb
subtypes.ipynb
formats.ipynb
sets.ipynb
cards.ipynb
card_prices.ipynb  # Deve ser executado após cards.ipynb
```

## ⚠️ Escopo da Ingestão

- **Cards**: por coleção, dentro da janela `years_back` — sem cap fixo de páginas (o cap de
  100 páginas "para demonstração" foi removido; cada coleção pagina até esgotar)
- **Sets**: filtrados por `releaseDate >= cutoff`, mesma janela `years_back`
- **Card prices**: cutoff também lido de `years_back` (antes era um `5` hardcoded, dessincronizado)
- Para mudar a janela (ex.: 2 anos), basta alterar o secret `years_back` no scope `mtg-pipeline` —
  os três notebooks já leem o mesmo valor

## 📋 Checklist de Execução

- [ ] Segredos configurados no Databricks
- [ ] Permissões S3 verificadas
- [ ] Cluster Spark disponível
- [ ] API MTG acessível
- [ ] Espaço em disco suficiente
- [ ] Limitações de demonstração compreendidas

## 🔗 Próximos Passos

Após a ingestão, os dados estarão disponíveis para:
1. **Camada Bronze**: Processamento e limpeza adicional
2. **Camada Silver**: Transformações e enriquecimento
3. **Camada Gold**: Modelos de dados finais

## 🏗️ Engenharia de Dados

### 🎯 Princípios da Camada de Ingestão

#### **1. Dados Brutos (Raw Data)**
- ✅ Preservação total da estrutura original da API
- ✅ Sem transformações ou limpezas significativas
- ✅ Metadados de origem mantidos
- ✅ Timestamp de ingestão para rastreabilidade

#### **2. Idempotência**
- ✅ Execução múltipla não duplica dados
- ✅ Verificação de arquivos existentes
- ✅ Controle de particionamento temporal
- ✅ Logs de reprocessamento

#### **3. Tolerância a Falhas**
- ✅ Retry automático com backoff exponencial
- ✅ Rate limiting inteligente
- ✅ Timeout configurável
- ✅ Logs estruturados para debugging

#### **4. Performance**
- ✅ Particionamento por ano/mês
- ✅ Formato Parquet otimizado
- ✅ Processamento em lotes
- ✅ Filtro temporal para dados grandes

### 📐 Regras da Camada

#### **Regra #1: Sem Transformações Complexas**
```python
# ✅ CORRETO - Dados brutos preservados
{
    "name": "Black Lotus",
    "manaCost": "{0}",
    "type": "Artifact",
    "rarity": "Rare"
}

# ❌ INCORRETO - Transformações na ingestão
{
    "card_name": "Black Lotus",  # Campo renomeado
    "mana_cost_parsed": 0,       # Valor calculado
    "is_rare": True              # Lógica aplicada
}
```

#### **Regra #2: Metadados Obrigatórios**
```python
# Campos adicionados em todos os registros
{
    "ingestion_timestamp": "2024-01-15T10:30:00Z",
    "source": "mtg_api",
    "endpoint": "cards",
    "partition_year": 2024,
    "partition_month": 1
}
```

#### **Regra #3: Nomenclatura Padrão**
```python
# Arquivos Parquet
"{year}_{month:02d}_{table_name}.parquet"

# Exemplo: 2024_01_cards.parquet
```

#### **Regra #4: Schema Explícito**
```python
# Schema definido explicitamente para cada tabela
schema_fields = [
    StructField("name", StringType(), True),
    StructField("manaCost", StringType(), True),
    # ... outros campos
]
```

#### **Regra #5: Logs Estruturados**
```python
# Padrão de logging
print(f"{table_name}: {count} registros processados")
print(f"Arquivo {file_name} criado com sucesso")
print(f"Erro na requisição: {error_message}")
```

## 🔍 Data Quality

### 🎯 Validações Implementadas

#### **1. Limpeza de Dados**
Cada tabela possui uma função específica de limpeza para lidar com campos complexos e garantir a estruturação adequada dos dados para a camada Bronze:

```python
# Cards - Conversão de tipos e arrays JSON
def clean_cards_data(data):
    # Campos simples → String
    # Arrays → JSON string
    # Tipos específicos (cmc → Float, multiverseid → Integer)

# Sets - Explosão de campo booster
def clean_sets_data(data):
    # Campo booster complexo → múltiplas colunas
    # booster_0, booster_1, booster_2, etc.

# Types/SuperTypes/SubTypes/Formats - Estruturação simples
# (função genérica em ingestion_utils.py, usada pelos 4 notebooks via ingest_reference_table)
def clean_simple_list(data, field_name):
    # Lista de strings → Lista de dicionários
    # {"type_name": "Creature"}
```

#### **2. Schema Validation**
Schemas explícitos para cada tabela:

```python
# Cards - 25 campos com tipos específicos
schema_fields = [
    StructField("name", StringType(), True),
    StructField("cmc", FloatType(), True),
    StructField("multiverseid", IntegerType(), True),
    # ... outros campos
]

# Sets - 13 campos + 20 colunas booster
# Types/SuperTypes/SubTypes/Formats - 1 campo cada
```

#### **3. Controle de Qualidade**
- ✅ **Verificação de dados vazios**: `if not data: return None`
- ✅ **Controle de duplicatas**: Verificação de arquivos existentes
- ✅ **Tratamento de erros**: Try/catch em conversões
- ✅ **Logs estruturados**: Contagem e status de processamento

### 📊 Métricas Coletadas

#### **Logs de Processamento**
```python
print(f"Dados obtidos: {len(table_data)} registros")
print(f"Dados limpos: {len(cleaned_data)} registros")
print(f"Registros processados: {count}")
print(f"Arquivo criado: {file_name}")
```

#### **Verificações de Integridade**
```python
# Evita reprocessamento
if len(existing_files) > 0:
    print(f"Arquivo já existe - pulando")

# Validação de dados
if not data:
    print(f"Nenhum dado para salvar")
```

### 🛡️ Tratamento de Erros

#### **API Errors**
- **Rate Limiting**: HTTP 429 → Backoff exponencial
- **Timeouts**: 30s → Retry automático
- **JSON Decode**: Tratamento de respostas inválidas

#### **Data Errors**
- **Campos faltantes**: Conversão para `None`
- **Tipos inválidos**: Conversão segura para string
- **Arrays complexos**: Conversão para JSON string

### 🎯 Boas Práticas

- ✅ **Schema explícito**: Validação automática do Spark
- ✅ **Idempotência**: Execução múltipla sem duplicação
- ✅ **Logs detalhados**: Rastreabilidade completa
- ✅ **Preservação de dados**: Sem transformações complexas

## 🎴 Galeria Visual - Magic: The Gathering

### 🃏 Tipos de Cartas
```
🏷️ Creature    ⚡ Instant    🔮 Sorcery    🛡️ Artifact
🌿 Enchantment 🏰 Land       🎭 Planeswalker
```

### 🌈 Cores de Mana
```
⚪ White (Branco)    🔵 Blue (Azul)     ⚫ Black (Preto)
🔴 Red (Vermelho)   🟢 Green (Verde)   🌈 Colorless (Incolor)
```

### ⭐ Raridades
```
🟢 Common (Comum)     🔵 Uncommon (Incomum)
🟣 Rare (Rara)        🟡 Mythic (Mítica)
```

### 🎮 Formatos de Jogo
```
🏆 Standard    🗡️ Modern    👑 Legacy    🏛️ Vintage
🎪 Commander   🎲 Limited   🎯 Constructed
```

### 📦 Expansões Populares
```
🌍 Core Set    🏰 Dominaria  🐉 Dragons    🌙 Innistrad
⚡ Ravnica     🏔️ Zendikar   🌊 Ixalan     🎭 Theros
```

### 🎨 Elementos Visuais
```
✨ Mana Cost    🎯 Power/Toughness    🏷️ Type Line
📝 Text Box     🎨 Artist Credit     🔢 Collector Number
```

## 📞 Suporte

Para dúvidas ou problemas:
- Verificar logs de execução
- Consultar documentação da API MTG
- Revisar configurações de segredos
- Verificar conectividade de rede
- Consultar este README para referência 📚 
