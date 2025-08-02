<div align="center">
<!-- Imagem ilustrativa da tabela (adicione o link abaixo) -->
<img src="https://i.postimg.cc/jjvN23QK/remote-image.png" alt="Imagem de documentação" width="600"/>
</div>
<br>

# TB_ANALISE_MERCADO_CARTAS_EXECUTIVO

## 1. Nome da Tabela e Camada
- **Tabela:** TB_ANALISE_MERCADO_CARTAS_EXECUTIVO
- **Camada:** Gold

## 2. Descrição Completa
Tabela Gold contendo análise executiva do mercado de cartas Magic: The Gathering, com agregações por segmento de mercado, métricas de valor, market share e categorizações para tomada de decisão estratégica. Esta tabela fornece insights prontos para consumo executivo sobre o comportamento do mercado de cartas.

## 3. Origem dos Dados
- **Fonte:** TB_FATO_SILVER_CARDS, TB_FATO_SILVER_CARDPRICES (camada Silver)
- **Arquivo de staging:** s3:/<bucket>/magic_the_gathering/gold/TB_ANALISE_MERCADO_CARTAS_EXECUTIVO

## 4. Linhagem dos Dados
- **Fluxo:**  
  1. MTG API (endpoint: /cards, /prices)  
  2. Ingestão para S3 (staging)  
  3. Processamento Bronze (`src/02 - Bronze/Dev/`)  
  4. Transformação Silver (`src/03 - Silver/Dev/`)  
  5. Análise Gold (`src/04 - Gold/TB_ANALISE_MERCADO_CARTAS_EXECUTIVO.ipynb`)  
  6. Escrita na tabela Delta: TB_ANALISE_MERCADO_CARTAS_EXECUTIVO (Unity Catalog)

## 5. Schema Detalhado
| Nome da Coluna   | Tipo    | Descrição                        | Obrigatória | Chave | Regra de Preenchimento         |
|------------------|---------|----------------------------------|-------------|-------|-------------------------------|
| DATA_REF         | date    | Data de referência (particionamento) | Sim     | Sim   | make_date(RELEASE_YEAR, RELEASE_MONTH, 1) |
| NME_CARD         | string  | Nome da carta                    | Sim         | Sim   | Dados originais da Silver      |
| NME_SET          | string  | Nome do conjunto                 | Sim         | Não   | Dados originais da Silver      |
| NME_CARD_TYPE    | string  | Tipo da carta                    | Sim         | Não   | Dados originais da Silver      |
| NME_RARITY       | string  | Raridade da carta                | Sim         | Não   | Dados originais da Silver      |
| NME_ARTIST       | string  | Artista da carta                 | Sim         | Não   | Dados originais da Silver      |
| VALOR_TOTAL_MERCADO | decimal(10,2) | Valor total do mercado | Sim    | Não   | sum(VLR_USD) por segmento      |
| QTD_CARTAS_ATIVAS | int     | Quantidade de cartas ativas      | Sim         | Não   | countDistinct(NME_CARD)        |
| VALOR_MEDIO_CARTA | decimal(10,2) | Valor médio por carta        | Sim         | Não   | avg(VLR_USD)                   |
| TICKET_MEDIANA   | decimal(10,2) | Valor mediano (ticket médio) | Sim     | Não   | percentile_approx(VLR_USD, 0.5) |
| MARKET_SHARE_SET | decimal(10,4) | Market share do set (%)      | Sim         | Não   | VALOR_TOTAL_MERCADO / sum(VALOR_TOTAL_MERCADO) |
| VARIACAO_PERC_VALOR | decimal(10,4) | Variação percentual do valor | Não | Não | (VALOR_ATUAL - VALOR_ANTERIOR) / VALOR_ANTERIOR |
| RANK_VALORIZACAO | int     | Ranking de valorização           | Não         | Não   | row_number() por DATA_REF      |
| CATEGORIA_VALOR_MERCADO | string | Categoria por valor | Sim    | Não   | Categorização baseada em VALOR_TOTAL_MERCADO |
| CATEGORIA_MARKET_SHARE | string | Categoria por market share | Sim | Não | Categorização baseada em MARKET_SHARE_SET |

