"""Ação e Subação na tela de NL.

Contém:
  - leitura/complemento das colunas Ação e Subação (planilha de NL e, se faltar,
    base do QlikView, sempre pela chave NE);
  - tabela expansível Ação -> Subação (mesmo estilo da tabela de credores);
  - relatório Excel por Ação e Subação (recorte do painel ou tudo).

O app cria as colunas Acao_Relacao e SubAcao_Relacao em carregar_dados_integrados()
e as usa nos filtros e nos componentes abaixo.
"""
from __future__ import annotations

import datetime
import io
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

TEMPLATE = Path(__file__).with_name("tabela_acoes_template.html")

SEM_ACAO = "NÃO INFORMADA"
SEM_SUBACAO = "NÃO INFORMADA"
_VAZIOS = {"", "NAN", "NONE", "NULL", "#N/A", "N/A", "#REF!", "#VALUE!", "-"}


# ----------------------------------------------------------------------------
# Leitura das colunas
# ----------------------------------------------------------------------------
def _norm(valor) -> str:
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]", "", texto.upper())


def col_por_nome(df: pd.DataFrame, alvo: str):
    """Acha a coluna pelo nome, ignorando acento, caixa e espaços ('SubAção' -> SUBACAO)."""
    return next((c for c in df.columns if _norm(c) == alvo), None)


def _texto(serie: pd.Series) -> pd.Series:
    s = serie.fillna("").astype(str).str.strip()
    return s.where(~s.str.upper().isin(_VAZIOS), "")


def extrair_acao_subacao_base(df1: pd.DataFrame) -> pd.DataFrame:
    """Cria Acao_Base1 / SubAcao_Base1 a partir da planilha de NL (se tiver as colunas)."""
    c_acao, c_sub = col_por_nome(df1, "ACAO"), col_por_nome(df1, "SUBACAO")
    df1["Acao_Base1"] = _texto(df1[c_acao]) if c_acao else ""
    df1["SubAcao_Base1"] = _texto(df1[c_sub]) if c_sub else ""
    return df1


def completar_acao_subacao(df: pd.DataFrame, df_qlik: pd.DataFrame, limpar_chave_ne) -> pd.DataFrame:
    """Cria Acao_Relacao / SubAcao_Relacao.

    Prioridade: valor já presente na planilha de NL; se vazio, busca na base do
    QlikView (BASE_TRATADA) pela NE, localizando as colunas Ação/Subação pelo nome
    do cabeçalho. Sem valor em nenhum lugar -> 'NÃO INFORMADA'.
    """
    df = df.copy()
    df["Acao_QLIK"] = ""
    df["SubAcao_QLIK"] = ""

    if df_qlik is not None and not df_qlik.empty and df_qlik.shape[1] >= 8:
        c_acao, c_sub = col_por_nome(df_qlik, "ACAO"), col_por_nome(df_qlik, "SUBACAO")
        if c_acao or c_sub:
            tmp = pd.DataFrame({
                "NE_Chave": limpar_chave_ne(df_qlik.iloc[:, 7]),  # coluna H = NE (igual ao marcador)
                "Acao_QLIK": _texto(df_qlik[c_acao]) if c_acao else "",
                "SubAcao_QLIK": _texto(df_qlik[c_sub]) if c_sub else "",
            })
            tmp = tmp[tmp["NE_Chave"] != ""]
            mapa = tmp.groupby("NE_Chave", as_index=False)[["Acao_QLIK", "SubAcao_QLIK"]].agg(
                lambda v: next((x for x in v if x), "")
            )
            df = df.drop(columns=["Acao_QLIK", "SubAcao_QLIK"]).merge(mapa, on="NE_Chave", how="left")
            df["Acao_QLIK"] = df["Acao_QLIK"].fillna("")
            df["SubAcao_QLIK"] = df["SubAcao_QLIK"].fillna("")

    base_acao = df["Acao_Base1"] if "Acao_Base1" in df.columns else ""
    base_sub = df["SubAcao_Base1"] if "SubAcao_Base1" in df.columns else ""
    acao = pd.Series(base_acao, index=df.index).astype(str).str.strip()
    sub = pd.Series(base_sub, index=df.index).astype(str).str.strip()
    df["Acao_Relacao"] = acao.where(acao != "", df["Acao_QLIK"]).replace("", SEM_ACAO)
    df["SubAcao_Relacao"] = sub.where(sub != "", df["SubAcao_QLIK"]).replace("", SEM_SUBACAO)
    return df


