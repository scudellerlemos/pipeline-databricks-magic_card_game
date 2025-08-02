<div align="center">
<!-- Imagem ilustrativa da tabela (adicione o link abaixo) -->
<img src="https://i.postimg.cc/jjvN23QK/remote-image.png" alt="Imagem de documentação" width="600"/>
</div>
<br>

# TB_METRICAS_PERFORMANCE_INVESTIMENTOS

## 1. Nome da Tabela e Camada
- **Tabela:** TB_METRICAS_PERFORMANCE_INVESTIMENTOS
- **Camada:** Gold

## 2. Descrição Completa
Tabela Gold contendo métricas de performance e ROI para análise de investimentos em cartas Magic: The Gathering. Esta tabela fornece KPIs financeiros, indicadores de risco, métricas de liquidez e análises de retorno para suportar decisões de investimento estratégico no mercado de cartas.

## 3. Origem dos Dados
- **Fonte:** TB_FATO_SILVER_CARDS, TB_FATO_SILVER_CARDPRICES (camada Silver)
- **Arquivo de staging:** s3:/<bucket>/magic_the_gathering/gold/TB_METRICAS_PERFORMANCE_INVESTIMENTOS

## 4. Linhagem dos Dados
- **Fluxo:**  
  1. MTG API (endpoint: /cards, /prices)  
  2. Ingestão para S3 (staging)  
  3. Processamento Bronze (`src/02 - Bronze/Dev/`)  
  4. Transformação Silver (`src/03 - Silver/Dev/`)  
  5. Análise Gold (`src/04 - Gold/TB_METRICAS_PERFORMANCE_INVESTIMENTOS.ipynb`)  
  6. Escrita na tabela Delta: TB_METRICAS_PERFORMANCE_INVESTIMENTOS (Unity Catalog)

## 5. Schema Detalhado
| Nome da Coluna   | Tipo    | Descrição                        | Obrigatória | Chave | Regra de Preenchimento         |
|------------------|---------|----------------------------------|-------------|-------|-------------------------------|
| DATA_REF         | date    | Data de referência (particionamento) | Sim     | Sim   | make_date(RELEASE_YEAR, RELEASE_MONTH, 1) |
| NME_CARD         | string  | Nome da carta                    | Sim         | Sim   | Dados originais da Silver      |
| NME_SET          | string  | Nome do conjunto                 | Sim         | Não   | Dados originais da Silver      |
| NME_CARD_TYPE    | string  | Tipo da carta                    | Sim         | Não   | Dados originais da Silver      |
| NME_RARITY       | string  | Raridade da carta                | Sim         | Não   | Dados originais da Silver      |
| VALOR_ATUAL      | decimal(10,2) | Valor atual da carta         | Sim         | Não   | sum(VLR_USD) por carta         |
| VALOR_ANTERIOR   | decimal(10,2) | Valor anterior da carta      | Não         | Não   | lag(VALOR_ATUAL) por carta     |
| VARIACAO_PERC_VALOR | decimal(10,4) | Variação percentual do valor | Não | Não | (VALOR_ATUAL - VALOR_ANTERIOR) / VALOR_ANTERIOR |
| ROI_7D           | decimal(10,4) | Retorno sobre investimento 7 dias | Não | Não | Cálculo de ROI em 7 dias       |
| ROI_30D          | decimal(10,4) | Retorno sobre investimento 30 dias | Não | Não | Cálculo de ROI em 30 dias      |
| VOLATILIDADE_7D  | decimal(10,4) | Volatilidade em 7 dias        | Não         | Não   | Desvio padrão dos retornos     |
| VOLATILIDADE_30D | decimal(10,4) | Volatilidade em 30 dias       | Não         | Não   | Desvio padrão dos retornos     |
| LIQUIDEZ_INDICATOR | string | Indicador de liquidez         | Sim         | Não   | Categorização baseada em volume |
| RISCO_CATEGORIA  | string  | Categoria de risco              | Sim         | Não   | Categorização baseada em volatilidade |
| RANK_PERFORMANCE | int     | Ranking de performance           | Não         | Não   | row_number() por DATA_REF      |

## 6. Regras de Implementação
- **Filtro temporal:** Baseado em RELEASE_YEAR e RELEASE_MONTH das cartas
- **Deduplicação:** Por DATA_REF + NME_CARD + NME_SET + NME_CARD_TYPE + NME_RARITY
- **Merge incremental:** Atualização inteligente de dados
- **Particionamento:** Por DATA_REF, NME_SET
- **Arredondamento:** 2 casas decimais para valores, 4 para percentuais

## 7. Transformações Aplicadas
| Transformação | Descrição |
|---------------|-----------|
| Cálculo de ROI | Retorno sobre investimento em diferentes períodos (7D, 30D) |
| Análise de Volatilidade | Cálculo de volatilidade usando desvio padrão dos retornos |
| Indicadores de Liquidez | Categorização baseada em volume de negociação |
| Categorização de Risco | Classificação automática baseada em volatilidade |
| Rankings | Ranking de performance por DATA_REF |
| Análise Temporal | Comparação de valores usando window functions |

## 7.1 Regras de Negócio Aplicadas
| Regra de Negócio | Descrição |
|------------------|-----------|
| DATA_REF | Criada a partir de RELEASE_YEAR e RELEASE_MONTH usando make_date() |
| ROI 7D | Cálculo de retorno sobre investimento em 7 dias |
| ROI 30D | Cálculo de retorno sobre investimento em 30 dias |
| Volatilidade | Desvio padrão dos retornos em janelas móveis |
| Liquidez | Categorização: Alta, Média, Baixa baseada em volume |
| Risco | Categorização: Baixo, Médio, Alto baseada em volatilidade |
| Rankings | Ranking por DATA_REF baseado na performance |
| Particionamento | Por DATA_REF, NME_SET |
| Arredondamento | 2 casas para valores monetários, 4 para percentuais |

## 7.2 Colunas Criadas na Gold
| Coluna | Descrição |
|--------|-----------|
| DATA_REF | Data de referência para análise temporal |
| VALOR_ATUAL | Valor atual da carta no mercado |
| VALOR_ANTERIOR | Valor anterior para comparação |
| VARIACAO_PERC_VALOR | Variação percentual do valor |
| ROI_7D | Retorno sobre investimento em 7 dias |
| ROI_30D | Retorno sobre investimento em 30 dias |
| VOLATILIDADE_7D | Volatilidade calculada em 7 dias |
| VOLATILIDADE_30D | Volatilidade calculada em 30 dias |
| LIQUIDEZ_INDICATOR | Indicador de liquidez da carta |
| RISCO_CATEGORIA | Categoria de risco baseada em volatilidade |
| RANK_PERFORMANCE | Ranking de performance por período |

## 8. Particionamento
- **Colunas:** DATA_REF, NME_SET
- **Lógica:** Otimizado para consultas de performance por período e set

## 9. Histórico de Alterações
| Data       | Responsável | Alteração                |
|------------|-------------|--------------------------|
| 2025-08-02 | Felipe      | Criação inicial          |

## 10. Observações
- Pipeline modularizado usando gold_utils.py
- Configuração via Unity Catalog (magic_the_gathering.gold)
- Arredondamento: 2 casas decimais para valores monetários, 4 para percentuais
- Particionamento otimizado para consultas de performance
- Categorizações automáticas para análise de risco
- Merge incremental baseado em chaves compostas
- Window functions com partições adequadas para performance
- Métricas financeiras validadas para tomada de decisão 