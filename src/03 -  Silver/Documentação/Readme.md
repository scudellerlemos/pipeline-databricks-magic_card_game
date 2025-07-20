# 📚 Documentação da Camada Silver
<br>
<br>
<div align="center">
<!-- Imagem ilustrativa da tabela (adicione o link abaixo) -->
<img src="https://i.postimg.cc/1t61LYFb/doc.png" alt="Imagem de documentação" width="400"/>
</div>
<br>

## 📋 Visão Geral

Esta pasta contém a **documentação completa** de todas as tabelas da camada Silver do pipeline de dados do Magic: The Gathering. Cada tabela possui sua documentação detalhada com schema, regras de negócio, enriquecimento, particionamento e linhagem de dados.

## 🎯 Objetivo

Fornecer documentação executiva e técnica de todas as tabelas Silver, permitindo:
- **Visão geral rápida** das tabelas disponíveis
- **Acesso direto** à documentação detalhada de cada tabela
- **Entendimento da arquitetura** de dados da camada Silver
- **Referência técnica** para desenvolvimento, análise e manutenção

## 🃏 Tabelas Documentadas

### 🎴 **TB_FATO_SILVER_CARDS** - Cartas do Magic
- **Descrição**: Dados limpos e enriquecidos de cartas do Magic: The Gathering
- **Chave Primária**: `ID_CARD`
- **Particionamento**: `ANO_PART`, `MES_PART`
- **Filtro Temporal**: Últimos 5 anos
- **Schema**: 30+ colunas (dados enriquecidos)
- **Características**: 
  - Enriquecimento de tipos, cores, categorias
  - Padronização de nomes, custos, textos
  - Deduplicação e merge incremental
- **[📖 Ver Documentação Completa](./TB_FATO_SILVER_CARDS/README.md)**

### 📦 **TB_REF_SILVER_SETS** - Coleções
- **Descrição**: Dados limpos e enriquecidos de sets (coleções) do Magic
- **Chave Primária**: `COD_SET`
- **Particionamento**: `RELEASE_YEAR`, `RELEASE_MONTH`
- **Filtro Temporal**: Últimos 5 anos
- **Schema**: 20+ colunas (dados expandidos)
- **Características**:
  - Metadados de lançamento
  - Padronização e enriquecimento
- **[📖 Ver Documentação Completa](./TB_REF_SILVER_SETS/README.md)**

### 🏷️ **TB_REF_SILVER_TYPES** - Tipos de Cartas
- **Descrição**: Dados de referência limpos de tipos de cartas
- **Chave Primária**: `NME_TYPE`
- **Particionamento**: `INGESTION_YEAR`, `INGESTION_MONTH`
- **Filtro Temporal**: Não aplicado (dados de referência)
- **Schema**: 5 colunas (dados simples)
- **Características**:
  - Dados estáticos de referência
  - Padronização e merge incremental
- **[📖 Ver Documentação Completa](./TB_REF_SILVER_TYPES/README.md)**

### ⭐ **TB_REF_SILVER_SUPERTYPES** - Supertipos de Cartas
- **Descrição**: Dados de referência limpos de supertipos de cartas
- **Chave Primária**: `NME_SUPERTYPE`
- **Particionamento**: `INGESTION_YEAR`, `INGESTION_MONTH`
- **Filtro Temporal**: Não aplicado (dados de referência)
- **Schema**: 5 colunas (dados simples)
- **Características**:
  - Dados estáticos de referência
  - Padronização e merge incremental
- **[📖 Ver Documentação Completa](./TB_REF_SILVER_SUPERTYPES/README.md)**

### 🔖 **TB_REF_SILVER_SUBTYPES** - Subtipos de Cartas
- **Descrição**: Dados de referência limpos de subtipos de cartas
- **Chave Primária**: `NME_SUBTYPE`
- **Particionamento**: `INGESTION_YEAR`, `INGESTION_MONTH`
- **Filtro Temporal**: Não aplicado (dados de referência)
- **Schema**: 5 colunas (dados simples)
- **Características**:
  - Dados estáticos de referência
  - Padronização e merge incremental
- **[📖 Ver Documentação Completa](./TB_REF_SILVER_SUBTYPES/README.md)**

