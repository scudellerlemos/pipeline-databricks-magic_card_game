<div align="center">
<!-- Imagem ilustrativa da tabela (adicione o link abaixo) -->
<img src="https://i.postimg.cc/jjvN23QK/remote-image.png" alt="Imagem de documentação" width="600"/>
</div>

# TB_BRONZE_CARD_PRICES

## 1. Nome da Tabela e Camada
- **Tabela:** TB_BRONZE_CARD_PRICES
- **Camada:** Bronze

## 2. Descrição Completa
Tabela Bronze contendo os dados brutos de preços de cartas do Magic: The Gathering, extraídos da MTG API, padronizados conforme a governança do projeto e preparados para análises e enriquecimento nas camadas superiores.

## 3. Origem dos Dados
- **Fonte:** MTG API (https://api.magicthegathering.io)
- **Arquivo de staging:** s3://<bucket>/magic_the_gathering/stage/*_card_prices.parquet

## 4. Linhagem dos Dados
- **Fluxo:**  
  1. MTG API (endpoint: /cards com preços)  
  2. Ingestão para S3 (staging)  
  3. Leitura pelo notebook `src/01 - Ingestion/Dev/TB_RAW_CARDPRICES.ipynb`  
  4. Carregamento e padronização no notebook `src/02 - Bronze/Dev/TB_BRONZE_CARDPRICES.ipynb`  
  5. Escrita na tabela Delta: TB_BRONZE_CARDPRICES (Unity Catalog)

## 5. Schema Detalhado
| Nome da Coluna      | Tipo    | Descrição                        | Obrigatória | Chave | Regra de Preenchimento         |
|---------------------|---------|----------------------------------|-------------|-------|-------------------------------|
| ID_CARD             | string  | Identificador único da carta     | Sim         | Não   | Gerado pela API               |
| NME_CARD            | string  | Nome da carta                    | Sim         | Sim   | Padronização GOV              |
| VLR_USD             | double  | Preço em USD                     | Não         | Não   |                               |
| VLR_USD_FOIL        | double  | Preço foil em USD                | Não         | Não   |                               |
| VLR_EUR             | double  | Preço em EUR                     | Não         | Não   |                               |
| VLR_EUR_FOIL        | double  | Preço foil em EUR                | Não         | Não   |                               |
| VLR_TIX             | double  | Preço em TIX                     | Não         | Não   |                               |
| DESC_PRICES         | string  | Descrição dos preços             | Não         | Não   |                               |
| DT_PRICE_UPDATE     | timestamp | Data de atualização do preço   | Não         | Não   |                               |
| VLR_MARKET          | double  | Preço de mercado                 | Não         | Não   |                               |
| VLR_MARKET_FOIL     | double  | Preço de mercado foil            | Não         | Não   |                               |
| VLR_LOW             | double  | Preço mais baixo                 | Não         | Não   |                               |
| VLR_LOW_FOIL        | double  | Preço mais baixo foil            | Não         | Não   |                               |
| VLR_HIGH            | double  | Preço mais alto                  | Não         | Não   |                               |
| VLR_HIGH_FOIL       | double  | Preço mais alto foil             | Não         | Não   |                               |
| NME_PRICE_STATUS    | string  | Status do preço                  | Não         | Não   |                               |
| FLG_PRICE_AVAILABLE | boolean | Flag preço disponível            | Não         | Não   |                               |
| URL_IMAGE           | string  | URL da imagem                    | Não         | Não   |                               |
| URL_SCRYFALL        | string  | URL Scryfall                     | Não         | Não   |                               |
| NME_RARITY          | string  | Raridade da carta                | Não         | Não   |                               |
| COD_SET             | string  | Código do set                    | Não         | Não   |                               |
| NME_SOURCE          | string  | Fonte dos dados                  | Sim         | Não   |                               |
| DESC_ERROR          | string  | Descrição de erro (se houver)    | Não         | Não   |                               |
| DT_INGESTION        | timestamp | Data/hora de ingestão           | Sim         | Não   |                               |
| RELEASE_YEAR        | int     | Ano de lançamento (particionamento) | Sim      | Não   | Derivado de releaseDate do set|
| RELEASE_MONTH       | int     | Mês de lançamento (particionamento) | Sim      | Não   | Derivado de releaseDate do set|

## 6. Regras de Implementação
- **Filtro temporal:** Apenas preços de cartas de sets lançados nos últimos 5 anos (baseado em releaseDate dos sets)
- **Deduplicação:** Por NME_CARD
- **Merge incremental:** Atualização inteligente de dados
- **Particionamento:** Por RELEASE_YEAR e RELEASE_MONTH

## 7. Regras de Renomeação
| Coluna Original | Coluna Bronze      |
|-----------------|-----------------|
| id              | ID_CARD         |
| name            | NME_CARD        |
| usd             | VLR_USD         |
| usd_foil        | VLR_USD_FOIL    |
| eur             | VLR_EUR         |
| eur_foil        | VLR_EUR_FOIL    |
| tix             | VLR_TIX         |
| prices          | DESC_PRICES     |
| price_updated_at | DT_PRICE_UPDATE |
| market_price    | VLR_MARKET      |
| market_price_foil | VLR_MARKET_FOIL |
| low_price       | VLR_LOW         |
| low_price_foil  | VLR_LOW_FOIL    |
| high_price      | VLR_HIGH        |
| high_price_foil | VLR_HIGH_FOIL   |
| price_status    | NME_PRICE_STATUS |
| price_available | FLG_PRICE_AVAILABLE |
| image_url       | URL_IMAGE       |
| scryfall_uri    | URL_SCRYFALL    |
| rarity          | NME_RARITY      |
| set             | COD_SET         |
| source          | NME_SOURCE      |
| error           | DESC_ERROR      |
| ingestion_timestamp | DT_INGESTION |
| created_at      | DT_CREATED      |
| updated_at      | DT_UPDATED      |

## 8. Particionamento
- **Colunas:** RELEASE_YEAR, RELEASE_MONTH
- **Lógica:** Derivadas do releaseDate do set associado à carta

## 9. Histórico de Alterações
| Data       | Responsável | Alteração                |
|------------|-------------|--------------------------|
| 2025-07-01 | Felipe      | Criação inicial          |
| 2025-07-12 | Felipe      | Particionamento add      |

## 10. Observações
- O pipeline exibe logs detalhados de colunas renomeadas e removidas.
- A tabela é recriada automaticamente se o schema estiver divergente.
- Filtro temporal baseado em cards existentes em TB_BRONZE_CARDS.
- Preços são atualizados incrementalmente para manter histórico. 
