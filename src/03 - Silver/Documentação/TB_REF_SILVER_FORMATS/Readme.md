<div align="center">
<!-- Imagem ilustrativa da tabela (adicione o link abaixo) -->
<img src="https://i.postimg.cc/jjvN23QK/remote-image.png" alt="Imagem de documentação" width="600"/>
</div>
<br>

# TB_REF_SILVER_FORMATS

## 1. Nome da Tabela e Camada
- **Tabela:** TB_REF_SILVER_FORMATS
- **Camada:** Silver

## 2. Descrição Completa
Tabela Silver contendo os dados limpos e transformados de formatos de jogo do Magic: The Gathering, processados a partir da camada Bronze, com aplicação de regras de negócio, limpeza de dados e padronização para análises de metagame e competitividade.

## 3. Origem dos Dados
- **Fonte:** TB_BRONZE_FORMATS (camada Bronze)
- **Arquivo de staging:** s3:/bucket/magic_the_gathering/silver/TB_REF_SILVER_FORMATS

## 4. Linhagem dos Dados
- **Fluxo:**  
  1. MTG API (endpoint: /formats)  
  2. Ingestão para S3 (staging)  
  3. Processamento Bronze (`src/02 - Bronze/Dev/TB_BRONZE_FORMATS.ipynb`)  
  4. Transformação Silver (`src/03 - Silver/Dev/TB_REF_SILVER_FORMATS.ipynb`)  
  5. Escrita na tabela Delta: TB_REF_SILVER_FORMATS (Unity Catalog)

## 5. Schema Detalhado
| Nome da Coluna   | Tipo    | Descrição                        | Obrigatória | Chave | Regra de Preenchimento         |
|------------------|---------|----------------------------------|-------------|-------|-------------------------------|
| NME_FORMAT       | string  | Nome do formato de jogo          | Sim         | Sim   | Title case, sem acentos        |
| NME_SOURCE       | string  | Fonte dos dados                  | Sim         | Não   |              |
| DT_INGESTION     | timestamp | Data/hora de ingestão           | Sim         | Não   |                               |
| INGESTION_YEAR   | int     | Ano de ingestão (particionamento) | Sim      | Não   | Derivado de DT_INGESTION      |
| INGESTION_MONTH  | int     | Mês de ingestão (particionamento) | Sim      | Não   | Derivado de DT_INGESTION      |

## 6. Regras de Implementação
- **Filtro temporal:** Não aplicado (dados de referência)
- **Deduplicação:** Por NME_FORMAT
- **Merge incremental:** Atualização inteligente de dados
- **Particionamento:** Por INGESTION_YEAR e INGESTION_MONTH
- **Limpeza:** Nulos → 0 para números, "NA" para strings

## 7. Transformações Aplicadas
| Transformação | Descrição |
|---------------|-----------|
| Title Case | Nomes de formatos em formato título |
| Limpeza de Nulos | Strings: nulos → "NA" |
| Conversão de Tipos | Datas para TIMESTAMP |
| Remoção de Duplicatas | Baseado em NME_FORMAT |
| Particionamento | Por ano e mês de ingestão |

## 8. Particionamento
- **Colunas:** INGESTION_YEAR, INGESTION_MONTH
- **Lógica:** Derivadas do DT_INGESTION

## 9. Histórico de Alterações
| Data       | Responsável | Alteração                |
|------------|-------------|--------------------------|
| 2025-01-20 | Felipe      | Criação inicial          |

## 10. Observações
- Pipeline exibe logs detalhados de transformações aplicadas.
- Tabela é recriada automaticamente se o schema estiver divergente.
- Dados de referência sem filtro temporal aplicado.
- Merge incremental baseado em NME_FORMAT.
- Formatos incluem Standard, Modern, Legacy, Vintage, etc. 
