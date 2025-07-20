<div align="center">
<!-- Imagem ilustrativa da tabela (adicione o link abaixo) -->
<img src="https://i.postimg.cc/jjvN23QK/remote-image.png" alt="Imagem de documentação" width="600"/>
</div>
<br>

# TB_REF_SILVER_SETS

## 1. Nome da Tabela e Camada
- **Tabela:** TB_REF_SILVER_SETS
- **Camada:** Silver

## 2. Descrição Completa
Tabela Silver contendo os dados limpos e transformados de conjuntos de cartas do Magic: The Gathering, processados a partir da camada Bronze, com aplicação de regras de negócio, limpeza de dados e padronização para análises de lançamentos e coleções.

## 3. Origem dos Dados
- **Fonte:** TB_BRONZE_SETS (camada Bronze)
- **Arquivo de staging:** s3://<bucket>/magic_the_gathering/silver/TB_REF_SILVER_SETS

## 4. Linhagem dos Dados
- **Fluxo:**  
  1. MTG API (endpoint: /sets)  
  2. Ingestão para S3 (staging)  
  3. Processamento Bronze (`src/02 - Bronze/Dev/TB_BRONZE_SETS.ipynb`)  
  4. Transformação Silver (`src/03 - Silver/Dev/TB_REF_SILVER_SETS.ipynb`)  
  5. Escrita na tabela Delta: TB_REF_SILVER_SETS (Unity Catalog)

## 5. Schema Detalhado
| Nome da Coluna   | Tipo    | Descrição                        | Obrigatória | Chave | Regra de Preenchimento         |
|------------------|---------|----------------------------------|-------------|-------|-------------------------------|
| NME_SET          | string  | Nome do conjunto                 | Sim         | Sim   | Title case, sem acentos        |
| NME_CODE         | string  | Código do conjunto               | Sim         | Não   | Upper case                     |
| NME_BLOCK        | string  | Nome do bloco                    | Não         | Não   | Title case, sem acentos        |
| NME_BLOCK_CODE   | string  | Código do bloco                  | Não         | Não   | Upper case                     |
| NME_SOURCE       | string  | Fonte dos dados                  | Sim         | Não   |             |
| DT_INGESTION     | timestamp | Data/hora de ingestão           | Sim         | Não   |                               |
| RELEASE_YEAR     | int     | Ano de lançamento (particionamento) | Sim     | Não   | Derivado de DT_RELEASE        |
| RELEASE_MONTH    | int     | Mês de lançamento (particionamento) | Sim     | Não   | Derivado de DT_RELEASE        |

## 6. Regras de Implementação
- **Filtro temporal:** Não aplicado (dados de referência)
- **Deduplicação:** Por NME_SET
- **Merge incremental:** Atualização inteligente de dados
- **Particionamento:** Por RELEASE_YEAR e RELEASE_MONTH
- **Limpeza:** Nulos → 0 para números, "NA" para strings

## 7. Transformações Aplicadas
| Transformação | Descrição |
|---------------|-----------|
| Title Case | Nomes de conjuntos e blocos em formato título |
| Upper Case | Códigos de conjuntos e blocos em maiúsculas |
| Limpeza de Nulos | Strings: nulos → "NA" |
| Conversão de Tipos | Datas para TIMESTAMP |
| Remoção de Duplicatas | Baseado em NME_SET |
| Particionamento | Por ano e mês de lançamento |

## 8. Particionamento
- **Colunas:** RELEASE_YEAR, RELEASE_MONTH
- **Lógica:** Derivadas do DT_RELEASE

## 9. Histórico de Alterações
| Data       | Responsável | Alteração                |
|------------|-------------|--------------------------|
| 2025-01-18 | Felipe      | Criação inicial          |

## 10. Observações
- Pipeline exibe logs detalhados de transformações aplicadas.
- Tabela é recriada automaticamente se o schema estiver divergente.
- Dados de referência sem filtro temporal aplicado.
- Merge incremental baseado em NME_SET.
- Conjuntos incluem expansões principais, suplementares e especiais. 