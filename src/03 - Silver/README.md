# Camada Silver - Magic: The Gathering

## 🎯 **Objetivo**
Transformar dados da camada Bronze em dados limpos, normalizados e padronizados para uso na camada Gold.

## 📊 **Convenções de Nomenclatura**

### **Padrões GOV Aplicados**
- **NME_**: Prefixo para nomes/descrições
- **COD_**: Prefixo para códigos
- **ID_**: Prefixo para identificadores únicos
- **FLG_**: Prefixo para flags booleanos
- **DT_**: Prefixo para datas/timestamps
- **TXT_**: Prefixo para textos longos

### **Abreviações GOV**
- **NOME → NME**
- **DATA → DT**
- **TEXTO → TXT**

## 🃏 **Dicionário de Dados - Tabela Cards**

### **📋 Tabela Principal: `silver.cards`**

### **Identificação**
| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `ID_CARD` | STRING | Identificador único da carta | "0000579f-7b35-4ed3-b44c-db2a538066fe" |
| `NME_CARD` | STRING | Nome da carta (capitalizado, sem acentos) | "Lightning Bolt" |

### **Custo e Tipo**
| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `DESC_MANA_COST` | STRING | Custo de mana original | "{R}" |
| `MANA_COST` | INTEGER | Custo de mana convertido (CMC) | 1 |
| `NME_CARD_TYPE` | STRING | Tipo principal da carta | "Instant" |
| `DESC_CARD_TYPE` | STRING | Subtipo da carta | "Arcane" |
| `NME_RARITY` | STRING | Raridade da carta | "Common" |

### **Cores**
| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `COD_COLORS` | STRING | Códigos de cores normalizados | "Red" |
| `NME_COLOR_CATEGORY` | STRING | Categoria: Colorless/Mono/Dual Color/Multicolor | "Mono" |

### **Estatísticas de Criatura**
| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `NME_POWER` | INTEGER | Ataque da criatura | 3 |
| `NME_TOUGHNESS` | INTEGER | Defesa da criatura | 2 |

### **Informações de Edição**
| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `COD_SET` | STRING | Código da edição | "NEO" |
| `NME_ARTIST` | STRING | Nome do artista | "Christopher Rush" |

### **Texto da Carta**
| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `DESC_CARD` | STRING | Texto da carta limpo e normalizado | "Lightning Bolt deals 3 damage to any target." |

### **Habilidades**
| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `COD_DIM_HABILITY` | ARRAY<STRING> | Array de chaves MD5 das habilidades | ["a1b2c3d4..."] |

### **📋 Tabela de Dimensão: `silver.dim_habilities`**

### **Identificação da Habilidade**
| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `COD_DIM_HABILITY` | STRING | Chave MD5 determinística da habilidade | "a1b2c3d4e5f6..." |
| `NME_HABILITY` | STRING | Nome da habilidade (capitalizado) | "Flying" |
| `DESC_HABILITY_LOWER` | STRING | Nome da habilidade em minúsculas | "flying" |

### **Estatísticas**
| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `QTD_CARDS_WITH_ABILITY` | INTEGER | Quantidade de cartas com a habilidade | 150 |

### **Metadados**
| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `DTH_CREATION` | TIMESTAMP | Data de criação do registro | 2024-01-15 10:30:00 |
| `NME_SOURCE` | STRING | Fonte dos dados | "silver_pipeline" |

### **Metadados de Qualidade**
| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `SCORE_QUALIDADE` | INTEGER | Score de qualidade dos dados | 95 |
| `NME_STATUS_VALIDACAO` | STRING | Status da validação | "Validated" |
| `DT_ULT_VALIDACAO` | TIMESTAMP | Data da última validação | 2024-01-15 10:30:00 |

### **Auditoria**
| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `DT_CRIACAO` | TIMESTAMP | Data de criação do registro | 2024-01-15 10:30:00 |
| `DT_ATUALIZACAO` | TIMESTAMP | Data da última atualização | 2024-01-15 10:30:00 |

### **Particionamento**
| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `ANO_PART` | INTEGER | Ano do particionamento | 2024 |
| `MES_PART` | INTEGER | Mês do particionamento | 1 |

## 🔧 **Transformações Aplicadas**

### **1. Padronização de Texto**
- Capitalização inteligente por palavra (INITCAP)
- Remoção de acentos e normalização
- Limpeza de quebras de linha e aspas duplicadas
- Conversão de símbolos de mana para texto legível

### **2. Tratamento de Nulos**
- MANA_COST: COALESCE para 0
- NME_POWER/NME_TOUGHNESS: COALESCE para 0
- COD_COLORS: Array vazio → 'Colorless'
- DESC_CARD: NULL → 'NA'

### **3. Normalização de Tipos**
- Separação de tipo principal e subtipo
- Cores: Array → String normalizado
- Categorização de cores: Colorless/Mono/Dual Color/Multicolor
- Conversão de power/toughness para INTEGER

