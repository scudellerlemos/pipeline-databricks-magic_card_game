<div align="center">
<!-- Imagem ilustrativa da tabela (adicione o link abaixo) -->
<img src="https://i.postimg.cc/jjvN23QK/remote-image.png" alt="Imagem de documentação" width="600"/>
</div>

# TB_BRONZE_SETS

## 1. Nome da Tabela e Camada
- **Tabela:** TB_BRONZE_SETS
- **Camada:** Bronze

## 2. Descrição Completa
Tabela Bronze contendo os dados brutos de sets (coleções) do Magic: The Gathering, extraídos da MTG API, padronizados conforme a governança do projeto e preparados para análises e enriquecimento nas camadas superiores.

## 3. Origem dos Dados
- **Fonte:** MTG API (https://api.magicthegathering.io)
- **Arquivo de staging:** s3:/<bucket>/magic_the_gathering/stage/*_sets.parquet

## 4. Linhagem dos Dados
- **Fluxo:**  
  1. MTG API (endpoint: /sets)  
  2. Ingestão para S3 (staging)  
  3. Leitura pelo notebook `src/01 - Ingestion/Dev/TB_RAW_SETS.ipynb`  
  4. Carregamento e padronização no notebook `src/02 - Bronze/Dev/TB_BRONZE_SETS.ipynb`  
  5. Escrita na tabela Delta: TB_BRONZE_SETS (Unity Catalog)

## 5. Schema Detalhado
| Nome da Coluna      | Tipo    | Descrição                        | Obrigatória | Chave | Regra de Preenchimento         |
|---------------------|---------|----------------------------------|-------------|-------|-------------------------------|
| COD_SET             | string  | Código único do set              | Sim         | Sim   | Gerado pela API               |
| NME_SET             | string  | Nome do set                      | Sim         | Não   | Padronização GOV              |
| NME_TYPE            | string  | Tipo do set                      | Não         | Não   |                               |
| NME_BORDER          | string  | Tipo de borda                    | Não         | Não   |                               |
| ID_MKM              | string  | ID do Cardmarket                 | Não         | Não   |                               |
| NME_MKM             | string  | Nome no Cardmarket               | Não         | Não   |                               |
| DT_RELEASE          | date    | Data de lançamento               | Não         | Não   |                               |
| COD_GATHERER        | string  | Código Gatherer                  | Não         | Não   |                               |
| COD_MAGIC_CARDS_INFO| string  | Código Magic Cards Info          | Não         | Não   |                               |
| DESC_BOOSTER        | array   | Configuração do booster          | Não         | Não   |                               |
| COD_OLD             | string  | Código antigo                    | Não         | Não   |                               |
| FLG_ONLINE_ONLY     | boolean | Flag online apenas               | Não         | Não   |                               |
| NME_SOURCE          | string  | Fonte dos dados                  | Sim         | Não   |                               |
| DESC_BOOSTER_0      | string  | Booster slot 0                   | Não         | Não   | Campo de Array separado para melhor ingestão e transformação                              |
| DESC_BOOSTER_1      | string  | Booster slot 1                   | Não         | Não   | Campo de Array separado para melhor ingestão e transformação                               |
| DESC_BOOSTER_2      | string  | Booster slot 2                   | Não         | Não   | Campo de Array separado para melhor ingestão e transformação                               |
| DESC_BOOSTER_3      | string  | Booster slot 3                   | Não         | Não   | Campo de Array separado para melhor ingestão e transformação                               |
| DESC_BOOSTER_4      | string  | Booster slot 4                   | Não         | Não   | Campo de Array separado para melhor ingestão e transformação                               |
| DESC_BOOSTER_5      | string  | Booster slot 5                   | Não         | Não   |Campo de Array separado para melhor ingestão e transformação                                |
| DESC_BOOSTER_6      | string  | Booster slot 6                   | Não         | Não   | Campo de Array separado para melhor ingestão e transformação                               |
| DESC_BOOSTER_7      | string  | Booster slot 7                   | Não         | Não   | Campo de Array separado para melhor ingestigação e transformação                               |
| DESC_BOOSTER_8      | string  | Booster slot 8                   | Não         | Não   | Campo de Array separado para melhor ingestão e transformação                               |
| DESC_BOOSTER_9      | string  | Booster slot 9                   | Não         | Não   | Campo de Array separado para melhor ingestão e transformação                               |
| DESC_BOOSTER_10     | string  | Booster slot 10                  | Não         | Não   | Campo de Array separado para melhor ingestão e transformação                               |
| DESC_BOOSTER_11     | string  | Booster slot 11                  | Não         | Não   | Campo de Array separado para melhor ingestão e transformação                               |
| DESC_BOOSTER_12     | string  | Booster slot 12                  | Não         | Não   | Campo de Array separado para melhor ingestão e transformação                               |
| DESC_BOOSTER_13     | string  | Booster slot 13                  | Não         | Não   | Campo de Array separado para melhor ingestão e transformação                               |
| DESC_BOOSTER_14     | string  | Booster slot 14                  | Não         | Não   | Campo de Array separado para melhor ingestão e transformação                               |
| DESC_BOOSTER_15     | string  | Booster slot 15                  | Não         | Não   | Campo de Array separado para melhor ingestão e transformação                               |
| DESC_BOOSTER_16     | string  | Booster slot 16                  | Não         | Não   | Campo de Array separado para melhor ingestão e transformação                               |
| DESC_BOOSTER_17     | string  | Booster slot 17                  | Não         | Não   | Campo de Array separado para melhor ingestão e transformação                               |
| DESC_BOOSTER_18     | string  | Booster slot 18                  | Não         | Não   | Campo de Array separado para melhor ingestão e transformação                               |
| DESC_BOOSTER_19     | string  | Booster slot 19                  | Não         | Não   | Campo de Array separado para melhor ingestão e transformação                               |
| RELEASE_YEAR        | int     | Ano de lançamento (particionamento) | Sim      | Não   | Derivado de DT_RELEASE        |
| RELEASE_MONTH       | int     | Mês de lançamento (particionamento) | Sim      | Não   | Derivado de DT_RELEASE        |
| FLG_DIGITAL         | boolean | Flag digital                     | Não         | Não   |                               |
| FLG_FOIL_ONLY       | boolean | Flag foil apenas                 | Não         | Não   |                               |
| COD_BLOCK           | string  | Código do bloco                  | Não         | Não   |                               |
| COD_PARENT          | string  | Código do set pai                | Não         | Não   |                               |
| COD_PARENT_CODE     | string  | Código do set pai                | Não         | Não   |                               |
| URL_SCRYFALL        | string  | URL Scryfall                     | Não         | Não   |                               |
| URL_SCRYFALL_API    | string  | URL API Scryfall                 | Não         | Não   |                               |
| ID_TCGPLAYER        | string  | ID TCGPlayer                     | Não         | Não   |                               |
| ID_CARDMARKET       | string  | ID Cardmarket                    | Não         | Não   |                               |
| DT_INGESTION        | timestamp | Data/hora de ingestão           | Sim         | Não   |                               |

## 6. Regras de Implementação
- **Filtro temporal:** Apenas sets lançados nos últimos 5 anos (baseado em releaseDate)
- **Deduplicação:** Por COD_SET
- **Merge incremental:** Atualização inteligente de dados
- **Particionamento:** Por RELEASE_YEAR e RELEASE_MONTH

## 7. Regras de Renomeação
| Coluna Original | Coluna Bronze      |
|-----------------|-----------------|
| code            | COD_SET         |
| name            | NME_SET         |
| type            | NME_TYPE        |
| border          | NME_BORDER      |
| mkm_id          | ID_MKM          |
| mkm_name        | NME_MKM         |
| releaseDate     | DT_RELEASE      |
| gathererCode    | COD_GATHERER    |
| magicCardsInfoCode | COD_MAGIC_CARDS_INFO |
| booster         | DESC_BOOSTER    |
| oldCode         | COD_OLD         |
| onlineOnly      | FLG_ONLINE_ONLY |
| source          | NME_SOURCE      |
| booster_0       | DESC_BOOSTER_0  |
| booster_1       | DESC_BOOSTER_1  |
| booster_2       | DESC_BOOSTER_2  |
| booster_3       | DESC_BOOSTER_3  |
| booster_4       | DESC_BOOSTER_4  |
| booster_5       | DESC_BOOSTER_5  |
| booster_6       | DESC_BOOSTER_6  |
| booster_7       | DESC_BOOSTER_7  |
| booster_8       | DESC_BOOSTER_8  |
| booster_9       | DESC_BOOSTER_9  |
| booster_10      | DESC_BOOSTER_10 |
| booster_11      | DESC_BOOSTER_11 |
| booster_12      | DESC_BOOSTER_12 |
| booster_13      | DESC_BOOSTER_13 |
| booster_14      | DESC_BOOSTER_14 |
| booster_15      | DESC_BOOSTER_15 |
| booster_16      | DESC_BOOSTER_16 |
| booster_17      | DESC_BOOSTER_17 |
| booster_18      | DESC_BOOSTER_18 |
| booster_19      | DESC_BOOSTER_19 |
| digital         | FLG_DIGITAL     |
| foilOnly        | FLG_FOIL_ONLY   |
| block           | NME_BLOCK       |
| blockCode       | COD_BLOCK       |
| parent          | COD_PARENT      |
| parentCode      | COD_PARENT_CODE |
| scryfallUri     | URL_SCRYFALL    |
| scryfallApiUri  | URL_SCRYFALL_API|
| tcgplayerId     | ID_TCGPLAYER    |
| cardmarketId    | ID_CARDMARKET   |
| ingestion_timestamp | DT_INGESTION |


## 8. Particionamento
- **Colunas:** RELEASE_YEAR, RELEASE_MONTH
- **Lógica:** Derivadas do DT_RELEASE do set

## 9. Histórico de Alterações
| Data       | Responsável | Alteração                |
|------------|-------------|--------------------------|
| 2025-07-01 | Felipe      | Criação inicial          |
| 2025-07-07 | Felipe      | Particionamento add      |

## 10. Observações
- O pipeline exibe logs detalhados de colunas renomeadas e removidas.
- A tabela é recriada automaticamente se o schema estiver divergente.
- Os dados de booster são expandidos em colunas individuais para facilitar análises. 
