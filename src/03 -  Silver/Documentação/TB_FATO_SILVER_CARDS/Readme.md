<div align="center">
<!-- Imagem ilustrativa da tabela (adicione o link abaixo) -->
<img src="https://i.postimg.cc/jjvN23QK/remote-image.png" alt="Imagem de documentação" width="600"/>
</div>
<br>

# TB_FATO_SILVER_CARDS

## 1. Nome da Tabela e Camada
- **Tabela:** TB_FATO_SILVER_CARDS
- **Camada:** Silver

## 2. Descrição Completa
Tabela Silver contendo os dados limpos e transformados de cartas do Magic: The Gathering, processados a partir da camada Bronze, com aplicação de regras de negócio, limpeza de dados e padronização para análises de gameplay, deckbuilding e estratégias competitivas.

## 3. Origem dos Dados
- **Fonte:** TB_BRONZE_CARDS (camada Bronze)
- **Arquivo de staging:** s3://<bucket>/magic_the_gathering/silver/TB_FATO_SILVER_CARDS

## 4. Linhagem dos Dados
- **Fluxo:**  
  1. MTG API (endpoint: /cards)  
  2. Ingestão para S3 (staging)  
  3. Processamento Bronze (`src/02 - Bronze/Dev/TB_BRONZE_CARDS.ipynb`)  
  4. Transformação Silver (`src/03 - Silver/Dev/TB_FATO_SILVER_CARDS.ipynb`)  
  5. Escrita na tabela Delta: TB_REF_SILVER_CARDS (Unity Catalog)

## 5. Schema Detalhado
| Nome da Coluna   | Tipo    | Descrição                        | Obrigatória | Chave | Regra de Preenchimento         |
|------------------|---------|----------------------------------|-------------|-------|-------------------------------|
| NME_CARD         | string  | Nome da carta                    | Sim         | Sim   | Title case, sem acentos        |
| NME_SET          | string  | Nome do conjunto                 | Sim         | Não   | Title case, sem acentos        |
| NME_TYPE         | string  | Tipo da carta                    | Sim         | Não   | Title case, sem acentos        |
| NME_RARITY       | string  | Raridade da carta                | Sim         | Não   | Title case, sem acentos        |
| NUM_CMC          | int     | Custo de mana convertido         | Não         | Não   | Nulos → 0                     |
| NME_COLORS       | string  | Cores da carta                   | Não         | Não   | Title case, sem acentos        |
| NME_MANA_COST    | string  | Custo de mana                    | Não         | Não   | Upper case                     |
| NUM_POWER        | int     | Poder da criatura                | Não         | Não   | Nulos → 0                     |
| NUM_TOUGHNESS    | int     | Resistência da criatura          | Não         | Não   | Nulos → 0                     |
| DESC_ORIGINAL_TEXT | string | Texto original da carta          | Não         | Não   | Title case, sem acentos        |
| NME_SOURCE       | string  | Fonte dos dados                  | Sim         | Não   |               |
| DT_INGESTION     | timestamp | Data/hora de ingestão           | Sim         | Não   |                               |
| RELEASE_YEAR     | int     | Ano de lançamento (particionamento) | Sim     | Não   | Derivado de NME_SET           |
| RELEASE_MONTH    | int     | Mês de lançamento (particionamento) | Sim     | Não   | Derivado de NME_SET           |

## 6. Regras de Implementação
- **Filtro temporal:** Não aplicado (dados históricos de cartas)
- **Deduplicação:** Por NME_CARD + NME_SET
- **Merge incremental:** Atualização inteligente de dados
- **Particionamento:** Por RELEASE_YEAR e RELEASE_MONTH
- **Limpeza:** Nulos → 0 para números, "NA" para strings

## 7. Transformações Aplicadas
| Transformação | Descrição |
|---------------|-----------|
| Title Case | Nomes de cartas, conjuntos, tipos e raridades em formato título |
| Upper Case | Custo de mana em maiúsculas |
| Limpeza de Nulos | Strings: nulos → "NA", Números: nulos → 0 |
| Conversão de Tipos | CMC, Power, Toughness para INT |
| Remoção de Duplicatas | Baseado em NME_CARD + NME_SET |
| Particionamento | Por ano e mês de lançamento do conjunto |

## 7.1 Regras de Negócio Aplicadas
| Regra de Negócio | Descrição |
|------------------|-----------|
| Filtro temporal | Apenas cartas dos últimos 5 anos são consideradas |
| Padronização de nomes | Nomes de cartas, artistas, raridades e sets em Title Case, sem acentos |
| Custo de mana | DESC_MANA_COST: nulos/vazios/"null" → "0"; MANA_COST nulo → 0 |
| Poder e resistência | NME_POWER e NME_TOUGHNESS nulos → 0 |
| Tipos de carta | Derivação de NME_CARD_TYPE e DESC_CARD_TYPE a partir do tipo original, separando subtipo se houver "—" |
| Cores | COD_COLORS nulo/vazio → "Colorless"; criação de NME_COLOR_CATEGORY (Colorless, Mono, Dual Color, Multicolor); QTY_COLORS: número de cores diferentes no custo de mana |
| Texto da carta | Substituição de símbolos de mana por nomes (ex: {W} → [White]), remoção de acentos, nulos → "NA" |
| Deduplicação | Por ID_CARD |
| Particionamento | Por ano e mês de ingestão (ANO_PART, MES_PART) |
| Merge incremental | Atualização inteligente dos dados por ID_CARD |
| Conversão de arrays/JSON | Arrays convertidos para string simples em colunas como NME_PRINTINGS, COD_COLORS, DESC_SUBTYPES |

## 7.2 Colunas Criadas na Silver
| Coluna             | Descrição                                                    |
|--------------------|-------------------------------------------------------------|
| NME_COLOR_CATEGORY | Categoria de cor da carta (Colorless, Mono, Dual, Multi)    |
| QTY_COLORS         | Quantidade de cores diferentes no custo de mana             |
| ANO_PART           | Ano de ingestão (particionamento físico)                    |
| MES_PART           | Mês de ingestão (particionamento físico)                    |
| NME_CARD_TYPE      | Tipo principal da carta (derivado)                          |
| DESC_CARD_TYPE     | Subtipo ou descrição detalhada do tipo (derivado)           |

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
- Dados históricos de cartas sem filtro temporal aplicado.
- Merge incremental baseado em NME_CARD + NME_SET.
- Valores numéricos nulos são convertidos para 0.
- Texto original preserva formatação original da carta. 