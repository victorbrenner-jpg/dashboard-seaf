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