# ----------------------------------------------------------------------------
# Tabela Ação -> Subação
# ----------------------------------------------------------------------------
def _brl(v: float) -> str:
    s = f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def _qtd(n: int) -> str:
    return f"{int(n):,}".replace(",", ".")


def montar_acoes(df: pd.DataFrame) -> dict:
    """Dados numéricos para a tabela (a formatação em R$ é feita no navegador)."""
    if df.empty:
        return {"acoes": [], "totais": {"qtd": 0, "ret": 0.0, "tot": 0.0}}

    agg = (
        df.groupby(["Acao_Relacao", "SubAcao_Relacao"], as_index=False)
        .agg(qtd=("NL_Numero", "nunique"),
             ret=("Valor_Retido_Limpo", "sum"),
             tot=("Valor_Total_Limpo", "sum"))
    )
    por_acao = (
        df.groupby("Acao_Relacao")
        .agg(qtd=("NL_Numero", "nunique"),
             ret=("Valor_Retido_Limpo", "sum"),
             tot=("Valor_Total_Limpo", "sum"))
        .sort_values("tot", ascending=False)
    )

    acoes = []
    for i, (acao, t) in enumerate(por_acao.iterrows(), start=1):
        subs = agg[agg["Acao_Relacao"] == acao].sort_values("tot", ascending=False)
        acoes.append({
            "id": i,
            "name": str(acao),
            "qtd": int(t["qtd"]),
            "ret": round(float(t["ret"]), 2),
            "tot": round(float(t["tot"]), 2),
            "expanded": False,
            "items": [
                {"sub": str(r.SubAcao_Relacao), "qtd": int(r.qtd),
                 "ret": round(float(r.ret), 2), "tot": round(float(r.tot), 2)}
                for r in subs.itertuples(index=False)
            ],
        })
    totais = {
        "qtd": int(df["NL_Numero"].nunique()),
        "ret": round(float(df["Valor_Retido_Limpo"].sum()), 2),
        "tot": round(float(df["Valor_Total_Limpo"].sum()), 2),
    }
    return {"acoes": acoes, "totais": totais}


