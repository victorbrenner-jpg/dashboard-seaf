"""Conciliação inicial de PD Extra-Orçamentária agrupada por empenho.

A tela preserva cada linha da planilha de origem e consolida os valores por
empenho. A mesma PD pode aparecer em empenhos diferentes.
"""
import io
import re
import unicodedata
import urllib.request

import pandas as pd
import streamlit as st


SPREADSHEET_ID = "1T4MNAKW88v-0LHYz2nW6hAMNS4L7YgueEMW0mxTwZWo"
URL_CSV = (
    f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
    "/export?format=csv&gid=0"
)


def _normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]+", "", texto.upper())


def _coluna(df, *nomes):
    mapa = {_normalizar(c): c for c in df.columns}
    for nome in nomes:
        achou = mapa.get(_normalizar(nome))
        if achou is not None:
            return achou
    return None


def _texto(serie):
    return serie.fillna("").astype(str).str.strip()


def _moeda(serie):
    def converter(valor):
        texto = str(valor or "").strip()
        if not texto:
            return 0.0
        texto = texto.replace("R$", "").replace(" ", "")
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
        try:
            return float(texto)
        except (TypeError, ValueError):
            return 0.0
    return serie.map(converter)


def _brl(valor):
    return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@st.cache_data(ttl=300, show_spinner=False)
def carregar_base():
    requisicao = urllib.request.Request(
        URL_CSV,
        headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"},
    )
    with urllib.request.urlopen(requisicao, timeout=45) as resposta:
        conteudo = resposta.read()
    base = pd.read_csv(
        io.BytesIO(conteudo),
        dtype=str,
        encoding="utf-8-sig",
        sep=None,
        engine="python",
    )
    base.columns = [str(c).strip() for c in base.columns]
    return base


def preparar_base(base):
    df = base.copy()
    col_empenho_atual = _coluna(df, "NE 2026")
    col_empenho_origem = _coluna(df, "Nº EMPENHO 2025", "NUMERO EMPENHO 2025", "EMPENHO")
    if col_empenho_atual is None and col_empenho_origem is None:
        raise ValueError("A planilha precisa conter NE 2026 ou Nº EMPENHO 2025.")

    atual = _texto(df[col_empenho_atual]) if col_empenho_atual else pd.Series("", index=df.index)
    origem = _texto(df[col_empenho_origem]) if col_empenho_origem else pd.Series("", index=df.index)
    df["Empenho"] = atual.where(atual.ne(""), origem).replace("", "NÃO INFORMADO")

    aliases = {
        "Processo SEI": ("PROCESSO SEI",),
        "UG": ("UG",),
        "Fonte": ("FONTE",),
        "Credor": ("NOME CREDOR",),
        "Modalidade": ("MODALIDADE",),
        "Marcador de Fonte": ("MARCADOR DE FONTE",),
        "PD Extra": ("PD EXTRA",),
        "OB Extra": ("OB EXTRA",),
        "Status": ("STATUS",),
        "Objeto": ("OBJETO TRATADO", "OBJETO"),
        "Data de Emissão": ("DATA DA EMISSÃO", "DATA DE EMISSAO"),
    }
    for destino, nomes in aliases.items():
        origem_coluna = _coluna(df, *nomes)
        df[destino] = _texto(df[origem_coluna]) if origem_coluna else ""

    bruto_coluna = _coluna(df, "VALOR BRUTO")
    liquido_coluna = _coluna(df, "VALOR LÍQUIDO", "VALOR LIQUIDO")
    df["Valor Bruto"] = _moeda(df[bruto_coluna]) if bruto_coluna else 0.0
    df["Valor Líquido"] = _moeda(df[liquido_coluna]) if liquido_coluna else 0.0

    ob = df["OB Extra"].str.upper().str.strip()
    ob_valida = ob.str.match(r"^\d{4}OB\d+$", na=False)
    ob_eh_pd = ob.str.match(r"^\d{4}PD\d+$", na=False)
    df["OB Extra válida"] = ob.where(ob_valida, "")
    df["Validação da OB"] = "Formato não reconhecido"
    df.loc[ob.eq(""), "Validação da OB"] = "Não informada"
    df.loc[ob_eh_pd, "Validação da OB"] = "Número de PD no campo OB"
    df.loc[ob_valida, "Validação da OB"] = "Válida"

    return df


def _opcoes(df, coluna):
    return sorted(v for v in df[coluna].dropna().astype(str).unique() if v and v.upper() not in {"NAN", "NÃO INFORMADO"})


