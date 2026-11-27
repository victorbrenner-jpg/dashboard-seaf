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
    """Excel com: (1) resumo Ação x Subação com subtotais; (2) detalhe das NLs."""
    if df.empty:
        raise ValueError("Não há liquidações para o recorte escolhido.")
    import xlsxwriter

    saida = io.BytesIO()
    wb = xlsxwriter.Workbook(saida, {"in_memory": True, "nan_inf_to_errors": True})

    azul = "#002855"
    f_titulo = wb.add_format({"bold": True, "font_size": 14, "font_color": azul})
    f_sub = wb.add_format({"italic": True, "font_color": "#64748B"})
    f_cab = wb.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": azul,
                           "border": 1, "align": "center", "valign": "vcenter", "text_wrap": True})
    f_txt = wb.add_format({"border": 1, "valign": "top", "text_wrap": True})
    f_int = wb.add_format({"border": 1, "num_format": "#,##0", "align": "center"})
    f_moeda = wb.add_format({"border": 1, "num_format": 'R$ #,##0.00'})
    f_data = wb.add_format({"border": 1, "num_format": "dd/mm/yyyy", "align": "center"})
    f_centro = wb.add_format({"border": 1, "align": "center"})
    f_st_txt = wb.add_format({"bold": True, "border": 1, "bg_color": "#E2E8F0", "text_wrap": True})
    f_st_int = wb.add_format({"bold": True, "border": 1, "bg_color": "#E2E8F0",
                              "num_format": "#,##0", "align": "center"})
    f_st_moeda = wb.add_format({"bold": True, "border": 1, "bg_color": "#E2E8F0",
                                "num_format": 'R$ #,##0.00'})
    f_tg_txt = wb.add_format({"bold": True, "border": 1, "bg_color": "#CBD5E1", "font_color": azul})
    f_tg_int = wb.add_format({"bold": True, "border": 1, "bg_color": "#CBD5E1", "font_color": azul,
                              "num_format": "#,##0", "align": "center"})
    f_tg_moeda = wb.add_format({"bold": True, "border": 1, "bg_color": "#CBD5E1", "font_color": azul,
                                "num_format": 'R$ #,##0.00'})

    # ---------------- Aba 1: resumo ----------------
    ws = wb.add_worksheet("Resumo Ação e Subação")
    ws.write(0, 0, "Relatório por Ação e Subação", f_titulo)
    ws.write(1, 0, f"{recorte + ' · ' if recorte else ''}gerado em "
                   f"{datetime.date.today().strftime('%d/%m/%Y')}", f_sub)
    cab = ["Ação", "Subação", "Qtd. NL", "Valor Retido", "Valor Total"]
    for c, t in enumerate(cab):
        ws.write(3, c, t, f_cab)

    agg = (
        df.groupby(["Acao_Relacao", "SubAcao_Relacao"], as_index=False)
        .agg(qtd=("NL_Numero", "nunique"), ret=("Valor_Retido_Limpo", "sum"), tot=("Valor_Total_Limpo", "sum"))
    )
    ordem = (
        df.groupby("Acao_Relacao")["Valor_Total_Limpo"].sum().sort_values(ascending=False).index.tolist()
    )
    linha = 4
    for acao in ordem:
        subs = agg[agg["Acao_Relacao"] == acao].sort_values("tot", ascending=False)
        for r in subs.itertuples(index=False):
            ws.write(linha, 0, r.Acao_Relacao, f_txt)
            ws.write(linha, 1, r.SubAcao_Relacao, f_txt)
            ws.write_number(linha, 2, int(r.qtd), f_int)
            ws.write_number(linha, 3, float(r.ret), f_moeda)
            ws.write_number(linha, 4, float(r.tot), f_moeda)
            linha += 1
        sub_df = df[df["Acao_Relacao"] == acao]
        ws.write(linha, 0, f"Subtotal — {acao}", f_st_txt)
        ws.write(linha, 1, "", f_st_txt)
        ws.write_number(linha, 2, int(sub_df["NL_Numero"].nunique()), f_st_int)
        ws.write_number(linha, 3, float(sub_df["Valor_Retido_Limpo"].sum()), f_st_moeda)
        ws.write_number(linha, 4, float(sub_df["Valor_Total_Limpo"].sum()), f_st_moeda)
        linha += 1
    ws.write(linha, 0, "TOTAL GERAL", f_tg_txt)
    ws.write(linha, 1, "", f_tg_txt)
    ws.write_number(linha, 2, int(df["NL_Numero"].nunique()), f_tg_int)
    ws.write_number(linha, 3, float(df["Valor_Retido_Limpo"].sum()), f_tg_moeda)
    ws.write_number(linha, 4, float(df["Valor_Total_Limpo"].sum()), f_tg_moeda)
    ws.set_column(0, 0, 62)
    ws.set_column(1, 1, 34)
    ws.set_column(2, 2, 10)
    ws.set_column(3, 4, 18)
    ws.freeze_panes(4, 0)
    ws.set_landscape()
    ws.fit_to_pages(1, 0)
    ws.repeat_rows(3)

    # ---------------- Aba 2: detalhe ----------------
    wd = wb.add_worksheet("Detalhe NL")
    colunas = [c for c in _COLUNAS_DETALHE if c[0] in df.columns]
    base = df.sort_values(["Acao_Relacao", "SubAcao_Relacao", "Credor_Tratado", "NL_Numero"], kind="stable")
    for c, (_, titulo, _) in enumerate(colunas):
        wd.write(0, c, titulo, f_cab)
    for i, reg in enumerate(base.to_dict("records"), start=1):
        for c, (campo, _, tipo) in enumerate(colunas):
            v = reg.get(campo)
            if tipo == "moeda":
                wd.write_number(i, c, float(v) if pd.notna(v) else 0.0, f_moeda)
            elif tipo == "data":
                d = pd.to_datetime(v, errors="coerce")
                if pd.isna(d):
                    wd.write(i, c, "", f_data)
                else:
                    wd.write_datetime(i, c, d.to_pydatetime(), f_data)
            elif tipo == "natureza":
                wd.write(i, c, _NATUREZA_EXIBICAO.get(str(v), "" if pd.isna(v) else str(v)), f_centro)
            else:
                wd.write(i, c, "" if pd.isna(v) else str(v), f_txt)
    larguras = {"Ação": 52, "Subação": 30, "Nome do Credor": 44, "Objeto Despesa": 40, "GD": 6,
                "Número NL": 17, "NE": 16, "Emissão": 12, "Natureza": 11, "Status": 22,
                "Fonte": 36, "Marcador de Fonte": 36, "Valor Retido": 17, "Valor": 17}
    for c, (_, titulo, _) in enumerate(colunas):
        wd.set_column(c, c, larguras.get(titulo, 18))
    wd.autofilter(0, 0, len(base), len(colunas) - 1)
    wd.freeze_panes(1, 0)
    wd.set_landscape()
    wd.fit_to_pages(1, 0)
    wd.repeat_rows(0)

    wb.close()
    return saida.getvalue()


