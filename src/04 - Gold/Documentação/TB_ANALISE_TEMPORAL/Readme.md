<div align="center">
<!-- Imagem ilustrativa da tabela (adicione o link abaixo) -->
<img src="https://i.postimg.cc/jjvN23QK/remote-image.png" alt="Imagem de documentação" width="600"/>
</div>
<br>

# TB_ANALISE_TEMPORAL

## 1. Nome da Tabela e Camada
- **Tabela:** TB_ANALISE_TEMPORAL
- **Camada:** Gold

## 2. Descrição Completa
Tabela Gold contendo análise de padrões temporais, sazonalidade e tendências de mercado para cartas Magic: The Gathering. Esta tabela fornece insights sobre comportamento sazonal, tendências de longo prazo, padrões cíclicos e indicadores de momentum para suportar estratégias de timing de investimento e análise de mercado.

## 3. Origem dos Dados
- **Fonte:** TB_FATO_SILVER_CARDS, TB_FATO_SILVER_CARDPRICES (camada Silver)
- **Arquivo de staging:** s3:/<bucket>/magic_the_gathering/gold/TB_ANALISE_TEMPORAL

## 4. Linhagem dos Dados
- **Fluxo:**  
  1. MTG API (endpoint: /cards, /prices)  
  2. Ingestão para S3 (staging)  
  3. Processamento Bronze (`src/02 - Bronze/Dev/`)  
  4. Transformação Silver (`src/03 - Silver/Dev/`)  
  5. Análise Gold (`src/04 - Gold/TB_ANALISE_TEMPORAL.ipynb`)  
  6. Escrita na tabela Delta: TB_ANALISE_TEMPORAL (Unity Catalog)

## 5. Schema Detalhado
| Nome da Coluna   | Tipo    | Descrição                        | Obrigatória | Chave | Regra de Preenchimento         |
|------------------|---------|----------------------------------|-------------|-------|-------------------------------|
| DATA_REF         | date    | Data de referência (particionamento) | Sim     | Sim   | make_date(RELEASE_YEAR, RELEASE_MONTH, 1) |
| NME_CARD         | string  | Nome da carta                    | Sim         | Sim   | Dados originais da Silver      |
| NME_SET          | string  | Nome do conjunto                 | Sim         | Não   | Dados originais da Silver      |
| ANO              | int     | Ano de referência                | Sim         | Não   | year(DATA_REF)                 |
| MES              | int     | Mês de referência                | Sim         | Não   | month(DATA_REF)                |
| SEMANA_ANO       | int     | Semana do ano                    | Sim         | Não   | weekofyear(DATA_REF)           |
| TRIMESTRE        | int     | Trimestre do ano                 | Sim         | Não   | quarter(DATA_REF)              |
| DIA_ANO          | int     | Dia do ano                       | Sim         | Não   | dayofyear(DATA_REF)            |
| NOME_MES         | string  | Nome do mês                      | Sim         | Não   | monthname(DATA_REF)            |
| VALOR_ATUAL      | decimal(10,2) | Valor atual da carta         | Sim         | Não   | sum(VLR_USD) por carta         |
| VALOR_ANTERIOR   | decimal(10,2) | Valor anterior da carta      | Não         | Não   | lag(VALOR_ATUAL) por carta     |
| VARIACAO_PERC_VALOR | decimal(10,4) | Variação percentual do valor | Não | Não | (VALOR_ATUAL - VALOR_ANTERIOR) / VALOR_ANTERIOR |
| MOMENTUM_7D      | decimal(10,4) | Momentum de 7 dias            | Não         | Não   | Média móvel de 7 dias          |
| MOMENTUM_30D     | decimal(10,4) | Momentum de 30 dias           | Não         | Não   | Média móvel de 30 dias         |
| TENDENCIA_LONGO_PRAZO | string | Tendência de longo prazo     | Sim         | Não   | Categorização baseada em tendência |
| SAZONALIDADE_MENSAL | string | Padrão sazonal mensal        | Sim         | Não   | Categorização baseada em sazonalidade |
| RANK_TEMPORAL    | int     | Ranking temporal                 | Não         | Não   | row_number() por DATA_REF      |

## 6. Regras de Implementação
- **Filtro temporal:** Baseado em RELEASE_YEAR e RELEASE_MONTH das cartas
- **Deduplicação:** Por DATA_REF + NME_CARD + NME_SET
- **Merge incremental:** Atualização inteligente de dados
- **Particionamento:** Por DATA_REF, NME_SET
- **Arredondamento:** 2 casas decimais para valores, 4 para percentuais

## 7. Transformações Aplicadas
| Transformação | Descrição |
|---------------|-----------|
| Extração Temporal | Criação de colunas de data (ano, mês, semana, trimestre) |
| Análise de Momentum | Cálculo de médias móveis para diferentes períodos |
| Detecção de Tendências | Análise de tendências de longo prazo |
| Análise Sazonal | Identificação de padrões sazonais mensais |
| Rankings Temporais | Ranking baseado em performance temporal |
| Análise de Variação | Comparação temporal de valores |

## 7.1 Regras de Negócio Aplicadas
| Regra de Negócio | Descrição |
|------------------|-----------|
| DATA_REF | Criada a partir de RELEASE_YEAR e RELEASE_MONTH usando make_date() |
| Extração Temporal | year(), month(), weekofyear(), quarter(), dayofyear() |
| Momentum 7D | Média móvel de 7 dias dos valores |
| Momentum 30D | Média móvel de 30 dias dos valores |
| Tendência Longo Prazo | Categorização: Crescente, Decrescente, Estável |
| Sazonalidade Mensal | Categorização: Alta, Média, Baixa sazonalidade |
| Rankings | Ranking por DATA_REF baseado na performance temporal |
| Particionamento | Por DATA_REF, NME_SET |
| Arredondamento | 2 casas para valores monetários, 4 para percentuais |

## 7.2 Colunas Criadas na Gold
| Coluna | Descrição |
|--------|-----------|
| DATA_REF | Data de referência para análise temporal |
| ANO | Ano extraído da data de referência |
| MES | Mês extraído da data de referência |
| SEMANA_ANO | Semana do ano extraída da data |
| TRIMESTRE | Trimestre do ano extraído da data |
| DIA_ANO | Dia do ano extraído da data |
| NOME_MES | Nome do mês em texto |
| VALOR_ATUAL | Valor atual da carta no mercado |
| VALOR_ANTERIOR | Valor anterior para comparação |
| VARIACAO_PERC_VALOR | Variação percentual do valor |
| MOMENTUM_7D | Momentum calculado em 7 dias |
| MOMENTUM_30D | Momentum calculado em 30 dias |
| TENDENCIA_LONGO_PRAZO | Categorização da tendência de longo prazo |
| SAZONALIDADE_MENSAL | Categorização da sazonalidade mensal |
| RANK_TEMPORAL | Ranking temporal por período |

## 8. Particionamento
- **Colunas:** DATA_REF, NME_SET
- **Lógica:** Otimizado para consultas temporais por período e set

## 9. Histórico de Alterações
| Data       | Responsável | Alteração                |
|------------|-------------|--------------------------|
| 2025-08-02 | Felipe      | Criação inicial          |

## 10. Observações
- Pipeline modularizado usando gold_utils.py
- Configuração via Unity Catalog (magic_the_gathering.gold)
- Arredondamento: 2 casas decimais para valores monetários, 4 para percentuais
- Particionamento otimizado para consultas temporais
- Categorizações automáticas para análise de tendências
- Merge incremental baseado em chaves compostas
- Window functions com partições adequadas para performance
- Análise temporal validadas para estratégias de timing 