def render():
    st.markdown(
        "<h2 class='titulo-pagina'>🔎 Conciliação de PD Extra-Orçamentária</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p class='subtitulo-pagina'>Consolidação inicial por número do empenho</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    try:
        base = preparar_base(carregar_base())
    except Exception as erro:
        st.error(
            "Não foi possível carregar a planilha de conciliação. "
            "Verifique se a aba de origem está liberada para leitura por CSV. "
            f"Detalhe: {erro}"
        )
        return

    if base.empty:
        st.info("A planilha não possui registros para conciliação.")
        return

    st.sidebar.markdown("#### 🔎 Filtros — Conciliação PD Extra")
    filtros = [
        ("UG", "UG"),
        ("Fonte", "Fonte"),
        ("Marcador de Fonte", "Marcador de Fonte"),
        ("Credor", "Credor"),
        ("Status", "Status"),
    ]
    filtrado = base.copy()
    selecoes = {}
    for rotulo, coluna in filtros:
        opcoes = _opcoes(base, coluna)
        selecoes[coluna] = st.sidebar.multiselect(
            rotulo,
            options=opcoes,
            key=f"conc_pd_extra_{_normalizar(coluna).lower()}",
        )
        if selecoes[coluna]:
            filtrado = filtrado[filtrado[coluna].isin(selecoes[coluna])]

    if st.sidebar.button("🔄 Atualizar planilha", key="atualizar_conciliacao_pd_extra"):
        carregar_base.clear()
        st.rerun()

    if filtrado.empty:
        st.warning("Nenhum registro corresponde aos filtros selecionados.")
        return

    resumo = (
        filtrado.groupby("Empenho", dropna=False)
        .agg(
            Registros=("Empenho", "size"),
            Credores=("Credor", lambda s: " | ".join(sorted(set(v for v in s if v)))),
            Modalidades=("Modalidade", lambda s: " | ".join(sorted(set(v for v in s if v)))),
            PDs=("PD Extra", lambda s: " | ".join(sorted(set(v for v in s if v)))),
            Valor_Bruto=("Valor Bruto", "sum"),
            Valor_Liquido=("Valor Líquido", "sum"),
        )
        .reset_index()
        .sort_values(["Valor_Bruto", "Empenho"], ascending=[False, True])
    )

    total_empenhos = filtrado["Empenho"].nunique()
    total_bruto = float(filtrado["Valor Bruto"].sum())
    total_liquido = float(filtrado["Valor Líquido"].sum())
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("EMPENHOS", f"{total_empenhos:,}".replace(",", "."))
    k2.metric("REGISTROS", f"{len(filtrado):,}".replace(",", "."))
    k3.metric("VALOR BRUTO", _brl(total_bruto))
    k4.metric("VALOR LÍQUIDO", _brl(total_liquido))

    st.markdown("### Resumo agrupado por empenho")
    st.caption(
        "Cada empenho é consolidado separadamente. Uma mesma PD pode aparecer "
        "em mais de um empenho, sem que os registros sejam descartados."
    )
    st.dataframe(
        resumo,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Empenho": st.column_config.TextColumn("Empenho"),
            "Registros": st.column_config.NumberColumn("Qtd. registros", format="%d"),
            "Valor_Bruto": st.column_config.NumberColumn("Valor bruto", format="R$ %.2f"),
            "Valor_Liquido": st.column_config.NumberColumn("Valor líquido", format="R$ %.2f"),
        },
    )

    empenhos = resumo["Empenho"].astype(str).tolist()
    selecionado = st.selectbox(
        "Selecione um empenho para consultar os registros vinculados",
        options=empenhos,
        key="conc_pd_extra_empenho_detalhe",
    )
    detalhe = filtrado[filtrado["Empenho"].astype(str).eq(selecionado)].copy()
    colunas_detalhe = [
        "Empenho", "Processo SEI", "UG", "Fonte", "Marcador de Fonte",
        "Credor", "Modalidade", "PD Extra", "OB Extra", "OB Extra válida",
        "Validação da OB", "Valor Bruto", "Valor Líquido", "Status",
    ]
    colunas_detalhe = [c for c in colunas_detalhe if c in detalhe.columns]
    st.markdown("### Detalhamento do empenho")
    st.dataframe(
        detalhe[colunas_detalhe],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Valor Bruto": st.column_config.NumberColumn(format="R$ %.2f"),
            "Valor Líquido": st.column_config.NumberColumn(format="R$ %.2f"),
        },
    )

    csv = resumo.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Exportar resumo por empenho",
        data=csv,
        file_name="conciliacao_pd_extra_por_empenho.csv",
        mime="text/csv",
        key="baixar_conciliacao_pd_extra",
    )
