# ============================================================================
# SILVER COLUMN DOCS - comentários de tabela/coluna pro Unity Catalog
# ============================================================================
"""
Fonte única dos comentários de tabela e coluna da Silver: usada por
silver_utils.save_to_silver / SilverTableProcessor.save_silver_table
(COMMENT ON TABLE / ALTER COLUMN...COMMENT no Unity Catalog) e pelos READMEs
de cada tabela em Documentação/ - evita descrever a mesma coluna em dois
lugares que divergem com o tempo.

Descrições voltadas pro negócio (o que a coluna significa pra quem consome o
dado), não pra como ela foi calculada - isso já está no notebook.

Cada notebook de tabela chama get_table_comment(nome)/get_column_comments(nome)
e repassa pro save_silver_table. Não faz %run aninhado aqui (AUD-10 só resolve
%run um nível) - importar via %run ./silver_column_docs direto no notebook,
sem dependência de dbutils/spark (é só dado estático), mesmo padrão de
bronze_column_docs.py.
"""

# Colunas técnicas presentes em toda tabela Silver (linhagem até a Stage/Bronze) -
# mesma descrição em qualquer tabela, uma vez só aqui.
COMMON_COLUMNS = {
    "Dt_ingestao": "Data/hora em que o dado de origem foi coletado da fonte.",
    "Nme_fonte": "Fonte de dados de origem (ex.: 'scryfall').",
    "Desc_url_origem": "Endpoint/URL da API de origem do dado.",
    "Desc_arquivo_origem": "Caminho do arquivo de origem na camada Bronze - usado só para auditoria/rastreabilidade.",
    "Id_execucao_bronze": "Id da execução da Bronze que originou esta linha - usado só para auditoria/rastreabilidade.",
    "Dt_ingestao_bronze": "Data/hora em que a Bronze processou o registro - usado só para auditoria/rastreabilidade.",
}