## 6. Regras de Implementação
- **Filtro temporal:** Baseado em RELEASE_YEAR e RELEASE_MONTH das cartas
- **Deduplicação:** Por DATA_REF + NME_CARD + NME_SET + NME_CARD_TYPE + NME_RARITY + NME_ARTIST
- **Merge incremental:** Atualização inteligente de dados
- **Particionamento:** Por DATA_REF, NME_SET, NME_CARD_TYPE, NME_RARITY
- **Arredondamento:** 2 casas decimais para valores, 4 para percentuais

## 7. Transformações Aplicadas
| Transformação | Descrição |
|---------------|-----------|
| Agregação por Segmento | Agrupamento por DATA_REF, NME_SET, NME_CARD_TYPE, NME_RARITY, NME_ARTIST, NME_CARD |
| Cálculo de Market Share | Percentual do valor total do set em relação ao total do período |
| Análise de Valorização | Cálculo de variação percentual usando lag() por carta |
| Rankings | Ranking de valorização por DATA_REF |
| Categorização | Categorização automática por valor e market share |
| Arredondamento | Precisão controlada (2-4 casas decimais) |

## 7.1 Regras de Negócio Aplicadas
| Regra de Negócio | Descrição |
|------------------|-----------|
| DATA_REF | Criada a partir de RELEASE_YEAR e RELEASE_MONTH usando make_date() |
| Agregações | sum(), avg(), countDistinct(), percentile_approx() por segmento |
| Market Share | Cálculo percentual do valor do set em relação ao total do período |
| Valorização | Análise temporal usando lag() para comparar períodos consecutivos |
| Rankings | Ranking por DATA_REF baseado na variação percentual |
| Categorização por Valor | Alto (>1M), Médio (100K-1M), Baixo (10K-100K), Baixíssimo (<10K) |
| Categorização por Market Share | Alto (>10%), Médio (5-10%), Baixo (1-5%), Mínimo (<1%) |
| Particionamento | Por DATA_REF, NME_SET, NME_CARD_TYPE, NME_RARITY |
| Arredondamento | 2 casas para valores monetários, 4 para percentuais |

## 7.2 Colunas Criadas na Gold
| Coluna | Descrição |
|--------|-----------|
| DATA_REF | Data de referência para análise temporal |
| VALOR_TOTAL_MERCADO | Valor total do mercado por segmento |
| QTD_CARTAS_ATIVAS | Quantidade de cartas únicas no segmento |
| VALOR_MEDIO_CARTA | Valor médio por carta no segmento |
| TICKET_MEDIANA | Valor mediano (ticket médio) do segmento |
| MARKET_SHARE_SET | Percentual do set no mercado total |
| VARIACAO_PERC_VALOR | Variação percentual do valor da carta |
| RANK_VALORIZACAO | Ranking de valorização por período |
| CATEGORIA_VALOR_MERCADO | Categorização automática por valor |
| CATEGORIA_MARKET_SHARE | Categorização automática por market share |

## 8. Particionamento
- **Colunas:** DATA_REF, NME_SET, NME_CARD_TYPE, NME_RARITY
- **Lógica:** Otimizado para consultas executivas por período, set, tipo e raridade

## 9. Histórico de Alterações
| Data       | Responsável | Alteração                |
|------------|-------------|--------------------------|
| 2025-08-02 | Felipe      | Criação inicial          |

## 10. Observações
- Pipeline modularizado usando gold_utils.py
- Configuração via Unity Catalog (magic_the_gathering.gold)
- Arredondamento: 2 casas decimais para valores monetários, 4 para percentuais
- Particionamento otimizado para consultas executivas
- Categorizações automáticas para análise rápida
- Merge incremental baseado em chaves compostas
- Window functions com partições adequadas para performance 