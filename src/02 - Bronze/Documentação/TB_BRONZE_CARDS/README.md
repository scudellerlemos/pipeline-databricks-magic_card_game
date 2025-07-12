<div align="center">
<!-- Imagem ilustrativa da tabela (adicione o link abaixo) -->
<img src="https://i.postimg.cc/jjvN23QK/remote-image.png" alt="Imagem ilustrativa da tabela" width="600"/>
</div>

# TB_BRONZE_CARDS

## 1. Nome da Tabela e Camada
- **Tabela:** TB_BRONZE_CARDS
- **Camada:** Bronze

## 2. Descrição Completa
Tabela Bronze contendo os dados brutos de cartas do Magic: The Gathering, extraídos da MTG API, padronizados conforme a governança do projeto e preparados para análises e enriquecimento nas camadas superiores.

## 3. Origem dos Dados
- **Fonte:** MTG API (https://api.magicthegathering.io)
- **Arquivo de staging:** s3://<bucket>/magic_the_gathering/stage/cards_*.parquet

## 4. Linhagem dos Dados
- **Fluxo:**  
  1. MTG API (endpoint: /cards)  
  2. Ingestão para S3 (staging)  
  3. Leitura pelo notebook `src/01 - Ingestion/Dev/TB_RAW_CARDS.ipynb`  
  4. Transformação e padronização no notebook `src/02 - Bronze/Dev/TB_BRONZE_CARDS.ipynb`  
  5. Escrita na tabela Delta: TB_BRONZE_CARDS (Unity Catalog)

## 5. Schema Detalhado
| Nome da Coluna   | Tipo    | Descrição                        | Obrigatória | Chave | Regra de Preenchimento         |
|------------------|---------|----------------------------------|-------------|-------|-------------------------------|
| ID_CARD          | string  | Identificador único da carta     | Sim         | Sim   | Gerado pela API               |
| NME_CARD         | string  | Nome da carta                    | Sim         | Não   | Padronização GOV              |
| NME_ARTIST       | string  | Nome do artista                  | Não         | Não   |                               |
| NME_CARD_TYPE    | string  | Tipo da carta                    | Não         | Não   |                               |
| NME_RARITY       | string  | Raridade                         | Não         | Não   |                               |
| COD_SET          | string  | Código do set                    | Sim         | Não   |                               |
| NME_SET          | string  | Nome do set                      | Não         | Não   |                               |
| DESC_MANA_COST   | string  | Custo de mana (texto)            | Não         | Não   |                               |
| MANA_COST        | double  | Converted Mana Cost (CMC)         | Não         | Não   |                               |
| COD_COLORS       | array   | Cores                            | Não         | Não   |                               |
| COD_COLOR_IDENTITY | array | Identidade de cor                | Não         | Não   |                               |
| DESC_TYPES       | array   | Tipos                            | Não         | Não   |                               |
| DESC_SUBTYPES    | array   | Subtipos                         | Não         | Não   |                               |
| NME_POWER        | string  | Poder (creature)                 | Não         | Não   |                               |
| NME_TOUGHNESS    | string  | Resistência (creature)           | Não         | Não   |                               |
| COD_NUMBER       | string  | Número da carta no set           | Não         | Não   |                               |
| NME_LAYOUT       | string  | Layout da carta                  | Não         | Não   |                               |
| ID_MULTIVERSE    | string  | ID Multiverse                    | Não         | Não   |                               |
| URL_IMAGE        | string  | URL da imagem                    | Não         | Não   |                               |
| DESC_VARIATIONS  | array   | Variações                        | Não         | Não   |                               |
| DESC_CARD        | string  | Texto da carta                   | Não         | Não   |                               |
| DT_INGESTION     | timestamp | Data/hora de ingestão           | Sim         | Não   |                               |
| NME_SOURCE       | string  | Fonte dos dados                  | Sim         | Não   |                               |
| NME_ENDPOINT     | string  | Endpoint de origem               | Sim         | Não   |                               |
| RELEASE_YEAR     | int     | Ano de lançamento (particionamento) | Sim      | Não   | Derivado de releaseDate do set|
| RELEASE_MONTH    | int     | Mês de lançamento (particionamento) | Sim      | Não   | Derivado de releaseDate do set|
| DT_CREATED       | timestamp | Data de criação (opcional)      | Não         | Não   |                               |
| DT_UPDATED       | timestamp | Data de atualização (opcional)  | Não         | Não   |                               |

## 6. Regras de Implementação
- **Filtro temporal:** Apenas cartas de sets lançados nos últimos 5 anos (baseado em releaseDate dos sets)
- **Deduplicação:** Por ID_CARD
- **Enriquecimento:** Join com dados de sets para particionamento correto
- **Merge incremental:** Atualização inteligente de dados

## 7. Regras de Renomeação
| Coluna Original | Coluna GOV      |
|-----------------|-----------------|
| id              | ID_CARD         |
| name            | NME_CARD        |
| artist          | NME_ARTIST      |
| type            | NME_CARD_TYPE   |
| rarity          | NME_RARITY      |
| set             | COD_SET         |
| setName         | NME_SET         |
| manaCost        | DESC_MANA_COST  |
| cmc             | MANA_COST       |
| colors          | COD_COLORS      |
| colorIdentity   | COD_COLOR_IDENTITY |
| types           | DESC_TYPES      |
| subtypes        | DESC_SUBTYPES   |
| power           | NME_POWER       |
| toughness       | NME_TOUGHNESS   |
| number          | COD_NUMBER      |
| layout          | NME_LAYOUT      |
| multiverseid    | ID_MULTIVERSE   |
| imageUrl        | URL_IMAGE       |
| variations      | DESC_VARIATIONS |
| text            | DESC_CARD       |
| ingestion_timestamp | DT_INGESTION |
| source          | NME_SOURCE      |
| endpoint        | NME_ENDPOINT    |


## 8. Particionamento
- **Colunas:** RELEASE_YEAR, RELEASE_MONTH
- **Lógica:** Derivadas do releaseDate do set associado à carta



## 9. Histórico de Alterações
| Data       | Responsável | Alteração                |
|------------|-------------|--------------------------|
| 2025-07-01 | Felipe      | Criação inicial          |
| 2025-07-10 | Felipe      | Particionamento add      |

## 10. Observações
- O pipeline exibe logs detalhados de colunas renomeadas e removidas.
- A tabela é recriada automaticamente se o schema estiver divergente.
- Para detalhes de preços, consultar TB_BRONZE_CARDPRICES. 
