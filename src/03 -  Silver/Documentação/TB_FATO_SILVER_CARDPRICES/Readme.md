<div align="center">
<!-- Imagem ilustrativa da tabela (adicione o link abaixo) -->
<img src="https://i.postimg.cc/jjvN23QK/remote-image.png" alt="Imagem de documentação" width="600"/>
</div>
<br>

# TB_FATO_SILVER_CARDPRICES

## 1. Nome da Tabela e Camada
- **Tabela:** TB_FATO_SILVER_CARDPRICES
- **Camada:** Silver

## 2. Descrição Completa
Tabela Silver contendo os dados limpos e transformados de preços de cartas do Magic: The Gathering, processados a partir da camada Bronze com aplicação de limpeza de dados e padronização para análises financeiras e de mercado.

## 3. Origem dos Dados
- **Fonte:** TB_BRONZE_CARDPRICES (camada Bronze)
- **Arquivo de staging:** s3://<bucket>/magic_the_gathering/silver/TB_FATO_SILVER_CARDPRICES

## 4. Linhagem dos Dados
- **Fluxo:**  
  1. MTG API (endpoint: /cards/{id}/prices)  
  2. Ingestão para S3 (staging)  
  3. Processamento Bronze (`src/02 - Bronze/Dev/TB_BRONZE_CARD_PRICES.ipynb`)  
  4. Transformação Silver (`src/03 - Silver/Dev/TB_FATO_SILVER_CARDPRICES.ipynb`)  
  5. Escrita na tabela Delta: TB_FATO_SILVER_CARDPRICES (Unity Catalog)

## 5. Schema Detalhado
| Nome da Coluna   | Tipo    | Descrição                        | Obrigatória | Chave | Regra de Preenchimento         |
|------------------|---------|----------------------------------|-------------|-------|-------------------------------|
| NME_CARD         | string  | Nome da carta                    | Sim         | Sim   | Title case, sem acentos        |
| NME_SET          | string  | Nome do conjunto                 | Sim         | Não   | Title case, sem acentos        |
| NME_PRICE_TYPE   | string  | Tipo de preço (usd, usd_foil, etc) | Sim      | Não   | Lower case                     |
| NUM_PRICE        | double  | Valor do preço                   | Não         | Não   | Decimal com 2 casas            |
| NME_SOURCE       | string  | Fonte dos dados                  | Sim         | Não   |             |
| DT_INGESTION     | timestamp | Data/hora de ingestão           | Sim         | Não   |                               |
| RELEASE_YEAR     | int     | Ano de lançamento (particionamento) | Sim     | Não   | Derivado de NME_SET           |
| RELEASE_MONTH    | int     | Mês de lançamento (particionamento) | Sim     | Não   | Derivado de NME_SET           |

## 6. Regras de Implementação
- **Filtro temporal:** Não aplicado (dados históricos de preços)
- **Deduplicação:** Por NME_CARD + NME_SET + NME_PRICE_TYPE
- **Merge incremental:** Atualização inteligente de dados
- **Particionamento:** Por RELEASE_YEAR e RELEASE_MONTH
- **Limpeza:** Nulos → 0 para números, "NA" para strings

## 7. Transformações Aplicadas
| Transformação | Descrição |
|---------------|-----------|
| Title Case | Nomes de cartas e conjuntos em formato título |
| Limpeza de Nulos | Strings: nulos → "NA", Números: nulos → 0 |
| Conversão de Tipos | Preços para DOUBLE |
| Remoção de Duplicatas | Baseado em NME_CARD + NME_SET + NME_PRICE_TYPE |
| Particionamento | Por ano e mês de lançamento do conjunto |

## 8. Particionamento
- **Colunas:** RELEASE_YEAR, RELEASE_MONTH
- **Lógica:** Derivadas do conjunto da carta

## 9. Histórico de Alterações
| Data       | Responsável | Alteração                |
|------------|-------------|--------------------------|
| 2025-07-20 | Felipe      | Criação inicial          |

## 10. Observações
- Pipeline exibe logs detalhados de transformações aplicadas.
- Tabela é recriada automaticamente se o schema estiver divergente.
- Dados de preços históricos sem filtro temporal aplicado.
- Merge incremental baseado em NME_CARD.
- Preços nulos são convertidos para 0.0. 
