"""Monitoramento da execução FNDE destinada às cooperativas da fonte 552."""

from __future__ import annotations

import unicodedata

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


URL_BASE_PAGAMENTOS = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vTD3b7L6byArEDgkVKOXXlc7RK0M2QKXLov83OydCaks3rDISWYWfgGNi6vG6pwy8t5Ul3Fd2wArhtT/"
    "pub?gid=1786485134&single=true&output=csv"
)
TOTAL_RECEBIDO = 18_881_868.00
PERCENTUAL_COOPERATIVAS = 0.45
META_COOPERATIVAS = TOTAL_RECEBIDO * PERCENTUAL_COOPERATIVAS

MESES = [
    "Jan/2026", "Fev/2026", "Mar/2026", "Abr/2026", "Mai/2026", "Jun/2026",
    "Jul/2026", "Ago/2026", "Set/2026", "Out/2026", "Nov/2026", "Dez/2026",
]

COOPERATIVAS = {
    "COODAPISJG — Cooperativa de Jaboatão dos Guararapes": ("COODAPISJG",),
    "ASSOCENE — Associação de Orientação às Cooperativas do Nordeste": ("ASSOCENE",),
    "Cooperativa dos Pequenos Agricultores Familiares da Mata Norte": ("MATA NORTE",),
    "COPAF — Cooperativa da Agricultura Familiar de Pernambuco": ("COPAF",),
}


def _normalizar(valor: object) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.upper().split())


def _moeda(valor: float) -> str:
    return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _valor_numero(valor: object) -> float:
    if pd.isna(valor) or str(valor).strip() == "":
        return 0.0
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return float(valor)
    texto = str(valor).replace("R$", "").replace(" ", "").strip()
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except (TypeError, ValueError):
        return 0.0


def _localizar_coluna(colunas: pd.Index, *nomes: str) -> str | None:
    mapa = {_normalizar(coluna): coluna for coluna in colunas}
    return next((mapa[_normalizar(nome)] for nome in nomes if _normalizar(nome) in mapa), None)


def _nome_cooperativa(nome: object) -> str | None:
    texto = _normalizar(nome)
    for exibicao, termos in COOPERATIVAS.items():
        if any(termo in texto for termo in termos):
            return exibicao
    return None


@st.cache_data(ttl=300, show_spinner=False)
def _carregar_pagamentos() -> pd.DataFrame:
    dados = pd.read_csv(URL_BASE_PAGAMENTOS)
    dados.columns = [str(coluna).strip() for coluna in dados.columns]
    coluna_fonte = _localizar_coluna(dados.columns, "Fonte")
    coluna_valor = _localizar_coluna(dados.columns, "Valor")
    coluna_data = _localizar_coluna(dados.columns, "Data Emissão", "Data Emissao", "Data")
    coluna_credor = _localizar_coluna(dados.columns, "Nome do Credor", "Credor")
    if not all((coluna_fonte, coluna_valor, coluna_data, coluna_credor)):
        raise ValueError("A base de pagamentos não contém as colunas necessárias para o monitoramento FNDE.")

    base = dados.copy()
    fonte = base[coluna_fonte].fillna("").astype(str)
    base = base[fonte.str.contains(r"(?<!\d)552(?!\d)", regex=True, na=False)].copy()
    base["Cooperativa"] = base[coluna_credor].map(_nome_cooperativa)
    base = base[base["Cooperativa"].notna()].copy()
    base["Valor executado"] = base[coluna_valor].map(_valor_numero)
    base["Data"] = pd.to_datetime(base[coluna_data], errors="coerce", dayfirst=True)
    base = base[(base["Data"].isna()) | (base["Data"].dt.year == 2026)].copy()
    base["Mês"] = base["Data"].dt.month.map(
        {1: "Jan/2026", 2: "Fev/2026", 3: "Mar/2026", 4: "Abr/2026", 5: "Mai/2026", 6: "Jun/2026",
         7: "Jul/2026", 8: "Ago/2026", 9: "Set/2026", 10: "Out/2026", 11: "Nov/2026", 12: "Dez/2026"}
    ).fillna("Sem mês informado")
    return base


def _card(titulo: str, valor: float, detalhe: str, classe: str) -> None:
    st.markdown(
        f"""<div class="fnde-card {classe}"><div class="fnde-card-title">{titulo}</div>
        <div class="fnde-card-value">{_moeda(valor)}</div><div class="fnde-card-detail">{detalhe}</div></div>""",
        unsafe_allow_html=True,
    )


