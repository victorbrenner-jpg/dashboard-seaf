"""Ajustes de infraestrutura compartilhados pelos módulos do painel."""

import time
import urllib.request

import pandas as pd
import streamlit as st


_PD_PUBLICACAO_MARKER = (
    "2PACX-1vRsMrqzxYHgTRv_tBJnDU_Rg1OpFmh_FCCo55w671Kna-IE8FIPD4rhL7O-bDwCsNMQW4Qj7UZGaBFP"
)
_URLLIB_URLOPEN_ORIGINAL = urllib.request.urlopen
_PD_TO_DATETIME_ORIGINAL = pd.to_datetime
_ST_SET_PAGE_CONFIG_ORIGINAL = st.set_page_config


_RESPONSIVE_CSS = r"""
<style>
/* HOMOLOGAÇÃO — responsividade isolada; desktop >= 769px permanece intacto. */
@media (max-width: 768px) {
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        width: 100% !important;
        max-width: 100vw !important;
        overflow-x: hidden !important;
    }

    body [data-testid="stMain"] {
        margin-left: 0 !important;
        width: 100vw !important;
    }

    body [data-testid="stMainBlockContainer"] {
        width: 100% !important;
        max-width: 100% !important;
        margin-left: 0 !important;
        padding-left: 0.85rem !important;
        padding-right: 0.85rem !important;
        padding-top: 94px !important;
        box-sizing: border-box !important;
    }

    body .barra-sistema {
        width: 100vw !important;
        max-width: 100vw !important;
        min-height: 42px !important;
        padding: 9px 12px !important;
        border-radius: 0 !important;
        box-sizing: border-box !important;
    }

    body .barra-sistema .marca-sistema {
        font-size: 13px !important;
        line-height: 1.2 !important;
        min-width: 0 !important;
    }

    body .barra-sistema .exercicio-sistema {
        font-size: 11px !important;
        white-space: nowrap !important;
        margin-left: 8px !important;
        flex: 0 0 auto !important;
    }

    /* Mobile: mantém somente o botão Início no acesso rápido. */
    body .st-key-seletor_tela_global {
        top: 42px !important;
        left: 0 !important;
        width: 100vw !important;
        max-width: 100vw !important;
        height: 44px !important;
        overflow: hidden !important;
        padding: 4px 8px !important;
        margin: 0 !important;
        box-sizing: border-box !important;
    }

    body .st-key-seletor_tela_global [data-testid="stSegmentedControl"] [role="radiogroup"],
    body .st-key-seletor_tela_global [data-baseweb="button-group"] {
        display: flex !important;
        flex-wrap: nowrap !important;
        width: auto !important;
        min-width: 0 !important;
        gap: 0 !important;
    }

    body .st-key-seletor_tela_global [data-testid="stSegmentedControl"] button:not(:first-child),
    body .st-key-seletor_tela_global button[data-testid*="segmented_control"]:not(:first-child) {
        display: none !important;
    }

    body .st-key-seletor_tela_global [data-testid="stSegmentedControl"] button:first-child,
    body .st-key-seletor_tela_global button[data-testid*="segmented_control"]:first-child {
        display: inline-flex !important;
        flex: 0 0 auto !important;
        width: auto !important;
        min-width: 92px !important;
        min-height: 34px !important;
        padding: 4px 12px !important;
        font-size: 11.5px !important;
        line-height: 1.15 !important;
        white-space: nowrap !important;
        justify-content: center !important;
        box-sizing: border-box !important;
    }

    /* Filtros mobile: mantém a lateral utilizável e legível. */
    body [data-testid="stSidebar"] {
        display: block !important;
        visibility: visible !important;
    }

    body [data-testid="stSidebar"]:hover,
    body [data-testid="stSidebar"]:focus-within,
    body [data-testid="stSidebar"]:has(input:focus),
    body [data-testid="stSidebar"]:has([role="combobox"][aria-expanded="true"]),
    body:has([data-baseweb="popover"]) [data-testid="stSidebar"],
    body:has([role="listbox"]) [data-testid="stSidebar"],
    body:has([role="menu"]) [data-testid="stSidebar"],
    body:has([data-baseweb="menu"]) [data-testid="stSidebar"],
    body:has([data-baseweb="select-menu"]) [data-testid="stSidebar"],
    body:has([role="combobox"][aria-expanded="true"]) [data-testid="stSidebar"] {
        min-width: min(340px, calc(100vw - 28px)) !important;
        width: min(340px, calc(100vw - 28px)) !important;
        max-width: min(340px, calc(100vw - 28px)) !important;
        overflow-y: auto !important;
    }

    body [data-testid="stSidebar"] > div:first-child {
        min-width: min(340px, calc(100vw - 28px)) !important;
        width: min(340px, calc(100vw - 28px)) !important;
        max-width: min(340px, calc(100vw - 28px)) !important;
        box-sizing: border-box !important;
    }

    body [data-testid="stSidebar"] label,
    body [data-testid="stSidebar"] label p,
    body [data-testid="stSidebar"] [data-testid="stWidgetLabel"],
    body [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
    body [data-testid="stSidebar"] .stMarkdown p,
    body [data-testid="stSidebar"] h1,
    body [data-testid="stSidebar"] h2,
    body [data-testid="stSidebar"] h3,
    body [data-testid="stSidebar"] h4 {
        color: #243447 !important;
        opacity: 1 !important;
    }

    body [data-testid="stSidebar"] [data-testid="stForm"]
    [data-testid="stHorizontalBlock"]:has([data-testid="stFormSubmitButton"]) {
        top: 88px !important;
        left: 38px !important;
        width: min(282px, calc(100vw - 76px)) !important;
        max-width: calc(100vw - 76px) !important;
        z-index: 100007 !important;
    }

    body [data-testid="stSidebar"] [data-testid="stFormSubmitButton"] button {
        min-height: 38px !important;
        font-size: 12px !important;
    }

    body [data-testid="stMain"] [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
        gap: 0.75rem !important;
        align-items: stretch !important;
    }

    body [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        flex: 1 1 calc(50% - 0.75rem) !important;
        width: auto !important;
        min-width: min(260px, 100%) !important;
    }

    body [data-testid="stMain"] [data-testid="stMetric"],
    body [data-testid="stMain"] [data-testid="stPlotlyChart"],
    body [data-testid="stMain"] iframe,
    body [data-testid="stMain"] canvas,
    body [data-testid="stMain"] svg {
        max-width: 100% !important;
    }

    body [data-testid="stMain"] [data-testid="stPlotlyChart"] {
        width: 100% !important;
        overflow: hidden !important;
    }

    body [data-testid="stMain"] [data-testid="stDataFrame"],
    body [data-testid="stMain"] [data-testid="stTable"] {
        display: block !important;
        width: 100% !important;
        max-width: 100% !important;
        overflow-x: auto !important;
        overflow-y: hidden !important;
        -webkit-overflow-scrolling: touch !important;
    }

    body [data-testid="stMain"] [data-testid="stButton"] button,
    body [data-testid="stMain"] [data-testid="stDownloadButton"] button,
    body [data-testid="stMain"] [data-testid="stFormSubmitButton"] button {
        width: 100% !important;
        min-height: 40px !important;
        white-space: normal !important;
    }

    body .titulo-pagina, body h1 {
        font-size: clamp(1.55rem, 6vw, 2rem) !important;
        line-height: 1.15 !important;
        overflow-wrap: normal !important;
        word-break: normal !important;
    }

    body h2 { font-size: clamp(1.25rem, 5vw, 1.7rem) !important; }
    body h3 { font-size: clamp(1.05rem, 4.5vw, 1.4rem) !important; }
}

@media (max-width: 480px) {
    body [data-testid="stMainBlockContainer"] {
        padding-left: 0.65rem !important;
        padding-right: 0.65rem !important;
        padding-top: 92px !important;
    }

    body [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        flex: 1 1 100% !important;
        width: 100% !important;
        min-width: 0 !important;
        max-width: 100% !important;
    }

    body .barra-sistema { padding: 9px 8px !important; }
    body .barra-sistema .marca-sistema { font-size: 11.5px !important; }
    body .barra-sistema .exercicio-sistema { font-size: 9.5px !important; }

    body .st-key-seletor_tela_global {
        height: 42px !important;
        padding: 4px 6px !important;
    }

    body .st-key-seletor_tela_global [data-testid="stSegmentedControl"] button:first-child,
    body .st-key-seletor_tela_global button[data-testid*="segmented_control"]:first-child {
        min-height: 32px !important;
        min-width: 86px !important;
        padding: 3px 10px !important;
        font-size: 10.5px !important;
    }

    body [data-testid="stSidebar"]:hover,
    body [data-testid="stSidebar"]:focus-within,
    body [data-testid="stSidebar"]:has(input:focus),
    body [data-testid="stSidebar"]:has([role="combobox"][aria-expanded="true"]) {
        min-width: calc(100vw - 24px) !important;
        width: calc(100vw - 24px) !important;
        max-width: calc(100vw - 24px) !important;
    }

    body [data-testid="stSidebar"] > div:first-child {
        min-width: calc(100vw - 24px) !important;
        width: calc(100vw - 24px) !important;
        max-width: calc(100vw - 24px) !important;
    }

    body [data-testid="stSidebar"] [data-testid="stForm"]
    [data-testid="stHorizontalBlock"]:has([data-testid="stFormSubmitButton"]) {
        top: 86px !important;
        left: 36px !important;
        width: calc(100vw - 72px) !important;
        max-width: calc(100vw - 72px) !important;
    }

    body [data-testid="stMain"] [data-testid="stMetricValue"] {
        font-size: clamp(1.2rem, 6.5vw, 1.65rem) !important;
        overflow-wrap: normal !important;
        word-break: normal !important;
        white-space: nowrap !important;
    }

    body [data-testid="stMain"] [data-testid="stMetricLabel"] {
        font-size: 0.86rem !important;
    }
}

@media (max-height: 500px) and (orientation: landscape) and (max-width: 950px) {
    body [data-testid="stMain"] {
        margin-left: 0 !important;
        width: 100vw !important;
    }

    body [data-testid="stMainBlockContainer"] {
        padding-top: 82px !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }

    body .barra-sistema {
        min-height: 36px !important;
        padding: 6px 12px !important;
    }

    body .st-key-seletor_tela_global {
        top: 36px !important;
        height: 40px !important;
        padding: 4px 8px !important;
    }

    body .st-key-seletor_tela_global [data-testid="stSegmentedControl"] button:first-child,
    body .st-key-seletor_tela_global button[data-testid*="segmented_control"]:first-child {
        min-height: 30px !important;
        min-width: 84px !important;
        padding: 3px 9px !important;
        font-size: 10px !important;
    }

    body [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        flex: 1 1 calc(50% - 0.6rem) !important;
        min-width: 260px !important;
    }
}
</style>
"""


