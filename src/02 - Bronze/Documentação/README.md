# 📚 Documentação da Camada Bronze
<br>
<br>
<div align="center">
<!-- Imagem ilustrativa da tabela (adicione o link abaixo) -->
<img src="https://i.postimg.cc/1t61LYFb/doc.png" alt="Imagem de documentação" width="400"/>
</div>
<br>


## 📋 Visão Geral

Esta pasta contém a **documentação completa** de todas as tabelas da camada Bronze do pipeline de dados do Magic: The Gathering. Cada tabela possui sua documentação detalhada com schema, regras de implementação, particionamento e linhagem de dados.

## 🎯 Objetivo

Fornecer documentação executiva e técnica de todas as tabelas Bronze, permitindo:
- **Visão geral rápida** das tabelas disponíveis
- **Acesso direto** à documentação detalhada de cada tabela
- **Entendimento da arquitetura** de dados da camada Bronze
- **Referência técnica** para desenvolvimento e manutenção

## 🃏 Tabelas Documentadas

### 🎴 **TB_BRONZE_CARDS** - Cartas do Magic
- **Descrição**: Dados brutos de cartas do Magic: The Gathering
- **Chave Primária**: `ID_CARD`
- **Particionamento**: `RELEASE_YEAR`, `RELEASE_MONTH`
- **Filtro Temporal**: Últimos 5 anos
- **Schema**: 28 colunas (dados complexos)
- **Características**: 
  - Dados de criaturas, magias, artefatos
  - Informações de mana, tipos, raridade
  - URLs de imagens e metadados
- **[📖 Ver Documentação Completa](./TB_BRONZE_CARDS/README.md)**

### 📦 **TB_BRONZE_SETS** - Coleções
- **Descrição**: Dados brutos de sets (coleções) do Magic
- **Chave Primária**: `COD_SET`
- **Particionamento**: `RELEASE_YEAR`, `RELEASE_MONTH`
- **Filtro Temporal**: Últimos 5 anos
- **Schema**: 45 colunas (dados expandidos)
- **Características**:
  - Informações de lançamento e tipo
  - Configuração de boosters (20 slots)
  - URLs de mercado e APIs externas
- **[📖 Ver Documentação Completa](./TB_BRONZE_SETS/README.md)**

### 🏷️ **TB_BRONZE_TYPES** - Tipos de Cartas
- **Descrição**: Dados de referência de tipos de cartas
- **Chave Primária**: `NME_TYPE`
- **Particionamento**: `INGESTION_YEAR`, `INGESTION_MONTH`
- **Filtro Temporal**: Não aplicado (dados de referência)
- **Schema**: 8 colunas (dados simples)
- **Características**:
  - Dados estáticos de referência
  - Tipos como "Criatura", "Mágica Instantanea", "Feitiço"
- **[📖 Ver Documentação Completa](./TB_BRONZE_TYPES/README.md)**

### ⭐ **TB_BRONZE_SUPERTYPES** - Supertipos de Cartas
- **Descrição**: Dados de referência de supertipos de cartas
- **Chave Primária**: `NME_SUPERTYPE`
- **Particionamento**: `INGESTION_YEAR`, `INGESTION_MONTH`
- **Filtro Temporal**: Não aplicado (dados de referência)
- **Schema**: 8 colunas (dados simples)
- **Características**:
  - Dados estáticos de referência
  - Supertipos como "Basico", "Lendária"
- **[📖 Ver Documentação Completa](./TB_BRONZE_SUPERTYPES/README.md)**

### 🔖 **TB_BRONZE_SUBTYPES** - Subtipos de Cartas
- **Descrição**: Dados de referência de subtipos de cartas
- **Chave Primária**: `NME_SUBTYPE`
- **Particionamento**: `INGESTION_YEAR`, `INGESTION_MONTH`
- **Filtro Temporal**: Não aplicado (dados de referência)
- **Schema**: 8 colunas (dados simples)
- **Características**:
  - Dados estáticos de referência
  - Subtipos como "Humano", "Dragão", "Equipamento"
- **[📖 Ver Documentação Completa](./TB_BRONZE_SUBTYPES/README.md)**

### 🎮 **TB_BRONZE_FORMATS** - Formatos de Jogo
- **Descrição**: Dados de referência de formatos de jogo
- **Chave Primária**: `NME_FORMAT`
- **Particionamento**: `INGESTION_YEAR`, `INGESTION_MONTH`
- **Filtro Temporal**: Não aplicado (dados de referência)
- **Schema**: 8 colunas (dados simples)
- **Características**:
  - Dados estáticos de referência
  - Formatos como "Standard", "Modern", "Commander"
