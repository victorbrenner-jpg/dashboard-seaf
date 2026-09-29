"""Tela de homologação para consulta e acompanhamento dos DEA."""

from __future__ import annotations

import io
import unicodedata

import pandas as pd
import streamlit as st


COLUNAS_VISAO = [
    "Credor", "Processo / SEI", "NE", "Valor", "Ano DEA", "Executiva",
    "Grupo de despesa", "Objeto", "Status pagamento", "Status CPF",
    "SIPR 2025", "SIPR 2026", "PD / OB", "Prioritário",
]


def _normalizar(texto: object) -> str:
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ASCII", "ignore").decode()
    return " ".join(texto.upper().replace("/", " ").split())


def _encontrar_coluna(colunas, *nomes: str) -> str | None:
    mapa = {_normalizar(coluna): coluna for coluna in colunas}
    for nome in nomes:
        encontrada = mapa.get(_normalizar(nome))
        if encontrada:
            return encontrada
    return None


def _moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _carregar_base(arquivo) -> pd.DataFrame:
    """Lê a aba BASE, cuja linha 3 contém os cabeçalhos da planilha DEA."""
    conteudo = arquivo.getvalue()
    planilha = pd.ExcelFile(io.BytesIO(conteudo))
    aba = "BASE" if "BASE" in planilha.sheet_names else planilha.sheet_names[0]
    dados = pd.read_excel(planilha, sheet_name=aba, header=2)
    dados = dados.dropna(how="all").copy()
    dados.columns = [str(coluna).strip() for coluna in dados.columns]

    renomear = {}
    campos = {
        "Credor": ("CREDOR",),
        "Processo / SEI": ("SEI", "PROCESSO", "PROCESSO SEI"),
        "NE": ("NE",),
        "Valor": ("VALOR",),
        "Ano DEA": ("ANO DO DEA", "ANO DO DEA2"),
        "Executiva": ("EXECUTIVA",),
        "Grupo de despesa": ("GRUPO DE DESPESA",),
        "Objeto": ("OBJETO",),
        "Status pagamento": ("STATUS PAGAMENTO",),
        "Status CPF": ("STATUS CPF",),
        "SIPR 2025": ("Nº SIPR 2025", "N SIPR 2025"),
        "SIPR 2026": ("Nº SIPR 2026", "N SIPR 2026"),
        "PD / OB": ("OB PD", "OB / PD"),
        "Prioritário": ("PRIORITÁRIO", "PRIORITARIO"),
    }
    for destino, opcoes in campos.items():
        origem = _encontrar_coluna(dados.columns, *opcoes)
        if origem:
            renomear[origem] = destino
    dados = dados.rename(columns=renomear)

    obrigatorias = {"Credor", "Valor", "Status pagamento", "Status CPF"}
    faltantes = obrigatorias - set(dados.columns)
    if faltantes:
        raise ValueError("A aba BASE não possui as colunas necessárias: " + ", ".join(sorted(faltantes)))

    for coluna in dados.columns:
        if coluna != "Valor":
            dados[coluna] = dados[coluna].fillna("").astype(str).str.strip()
    dados["Valor"] = pd.to_numeric(dados["Valor"], errors="coerce").fillna(0.0)
    return dados


def _opcoes(dados: pd.DataFrame, coluna: str) -> list[str]:
    if coluna not in dados.columns:
        return []
    return sorted(valor for valor in dados[coluna].dropna().astype(str).unique() if valor)


def _aplicar_multifiltro(dados: pd.DataFrame, coluna: str, valores: list[str]) -> pd.DataFrame:
    if valores and coluna in dados.columns:
        return dados[dados[coluna].isin(valores)]
    return dados