### 🎮 **TB_REF_SILVER_FORMATS** - Formatos de Jogo
- **Descrição**: Dados de referência limpos de formatos de jogo
- **Chave Primária**: `NME_FORMAT`
- **Particionamento**: `INGESTION_YEAR`, `INGESTION_MONTH`
- **Filtro Temporal**: Não aplicado (dados de referência)
- **Schema**: 5 colunas (dados simples)
- **Características**:
  - Dados estáticos de referência
  - Padronização e merge incremental
- **[📖 Ver Documentação Completa](./TB_REF_SILVER_FORMATS/README.md)**

### 💰 **TB_FATO_SILVER_CARDPRICES** - Preços de Cartas
- **Descrição**: Dados limpos e enriquecidos de preços de cartas
- **Chave Primária**: `NME_CARD`
- **Particionamento**: `RELEASE_YEAR`, `RELEASE_MONTH`
- **Filtro Temporal**: Últimos 5 anos
- **Schema**: 20+ colunas (dados de mercado)
- **Características**:
  - Preços em USD, EUR, TIX (normal e foil)
  - Atualização incremental de preços
- **[📖 Ver Documentação Completa](./TB_FATO_SILVER_CARDPRICES/README.md)**

## 🔄 Categorização das Tabelas

### 📊 **Tabelas de Dados Principais** (Com Filtro Temporal)
| Tabela | Tipo de Dado | Particionamento | Filtro |
|--------|-------------|-----------------|---------|
| TB_FATO_SILVER_CARDS | Cartas | ANO_PART/MES_PART | 5 anos |
| TB_REF_SILVER_SETS | Coleções | RELEASE_YEAR/MONTH | 5 anos |
| TB_FATO_SILVER_CARDPRICES | Preços | RELEASE_YEAR/MONTH | 5 anos |

### 🏷️ **Tabelas de Referência** (Sem Filtro Temporal)
| Tabela | Tipo de Dado | Particionamento | Característica |
|--------|-------------|-----------------|----------------|
| TB_REF_SILVER_TYPES | Tipos | INGESTION_YEAR/MONTH | Estático |
| TB_REF_SILVER_SUPERTYPES | Supertipos | INGESTION_YEAR/MONTH | Estático |
| TB_REF_SILVER_SUBTYPES | Subtipos | INGESTION_YEAR/MONTH | Estático |
| TB_REF_SILVER_FORMATS | Formatos | INGESTION_YEAR/MONTH | Estático |

## 🎴 **Flavor Text da Documentação**
*"Como um bibliotecário arcano organizando grimórios lapidados, a documentação da camada Silver revela o valor oculto de cada tabela, guiando magos e engenheiros de dados na busca por insights refinados."*

## 📈 Estatísticas da Camada Silver

### **Volume de Dados**
- **7 tabelas** documentadas
- **3 tabelas principais** com dados temporais
- **4 tabelas de referência** com dados estáticos
- **Total estimado**: ~100+ colunas enriquecidas

### **Padrões de Nomenclatura**
- **NME_**: Nomes e identificadores
- **COD_**: Códigos e chaves
- **VLR_**: Valores monetários
- **DT_**: Datas e timestamps
- **FLG_**: Flags booleanos
- **URL_**: URLs e links
- **DESC_**: Descrições e textos

### **Estratégias de Particionamento**
- **Dados Temporais**: Particionamento por ano/mês de referência
- **Dados de Referência**: Particionamento por ano/mês de ingestão
- **Otimização**: Distribuição equilibrada de dados

## 🔍 Como Usar Esta Documentação

### **Para Desenvolvedores**
1. **Visão Geral**: Comece por este README para entender a arquitetura
2. **Documentação Específica**: Acesse a documentação da tabela desejada
3. **Schema Detalhado**: Consulte as colunas e tipos de dados
4. **Regras de Negócio**: Entenda enriquecimentos e deduplicação

### **Para Analistas de Dados**
1. **Linhagem de Dados**: Entenda a origem e transformações
2. **Particionamento**: Otimize consultas usando partições
3. **Regras de Negócio**: Compreenda enriquecimentos aplicados
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
- ✅ **Enriquecimento e Limpeza**: Dados prontos para análise
- ✅ **Deduplicação**: Remoção de registros duplicados
- ✅ **Merge Incremental**: Atualização inteligente

### **Monitoramento**
- 📊 **Contagem de Registros**: Antes e depois do processamento
- 🔄 **Taxa de Atualização**: Frequência de mudanças
- ⚡ **Performance**: Tempo de processamento por tabela
- 🎯 **Qualidade**: Validação de integridade dos dados 
