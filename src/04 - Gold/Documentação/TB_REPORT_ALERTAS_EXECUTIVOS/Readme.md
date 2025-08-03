<div align="center">
<!-- Imagem ilustrativa da tabela (adicione o link abaixo) -->
<img src="https://i.postimg.cc/jjvN23QK/remote-image.png" alt="Imagem de documentação" width="600"/>
</div>
<br>

# TB_REPORT_ALERTAS_EXECUTIVOS

## 1. Nome da Tabela e Camada
- **Tabela:** TB_REPORT_ALERTAS_EXECUTIVOS
- **Camada:** Gold

## 2. Descrição Completa
Tabela Gold contendo sistema de alertas executivos para mudanças significativas no mercado de cartas Magic: The Gathering. Esta tabela fornece detecção automática de oportunidades, notificações de risco e priorização de ações para suportar decisões executivas rápidas e estratégicas no mercado de cartas.

## 3. Origem dos Dados
- **Fonte:** TB_REF_SILVER_CARDS, TB_REF_SILVER_CARDPRICES (camada Silver)
- **Arquivo de staging:** s3:/<bucket>/magic_the_gathering/gold/TB_REPORT_ALERTAS_EXECUTIVOS

## 4. Linhagem dos Dados
- **Fluxo:**  
  1. MTG API (endpoint: /cards, /prices)  
  2. Ingestão para S3 (staging)  
  3. Processamento Bronze (`src/02 - Bronze/Dev/`)  
  4. Transformação Silver (`src/03 - Silver/Dev/`)  
  5. Análise Gold (`src/04 - Gold/TB_REPORT_ALERTAS_EXECUTIVOS.ipynb`)  
  6. Escrita na tabela Delta: TB_REPORT_ALERTAS_EXECUTIVOS (Unity Catalog)

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
| THRESHOLD_ALERTA | decimal(10,4) | Limite para geração de alerta | Sim | Não | Configuração baseada em regras |
| FLG_ALERTA_ATIVO | boolean | Flag indicando se alerta está ativo | Sim | Não | VARIACAO_PERC_VALOR > THRESHOLD_ALERTA |
| TIPO_ALERTA      | string  | Tipo de alerta gerado            | Sim         | Não   | Categorização baseada em variação |
| PRIORIDADE_ALERTA | string | Prioridade do alerta             | Sim         | Não   | Alta, Média, Baixa baseada em magnitude |
| DESCRICAO_ALERTA | string  | Descrição detalhada do alerta    | Sim         | Não   | Texto explicativo do alerta |
| ACAO_RECOMENDADA | string  | Ação recomendada para o alerta   | Sim         | Não   | Comprar, Vender, Monitorar |
| RANK_URGENCIA    | int     | Ranking de urgência do alerta    | Não         | Não   | row_number() por DATA_REF      |

## 6. Regras de Implementação
- **Filtro temporal:** Baseado em RELEASE_YEAR e RELEASE_MONTH das cartas
- **Deduplicação:** Por DATA_REF + NME_CARD + NME_SET + NME_CARD_TYPE + NME_RARITY
- **Merge incremental:** Atualização inteligente de dados
- **Particionamento:** Por DATA_REF, NME_SET
- **Arredondamento:** 2 casas decimais para valores, 4 para percentuais

## 7. Transformações Aplicadas
| Transformação | Descrição |
|---------------|-----------|
| Detecção de Variações | Identificação de mudanças significativas nos valores |
| Geração de Alertas | Criação automática de alertas baseada em thresholds |
| Categorização de Alertas | Classificação por tipo e prioridade |
| Recomendações de Ação | Sugestões automáticas de ações |
| Ranking de Urgência | Priorização de alertas por urgência |
| Validação de Thresholds | Verificação de limites para geração de alertas |

## 7.1 Regras de Negócio Aplicadas
| Regra de Negócio | Descrição |
|------------------|-----------|
| DATA_REF | Criada a partir de RELEASE_YEAR e RELEASE_MONTH usando make_date() |
| Threshold de Alerta | Configuração de limites para geração de alertas |
| Tipo de Alerta | Oportunidade (variação positiva), Risco (variação negativa), Neutro |
| Prioridade | Alta (>20%), Média (10-20%), Baixa (5-10%) baseada em magnitude |
| Ação Recomendada | Comprar (oportunidade), Vender (risco), Monitorar (neutro) |
| Ranking | Ranking por DATA_REF baseado na urgência do alerta |
| Particionamento | Por DATA_REF, NME_SET |
| Arredondamento | 2 casas para valores monetários, 4 para percentuais |

## 7.2 Colunas Criadas na Gold
| Coluna | Descrição |
|--------|-----------|
| DATA_REF | Data de referência para análise temporal |
| VALOR_ATUAL | Valor atual da carta no mercado |
| VALOR_ANTERIOR | Valor anterior para comparação |
| VARIACAO_PERC_VALOR | Variação percentual do valor |
| THRESHOLD_ALERTA | Limite configurado para geração de alertas |
| FLG_ALERTA_ATIVO | Flag indicando se alerta está ativo |
| TIPO_ALERTA | Categorização do tipo de alerta |
| PRIORIDADE_ALERTA | Nível de prioridade do alerta |
| DESCRICAO_ALERTA | Descrição detalhada do alerta |
| ACAO_RECOMENDADA | Ação sugerida para o alerta |
| RANK_URGENCIA | Ranking de urgência do alerta |

## 8. Particionamento
- **Colunas:** DATA_REF, NME_SET
- **Lógica:** Otimizado para consultas de alertas por período e set

## 9. Histórico de Alterações
| Data       | Responsável | Alteração                |
|------------|-------------|--------------------------|
| 2025-08-02 | Felipe      | Criação inicial          |

## 10. Observações
- Pipeline modularizado usando gold_utils.py
- Configuração via Unity Catalog (magic_the_gathering.gold)
- Arredondamento: 2 casas decimais para valores monetários, 4 para percentuais
- Particionamento otimizado para consultas de alertas
- Sistema de alertas configurável via thresholds
- Merge incremental baseado em chaves compostas
- Window functions com partições adequadas para performance
- Alertas validados para tomada de decisão executiva
- Recomendações automáticas de ações estratégicas 