### **4. Cálculo de CMC**
- Soma de números no custo de mana
- Contagem de símbolos de cor
- Resultado: MANA_COST (CMC total)

### **5. Dimensão de Habilidades**
- Extração de habilidades via regex
- Geração de chaves MD5 determinísticas
- Criação de tabela de dimensão
- Array de chaves na tabela principal

### **6. Schema Padronizado**
- Nomenclatura GOV consistente
- Colunas atômicas (sem arrays/objetos)
- Metadados de auditoria

## 📈 **Validações Implementadas**

```sql
-- Validações básicas - Tabela Cards
SELECT COUNT(*) as total FROM silver.cards
SELECT COUNT(*) as nomes_nulos FROM silver.cards WHERE NME_CARD IS NULL
SELECT COUNT(*) as tipos_nulos FROM silver.cards WHERE NME_CARD_TYPE IS NULL
SELECT COUNT(*) as incolores FROM silver.cards WHERE NME_COLOR_CATEGORY = 'Colorless'
SELECT COUNT(*) as com_habilidades FROM silver.cards WHERE SIZE(COD_DIM_HABILITY) > 0

-- Validações - Tabela de Habilidades
SELECT COUNT(*) as total_habilidades FROM silver.dim_habilities
SELECT COUNT(*) as chaves_nulas FROM silver.dim_habilities WHERE COD_DIM_HABILITY IS NULL
SELECT COUNT(*) as nomes_nulos FROM silver.dim_habilities WHERE NME_HABILITY IS NULL
SELECT TOP 10 NME_HABILITY, QTD_CARDS_WITH_ABILITY FROM silver.dim_habilities ORDER BY QTD_CARDS_WITH_ABILITY DESC
```

## 🎮 **Conceitos MTG Aplicados**

### **Cores do Magic**
- **W**: White (Branco)
- **U**: Blue (Azul)
- **B**: Black (Preto)
- **R**: Red (Vermelho)
- **G**: Green (Verde)
- **Array vazio**: Colorless (Incolor)

### **Categorias de Cor**
- **Incolor**: Cartas sem cor
- **Mono**: Cartas de uma cor
- **Multicolor**: Cartas de múltiplas cores

### **Tipos de Carta**
- Creature (Criatura)
- Instant (Instantâneo)
- Sorcery (Feitiço)
- Enchantment (Encantamento)
- Artifact (Artefato)
- Planeswalker (Planeswalker)
- Land (Terreno)

## 🚀 **Como Usar**

### **Query de Exemplo - Cards**
```sql
SELECT 
    ID_CARD,
    NME_CARD,
    NME_CARD_TYPE,
    NME_COLOR_CATEGORY,
    MANA_COST,
    NME_POWER,
    NME_TOUGHNESS,
    COD_DIM_HABILITY
FROM silver.cards 
WHERE NME_POWER > 0
LIMIT 10
```

### **Query de Exemplo - Habilidades**
```sql
SELECT 
    COD_DIM_HABILITY,
    NME_HABILITY,
    QTD_CARDS_WITH_ABILITY
FROM silver.dim_habilities 
ORDER BY QTD_CARDS_WITH_ABILITY DESC
LIMIT 10
```

### **Query de Exemplo - Join Cards e Habilidades**
```sql
SELECT 
    c.ID_CARD,
    c.NME_CARD,
    c.NME_CARD_TYPE,
    h.NME_HABILITY
FROM silver.cards c
LATERAL VIEW EXPLODE(c.COD_DIM_HABILITY) abilities AS ability_key
JOIN silver.dim_habilities h ON h.COD_DIM_HABILITY = ability_key
WHERE c.NME_CARD_TYPE = 'Creature'
LIMIT 10
```

### **Filtros Comuns**
```sql
-- Criaturas vermelhas
WHERE COD_COLORS = 'Red' AND NME_POWER > 0

-- Cartas de custo baixo
WHERE MANA_COST <= 2

-- Cartas raras
WHERE NME_RARITY = 'Rare'

-- Cartas com habilidades específicas
WHERE ARRAY_CONTAINS(COD_DIM_HABILITY, MD5('flying'))

-- Criaturas com poder alto
WHERE NME_POWER >= 5 AND NME_TOUGHNESS >= 5
```

## 📝 **Notas de Implementação**

- **Unity Catalog**: Tabela registrada com comentários
- **Particionamento**: Por ano e mês para performance
- **UDFs**: Funções personalizadas para transformações complexas
- **Logs**: Logs formais sem informações sensíveis
- **Validação**: Score de qualidade e status de validação

## 🔄 **Próximos Passos**

1. **Camada Gold**: Agregações e lógica de negócio
2. **Views**: Para consultas frequentes
3. **Dashboards**: Visualizações dos dados
4. **Alertas**: Monitoramento de qualidade 