def render() -> None:
    st.markdown(
        """<style>
        .fnde-cabecalho{padding:4px 0 14px}.fnde-cabecalho h1{margin:0 0 10px;color:#1f3655;font-size:2rem;font-weight:800;line-height:1.2}
        .fnde-subtitulo{color:#637387;font-size:1.02rem;line-height:1.65}.fnde-divisor{border:0;border-top:1px solid #d9dfe6;margin:6px 0 18px}
        .fnde-card{background:#fff;border:1px solid #d7e3ee;border-radius:8px;padding:13px 16px;min-height:96px;box-shadow:0 1px 2px #00000008}
        .fnde-card-title{font-size:.78rem;font-weight:800;color:#174d7c;text-transform:uppercase}.fnde-card-value{font-size:1.38rem;font-weight:800;color:#063b70;margin-top:6px}.fnde-card-detail{font-size:.76rem;color:#63788d;margin-top:5px}
        .fnde-card.verde .fnde-card-value{color:#16865b}.fnde-card.laranja .fnde-card-value{color:#c97800}
        .fnde-box-title{background:linear-gradient(90deg,#075b88,#08749a);color:#fff;font-weight:700;padding:8px 11px;border-radius:7px 7px 0 0;margin-top:5px}
        .fnde-tabela{border:1px solid #d7e3ee;border-top:0;border-radius:0 0 7px 7px;overflow:auto;background:#fff}.fnde-tabela table{width:max-content;min-width:100%;border-collapse:collapse;font-size:.76rem;color:#163b5b}
        .fnde-tabela th{background:#edf4f8;padding:10px 12px;text-align:left;font-size:.67rem;white-space:nowrap;border-right:1px solid #dce7ef}.fnde-tabela td{padding:11px 12px;border-top:1px solid #e1eaf1;border-right:1px solid #edf2f6;white-space:nowrap}.fnde-tabela td:not(:first-child),.fnde-tabela th:not(:first-child){text-align:right}.fnde-tabela .fnde-credor{font-weight:750;white-space:normal;min-width:290px}.fnde-tabela .fnde-valor{font-weight:800;color:#16865b}.fnde-tabela .fnde-total{font-weight:800;background:#f4f9fc;color:#073b61}
        .fnde-analise{border:1px solid #d7e3ee;border-radius:8px;padding:14px 16px 12px;margin-top:14px;background:#fff}.fnde-analise-titulo{font-size:1.25rem;font-weight:800;color:#1f3655;margin:0 0 14px}
        .fnde-subtitulo-grafico{font-size:.9rem;font-weight:800;color:#073b61;margin:0 0 9px}.fnde-mini-cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:0 0 8px}.fnde-mini-card{border:1px solid #dbe5ee;border-radius:8px;padding:8px 10px;background:#f8fbfd}.fnde-mini-label{font-size:.58rem;color:#64748b;font-weight:800;letter-spacing:.04em}.fnde-mini-value{font-size:.92rem;color:#075b88;font-weight:800;margin-top:3px}
        .fnde-resumo-mes{border:1px solid #d7e3ee;border-radius:7px;overflow:hidden;background:#fff}.fnde-resumo-mes table{width:100%;border-collapse:collapse;font-size:.75rem;color:#163b5b}.fnde-resumo-mes th{background:#edf4f8;padding:9px;text-align:left;font-size:.64rem}.fnde-resumo-mes td{padding:9px;border-top:1px solid #e1eaf1}.fnde-resumo-mes td:not(:first-child),.fnde-resumo-mes th:not(:first-child){text-align:right}.fnde-resumo-mes .fnde-total{font-weight:800;background:#f4f9fc;color:#073b61}
        </style>""",
        unsafe_allow_html=True,
    )
    st.markdown(
        """<div class="fnde-cabecalho"><h1>Monitoramento FNDE — Cooperativas</h1>
        <div class="fnde-subtitulo"><em>Execução da fonte 552 para as cooperativas da agricultura familiar.</em></div></div><hr class="fnde-divisor">""",
        unsafe_allow_html=True,
    )

    try:
        pagamentos = _carregar_pagamentos()
    except Exception as erro:
        st.error("Não foi possível atualizar a base de pagamentos para o Monitoramento FNDE.")
        st.caption(f"Detalhe técnico: {erro}")
        if st.button("Atualizar conexão", key="fnde_atualizar_conexao"):
            _carregar_pagamentos.clear()
            st.rerun()
        return

    if "fnde_filtros_aplicados" not in st.session_state:
        st.session_state.fnde_filtros_aplicados = {"meses": [], "credores": []}

    with st.sidebar:
        st.markdown("#### Filtros — Monitoramento FNDE")
        with st.form("form_filtros_fnde"):
            meses = st.multiselect(
                "Mês de pagamento",
                MESES,
                default=st.session_state.fnde_filtros_aplicados["meses"],
            )
            credores = st.multiselect(
                "Cooperativa",
                list(COOPERATIVAS),
                default=st.session_state.fnde_filtros_aplicados["credores"],
            )
            aplicar = st.form_submit_button("Aplicar filtros", use_container_width=True, type="primary")
        limpar = st.button("Limpar filtros", use_container_width=True, key="limpar_filtros_fnde")
        st.caption("Fonte fixa: 552")

    if aplicar:
        st.session_state.fnde_filtros_aplicados = {"meses": meses, "credores": credores}
        st.rerun()
    if limpar:
        st.session_state.fnde_filtros_aplicados = {"meses": [], "credores": []}
        st.rerun()

    filtros = st.session_state.fnde_filtros_aplicados
    filtrado = pagamentos.copy()
    if filtros["meses"]:
        filtrado = filtrado[filtrado["Mês"].isin(filtros["meses"])]
    if filtros["credores"]:
        filtrado = filtrado[filtrado["Cooperativa"].isin(filtros["credores"])]

    executado = float(filtrado["Valor executado"].sum()) if not filtrado.empty else 0.0
    saldo = max(META_COOPERATIVAS - executado, 0.0)
    percentual_executado = (executado / META_COOPERATIVAS * 100) if META_COOPERATIVAS else 0.0
    meta_mensal = META_COOPERATIVAS / 12

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _card("Total recebido FNDE", TOTAL_RECEBIDO, "Receita anual de 2026", "azul")
    with c2:
        _card("Meta cooperativas", META_COOPERATIVAS, "45% do total recebido", "azul")
    with c3:
        _card("Executado", executado, f"{percentual_executado:.1f}% da meta anual", "verde")
    with c4:
        _card("Saldo a executar", saldo, "Meta anual ainda disponível", "laranja")

    st.markdown('<div class="fnde-box-title">Execução por cooperativa</div>', unsafe_allow_html=True)
    por_credor = filtrado.groupby("Cooperativa")["Valor executado"].sum() if not filtrado.empty else pd.Series(dtype=float)
    qtde_pagamentos = filtrado.groupby("Cooperativa").size() if not filtrado.empty else pd.Series(dtype=int)
    linhas_resumo = []
    for cooperativa in COOPERATIVAS:
        valor = float(por_credor.get(cooperativa, 0.0))
        quantidade = int(qtde_pagamentos.get(cooperativa, 0))
        linhas_resumo.append(
            f"<tr><td class='fnde-credor'>{cooperativa}</td><td>{quantidade}</td>"
            f"<td class='fnde-valor'>{_moeda(valor)}</td><td>{valor / META_COOPERATIVAS * 100:.1f}%</td></tr>"
        )
    st.markdown(
        "<div class='fnde-tabela'><table><thead><tr><th>CREDOR</th><th>PAGAMENTOS</th>"
        "<th>EXECUTADO</th><th>% DA META FNDE</th></tr></thead><tbody>"
        + "".join(linhas_resumo) + "</tbody></table></div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="fnde-box-title">Distribuição mensal de recursos por cooperativa</div>', unsafe_allow_html=True)
    matriz = pd.pivot_table(
        filtrado,
        index="Cooperativa",
        columns="Mês",
        values="Valor executado",
        aggfunc="sum",
        fill_value=0.0,
    ) if not filtrado.empty else pd.DataFrame()
    matriz = matriz.reindex(index=list(COOPERATIVAS), columns=MESES, fill_value=0.0)
    linhas = []
    for cooperativa, valores in matriz.iterrows():
        total_credor = float(valores.sum())
        celulas = "".join(f"<td>{_moeda(valor)}</td>" for valor in valores)
        linhas.append(f"<tr><td class='fnde-credor'>{cooperativa}</td>{celulas}<td class='fnde-total'>{_moeda(total_credor)}</td></tr>")
    totais_mes = matriz.sum(axis=0)
    total_geral = float(totais_mes.sum())
    rodape = "".join(f"<td class='fnde-total'>{_moeda(valor)}</td>" for valor in totais_mes)
    st.markdown(
        "<div class='fnde-tabela'><table><thead><tr><th>RAZÃO SOCIAL / CREDOR</th>"
        + "".join(f"<th>{mes.upper()}</th>" for mes in MESES)
        + "<th>TOTAL GERAL</th></tr></thead><tbody>" + "".join(linhas)
        + f"<tr><td class='fnde-total'>TOTAL CONSOLIDADO DO FILTRO</td>{rodape}<td class='fnde-total'>{_moeda(total_geral)}</td></tr>"
        + "</tbody></table></div>",
        unsafe_allow_html=True,
    )

    mensal = filtrado.groupby("Mês")["Valor executado"].sum() if not filtrado.empty else pd.Series(dtype=float)
    quantidade_mensal = filtrado.groupby("Mês").size() if not filtrado.empty else pd.Series(dtype=int)
    grafico = pd.DataFrame({"Mês": MESES, "Executado no mês": [float(mensal.get(mes, 0.0)) for mes in MESES]})
    grafico["Pagamentos"] = [int(quantidade_mensal.get(mes, 0)) for mes in MESES]
    meses_com_execucao = grafico.loc[grafico["Executado no mês"] > 0, "Executado no mês"]
    media_mensal = float(meses_com_execucao.mean()) if not meses_com_execucao.empty else 0.0
    desvio_mensal = float(meses_com_execucao.std(ddof=0)) if len(meses_com_execucao) > 1 else 0.0
    faixa_inferior = max(0.0, meta_mensal * 0.8)
    faixa_superior = meta_mensal * 1.2

    st.markdown('<div class="fnde-analise-titulo">Análise temporal e execução mensal</div>', unsafe_allow_html=True)
    with st.container():
        esquerda, direita = st.columns([1.18, .92], gap="large")
        with esquerda:
            st.markdown('<div class="fnde-subtitulo-grafico">Curva de execução mensal das cooperativas</div>', unsafe_allow_html=True)
            st.markdown(
                f"""<div class="fnde-mini-cards">
                <div class="fnde-mini-card"><div class="fnde-mini-label">META MENSAL</div><div class="fnde-mini-value">{_moeda(meta_mensal)}</div></div>
                <div class="fnde-mini-card"><div class="fnde-mini-label">MÉDIA EXECUTADA</div><div class="fnde-mini-value">{_moeda(media_mensal)}</div></div>
                <div class="fnde-mini-card"><div class="fnde-mini-label">FAIXA DE REFERÊNCIA</div><div class="fnde-mini-value">80% – 120% da meta</div></div>
                </div>""",
                unsafe_allow_html=True,
            )
            figura = go.Figure()
            figura.add_hrect(y0=faixa_inferior, y1=faixa_superior, fillcolor="rgba(2, 128, 144, .10)", line_width=0, layer="below")
            figura.add_hline(y=meta_mensal, line_width=1.5, line_dash="dash", line_color="#64748b", annotation_text="Meta mensal", annotation_position="top left", annotation_font=dict(size=10, color="#475569"))
            figura.add_scatter(name="Executado", x=grafico["Mês"], y=grafico["Executado no mês"], mode="lines+markers+text", text=[_moeda(valor) if valor else "" for valor in grafico["Executado no mês"]], textposition="top center", textfont=dict(size=9, color="#61758a"), line=dict(color="#00879a", width=3), marker=dict(color="#f39b16", size=9))
            figura.update_layout(height=330, margin=dict(l=10, r=10, t=28, b=10), showlegend=False, yaxis_tickprefix="R$ ", yaxis_tickformat=",.0f", plot_bgcolor="#fff", paper_bgcolor="#fff")
            figura.update_xaxes(showgrid=False, tickangle=-28)
            figura.update_yaxes(gridcolor="#e8eff4", zerolinecolor="#e8eff4")
            st.plotly_chart(figura, use_container_width=True, config={"displayModeBar": False})
        with direita:
            st.markdown('<div class="fnde-subtitulo-grafico">Resumo gerencial por mês</div>', unsafe_allow_html=True)
            linhas_mes = "".join(
                f"<tr><td>{linha['Mês']}</td><td>{linha['Pagamentos']}</td><td class='fnde-valor'>{_moeda(linha['Executado no mês'])}</td></tr>"
                for _, linha in grafico.iterrows()
            )
            st.markdown(
                "<div class='fnde-resumo-mes'><table><thead><tr><th>MÊS DE REFERÊNCIA</th><th>QTD. PAGAMENTOS</th><th>TOTAL EXECUTADO</th></tr></thead><tbody>"
                + linhas_mes
                + f"<tr><td class='fnde-total'>TOTAL GERAL</td><td class='fnde-total'>{int(grafico['Pagamentos'].sum())}</td><td class='fnde-total'>{_moeda(float(grafico['Executado no mês'].sum()))}</td></tr>"
                + "</tbody></table></div>",
                unsafe_allow_html=True,
            )

    st.caption("Base de cálculo: fonte 552, cooperativas cadastradas e pagamentos emitidos em 2026. Atualize a base de Pagamentos (OB) para refletir novas execuções.")
