<div align="center">
<!-- Imagem ilustrativa da tabela (adicione o link abaixo) -->
<img src="https://i.postimg.cc/jjvN23QK/remote-image.png" alt="Imagem de documentação" width="600"/>
</div>
<br>

# TB_BRONZE_SUPERTYPES

## 1. Nome da Tabela e Camada
- **Tabela:** TB_BRONZE_SUPERTYPES
- **Camada:** Bronze

## 2. Descrição Completa
Tabela Bronze contendo os dados brutos de supertipos de cartas do Magic: The Gathering, extraídos da MTG API, padronizados conforme a governança do projeto e preparados para análises e enriquecimento nas camadas superiores.

## 3. Origem dos Dados
- **Fonte:** MTG API (https://api.magicthegathering.io)
- **Arquivo de staging:** s3://<bucket>/magic_the_gathering/stage/*_supertypes.parquet

## 4. Linhagem dos Dados
- **Fluxo:**  
  1. MTG API (endpoint: /supertypes)  
  2. Ingestão para S3 (staging)  
  3. Leitura pelo notebook `src/01 - Ingestion/Dev/TB_RAW_SUPERTYPES.ipynb`  
  4. Carregamento e padronização no notebook `src/02 - Bronze/Dev/TB_BRONZE_SUPERTYPES.ipynb`  
  5. Escrita na tabela Delta: TB_BRONZE_SUPERTYPES (Unity Catalog)

## 5. Schema Detalhado
| Nome da Coluna   | Tipo    | Descrição                        | Obrigatória | Chave | Regra de Preenchimento         |
|------------------|---------|----------------------------------|-------------|-------|-------------------------------|
| NME_SUPERTYPE    | string  | Nome do supertipo de carta       | Sim         | Sim   | Gerado pela API               |
| NME_SOURCE       | string  | Fonte dos dados                  | Sim         | Não   | Padronização GOV              |
| DT_INGESTION     | timestamp | Data/hora de ingestão           | Sim         | Não   |                               |
| INGESTION_YEAR   | int     | Ano de ingestão (particionamento) | Sim      | Não   | Derivado de DT_INGESTION      |
| INGESTION_MONTH  | int     | Mês de ingestão (particionamento) | Sim      | Não   | Derivado de DT_INGESTION      |
                       |

## 6. Regras de Implementação
- **Filtro temporal:** Não aplicado (dados de referência)
- **Deduplicação:** Por NME_SUPERTYPE
- **Merge incremental:** Atualização inteligente de dados
- **Particionamento:** Por INGESTION_YEAR e INGESTION_MONTH

## 7. Regras de Renomeação
| Coluna Original | Coluna GOV      |
|-----------------|-----------------|
| supertype_name  | NME_SUPERTYPE   |
| source          | NME_SOURCE      |
| ingestion_timestamp | DT_INGESTION |


## 8. Particionamento
- **Colunas:** INGESTION_YEAR, INGESTION_MONTH
- **Lógica:** Derivadas do DT_INGESTION

## 9. Histórico de Alterações
| Data       | Responsável | Alteração                |
|------------|-------------|--------------------------|
| 2025-07-01 | Felipe      | Criação inicial          |
| 2025-07-10 | Felipe      | Particionamento add      |

## 10. Observações
- O pipeline exibe logs detalhados de colunas renomeadas e removidas.
- A tabela é recriada automaticamente se o schema estiver divergente.
- Dados de referência sem filtro temporal aplicado. 