SILVER_TABLES = {
    "TB_FATO_CARTAS": {
        "comment": "Catálogo de cartas de Magic: The Gathering - uma linha por impressão/edição de carta, pronta para análise de gameplay, deckbuilding e coleção. Responde 'o que é essa carta': texto de regras, custo de mana, tipo, raridade, artista e em qual coleção ela saiu. Preço e histórico de migração de id ficam em tabelas próprias (TB_FATO_PRECOS_CARTAS, TB_MOV_MIGRACOES_CARTAS) - junte por Nme_carta/Id_carta quando precisar combinar.",
        "columns": {
            "Id_carta": "Id único da impressão desta carta. Preservado como veio da fonte - nunca reatribuído, mesmo quando a Scryfall unifica cartas (ver TB_MOV_MIGRACOES_CARTAS para o id canônico pós-migração).",
            "Id_oracle": "Identificador da carta estável entre todas as suas impressões (diferentes edições da mesma carta compartilham este id). Use para agrupar todas as versões de uma carta.",
            "Nme_carta": "Nome da carta.",
            "Desc_custo_mana": "Custo de mana para conjurar a carta, em notação de símbolos.",
            "Qtd_custo_mana": "Custo de mana convertido (CMC) - número total de mana necessário, usado para curva de mana do deck.",
            "Cod_cores": "Cores da carta.",
            "Cod_identidade_cor": "Identidade de cor da carta - relevante para montar deck em formatos como Commander.",
            "Nme_tipo_carta": "Tipo principal da carta (Creature, Instant, Planeswalker...).",
            "Desc_detalhe_tipo_carta": "Complemento do tipo quando a carta tem subtítulo próprio (ex.: nome de um Planeswalker no lugar do subtipo).",
            "Desc_tipos": "Tipos da carta.",
            "Desc_subtipos": "Subtipos da carta (raça/classe da criatura, tipo de feitiço, etc.).",
            "Nme_raridade": "Raridade desta impressão da carta.",
            "Cod_colecao": "Coleção/edição em que esta impressão da carta saiu. Junte com TB_DIM_COLECOES para detalhes da coleção.",
            "Nme_colecao": "Nome da coleção/edição em que esta impressão da carta saiu.",
            "Desc_carta": "Texto de regras impresso na carta - o que ela faz.",
            "Nme_artista": "Ilustrador responsável pela arte desta impressão.",
            "Num_colecionador": "Número de colecionador desta carta dentro da coleção - usado para identificar a carta fisicamente num booster/pacote.",
            "Nme_forca": "Força da criatura em combate.",
            "Nme_resistencia": "Resistência da criatura em combate (dano que suporta antes de morrer).",
            "Nme_disposicao_carta": "Formato físico da carta (carta simples, carta dupla/split, transformável, etc.).",
            "Id_multiverso": "Id desta carta no banco oficial de cartas da Wizards (Gatherer) - use para linkar a carta na fonte oficial.",
            "Url_imagem": "Endereço da imagem desta impressão da carta.",
            "Cod_variacoes": "Outras impressões/variações visuais da mesma carta.",
            "Desc_nomes_estrangeiros": "Nome e texto desta carta traduzidos para outros idiomas.",
            "Desc_impressoes": "Todas as coleções em que esta carta já foi impressa.",
            "Desc_carta_original": "Texto de regras desta carta como impresso originalmente, antes de qualquer correção oficial (errata).",
            "Nme_tipo_original": "Linha de tipo original da carta, antes de reclassificações oficiais.",
            "Desc_legalidades": "Em quais formatos de jogo (Standard, Commander, Modern...) esta carta é permitida.",
            "Nme_categoria_cor": "Categoria de cor da carta derivada do custo de mana (Incolor, Monocolor, Bicolor, Multicolor) - facilita agrupar cartas por perfil de cor.",
            "Qtd_cores": "Quantidade de cores distintas no custo de mana da carta.",
            "Ano_ingestao": "Ano da coleta do dado de origem - usado só para particionamento físico da tabela.",
            "Mes_ingestao": "Mês da coleta do dado de origem - usado só para particionamento físico da tabela.",
        },
    },
    "TB_DIM_COLECOES": {
        "comment": "Catálogo das coleções/edições de Magic: The Gathering já lançadas, incluindo edições só digitais. Responde 'quando saiu, quantas cartas tem, a que bloco pertence e o que vem num pacote de booster' - use para organizar a coleção por edição ou situar uma carta na linha do tempo do jogo.",
        "columns": {
            "Cod_colecao": "Código curto da coleção/edição (ex.: 'M19').",
            "Nme_colecao": "Nome completo da coleção/edição.",
            "Nme_tipo_colecao": "Tipo da coleção (edição principal, masters, promocional, etc.).",
            "Nme_cor_borda": "Cor de borda padrão das cartas desta coleção.",
            "Id_cardmarket": "Id desta coleção na Cardmarket - use para cruzar com dado de preço/mercado europeu.",
            "Nme_cardmarket": "Nome desta coleção na Cardmarket - pode diferir do nome oficial.",
            "Dt_lancamento": "Data de lançamento da coleção.",
            "Cod_gatherer": "Código desta coleção no banco oficial de cartas da Wizards (Gatherer).",
            "Cod_magiccardsinfo": "Código desta coleção no site magiccards.info.",
            "Cod_antigo": "Código anterior da coleção, se ela já foi renomeada.",
            "Flg_somente_online": "Indica se a coleção só existe em ambiente digital (Arena/MTGO), sem versão física.",
            "Qtd_cartas": "Quantidade de cartas que compõem a coleção.",
            "Cod_colecao_pai": "Coleção 'pai', quando esta é uma sub-coleção (ex.: promoções vinculadas a uma edição principal).",
            "Nme_bloco": "Bloco de expansão ao qual a coleção pertence.",
            "Url_icone": "Endereço do ícone que representa a coleção.",
            **{f"Desc_booster_slot_{i}": f"Tipo de carta possível na posição {i} de um pacote de booster desta coleção." for i in range(20)},
            "Ano_lancamento": "Ano de lançamento da coleção - usado só para particionamento físico da tabela.",
            "Mes_lancamento": "Mês de lançamento da coleção - usado só para particionamento físico da tabela.",
        },
    },
    "TB_FATO_PRECOS_CARTAS": {
        "comment": "Histórico de cotações de preço de cartas de Magic: The Gathering em dólar, euro e MTGO ticket - uma linha por coleta de preço. Use para acompanhar valorização/desvalorização de uma carta ao longo do tempo, comparar preço entre cartas/coleções ou montar um indicador de valor de coleção. A mesma carta tem várias linhas (uma por coleta) de propósito - é histórico, não é 'o preço atual'.",
        "columns": {
            "Nme_carta": "Carta a que esta cotação de preço se refere. Uma cotação se aplica a todas as impressões da carta com este nome - junte com TB_FATO_CARTAS.Nme_carta.",
            "Cod_colecao": "Coleção/edição de referência usada nesta coleta de preço.",
            "Nme_raridade": "Raridade de referência usada nesta coleta de preço.",
            "Vlr_usd": "Preço em dólares americanos. NULO significa que não havia cotação em dólar nesta coleta, não que a carta vale zero.",
            "Vlr_eur": "Preço em euros. NULO significa que não havia cotação em euro nesta coleta, não que a carta vale zero.",
            "Vlr_tix": "Preço em MTGO tickets (moeda do Magic Online). NULO significa que não havia cotação em tix nesta coleta, não que a carta vale zero.",
            "Url_scryfall": "Endereço da página desta carta na Scryfall.",
            "Url_imagem": "Endereço da imagem de referência usada nesta coleta de preço.",
            "Dt_lancamento": "Data de lançamento da coleção de referência usada nesta coleta de preço.",
            "Ano_ingestao": "Ano da coleta de preço - usado só para particionamento físico da tabela.",
            "Mes_ingestao": "Mês da coleta de preço - usado só para particionamento físico da tabela.",
        },
    },
    "TB_MOV_MIGRACOES_CARTAS": {
        "comment": "Histórico de trocas de identificador de carta feitas pela Scryfall, quando duas cartas são unificadas em uma só ou uma é removida do catálogo. Use para reconciliar um id antigo de carta com o id vigente e não perder o vínculo em análises feitas antes da mudança - Id_carta_canonico já traz o id final, mesmo quando a carta passou por várias migrações em cadeia.",
        "columns": {
            "Id_migracao": "Id único deste registro de migração.",
            "Url_scryfall": "Endereço da API da Scryfall para este registro de migração.",
            "Dt_execucao": "Data em que esta migração de id foi executada.",
            "Nme_estrategia_migracao": "Como a migração foi feita: unificação de duas cartas em uma só, ou remoção de uma carta do catálogo.",
            "Id_carta_antigo": "Id de carta que deixou de ser usado por causa desta migração.",
            "Id_carta_novo": "Id de carta que passou a valer no lugar do antigo, quando a migração foi uma unificação. Vazio quando a migração foi uma remoção.",
            "Id_carta_canonico": "Id de carta final, já resolvido até a última migração da cadeia (uma carta pode ser migrada mais de uma vez) - use este id, não Id_carta_novo, para sempre chegar na versão vigente.",
            "Desc_nota": "Explicação, quando fornecida, do motivo desta migração.",
            "Id_carta_associada": "Carta associada a este registro de migração.",
            "Cod_idioma": "Idioma da carta associada a este registro de migração.",
            "Nme_carta_associada": "Nome da carta associada a este registro de migração.",
            "Cod_colecao_associada": "Coleção da carta associada a este registro de migração.",
            "Id_oracle_associado": "Identificador estável (entre impressões) da carta associada a este registro de migração.",
            "Num_colecionador_associado": "Número de colecionador da carta associada a este registro de migração.",
            "Ano_execucao": "Ano de execução da migração - usado só para particionamento físico da tabela.",
            "Mes_execucao": "Mês de execução da migração - usado só para particionamento físico da tabela.",
        },
    },
    "TB_DOM_SIMBOLOS": {
        "comment": "Lista de referência dos símbolos de mana e custo que aparecem no texto e no custo de mana das cartas (ex.: símbolo de mana branca, símbolo de taps). Use para traduzir/exibir corretamente esses símbolos e para saber quanto cada um vale em custo de mana. Lista de apoio, praticamente estática - raramente ganha símbolo novo.",
        "columns": {
            "Cod_simbolo": "Código do símbolo, na mesma notação usada em Desc_custo_mana/Desc_carta de TB_FATO_CARTAS - junte por este código para traduzir um símbolo encontrado no texto de uma carta.",
            "Url_icone": "Endereço da imagem deste símbolo.",
            "Desc_variante_livre": "Forma alternativa de escrever este símbolo em texto livre, quando existe.",
            "Desc_simbolo": "Descrição deste símbolo em texto.",
            "Flg_transponivel": "Indica se este símbolo pode aparecer em ordem trocada dentro de um texto de regra.",
            "Flg_representa_mana": "Indica se este símbolo representa mana (nem todo símbolo representa - alguns são custos não-mana, como o de virar a carta).",
            "Flg_aparece_custo_mana": "Indica se este símbolo pode aparecer no custo de mana de uma carta.",
            "Qtd_valor_mana": "Quanto este símbolo contribui para o custo convertido de mana de uma carta.",
            "Flg_hibrido": "Indica se é um símbolo de mana híbrida (pode ser pago com qualquer uma de duas cores).",
            "Flg_phyrexiano": "Indica se é um símbolo de mana phyrexiana (pode ser pago com mana de uma cor ou com pontos de vida).",
            "Qtd_custo_convertido": "Custo de mana convertido equivalente deste símbolo, quando difere de Qtd_valor_mana em casos especiais.",
            "Flg_humoristico": "Indica se este símbolo só aparece em cartas não-oficiais/humorísticas.",
            "Cod_cores": "Cor(es) de mana associada(s) a este símbolo.",
            "Desc_grafias_gatherer": "Formas alternativas deste símbolo usadas no banco oficial de cartas da Wizards (Gatherer).",
        },
    },
    "TB_FATO_ESCLARECIMENTOS_CARTAS": {
        "comment": "Esclarecimentos oficiais de regras (rulings) publicados para cartas específicas de Magic: The Gathering, ligados por Id_oracle a todas as impressões da carta. Use para responder dúvida de interação entre cartas ou interpretação de regra que o texto da carta sozinha não deixa claro - uma carta pode acumular vários esclarecimentos ao longo do tempo.",
        "columns": {
            "Id_esclarecimento": "Id único deste esclarecimento (gerado a partir do conteúdo, pois a fonte não fornece um id próprio).",
            "Id_oracle": "Carta a que este esclarecimento se aplica (mesmo valor para todas as impressões da carta) - junte com TB_FATO_CARTAS.Id_oracle.",
            "Nme_emissor": "Quem emitiu este esclarecimento: a própria Wizards (oficial) ou a Scryfall (complementar).",
            "Dt_publicacao": "Data de publicação deste esclarecimento.",
            "Desc_esclarecimento": "Texto do esclarecimento de regras.",
            "Ano_publicacao": "Ano de publicação do esclarecimento - usado só para particionamento físico da tabela.",
            "Mes_publicacao": "Mês de publicação do esclarecimento - usado só para particionamento físico da tabela.",
        },
    },
}


def get_table_comment(silver_table_name):
    return SILVER_TABLES.get(silver_table_name, {}).get("comment")


def get_column_comments(silver_table_name):
    """COMMON_COLUMNS + colunas específicas da tabela (específica vence em conflito de chave)."""
    table_columns = SILVER_TABLES.get(silver_table_name, {}).get("columns", {})
    return {**COMMON_COLUMNS, **table_columns}


if __name__ == "__main__":
    for table_name in SILVER_TABLES:
        assert get_table_comment(table_name), f"{table_name} sem comment de tabela"
    cartas_comments = get_column_comments("TB_FATO_CARTAS")
    assert cartas_comments["Dt_ingestao"] == COMMON_COLUMNS["Dt_ingestao"]
    assert cartas_comments["Nme_carta"] == SILVER_TABLES["TB_FATO_CARTAS"]["columns"]["Nme_carta"]
    assert get_table_comment("inexistente") is None
    assert get_column_comments("inexistente") == COMMON_COLUMNS
    print("silver_column_docs: OK")