def renderizar_html(dados: dict) -> str:
    js = json.dumps(dados, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.read_text(encoding="utf-8").replace("__DADOS_JSON__", js)


def exibir_tabela_acoes(df_filtrado: pd.DataFrame, altura: int | None = None) -> None:
    """Mostra a tabela. A altura é ajustada pelo próprio HTML (recolhida = tudo visível,
    sem rolagem); o parâmetro `altura` é mantido só por compatibilidade e é ignorado.
    A altura inicial abaixo é uma estimativa até o navegador medir o conteúdo real."""
    import streamlit.components.v1 as components

    dados = montar_acoes(df_filtrado)
    estimada = min(max(230 + 80 * len(dados["acoes"]), 260), 1000)
    components.html(renderizar_html(dados), height=estimada, scrolling=True)


# ----------------------------------------------------------------------------
# Relatório Excel
# ----------------------------------------------------------------------------
_NATUREZA_EXIBICAO = {"SEM_CLASSE": "N/C"}

# (coluna no app, título no Excel, tipo)
_COLUNAS_DETALHE = [
    ("Acao_Relacao", "Ação", "texto"),
    ("SubAcao_Relacao", "Subação", "texto"),
    ("Credor_Tratado", "Nome do Credor", "texto"),
    ("Objeto_Relacao", "Objeto Despesa", "texto"),
    ("Grupo_Classificado", "GD", "texto"),
    ("NL_Numero", "Número NL", "texto"),
    ("NE_Chave", "NE", "texto"),
    ("Data_DT", "Emissão", "data"),
    ("Natureza_NL", "Natureza", "natureza"),
    ("Status_Filtro", "Status", "texto"),
    ("Fonte_Relacao", "Fonte", "texto"),
    ("Marcador_Fonte_Relacao", "Marcador de Fonte", "texto"),
    ("Valor_Retido_Limpo", "Valor Retido", "moeda"),
    ("Valor_Total_Limpo", "Valor", "moeda"),
]


def gerar_relatorio_excel(df: pd.DataFrame, recorte: str = "") -> bytes:
    """Preenche uma cópia do modelo oficial, preservando a Tabela Dinâmica."""
    import zipfile
    import html
    import datetime as dt

    if df.empty:
        raise ValueError("Não há liquidações para o recorte escolhido.")

    modelo = Path(__file__).resolve().parent.parent / "modelos" / "modelo_Relatorio_por_ Ação_ e_Subação.xlsx"

    if not modelo.exists():
        raise FileNotFoundError(f"Modelo oficial não encontrado: {modelo}")

    colunas = _COLUNAS_DETALHE
    ultima_coluna = "N"

    chaves_ordenacao = [
        c for c in [
            "Acao_Relacao",
            "SubAcao_Relacao",
            "Credor_Tratado",
            "NL_Numero",
        ] if c in df.columns
    ]

    base = df.copy()

    if chaves_ordenacao:
        base = base.sort_values(chaves_ordenacao, kind="stable")

    def texto_xml(valor):
        if pd.isna(valor):
            valor = ""
        valor = str(valor)
        valor = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", valor)
        return html.escape(valor, quote=False)

    def celula_texto(referencia, valor, estilo):
        conteudo = texto_xml(valor)
        return (
            f'<c r="{referencia}" s="{estilo}" t="inlineStr">'
            f'<is><t xml:space="preserve">{conteudo}</t></is></c>'
        )

    def celula_numero(referencia, valor, estilo):
        numero = float(valor) if pd.notna(valor) else 0.0
        return f'<c r="{referencia}" s="{estilo}"><v>{numero:.15g}</v></c>'

    estilos = {
        0: 2, 1: 4, 2: 2, 3: 2,
        4: 4, 5: 4, 6: 4, 7: 5,
        8: 6, 9: 4, 10: 4, 11: 4,
        12: 3, 13: 3,
    }

    linhas_xml = []

    for numero_linha, registro in enumerate(base.to_dict("records"), start=2):
        celulas = []

        for indice, (campo, titulo, tipo) in enumerate(colunas):
            referencia = f"{chr(65 + indice)}{numero_linha}"
            valor = registro.get(campo)
            estilo = estilos[indice]

            if tipo == "moeda":
                celulas.append(celula_numero(referencia, valor, estilo))

            elif tipo == "data":
                data = pd.to_datetime(valor, errors="coerce")

                if pd.isna(data):
                    celulas.append(celula_texto(referencia, "", estilo))
                else:
                    data = data.to_pydatetime()
                    serial = (data - dt.datetime(1899, 12, 30)).total_seconds() / 86400
                    celulas.append(celula_numero(referencia, serial, estilo))

            elif tipo == "natureza":
                exibicao = "" if pd.isna(valor) else _NATUREZA_EXIBICAO.get(str(valor), str(valor))
                celulas.append(celula_texto(referencia, exibicao, estilo))

            else:
                celulas.append(celula_texto(referencia, valor, estilo))

        linhas_xml.append(
            f'<row r="{numero_linha}" ht="20.1" customHeight="1">'
            + "".join(celulas)
            + "</row>"
        )

    ultima_linha = len(base) + 1
    novo_intervalo = f"A1:{ultima_coluna}{ultima_linha}"

    saida = io.BytesIO()

    with zipfile.ZipFile(modelo, "r") as origem:
        arquivos = {item.filename: origem.read(item.filename) for item in origem.infolist()}
        informacoes = {item.filename: item for item in origem.infolist()}

    caminho_detalhe = "xl/worksheets/sheet2.xml"
    caminho_cache = "xl/pivotCache/pivotCacheDefinition1.xml"
    caminho_workbook = "xl/workbook.xml"

    for caminho in [caminho_detalhe, caminho_cache, caminho_workbook]:
        if caminho not in arquivos:
            raise ValueError(f"Componente esperado não encontrado no modelo: {caminho}")

    # Atualiza somente as linhas de dados da aba Detalhe NL.
    detalhe = arquivos[caminho_detalhe].decode("utf-8")

    padrao_sheetdata = r"(<sheetData\b[^>]*>)(.*?)(</sheetData>)"
    correspondencia = re.search(padrao_sheetdata, detalhe, flags=re.S)

    if not correspondencia:
        raise ValueError("Não foi possível localizar a área de dados da aba Detalhe NL.")

    conteudo_antigo = correspondencia.group(2)
    cabecalho = re.search(
        r'<row\b[^>]*\br="1"[^>]*>.*?</row>',
        conteudo_antigo,
        flags=re.S,
    )

    if not cabecalho:
        raise ValueError("Não foi possível preservar o cabeçalho da aba Detalhe NL.")

    novo_conteudo = cabecalho.group(0) + "".join(linhas_xml)

    detalhe = (
        detalhe[:correspondencia.start()]
        + correspondencia.group(1)
        + novo_conteudo
        + correspondencia.group(3)
        + detalhe[correspondencia.end():]
    )

    detalhe = re.sub(
        r'<dimension\b[^>]*/>',
        f'<dimension ref="{novo_intervalo}"/>',
        detalhe,
        count=1,
    )

    detalhe = re.sub(
        r'ref="A1:N\d+"',
        f'ref="{novo_intervalo}"',
        detalhe,
    )

    arquivos[caminho_detalhe] = detalhe.encode("utf-8")

    # Atualiza a origem da Tabela Dinâmica.
    cache = arquivos[caminho_cache].decode("utf-8")

    cache = re.sub(
        r'(<pivotCacheDefinition\b[^>]*?)\srefreshOnLoad="[^"]*"',
        r'\1',
        cache,
    )
    cache = re.sub(
        r'(<pivotCacheDefinition\b[^>]*?)\senableRefresh="[^"]*"',
        r'\1',
        cache,
    )

    cache = re.sub(
        r'<pivotCacheDefinition\b',
        '<pivotCacheDefinition refreshOnLoad="1" enableRefresh="1"',
        cache,
        count=1,
    )

    cache, quantidade = re.subn(
        r'(<worksheetSource\b[^>]*\bref=")[^"]*(")',
        rf'\g<1>{novo_intervalo}\g<2>',
        cache,
        count=1,
    )

    if quantidade == 0:
        raise ValueError("Não foi possível atualizar a origem da Tabela Dinâmica.")

    arquivos[caminho_cache] = cache.encode("utf-8")

    # Atualiza o intervalo do filtro definido para Detalhe NL.
    workbook = arquivos[caminho_workbook].decode("utf-8")

    workbook, quantidade = re.subn(
        r'(<definedName\b[^>]*name="_xlnm\._FilterDatabase"[^>]*>).*?(</definedName>)',
        rf"\g<1>'Detalhe NL'!$A$1:$N${ultima_linha}\g<2>",
        workbook,
        count=1,
        flags=re.S,
    )

    if quantidade == 0:
        raise ValueError("Não foi possível atualizar o intervalo do filtro do modelo.")

    arquivos[caminho_workbook] = workbook.encode("utf-8")

    # Monta uma cópia em memória, mantendo os demais componentes do modelo.
    with zipfile.ZipFile(saida, "w", compression=zipfile.ZIP_DEFLATED) as destino:
        for nome, conteudo in arquivos.items():
            destino.writestr(informacoes[nome], conteudo)

    resultado = saida.getvalue()

    # Valida o arquivo gerado antes de entregá-lo ao aplicativo.
    with zipfile.ZipFile(io.BytesIO(resultado), "r") as teste:
        erro = teste.testzip()

        if erro:
            raise ValueError(f"Falha na validação do arquivo Excel: {erro}")

        import xml.etree.ElementTree as ET
        ET.fromstring(teste.read(caminho_detalhe))
        ET.fromstring(teste.read(caminho_cache))
        ET.fromstring(teste.read(caminho_workbook))

    return resultado