- **[📖 Ver Documentação Completa](./TB_BRONZE_FORMATS/README.md)**

### 💰 **TB_BRONZE_CARDPRICES** - Preços de Cartas
- **Descrição**: Dados brutos de preços de cartas
- **Chave Primária**: `NME_CARD`
- **Particionamento**: `RELEASE_YEAR`, `RELEASE_MONTH`
- **Filtro Temporal**: Últimos 5 anos
- **Schema**: 28 colunas (dados de mercado)
- **Características**:
  - Preços em USD, EUR, TIX (normal e foil)
  - Dados de mercado (high, low, market)
  - Atualização incremental de preços
- **[📖 Ver Documentação Completa](./TB_BRONZE_CARD_PRICES/README.md)**

## 🔄 Categorização das Tabelas

### 📊 **Tabelas de Dados Principais** (Com Filtro Temporal)
| Tabela | Tipo de Dado | Particionamento | Filtro |
|--------|-------------|-----------------|---------|
| TB_BRONZE_CARDS | Cartas | RELEASE_YEAR/MONTH | 5 anos |
| TB_BRONZE_SETS | Coleções | RELEASE_YEAR/MONTH | 5 anos |
| TB_BRONZE_CARDPRICES | Preços | RELEASE_YEAR/MONTH | 5 anos |

### 🏷️ **Tabelas de Referência** (Sem Filtro Temporal)
| Tabela | Tipo de Dado | Particionamento | Característica |
|--------|-------------|-----------------|----------------|
| TB_BRONZE_TYPES | Tipos | INGESTION_YEAR/MONTH | Estático |
| TB_BRONZE_SUPERTYPES | Supertipos | INGESTION_YEAR/MONTH | Estático |
| TB_BRONZE_SUBTYPES | Subtipos | INGESTION_YEAR/MONTH | Estático |
| TB_BRONZE_FORMATS | Formatos | INGESTION_YEAR/MONTH | Estático |

## 🎴 **Flavor Text da Documentação**
*"Como um bibliotecário sábio organizando grimórios antigos, a documentação da camada Bronze preserva o conhecimento de cada tabela, permitindo que futuros magos da engenharia de dados encontrem rapidamente os segredos que buscam."*

## 📈 Estatísticas da Camada Bronze

### **Volume de Dados**
- **7 tabelas** documentadas
- **3 tabelas principais** com dados temporais
- **4 tabelas de referência** com dados estáticos
- **Total estimado**: ~150+ colunas padronizadas

### **Padrões de Nomenclatura**
- **NME_**: Nomes e identificadores
- **COD_**: Códigos e chaves
- **VLR_**: Valores monetários
- **DT_**: Datas e timestamps
- **FLG_**: Flags booleanos
- **URL_**: URLs e links
- **DESC_**: Descrições e textos

### **Estratégias de Particionamento**
- **Dados Temporais**: Particionamento por ano/mês de lançamento
- **Dados de Referência**: Particionamento por ano/mês de ingestão
- **Otimização**: Distribuição equilibrada de dados

## 🔍 Como Usar Esta Documentação

### **Para Desenvolvedores**
1. **Visão Geral**: Comece por este README para entender a arquitetura
2. **Documentação Específica**: Acesse a documentação da tabela desejada
3. **Schema Detalhado**: Consulte as colunas e tipos de dados
4. **Regras de Implementação**: Entenda filtros e deduplicação

### **Para Analistas de Dados**
1. **Linhagem de Dados**: Entenda a origem e transformações
2. **Particionamento**: Otimize consultas usando partições
3. **Regras de Negócio**: Compreenda filtros temporais aplicados
4. **Relacionamentos**: Identifique chaves para joins

### **Para Administradores**
1. **Configuração**: Verifique segredos e configurações necessárias
2. **Monitoramento**: Acompanhe logs e métricas de processamento
3. **Manutenção**: Entenda estratégias de merge e atualização
4. **Recuperação**: Conheça procedimentos de backup e restore

## 🛡️ Controle de Qualidade

### **Validações Implementadas**
- ✅ **Schema Padronizado**: Nomenclatura consistente
- ✅ **Particionamento Adequado**: Otimização de performance
- ✅ **Filtros Temporais**: Controle de volume de dados
- ✅ **Deduplicação**: Remoção de registros duplicados
- ✅ **Merge Incremental**: Atualização inteligente

### **Monitoramento**
- 📊 **Contagem de Registros**: Antes e depois do processamento
- 🔄 **Taxa de Atualização**: Frequência de mudanças
- ⚡ **Performance**: Tempo de processamento por tabela
- 🎯 **Qualidade**: Validação de integridade dos dados
