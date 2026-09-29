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


def _painel_titulo(titulo: str, complemento: str = "") -> None:
    st.markdown(
        f"""
        <div class="dea-painel-titulo">
            <span>{titulo}</span>
            <small>{complemento}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_resumo(dados: pd.DataFrame, coluna: str, titulo: str) -> None:
    if coluna not in dados.columns or dados.empty:
        linhas = "<tr><td colspan='3'>Aguardando base DEA</td></tr>"
    else:
        resumo = dados.groupby(coluna, dropna=False)["Valor"].sum().sort_values(ascending=False).head(7)
        maior = float(resumo.max()) if not resumo.empty else 0.0
        linhas = "".join(
            f"""
            <tr>
              <td>{str(rotulo) if str(rotulo) else "Não informado"}</td>
              <td><span class="dea-barra"><i style="width:{(float(valor) / maior * 100) if maior else 0:.0f}%"></i></span></td>
              <td>{_moeda(float(valor))}</td>
            </tr>
            """
            for rotulo, valor in resumo.items()
        )
    st.markdown(
        f"""
        <div class="dea-resumo">
            <div class="dea-resumo-titulo">{titulo}</div>
            <table>
              <thead><tr><th>Situação</th><th></th><th>Valor total</th></tr></thead>
              <tbody>{linhas}</tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render() -> None:
    st.markdown(
        """
        <style>
          .dea-titulo {display:flex;align-items:center;justify-content:space-between;margin:0 0 .65rem;}
          .dea-titulo h2 {margin:0;color:#073d67;font:700 2rem/1.1 'Segoe UI',Arial,sans-serif;}
          .dea-titulo p {margin:0;color:#3f6280;font-size:.78rem;border:1px solid #bddaf1;border-radius:8px;background:#f5fbff;padding:.55rem .8rem;}
          .dea-card {min-height:84px;border:1px solid #c8e0ef;border-radius:8px;background:#fff;display:flex;align-items:center;gap:.8rem;padding:.75rem 1rem;box-sizing:border-box;}
          .dea-card .icone {width:42px;height:42px;border-radius:50%;background:#eef7ff;display:flex;align-items:center;justify-content:center;font-size:1.45rem;flex:0 0 auto;}
          .dea-card .rotulo {font:700 .78rem/1.1 'Segoe UI',Arial,sans-serif;color:#154a72;text-transform:none;}
          .dea-card .valor {font:800 1.35rem/1.2 'Segoe UI',Arial,sans-serif;color:#073d67;margin-top:.25rem;}
          .dea-card .detalhe {font:600 .7rem/1.2 'Segoe UI',Arial,sans-serif;color:#58718a;margin-top:.18rem;}
          .dea-painel-titulo {background:linear-gradient(100deg,#003b5c,#007f94);color:#fff;border-radius:7px 7px 0 0;padding:.55rem .85rem;font:700 .93rem 'Segoe UI',Arial,sans-serif;display:flex;justify-content:space-between;align-items:center;}
          .dea-painel-titulo small {font:500 .68rem 'Segoe UI',Arial,sans-serif;opacity:.92;}
          .dea-quadro {border:1px solid #c9ddec;border-top:0;border-radius:0 0 7px 7px;padding:.1rem .1rem .35rem;background:#fff;}
          .dea-resumo {border:1px solid #bfdaeb;border-radius:7px;background:#fff;margin-bottom:.65rem;overflow:hidden;}
          .dea-resumo-titulo {background:#005473;color:#fff;padding:.42rem .65rem;font:700 .82rem 'Segoe UI',Arial,sans-serif;}
          .dea-resumo table {width:100%;border-collapse:collapse;font:600 .7rem 'Segoe UI',Arial,sans-serif;color:#173e5e;}
          .dea-resumo th {background:#f1f7fb;font-size:.63rem;text-align:left;padding:.32rem .45rem;color:#254f70;}
          .dea-resumo td {padding:.33rem .45rem;border-top:1px solid #e3edf4;}
          .dea-resumo td:last-child,.dea-resumo th:last-child {text-align:right;white-space:nowrap;}
          .dea-barra {display:block;height:10px;background:#e8f0f5;border-radius:2px;min-width:35px;}
          .dea-barra i {display:block;height:100%;border-radius:2px;background:linear-gradient(90deg,#26b39d,#0987aa);}
          .dea-sem-base {margin:.75rem 0 .6rem;border:1px solid #bddaf1;border-radius:7px;padding:.62rem .8rem;background:#f2f9ff;color:#14527c;font-size:.84rem;}
          [data-testid="stSidebar"] .dea-filtros-titulo {font:800 1.05rem 'Segoe UI',Arial,sans-serif;color:#073d67;margin:.1rem 0 .45rem;}
          [data-testid="stSidebar"] .stButton button {border-radius:7px;font-weight:700;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="dea-titulo">
          <h2>📋 Monitoramento de DEA</h2>
          <p>Planejamento e situação de pagamento das Despesas de Exercícios Anteriores (DEA)</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("<div class='dea-filtros-titulo'>⚱ Filtros</div>", unsafe_allow_html=True)
        col_aplicar, col_limpar = st.columns(2)
        with col_aplicar:
            st.button("⚑ Aplicar", key="dea_aplicar", use_container_width=True)
        with col_limpar:
            if st.button("↻ Limpar", key="dea_limpar", use_container_width=True):
                for chave in ("dea_anos", "dea_status_cpf", "dea_status_pagamento", "dea_grupos", "dea_executivas", "dea_prioritarios", "dea_credor"):
                    st.session_state.pop(chave, None)
                st.rerun()
        st.markdown("---")
        st.markdown("#### Base de acompanhamento DEA")
        arquivo = st.file_uploader(
            "Atualizar planilha DEA (.xlsx)", type=["xlsx"], key="arquivo_monitoramento_dea",
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
        anos = st.multiselect("Ano do DEA", _opcoes(dados, "Ano DEA"), key="dea_anos", disabled=not base_carregada)
        status_cpf = st.multiselect("Status CPF", _opcoes(dados, "Status CPF"), key="dea_status_cpf", disabled=not base_carregada)
        status_pagamento = st.multiselect("Status do Pagamento", _opcoes(dados, "Status pagamento"), key="dea_status_pagamento", disabled=not base_carregada)
        grupos = st.multiselect("Grupo de Despesa", _opcoes(dados, "Grupo de despesa"), key="dea_grupos", disabled=not base_carregada)
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
    pagos = filtrado[
        filtrado["Status pagamento"].str.contains("PAGO", case=False, na=False)
        & ~filtrado["Status pagamento"].str.contains("NÃO PAGO|NAO PAGO", case=False, na=False)
    ]
    prioritarios_dados = filtrado[
        filtrado.get("Prioritário", pd.Series("", index=filtrado.index)).str.upper().eq("SIM")
    ]

    cards = [
        ("💰", "Valor total monitorado", total, f"{len(filtrado):,} registros".replace(",", ".")),
        ("⏱", "Aguardando CPF", float(aguardando_cpf["Valor"].sum()), f"{len(aguardando_cpf):,} registros".replace(",", ".")),
        ("✓", "Pagos", float(pagos["Valor"].sum()), f"{len(pagos):,} registros".replace(",", ".")),
        ("★", "Prioritários", float(prioritarios_dados["Valor"].sum()), f"{len(prioritarios_dados):,} registros".replace(",", ".")),
    ]
    for coluna, card in zip(st.columns(4), cards):
        icone, rotulo, valor, detalhe = card
        coluna.markdown(
            f"<div class='dea-card'><div class='icone'>{icone}</div><div><div class='rotulo'>{rotulo}</div><div class='valor'>{_moeda(valor)}</div><div class='detalhe'>{detalhe}</div></div></div>",
            unsafe_allow_html=True,
        )

    if not base_carregada:
        st.markdown("<div class='dea-sem-base'>A estrutura está pronta. Atualize a planilha DEA na lateral para preencher os cards, filtros e quadros com os dados reais.</div>", unsafe_allow_html=True)

    agrupamento = {
        "Processo / SEI": "nunique",
        "SIPR 2026": lambda serie: "Sim" if serie.astype(bool).any() else "Não",
        "Status CPF": lambda serie: ", ".join(sorted(valor for valor in serie.unique() if valor)),
        "Status pagamento": lambda serie: ", ".join(sorted(valor for valor in serie.unique() if valor)),
        "Valor": "sum",
    }
    agrupamento = {coluna: regra for coluna, regra in agrupamento.items() if coluna in filtrado.columns}
    resumo = filtrado.groupby("Credor", dropna=False).agg(agrupamento).reset_index().sort_values("Valor", ascending=False)
    resumo = resumo.rename(columns={"Processo / SEI": "Processos", "SIPR 2026": "SIPR 2026", "Status pagamento": "Status Pagamento", "Valor": "Valor total"})
    if "Valor total" in resumo:
        resumo["Valor total"] = resumo["Valor total"].map(_moeda)
    resumo.index = range(1, len(resumo) + 1)
    resumo.index.name = "#"

    esquerda, direita = st.columns([2.9, 1.2])
    with esquerda:
        _painel_titulo("▣  Planejamento DEA por Credor", "Todos os credores | Ordenado por valor (decrescente)")
        with st.container(border=True):
            st.dataframe(resumo, use_container_width=True, height=410)
        _painel_titulo("▣  Objetos de despesa com maior valor")
        objetos = filtrado.groupby("Objeto", dropna=False)["Valor"].sum().sort_values(ascending=False).head(8).reset_index()
        objetos["Valor"] = objetos["Valor"].map(_moeda)
        objetos.index = range(1, len(objetos) + 1)
        objetos.index.name = "#"
        with st.container(border=True):
            st.dataframe(objetos.rename(columns={"Valor": "Valor total"}), use_container_width=True, height=220)
    with direita:
        _render_resumo(filtrado, "Status pagamento", "◉  Status do pagamento")
        _render_resumo(filtrado, "Status CPF", "✧  Status CPF")
        _render_resumo(filtrado, "Grupo de despesa", "◉  Grupo de despesa")
        _render_resumo(filtrado, "Executiva", "▣  Por Executiva")