def render() -> None:
    st.markdown("<h2 class='titulo-pagina'>📋 Monitoramento de DEA</h2>", unsafe_allow_html=True)
    st.caption("Acompanhe solicitações, aprovação do CPF e a situação de pagamento dos DEA.")

    with st.sidebar:
        st.markdown("### Base de acompanhamento DEA")
        arquivo = st.file_uploader(
            "Planilha DEA (.xlsx)", type=["xlsx"], key="arquivo_monitoramento_dea",
            help="Envie a planilha com a aba BASE para atualizar a consulta desta sessão.",
        )

    dados = pd.DataFrame(columns=COLUNAS_VISAO)
    base_carregada = arquivo is not None
    if arquivo is not None:
        try:
            dados = _carregar_base(arquivo)
        except Exception as erro:
            st.error(f"Não foi possível ler a planilha DEA: {erro}")
            base_carregada = False

    with st.sidebar:
        st.markdown("---")
        st.markdown("### Filtros DEA")
        anos = st.multiselect("Ano do DEA", _opcoes(dados, "Ano DEA"), key="dea_anos", disabled=not base_carregada)
        status_cpf = st.multiselect("Status CPF", _opcoes(dados, "Status CPF"), key="dea_status_cpf", disabled=not base_carregada)
        status_pagamento = st.multiselect(
            "Status do pagamento", _opcoes(dados, "Status pagamento"), key="dea_status_pagamento", disabled=not base_carregada
        )
        grupos = st.multiselect(
            "Grupo de despesa", _opcoes(dados, "Grupo de despesa"), key="dea_grupos", disabled=not base_carregada
        )
        executivas = st.multiselect("Executiva", _opcoes(dados, "Executiva"), key="dea_executivas", disabled=not base_carregada)
        prioritarios = st.multiselect("Prioritário", _opcoes(dados, "Prioritário"), key="dea_prioritarios", disabled=not base_carregada)
        termo_credor = st.text_input("Credor (buscar por nome)", key="dea_credor", disabled=not base_carregada)

    filtrado = dados.copy()
    for coluna, valores in (
        ("Ano DEA", anos), ("Status CPF", status_cpf), ("Status pagamento", status_pagamento),
        ("Grupo de despesa", grupos), ("Executiva", executivas), ("Prioritário", prioritarios),
    ):
        filtrado = _aplicar_multifiltro(filtrado, coluna, valores)
    if termo_credor:
        filtrado = filtrado[filtrado["Credor"].str.contains(termo_credor, case=False, na=False)]

    total = float(filtrado["Valor"].sum())
    aguardando_cpf = filtrado[filtrado["Status CPF"].str.contains("AGUARD", case=False, na=False)]
    pagos = filtrado[filtrado["Status pagamento"].str.contains("PAGO", case=False, na=False) & ~filtrado["Status pagamento"].str.contains("NÃO PAGO|NAO PAGO", case=False, na=False)]
    prioritarios_dados = filtrado[filtrado.get("Prioritário", pd.Series("", index=filtrado.index)).str.upper().eq("SIM")]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("VALOR TOTAL MONITORADO", _moeda(total), f"{len(filtrado):,} registros".replace(",", "."))
    col2.metric("AGUARDANDO CPF", _moeda(float(aguardando_cpf["Valor"].sum())), f"{len(aguardando_cpf):,} registros".replace(",", "."))
    col3.metric("PAGOS", _moeda(float(pagos["Valor"].sum())), f"{len(pagos):,} registros".replace(",", "."))
    col4.metric("PRIORITÁRIOS", _moeda(float(prioritarios_dados["Valor"].sum())), f"{len(prioritarios_dados):,} registros".replace(",", "."))

    if not base_carregada:
        st.info("A estrutura do monitoramento está pronta. Use **Upload** na lateral para carregar a base DEA e preencher os cards, filtros e tabelas.")

    st.markdown("### 📋 Planejamento DEA por Credor")
    agrupamento = {
        "Processo / SEI": "nunique", "SIPR 2026": lambda serie: "Sim" if serie.astype(bool).any() else "Não",
        "Status CPF": lambda serie: ", ".join(sorted(valor for valor in serie.unique() if valor)),
        "Status pagamento": lambda serie: ", ".join(sorted(valor for valor in serie.unique() if valor)),
        "Valor": "sum",
    }
    agrupamento = {coluna: regra for coluna, regra in agrupamento.items() if coluna in filtrado.columns}
    resumo = filtrado.groupby("Credor", dropna=False).agg(agrupamento).reset_index().sort_values("Valor", ascending=False)
    resumo = resumo.rename(columns={"Processo / SEI": "Processos", "Status pagamento": "Status Pagamento", "Status CPF": "Status CPF", "Valor": "Valor total"})
    if "Valor total" in resumo:
        resumo["Valor total"] = resumo["Valor total"].map(_moeda)
    st.dataframe(resumo, use_container_width=True, hide_index=True, height=430)

    esquerda, direita = st.columns([1.25, 0.75])
    with esquerda:
        st.markdown("### Objetos de despesa com maior valor")
        if "Objeto" in filtrado.columns:
            objetos = filtrado.groupby("Objeto", dropna=False)["Valor"].sum().sort_values(ascending=False).head(12).reset_index()
            objetos["Valor"] = objetos["Valor"].map(_moeda)
            st.dataframe(objetos.rename(columns={"Valor": "Valor total"}), use_container_width=True, hide_index=True)
    with direita:
        st.markdown("### Resumo por status")
        por_status = filtrado.groupby("Status pagamento", dropna=False)["Valor"].sum().sort_values(ascending=False).reset_index()
        por_status["Valor"] = por_status["Valor"].map(_moeda)
        st.dataframe(por_status.rename(columns={"Status pagamento": "Situação", "Valor": "Valor total"}), use_container_width=True, hide_index=True)