def _set_page_config_com_responsividade(*args, **kwargs):
    """Mantém o page config original e injeta somente CSS responsivo em homologação."""
    resultado = _ST_SET_PAGE_CONFIG_ORIGINAL(*args, **kwargs)
    st.markdown(_RESPONSIVE_CSS, unsafe_allow_html=True)
    return resultado


def _urlopen_com_atualizacao_pd(requisicao, *args, **kwargs):
    """Evita reutilizar uma publicação CSV antiga somente na base de PD."""
    try:
        url = (
            requisicao.full_url
            if isinstance(requisicao, urllib.request.Request)
            else str(requisicao)
        )

        if _PD_PUBLICACAO_MARKER in url and "output=csv" in url:
            separador = "&" if "?" in url else "?"
            url_atualizada = f"{url}{separador}_ts={int(time.time() * 1000)}"

            if isinstance(requisicao, urllib.request.Request):
                requisicao = urllib.request.Request(
                    url_atualizada,
                    data=requisicao.data,
                    headers=dict(requisicao.header_items()),
                    method=requisicao.get_method(),
                )
            else:
                requisicao = url_atualizada
    except Exception:
        pass

    return _URLLIB_URLOPEN_ORIGINAL(requisicao, *args, **kwargs)


def _to_datetime_data_emissao_pd(arg, *args, **kwargs):
    """Corrige apenas a leitura brasileira da Data Emissão usada na carga da PD.

    A carga atual da PD usa format='mixed' com dayfirst=False. Para valores como
    02/09/2026 isso faz o pandas interpretar 9 de fevereiro. Nesta situação
    específica, força dayfirst=True. As demais conversões de data do painel
    permanecem inalteradas.
    """
    try:
        nome_serie = getattr(arg, "name", None)
        if (
            nome_serie == "Data Emissão"
            and kwargs.get("format") == "mixed"
            and kwargs.get("dayfirst") is False
        ):
            kwargs = dict(kwargs)
            kwargs["dayfirst"] = True
    except Exception:
        pass

    return _PD_TO_DATETIME_ORIGINAL(arg, *args, **kwargs)


# O app importa este pacote antes de definir carregar_dados_pd(). Assim,
# somente a leitura da publicação CSV da PD recebe um parâmetro anti-cache;
# todas as demais URLs continuam usando o comportamento original.
if st.set_page_config is not _set_page_config_com_responsividade:
    st.set_page_config = _set_page_config_com_responsividade

if urllib.request.urlopen is not _urlopen_com_atualizacao_pd:
    urllib.request.urlopen = _urlopen_com_atualizacao_pd

# Correção pontual da ambiguidade DD/MM/AAAA na Data Emissão da PD.
if pd.to_datetime is not _to_datetime_data_emissao_pd:
    pd.to_datetime = _to_datetime_data_emissao_pd
