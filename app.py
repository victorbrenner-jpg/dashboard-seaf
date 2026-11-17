import base64
import datetime
import html
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import urllib.parse
import urllib.request
import unicodedata
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
import textwrap

from modulos import conferencia, home, monitoramento_dea, monitoramento_fnde, relatorio_mde, relatorio_credores, ob_base, conciliacao_pd_extra


def assinatura_exportacao(df: pd.DataFrame, *contexto: object) -> tuple:
    """Identifica o recorte que originou um arquivo preparado na sessão.

    Os relatórios Excel são gerados apenas quando solicitados. Esta assinatura
    impede que um arquivo preparado para filtros anteriores continue disponível
    após qualquer mudança no recorte de dados.
    """
    contexto_normalizado = tuple(map(str, contexto))
    if df is None or df.empty:
        return (0, (), 0, contexto_normalizado)

    try:
        conteudo = int(pd.util.hash_pandas_object(df, index=True).sum())
    except (TypeError, ValueError):
        conteudo = hash((len(df), tuple(map(str, df.columns))))

    return (len(df), tuple(map(str, df.columns)), conteudo, contexto_normalizado)


# 1. CONFIGURAÇÃO DA PÁGINA (Deve ser a primeira linha executável do Streamlit)
st.set_page_config(
    page_title="Painel de Controle Financeiro SEAF - 2026",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -------------------------------------------------------------------------
# GERENCIAMENTO DE ESTADO, MEMÓRIA DE FILTROS E NAVEGAÇÃO ENTRE TELAS
# -------------------------------------------------------------------------
def sincronizar_filtro(chave_memoria, chave_widget):
    if chave_widget in st.session_state:
        st.session_state[chave_memoria] = st.session_state[chave_widget]


# Estado da tela ativa. A marca de versão evita que uma sessão anterior (por
# exemplo, após um deploy interrompido) abra a V2 em um módulo antigo.
VERSAO_INTERFACE = "v2-homolog-2026-09-01"
if st.session_state.get("versao_interface") != VERSAO_INTERFACE:
    st.session_state["versao_interface"] = VERSAO_INTERFACE
    st.session_state["tela_atual"] = "Início"
    st.session_state.pop("seletor_tela_global", None)
elif "tela_atual" not in st.session_state:
    st.session_state["tela_atual"] = "Início"

# --- MEMÓRIA DA TELA 1 (Pagamentos - OB) ---
if "mem_ob_tipo_data" not in st.session_state:
    st.session_state["mem_ob_tipo_data"] = "Por Mês de Competência"
if "mem_ob_meses" not in st.session_state:
    st.session_state["mem_ob_meses"] = []
if "mem_ob_ano" not in st.session_state:
    st.session_state["mem_ob_ano"] = ob_base.ano_padrao()
if "mem_ob_dt_ini" not in st.session_state:
    st.session_state["mem_ob_dt_ini"] = datetime.date(st.session_state["mem_ob_ano"], 1, 1)
if "mem_ob_dt_fim" not in st.session_state:
    st.session_state["mem_ob_dt_fim"] = datetime.date(st.session_state["mem_ob_ano"], 12, 31)
if "mem_ob_despesa" not in st.session_state:
    st.session_state["mem_ob_despesa"] = []
elif isinstance(st.session_state["mem_ob_despesa"], str):
    st.session_state["mem_ob_despesa"] = (
        []
        if st.session_state["mem_ob_despesa"] == "Todas as Despesas"
        else [st.session_state["mem_ob_despesa"]]
    )
if "mem_ob_grupos" not in st.session_state:
    st.session_state["mem_ob_grupos"] = []
if "mem_ob_tipo_item" not in st.session_state:
    st.session_state["mem_ob_tipo_item"] = []
if "mem_ob_credores" not in st.session_state:
    st.session_state["mem_ob_credores"] = []
if "mem_ob_fontes" not in st.session_state:
    st.session_state["mem_ob_fontes"] = []
if "mem_ob_marcadores_fonte" not in st.session_state:
    st.session_state["mem_ob_marcadores_fonte"] = []
if "mem_ob_objetos" not in st.session_state:
    st.session_state["mem_ob_objetos"] = []

# --- MEMÓRIA DA TELA 2 (Liquidação - NL) ---
if "mem_nl_tipo_periodo" not in st.session_state:
    st.session_state["mem_nl_tipo_periodo"] = "Por Mês de Competência"
if "mem_nl_comps" not in st.session_state:
    st.session_state["mem_nl_comps"] = []
if "mem_nl_datas" not in st.session_state:
    st.session_state["mem_nl_datas"] = None
if "mem_nl_dt_ini" not in st.session_state:
    intervalo_nl_anterior = st.session_state.get("mem_nl_datas")
    st.session_state["mem_nl_dt_ini"] = (
        intervalo_nl_anterior[0]
        if isinstance(intervalo_nl_anterior, (tuple, list))
        and len(intervalo_nl_anterior) == 2
        else None
    )
if "mem_nl_dt_fim" not in st.session_state:
    intervalo_nl_anterior = st.session_state.get("mem_nl_datas")
    st.session_state["mem_nl_dt_fim"] = (
        intervalo_nl_anterior[1]
        if isinstance(intervalo_nl_anterior, (tuple, list))
        and len(intervalo_nl_anterior) == 2
        else None
    )
if "mem_nl_grupo" not in st.session_state:
    st.session_state["mem_nl_grupo"] = []
elif isinstance(st.session_state["mem_nl_grupo"], str):
    # Mantém compatibilidade com a seleção única salva em sessões antigas.
    st.session_state["mem_nl_grupo"] = (
        []
        if st.session_state["mem_nl_grupo"] == "Todos"
        else [st.session_state["mem_nl_grupo"]]
    )
if "mem_nl_status" not in st.session_state:
    st.session_state["mem_nl_status"] = "Todos"
if "mem_nl_credores" not in st.session_state:
    st.session_state["mem_nl_credores"] = []
if "mem_nl_fonte" not in st.session_state:
    st.session_state["mem_nl_fonte"] = []
elif isinstance(st.session_state["mem_nl_fonte"], str):
    # Mantém compatibilidade com a seleção única salva em sessões antigas.
    st.session_state["mem_nl_fonte"] = (
        []
        if st.session_state["mem_nl_fonte"] == "Todas as fontes (Exibe tudo)"
        else [st.session_state["mem_nl_fonte"]]
    )
if "mem_nl_marcador_fonte" not in st.session_state:
    st.session_state["mem_nl_marcador_fonte"] = []
if "mem_nl_objetos" not in st.session_state:
    st.session_state["mem_nl_objetos"] = []

# --- MEMÓRIA DA TELA PD (filtros aplicados) ---
# Os widgets ficam em modo de edição dentro de um formulário. Somente ao
# clicar em "Aplicar filtros" estes valores passam a controlar o painel e
# as opções disponíveis nos filtros em cascata.
if "mem_pd_periodo" not in st.session_state:
    st.session_state["mem_pd_periodo"] = None
if "mem_pd_ug" not in st.session_state:
    st.session_state["mem_pd_ug"] = []
if "mem_pd_fonte" not in st.session_state:
    st.session_state["mem_pd_fonte"] = []
if "mem_pd_gd" not in st.session_state:
    st.session_state["mem_pd_gd"] = []
if "mem_pd_despesa" not in st.session_state:
    st.session_state["mem_pd_despesa"] = []
if "mem_pd_objeto" not in st.session_state:
    st.session_state["mem_pd_objeto"] = []
if "mem_pd_credor" not in st.session_state:
    st.session_state["mem_pd_credor"] = []
if "mem_pd_status" not in st.session_state:
    st.session_state["mem_pd_status"] = []

# --- MEMÓRIA DA TELA 3 (Priorização semanal) ---
# Os widgets desta tela não são renderizados quando o usuário navega para NL
# ou OB. Por isso os valores selecionados ficam em chaves independentes.
if "mem_plan_grupos" not in st.session_state:
    st.session_state["mem_plan_grupos"] = []
if "mem_plan_tipos_nl" not in st.session_state:
    st.session_state["mem_plan_tipos_nl"] = []
if "mem_plan_mes_programacao" not in st.session_state:
    # No primeiro acesso, abre no mês corrente. A seleção feita pelo usuário
    # continua preservada durante a navegação entre as telas.
    st.session_state["mem_plan_mes_programacao"] = datetime.date.today().strftime("%m/%Y")

# Estilização CSS
st.markdown(
    """
    <style>
    .titulo-pagina {
        color: #002b49;
        font-size: 2.25rem !important;
        font-weight: 700 !important;
        margin-bottom: 4px !important;
        font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
    }
    .barra-sistema {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: linear-gradient(90deg, #002b49 0%, #005691 52%, #028090 100%);
        color: #ffffff;
        border-radius: 9px 9px 0 0;
        /* Reserva a largura da aba lateral de filtros antes da marca. */
        padding: 10px 18px 10px 52px;
        font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        z-index: 100002 !important;
        box-shadow: 0 3px 10px rgba(0, 43, 73, 0.25) !important;
    }
    .barra-sistema .marca-sistema {
        font-weight: 800;
        letter-spacing: 0.3px;
        font-size: 15px;
    }
    .barra-sistema .exercicio-sistema {
        font-size: 12px;
        font-weight: 700;
        opacity: 0.95;
    }
    .st-key-seletor_tela_global {
        background: #eef4fa;
        border: 1px solid #cbd5e1;
        border-top: 0;
        border-radius: 0 0 9px 9px;
        padding: 7px 12px 8px 12px;
        margin-bottom: 18px;
        position: fixed !important;
        top: 41px !important;
        left: 0 !important;
        width: 100vw !important;
        z-index: 100001 !important;
        box-shadow: 0 5px 10px rgba(15, 23, 42, 0.14) !important;
    }
    /* Cabeçalho único e fixo: a navegação nunca se separa da barra SEAF. */
    .st-key-topo_navegacao {
        position: static !important;
    }
    .st-key-topo_navegacao .barra-sistema {
        border-radius: 0 !important;
    }
    .st-key-topo_navegacao .st-key-seletor_tela_global {
        margin-bottom: 0 !important;
        /* Impede que o primeiro módulo fique sob a aba vertical de filtros. */
        padding: 8px 22px 9px 52px !important;
    }
    /* Navegação por módulos: abas corporativas, com módulo ativo evidente. */
    .st-key-seletor_tela_global [data-testid="stSegmentedControl"] {
        background: transparent !important;
    }
    .st-key-seletor_tela_global [data-testid="stSegmentedControl"] [role="radiogroup"],
    .st-key-seletor_tela_global [data-baseweb="button-group"] {
        gap: 7px !important;
        background: transparent !important;
    }
    .st-key-seletor_tela_global [data-testid="stSegmentedControl"] button,
    .st-key-seletor_tela_global button[data-testid*="segmented_control"] {
        min-height: 36px !important;
        padding: 0 17px !important;
        border: 1px solid #c7d5e2 !important;
        border-radius: 7px !important;
        background: #ffffff !important;
        color: #334155 !important;
        font-size: 13px !important;
        font-weight: 650 !important;
        box-shadow: 0 2px 5px rgba(15, 42, 68, 0.07) !important;
        transition: all .18s ease !important;
    }
    .st-key-seletor_tela_global [data-testid="stSegmentedControl"] button:hover,
    .st-key-seletor_tela_global button[data-testid*="segmented_control"]:hover {
        background: #f0fdfa !important;
        border-color: #028090 !important;
        color: #005b63 !important;
        transform: translateY(-1px);
        box-shadow: 0 5px 10px rgba(2, 128, 144, 0.14) !important;
    }
    .st-key-seletor_tela_global [data-testid="stSegmentedControl"] button[aria-pressed="true"],
    .st-key-seletor_tela_global button[data-testid*="segmented_control"][aria-pressed="true"] {
        border-color: #007b84 !important;
        background: linear-gradient(135deg, #005691 0%, #028090 100%) !important;
        color: #ffffff !important;
        box-shadow: 0 5px 12px rgba(0, 86, 145, 0.25) !important;
    }
    .st-key-seletor_tela_global [data-testid="stSegmentedControl"] button[aria-pressed="true"]:hover,
    .st-key-seletor_tela_global button[data-testid*="segmented_control"][aria-pressed="true"]:hover {
        background: linear-gradient(135deg, #004a7c 0%, #01757d 100%) !important;
        color: #ffffff !important;
    }
    /* A barra SEAF e a navegação são fixas. O conteúdo começa logo abaixo
       delas sem permitir que o wrapper flex principal seja esticado. */
    body [data-testid="stMainBlockContainer"] {
        padding-top: 2.25rem !important;
    }
    /* O Streamlit mantém no bloco principal vários stElementContainer vazios
       (altura 0). Como o stVerticalBlock aplica gap de 1rem entre filhos, cada
       container vazio ainda criava 1rem de espaço e a soma empurrava o título
       centenas de pixels para baixo. Elementos realmente vazios não precisam
       participar do layout. */
    body [data-testid="stMainBlockContainer"] [data-testid="stElementContainer"]:empty {
        display: none !important;
    }
    /* Em versões atuais do Streamlit, muitos containers tecnicamente não são
       :empty porque recebem comentários/nós internos, embora tenham altura 0.
       :has() identifica esses placeholders sem conteúdo visual e os retira do
       fluxo, evitando que o gap de 1rem seja aplicado dezenas de vezes. */
    body [data-testid="stMainBlockContainer"] [data-testid="stElementContainer"]:not(:has(*)) {
        display: none !important;
    }
    body [data-testid="stMainBlockContainer"] [data-testid="stElementContainer"][style*="height: 0"] {
        display: none !important;
    }
    /* Padrão visual global: placeholders sem conteúdo não podem consumir o
       gap do stVerticalBlock. Mantemos o gap normal somente entre elementos
       reais, reproduzindo o espaçamento aprovado na tela de Liquidação. */
    body [data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] {
        row-gap: 1rem;
    }
    body [data-testid="stMainBlockContainer"] [data-testid="stElementContainer"]:not(:has(> *)) {
        display: none !important;
    }
    /* Navegação no fluxo normal do Streamlit: evita qualquer espaço fantasma
       entre o menu global e o conteúdo das páginas. */
    .st-key-topo_navegacao {
        position: relative !important;
        width: 100% !important;
        height: auto !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: visible !important;
        z-index: 10 !important;
    }
    /* Mantém o cabeçalho técnico invisível, sem eliminar o controle nativo
       que permite reabrir os filtros quando a barra lateral for recolhida. */
    header[data-testid="stHeader"] {
        background: transparent !important;
        height: 0 !important;
        z-index: 100003 !important;
    }
    header[data-testid="stHeader"] [data-testid="stToolbar"],
    header[data-testid="stHeader"] [data-testid="stDecoration"] {
        display: none !important;
    }
    [data-testid="stSidebarCollapsedControl"] {
        display: none !important;
    }
    [data-testid="stSidebar"] {
        z-index: 100000 !important;
        padding-top: 108px !important;
        /* Aba lateral de filtros: abre apenas ao passar o mouse ou navegar
           pelos seus campos com o teclado. */
        display: block !important;
        visibility: visible !important;
        transform: translateX(0) !important;
        margin-left: 0 !important;
        min-width: 28px !important;
        width: 28px !important;
        max-width: 28px !important;
        overflow: hidden !important;
        /* Período de tolerância: após escolher uma opção o menu portal fecha
           antes de o foco retornar ao campo. Sem essa janela a lateral dava
           a impressão de "fugir" do usuário. */
        transition: width .22s ease 1.35s, min-width .22s ease 1.35s, max-width .22s ease 1.35s !important;
        background: #f1f5f9 !important;
        border-right: 1px solid #d4e0ea !important;
    }
    [data-testid="stSidebar"][aria-expanded="false"] {
        min-width: 28px !important;
        width: 28px !important;
        max-width: 28px !important;
        transform: translateX(0) !important;
        visibility: visible !important;
    }
    [data-testid="stSidebar"]:hover,
    [data-testid="stSidebar"]:focus-within,
    [data-testid="stSidebar"]:has(input:focus),
    [data-testid="stSidebar"]:has([role="combobox"][aria-expanded="true"]),
    [data-testid="stSidebar"][aria-expanded="false"]:hover,
    [data-testid="stSidebar"][aria-expanded="false"]:focus-within {
        min-width: 312px !important;
        width: 312px !important;
        max-width: 312px !important;
        overflow-y: auto !important;
        transition-delay: 0s !important;
    }
    /* IMPORTANTE: os menus do multiselect do Streamlit/BaseWeb são
       renderizados em um portal fora da sidebar. Ao mover o mouse da
       sidebar para a lista de opções, :hover e :focus-within deixam de
       valer e a barra começava a se recolher no meio da seleção.
       Enquanto existir um popover/listbox/menu aberto em qualquer ponto
       da página, mantemos a sidebar travada na largura expandida. */
    body:has([data-baseweb="popover"]) [data-testid="stSidebar"],
    body:has([role="listbox"]) [data-testid="stSidebar"],
    body:has([role="menu"]) [data-testid="stSidebar"],
    body:has([data-baseweb="menu"]) [data-testid="stSidebar"],
    body:has([data-baseweb="select-menu"]) [data-testid="stSidebar"],
    body:has([role="combobox"][aria-expanded="true"]) [data-testid="stSidebar"] {
        min-width: 312px !important;
        width: 312px !important;
        max-width: 312px !important;
        overflow-y: auto !important;
        transition-delay: 0s !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        min-width: 312px !important;
        width: 312px !important;
    }
    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
        visibility: visible !important;
        opacity: 1 !important;
    }

    /* Barra de ações dos filtros no espaço superior reservado da sidebar.
       Os botões continuam pertencendo ao st.form (logo, mantêm a lógica de
       Aplicar/Limpar), mas visualmente ficam sempre acessíveis no topo. */
    [data-testid="stSidebar"] [data-testid="stForm"]
    [data-testid="stHorizontalBlock"]:has([data-testid="stFormSubmitButton"]) {
        position: fixed !important;
        top: 116px !important;
        left: 39px !important;
        width: 264px !important;
        z-index: 100006 !important;
        gap: 7px !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    /* Aplicar: azul institucional, coerente com cabeçalho/aba FILTROS. */
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"]
    button[kind="primary"],
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"]
    button[data-testid="stBaseButton-primary"],
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"]
    button[data-testid*="BaseButton-primary"] {
        min-height: 36px !important;
        border-radius: 7px !important;
        border: 1px solid #165a8a !important;
        background: #165a8a !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        box-shadow: 0 2px 6px rgba(22, 90, 138, .18) !important;
    }
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"]
    button[kind="primary"]:hover,
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"]
    button[data-testid="stBaseButton-primary"]:hover,
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"]
    button[data-testid*="BaseButton-primary"]:hover {
        border-color: #10456c !important;
        background: #10456c !important;
        color: #ffffff !important;
    }

    /* Limpar: azul-cinza claro. Evita o vermelho, que visualmente comunica
       erro/perigo e não combina com uma ação rotineira de limpeza de filtro. */
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"]
    button[kind="secondary"],
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"]
    button[data-testid="stBaseButton-secondary"],
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"]
    button[data-testid*="BaseButton-secondary"] {
        min-height: 36px !important;
        border-radius: 7px !important;
        border: 1px solid #c4ced8 !important;
        background: #f1f4f7 !important;
        color: #425466 !important;
        font-weight: 700 !important;
        box-shadow: none !important;
    }
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"]
    button[kind="secondary"]:hover,
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"]
    button[data-testid="stBaseButton-secondary"]:hover,
    [data-testid="stSidebar"] [data-testid="stFormSubmitButton"]
    button[data-testid*="BaseButton-secondary"]:hover {
        border-color: #aebdca !important;
        background: #e6ebf0 !important;
        color: #243b53 !important;
    }
    [data-testid="stSidebar"]::after {
        content: "FILTROS";
        position: fixed;
        top: 138px;
        left: 5px;
        z-index: 100005;
        writing-mode: vertical-rl;
        transform: rotate(180deg);
        color: #ffffff;
        background: #005691;
        border-radius: 0 6px 6px 0;
        padding: 10px 5px;
        font-size: 10px;
        font-weight: 800;
        letter-spacing: .5px;
        pointer-events: none;
    }
    [data-testid="stSidebar"]:hover::after,
    [data-testid="stSidebar"]:focus-within::after {
        display: none;
    }
    body:has([data-baseweb="popover"]) [data-testid="stSidebar"]::after,
    body:has([role="listbox"]) [data-testid="stSidebar"]::after,
    body:has([role="menu"]) [data-testid="stSidebar"]::after,
    body:has([data-baseweb="menu"]) [data-testid="stSidebar"]::after,
    body:has([data-baseweb="select-menu"]) [data-testid="stSidebar"]::after,
    body:has([role="combobox"][aria-expanded="true"]) [data-testid="stSidebar"]::after {
        display: none;
    }
    .subtitulo-pagina {
        color: #6c757d;
        font-size: 1.25rem !important;
        font-style: italic;
        margin-top: 0px !important;
        margin-bottom: 2px !important;
        font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
    }
    .metric-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border-left: 6px solid #002b49;
        padding: 12px 16px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 43, 73, 0.05);
        border: 1px solid #e2e8f0;
    }
    /* Botões: contraste e hierarquia para ações de decisão. */
    div.stButton > button,
    div.stDownloadButton > button {
        min-height: 38px;
        border: 1px solid #b8c9d8;
        border-radius: 7px;
        background: linear-gradient(180deg, #ffffff 0%, #f4f7fa 100%);
        color: #002b49;
        font-weight: 700;
        box-shadow: 0 2px 5px rgba(15, 42, 68, 0.08);
        transition: transform .16s ease, box-shadow .16s ease, border-color .16s ease, background .16s ease;
    }
    div.stButton > button:hover,
    div.stDownloadButton > button:hover {
        border-color: #028090;
        background: #f0fdfa;
        box-shadow: 0 5px 12px rgba(2, 128, 144, 0.16);
        transform: translateY(-1px);
    }
    div.stButton > button:active,
    div.stDownloadButton > button:active {
        transform: translateY(0);
        box-shadow: 0 1px 3px rgba(15, 42, 68, 0.12);
    }
    div.stButton > button:focus-visible,
    div.stDownloadButton > button:focus-visible {
        outline: 3px solid rgba(2, 128, 144, 0.25);
        outline-offset: 2px;
    }
    div.stDownloadButton > button,
    div.st-key-btn_gerar_relatorio_nl button,
    div.st-key-btn_gerar_relatorio_pd button,
    [class*="st-key-adicionar_objeto_"] button {
        border-color: #007b84;
        background: linear-gradient(135deg, #005691 0%, #028090 100%);
        color: #ffffff;
        box-shadow: 0 4px 10px rgba(0, 86, 145, 0.22);
    }
    div.stDownloadButton > button:hover,
    div.st-key-btn_gerar_relatorio_nl button:hover,
    div.st-key-btn_gerar_relatorio_pd button:hover,
    [class*="st-key-adicionar_objeto_"] button:hover {
        border-color: #006f78;
        background: linear-gradient(135deg, #004a7c 0%, #01757d 100%);
        color: #ffffff;
    }
    /* Estilo explícito para a exportação por credor, inclusive com wrappers do Streamlit. */
    .st-key-exportar_relacao_credores_ob button {
        min-height: 38px;
        border: 1px solid #007b84 !important;
        border-radius: 7px;
        background: linear-gradient(135deg, #005691 0%, #028090 100%) !important;
        color: #ffffff !important;
        font-weight: 700;
        box-shadow: 0 4px 10px rgba(0, 86, 145, 0.22);
    }
    .st-key-exportar_relacao_credores_ob button p {
        color: inherit !important;
    }
    .st-key-exportar_relacao_credores_ob button:hover {
        border-color: #006f78 !important;
        background: linear-gradient(135deg, #004a7c 0%, #01757d 100%) !important;
    }
    div.stDownloadButton > button:disabled,
    div.st-key-btn_gerar_relatorio_nl button:disabled,
    div.st-key-btn_gerar_relatorio_pd button:disabled,
    [class*="st-key-adicionar_objeto_"] button:disabled {
        opacity: 1 !important;
        border-color: #cbd5e1 !important;
        background: #e8eef3 !important;
        color: #64748b !important;
        box-shadow: none !important;
        cursor: not-allowed !important;
        transform: none !important;
    }
    div.stDownloadButton > button:disabled:hover,
    div.st-key-btn_gerar_relatorio_nl button:disabled:hover,
    div.st-key-btn_gerar_relatorio_pd button:disabled:hover,
    [class*="st-key-adicionar_objeto_"] button:disabled:hover {
        border-color: #cbd5e1 !important;
        background: #e8eef3 !important;
        color: #64748b !important;
        box-shadow: none !important;
        transform: none !important;
    }
    [class*="st-key-limpar_"] button {
        border-color: #d8b4b4;
        color: #9f2d2d;
        background: #fffafa;
        box-shadow: none;
    }
    [class*="st-key-limpar_"] button:hover {
        border-color: #c65b5b;
        color: #8b2525;
        background: #fff1f1;
        box-shadow: 0 4px 10px rgba(159, 45, 45, 0.12);
    }
    /* Ação de adicionar: mantém o rótulo visível antes, durante e depois do hover. */
    div.stButton[class*="st-key-adicionar_objeto_"] > button,
    [class*="st-key-adicionar_objeto_"] button {
        border-color: #d8b4b4 !important;
        color: #9f2d2d !important;
        background: #fffafa !important;
        box-shadow: none !important;
    }
    div.stButton[class*="st-key-adicionar_objeto_"] > button:hover:not(:disabled),
    [class*="st-key-adicionar_objeto_"] button:hover:not(:disabled) {
        border-color: #c65b5b !important;
        color: #8b2525 !important;
        background: #fff1f1 !important;
        box-shadow: 0 4px 10px rgba(198, 91, 91, 0.14) !important;
        transform: translateY(-1px);
    }
    /* Grades da priorização: cabeçalho institucional e leitura reforçada. */
    [data-testid="stDataFrame"] [role="columnheader"] {
        background: #005691 !important;
        color: #ffffff !important;
        border-color: #004a7c !important;
        font-weight: 700 !important;
    }
    [data-testid="stDataFrame"] [role="columnheader"] * {
        color: #ffffff !important;
        fill: #ffffff !important;
        font-weight: 700 !important;
    }
    [data-testid="stDataFrame"] [role="gridcell"],
    [data-testid="stDataFrame"] [role="gridcell"] * {
        color: #173a5e !important;
    }
    [data-testid="stDataFrame"] [role="gridcell"] {
        border-color: #d8e1ea !important;
    }
    .div-titulo {
        font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
        color: #002b49;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    .tabela-container {
        width: 100% !important;
        margin-bottom: 30px !important;
        overflow-x: auto !important; 
        overflow-y: hidden !important;
        background-color: #ffffff;
        border-radius: 6px;
        border: 1px solid #e2e8f0;
    }
    /* Quadro de credores: conserva o painel compacto e permite consultar
       todos os fornecedores sem limitar a matriz pelos primeiros registros. */
    .tabela-credores-container {
        max-height: 680px !important;
        overflow-y: auto !important;
        overflow-x: auto !important;
    }
    .tabela-credores-container .html-executiva thead th {
        position: sticky !important;
        top: 0 !important;
        z-index: 2 !important;
    }
    .tabela-credores-container .subtitulo-tabela-html {
        position: sticky !important;
        top: 0 !important;
        z-index: 3 !important;
    }
    .subtitulo-tabela-html {
        font-family: 'Inter', 'Segoe UI', Arial, sans-serif !important;
        font-size: 14.5px !important;
        font-weight: 700 !important;
        padding: 14px 20px !important;
        color: #ffffff !important;
        margin: 0px !important;
        letter-spacing: 0.5px;
    }
    .html-executiva {
        width: 100% !important;
        min-width: 1350px !important; 
        border-collapse: collapse !important;
        font-family: 'Inter', 'Segoe UI', Arial, sans-serif !important;
        font-size: 13px !important;
    }
    .html-executiva th {
        font-weight: 700 !important;
        padding: 14px 12px !important;
        text-align: center !important;
        border-bottom: 2px solid #cbd5e1 !important;
        background-color: #f8fafc !important;
        color: #475569 !important;
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 0.7px;
        white-space: nowrap !important; 
    }
    .html-executiva th:first-child {
        text-align: left !important;
        padding-left: 20px !important;
        width: 250px !important; 
    }
    .html-executiva td {
        padding: 12px 12px !important;
        border-bottom: 1px solid