# ---------------------------------------------------------------------------
# Relatório a partir do MODELO Excel do usuário (modelos/modelo_Relatorio_por_*.xlsx)
# ---------------------------------------------------------------------------
NOME_INTERVALO_DINAMICO = "Dados_Relatorio_Acao"
_ABA_RESUMO = "xl/worksheets/sheet1.xml"
_ABA_DETALHE = "xl/worksheets/sheet2.xml"


def localizar_modelo_relatorio() -> Path:
    pasta = Path(__file__).resolve().parent.parent / "modelos"
    achados = sorted(pasta.glob("modelo_Relatorio_por*A*o*Suba*o*.xlsx"))
    if not achados:
        raise FileNotFoundError(
            "Modelo do relatório não encontrado na pasta 'modelos' "
            "(modelo_Relatorio_por_ Ação_ e_Subação.xlsx)."
        )
    return achados[0]


def preencher_modelo_relatorio(df: pd.DataFrame, caminho_modelo=None) -> bytes:
    """Preenche o modelo do usuário com as NLs filtradas na tela.

    - Aba 'Detalhe NL': uma linha por NL (mesma ordem de colunas do modelo).
    - Aba 'Resumo': tabela dinâmica reconstruída com os dados e configurada para
      atualizar ao abrir; a origem é um intervalo nomeado dinâmico, então
      linhas incluídas/excluídas na aba Detalhe entram na tabela ao atualizar.
    """
    import zipfile
    from xml.sax.saxutils import escape, quoteattr

    if df.empty:
        raise ValueError("Não há liquidações para o recorte escolhido.")

    caminho = Path(caminho_modelo) if caminho_modelo else localizar_modelo_relatorio()
    with zipfile.ZipFile(caminho) as z:
        arq = {n: z.read(n) for n in z.namelist()}

    # ---------- dados ----------
    base = df.sort_values(
        ["Acao_Relacao", "SubAcao_Relacao", "Credor_Tratado", "NL_Numero"], kind="stable"
    )
    nat = {"SEM_CLASSE": "N/C"}

    def s(v, padrao=""):
        if v is None or (not isinstance(v, str) and pd.isna(v)):
            return padrao
        return str(v)

    linhas = []
    for r in base.to_dict("records"):
        d = pd.to_datetime(r.get("Data_DT"), errors="coerce")
        serial = None if pd.isna(d) else (d.to_pydatetime().date() - datetime.date(1899, 12, 30)).days
        ret = r.get("Valor_Retido_Limpo")
        tot = r.get("Valor_Total_Limpo")
        linhas.append([
            s(r.get("Acao_Relacao"), "NÃO INFORMADA"),
            s(r.get("SubAcao_Relacao"), "NÃO INFORMADA"),
            s(r.get("Credor_Tratado")),
            s(r.get("Objeto_Relacao")),
            s(r.get("Grupo_Classificado"), "N/C"),
            s(r.get("NL_Numero")),
            s(r.get("NE_Chave")),
            serial,
            nat.get(s(r.get("Natureza_NL")), s(r.get("Natureza_NL"))),
            s(r.get("Status_Filtro")),
            s(r.get("Fonte_Relacao")),
            s(r.get("Marcador_Fonte_Relacao"), "0000-SEM MARCADOR"),
            0.0 if ret is None or pd.isna(ret) else float(ret),
            0.0 if tot is None or pd.isna(tot) else float(tot),
        ])
    n = len(linhas)
    ultima = n + 1
    letras = "ABCDEFGHIJKLMN"

    # ---------- aba Detalhe NL ----------
    xml = arq[_ABA_DETALHE].decode("utf-8")
    m_dados = re.search(r"<sheetData>(.*)</sheetData>", xml, re.S)
    todas = re.findall(r"<row r=\"\d+\".*?</row>", m_dados.group(1), re.S)
    cabecalho = todas[0]
    modelo_linha = todas[1] if len(todas) > 1 else None
    estilos = (
        {c: st for c, st in re.findall(r'<c r="([A-N])\d+" s="(\d+)"', modelo_linha)}
        if modelo_linha else {}
    )
    novas = [cabecalho]
    for i, lin in enumerate(linhas, start=2):
        cel = []
        for c, v in enumerate(lin):
            ref = f"{letras[c]}{i}"
            st = f' s="{estilos[letras[c]]}"' if letras[c] in estilos else ""
            if c >= 12 or c == 7:
                if v is None:
                    cel.append(f'<c r="{ref}"{st}/>')
                else:
                    cel.append(f'<c r="{ref}"{st}><v>{format(v, ".15g")}</v></c>')
            else:
                cel.append(f'<c r="{ref}"{st} t="inlineStr"><is><t>{escape(v)}</t></is></c>')
        novas.append(f'<row r="{i}" spans="1:14" ht="20.1" customHeight="1">{"".join(cel)}</row>')
    xml = xml[:m_dados.start()] + "<sheetData>" + "".join(novas) + "</sheetData>" + xml[m_dados.end():]
    xml = re.sub(r'<dimension ref="[^"]*"', f'<dimension ref="A1:N{ultima}"', xml, count=1)
    xml = re.sub(r'(<autoFilter ref=")[^"]*"', rf'\1A1:N{ultima}"', xml, count=1)
    arq[_ABA_DETALHE] = xml.encode("utf-8")

    # ---------- cache da tabela dinâmica (com registros) ----------
    campos_eixo = {0: None, 1: None, 4: None, 11: None}  # Ação, Subação, GD, Marcador
    for k in campos_eixo:
        campos_eixo[k] = sorted({lin[k] for lin in linhas})
    indice = {k: {v: i for i, v in enumerate(vs)} for k, vs in campos_eixo.items()}

    cd = arq["xl/pivotCache/pivotCacheDefinition1.xml"].decode("utf-8")
    campos = re.findall(r"<cacheField\b[^>]*?name=\"[^\"]*\"[^>]*>.*?</cacheField>", cd, re.S)
    novos = []
    datas = [lin[7] for lin in linhas if lin[7] is not None]

    def iso(serial):
        return (datetime.date(1899, 12, 30) + datetime.timedelta(days=serial)).strftime("%Y-%m-%dT00:00:00")

    for k, cf in enumerate(campos):
        abre = re.match(r"<cacheField\b[^>]*>", cf).group(0)
        if k in campos_eixo:
            itens = "".join(f"<s v={quoteattr(v)}/>" for v in campos_eixo[k])
            sh = f'<sharedItems count="{len(campos_eixo[k])}">{itens}</sharedItems>'
        elif k == 7:
            if datas:
                sh = ('<sharedItems containsSemiMixedTypes="0" containsNonDate="0" containsDate="1" '
                      f'containsString="0" minDate="{iso(min(datas))}" maxDate="{iso(max(datas)+1)}"/>')
            else:
                sh = "<sharedItems/>"
        elif k >= 12:
            vals = [lin[k] for lin in linhas]
            sh = ('<sharedItems containsSemiMixedTypes="0" containsString="0" containsNumber="1" '
                  f'minValue="{format(min(vals), ".15g")}" maxValue="{format(max(vals), ".15g")}"/>')
        else:
            sh = "<sharedItems/>"
        novos.append(f"{abre}{sh}</cacheField>")
    bloco = re.search(r"<cacheFields\b[^>]*>.*</cacheFields>", cd, re.S)
    cd = cd[:bloco.start()] + f'<cacheFields count="14">{"".join(novos)}</cacheFields>' + cd[bloco.end():]
    cd = re.sub(r'recordCount="\d+"', f'recordCount="{n}"', cd, count=1)
    cd = cd.replace(
        '<cacheSource type="worksheet"><worksheetSource ref="A1:N18" sheet="Detalhe NL"/></cacheSource>',
        f'<cacheSource type="worksheet"><worksheetSource name="{NOME_INTERVALO_DINAMICO}"/></cacheSource>',
    )
    assert NOME_INTERVALO_DINAMICO in cd, "origem do cache não encontrada no modelo"
    cd = re.sub(r"<pivotCacheDefinition\b", '<pivotCacheDefinition refreshOnLoad="1"', cd, count=1)
    arq["xl/pivotCache/pivotCacheDefinition1.xml"] = cd.encode("utf-8")

    regs = []
    for lin in linhas:
        cel = []
        for k, v in enumerate(lin):
            if k in campos_eixo:
                cel.append(f'<x v="{indice[k][v]}"/>')
            elif k == 7:
                cel.append(f'<d v="{iso(v)}"/>' if v is not None else "<m/>")
            elif k >= 12:
                cel.append(f'<n v="{format(v, ".15g")}"/>')
            else:
                cel.append(f"<s v={quoteattr(v)}/>")
        regs.append(f'<r>{"".join(cel)}</r>')
    arq["xl/pivotCache/pivotCacheRecords1.xml"] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<pivotCacheRecords xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        f'count="{n}">{"".join(regs)}</pivotCacheRecords>'
    ).encode("utf-8")

    # ---------- tabela dinâmica (layout) e células do Resumo ----------
    grupos = {}
    for lin in linhas:
        chave = (lin[0], lin[1], lin[11], lin[4])
        grupos[chave] = grupos.get(chave, 0.0) + lin[13]
    chaves = sorted(
        grupos,
        key=lambda c: tuple(indice[k][c[j]] for j, k in enumerate((0, 1, 11, 4))),
    )
    pt = arq["xl/pivotTables/pivotTable1.xml"].decode("utf-8")
    campos_pt = re.findall(r"<pivotField\b[^>]*/>|<pivotField\b[^>]*[^/]>.*?</pivotField>", re.search(
        r"<pivotFields\b[^>]*>(.*)</pivotFields>", pt, re.S).group(1), re.S)
    campos_pt_novos = []
    for k, pf in enumerate(campos_pt):
        if k in campos_eixo:
            itens = "".join(f'<item x="{i}"/>' for i in range(len(campos_eixo[k])))
            pf = re.sub(r"<items\b.*?</items>", "", pf, flags=re.S)
            pf = re.sub(r"<pivotField\b([^>]*?)/>", r"<pivotField\1></pivotField>", pf)
            pf = pf.replace("</pivotField>", f'<items count="{len(campos_eixo[k])}">{itens}</items></pivotField>')
        campos_pt_novos.append(pf)
    pt = re.sub(r"<pivotFields\b[^>]*>.*</pivotFields>",
                f'<pivotFields count="14">{"".join(campos_pt_novos)}</pivotFields>', pt, flags=re.S)

    ordem_campos = (0, 1, 11, 4)
    itens_linha, anterior = [], None
    for c in chaves:
        pos = [indice[k][c[j]] for j, k in enumerate(ordem_campos)]
        rep = 0
        if anterior is not None:
            while rep < 3 and pos[rep] == anterior[rep]:
                rep += 1
        xs = "".join("<x/>" if p == 0 else f'<x v="{p}"/>' for p in pos[rep:])
        itens_linha.append(f'<i r="{rep}">{xs}</i>' if rep else f"<i>{xs}</i>")
        anterior = pos
    itens_linha.append('<i t="grand"><x/></i>')
    pt = re.sub(r"<rowItems\b.*?</rowItems>",
                f'<rowItems count="{len(itens_linha)}">{"".join(itens_linha)}</rowItems>', pt, flags=re.S)
    ultima_pivo = 4 + len(chaves) + 1
    pt = re.sub(r'(<location ref=")[^"]*"', rf'\1A4:E{ultima_pivo}"', pt, count=1)
    arq["xl/pivotTables/pivotTable1.xml"] = pt.encode("utf-8")

    xr = arq[_ABA_RESUMO].decode("utf-8")
    hoje = datetime.date.today().strftime("%d/%m/%Y")
    xr = re.sub(r"(<c r=\"A2\"[^>]*?) t=\"s\"><v>1</v></c>",
                rf'\1 t="inlineStr"><is><t>Recorte do painel · gerado em {hoje}</t></is></c>', xr, count=1)
    linhas_piv = []
    for j, c in enumerate(chaves):
        r = 5 + j
        txt = "".join(
            f'<c r="{col}{r}" t="inlineStr"><is><t>{escape(v)}</t></is></c>'
            for col, v in zip("ABCD", c)
        )
        linhas_piv.append(f'<row r="{r}" spans="1:5">{txt}<c r="E{r}" s="8"><v>{format(grupos[c], ".15g")}</v></c></row>')
    rt = 5 + len(chaves)
    total = sum(grupos.values())
    linhas_piv.append(
        f'<row r="{rt}" spans="1:5"><c r="A{rt}" t="inlineStr"><is><t>Total Geral</t></is></c>'
        f'<c r="E{rt}" s="8"><v>{format(total, ".15g")}</v></c></row>'
    )
    corte = re.search(r'<row r="5".*?</row>.*</sheetData>', xr, re.S)
    xr = xr[:corte.start()] + "".join(linhas_piv) + "</sheetData>" + xr[corte.end():]
    xr = re.sub(r'<dimension ref="[^"]*"', f'<dimension ref="A1:E{rt}"', xr, count=1)
    arq[_ABA_RESUMO] = xr.encode("utf-8")

    # ---------- nomes definidos ----------
    wb = arq["xl/workbook.xml"].decode("utf-8")
    wb = re.sub(r"('Detalhe NL'!\$A\$1:\$N\$)\d+", rf"\g<1>{ultima}", wb)
    novo_nome = (
        f'<definedName name="{NOME_INTERVALO_DINAMICO}">'
        "OFFSET('Detalhe NL'!$A$1,0,0,COUNTA('Detalhe NL'!$A:$A),14)</definedName>"
    )
    if NOME_INTERVALO_DINAMICO not in wb:
        wb = wb.replace("<definedNames>", "<definedNames>" + novo_nome, 1)
    arq["xl/workbook.xml"] = wb.encode("utf-8")

    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in arq.items():
            z.writestr(nome, conteudo)
    return saida.getvalue()


def filtrar_por_busca(df: pd.DataFrame, busca: str) -> pd.DataFrame:
    """Aplica a busca digitada na tabela (ação ou subação, sem acento/maiúscula)."""
    def limpa(valor) -> str:
        texto = unicodedata.normalize("NFD", str(valor))
        return "".join(c for c in texto if not unicodedata.combining(c)).lower()

    q = limpa(busca or "").strip()
    if not q:
        return df
    acao = df["Acao_Relacao"].map(limpa)
    sub = df["SubAcao_Relacao"].map(limpa)
    return df[acao.str.contains(q, regex=False) | sub.str.contains(q, regex=False)]
