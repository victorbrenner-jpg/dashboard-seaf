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
/* ------------------------------------------------------------------
   HOMOLOGAÇÃO — camada responsiva isolada.
   Regras abaixo atuam somente até 768px e não alteram o desktop.
   ------------------------------------------------------------------ */
@media (max-width: 768px) {
    html,
    body,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {
        max-width: 100vw !important;
        overflow-x: hidden !important;
    }

    body [data-testid="stMainBlockContainer"] {
        width: 100% !important;
        max-width: 100% !important;
        padding-left: 0.85rem !important;
        padding-right: 0.85rem !important;
    }

    /* Cabeçalho superior e navegação permanecem em uma linha rolável,
       evitando que a página inteira ganhe rolagem horizontal. */
    body .barra-sistema {
        width: 100% !important;
        max-width: 100vw !important;
        padding-left: 12px !important;
        padding-right: 12px !important;
        box-sizing: border-box !important;
    }

    body .barra-sistema .marca-sistema {
        font-size: 13px !important;
        line-height: 1.2 !important;
    }

    body .barra-sistema .exercicio-sistema {
        font-size: 11px !important;
        white-space: nowrap !important;
        margin-left: 8px !important;
    }

    body .st-key-seletor_tela_global {
        width: 100% !important;
        max-width: 100vw !important;
        overflow-x: auto !important;
        overflow-y: hidden !important;
        -webkit-overflow-scrolling: touch !important;
        box-sizing: border-box !important;
        padding-left: 10px !important;
        padding-right: 10px !important;
    }

    body .st-key-seletor_tela_global [data-testid="stSegmentedControl"] [role="radiogroup"],
    body .st-key-seletor_tela_global [data-baseweb="button-group"] {
        display: flex !important;
        flex-wrap: nowrap !important;
        min-width: max-content !important;
        gap: 6px !important;
    }

    body .st-key-seletor_tela_global [data-testid="stSegmentedControl"] button,
    body .st-key-seletor_tela_global button[data-testid*="segmented_control"] {
        min-height: 34px !important;
        padding-left: 12px !important;
        padding-right: 12px !important;
        font-size: 12px !important;
        white-space: nowrap !important;
        flex: 0 0 auto !important;
    }

    /* Colunas da área principal passam a quebrar em até duas por linha. */
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

    /* Indicadores, gráficos e componentes nunca ultrapassam o viewport. */
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

    /* Tabelas mantêm todas as colunas e rolam somente dentro do componente. */
    body [data-testid="stMain"] [data-testid="stDataFrame"],
    body [data-testid="stMain"] [data-testid="stTable"] {
        display: block !important;
        width: 100% !important;
        max-width: 100% !important;
        overflow-x: auto !important;
        overflow-y: hidden !important;
        -webkit-overflow-scrolling: touch !important;
    }

    /* Botões de ação ficam confortáveis para toque sem mudar sua função. */
    body [data-testid="stMain"] [data-testid="stButton"] button,
    body [data-testid="stMain"] [data-testid="stDownloadButton"] button,
    body [data-testid="stMain"] [data-testid="stFormSubmitButton"] button {
        width: 100% !important;
        min-height: 40px !important;
        white-space: normal !important;
    }

    /* Sidebar: preserva a lógica atual e apenas impede largura maior que a tela. */
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
        min-width: min(312px, calc(100vw - 12px)) !important;
        width: min(312px, calc(100vw - 12px)) !important;
        max-width: min(312px, calc(100vw - 12px)) !important;
    }

    body [data-testid="stSidebar"] > div:first-child {
        min-width: min(312px, calc(100vw - 12px)) !important;
        width: min(312px, calc(100vw - 12px)) !important;
        max-width: min(312px, calc(100vw - 12px)) !important;
        box-sizing: border-box !important;
    }

    body [data-testid="stSidebar"] [data-testid="stForm"]
    [data-testid="stHorizontalBlock"]:has([data-testid="stFormSubmitButton"]) {
        left: 39px !important;
        width: min(264px, calc(100vw - 88px)) !important;
        max-width: calc(100vw - 88px) !important;
    }

    body .titulo-pagina,
    body h1 {
        font-size: clamp(1.55rem, 6vw, 2rem) !important;
        line-height: 1.15 !important;
    }

    body h2 {
        font-size: clamp(1.25rem, 5vw, 1.7rem) !important;
    }

    body h3 {
        font-size: clamp(1.05rem, 4.5vw, 1.4rem) !important;
    }
}

@media (max-width: 480px) {
    body [data-testid="stMainBlockContainer"] {
        padding-left: 0.65rem !important;
        padding-right: 0.65rem !important;
    }

    /* No celular, cada coluna ocupa uma linha inteira. */
    body [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        flex: 1 1 100% !important;
        width: 100% !important;
        min-width: 0 !important;
        max-width: 100% !important;
    }

    body .barra-sistema {
        padding-left: 9px !important;
        padding-right: 9px !important;
    }

    body .barra-sistema .marca-sistema {
        font-size: 12px !important;
    }

    body .barra-sistema .exercicio-sistema {
        font-size: 10px !important;
    }

    body .st-key-seletor_tela_global [data-testid="stSegmentedControl"] button,
    body .st-key-seletor_tela_global button[data-testid*="segmented_control"] {
        min-height: 32px !important;
        padding-left: 10px !important;
        padding-right: 10px !important;
        font-size: 11px !important;
    }

    body [data-testid="stMain"] [data-testid="stMetricValue"] {
        font-size: clamp(1.25rem, 7vw, 1.8rem) !important;
        overflow-wrap: anywhere !important;
    }

    body [data-testid="stMain"] [data-testid="stMetricLabel"] {
        font-size: 0.88rem !important;
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


# O app importa este pacote antes de executar st.set_page_config(). A camada
# responsiva é injetada imediatamente depois do page config e atua apenas nos
# breakpoints de tablet/celular, sem modificar a renderização desktop.
if st.set_page_config is not _set_page_config_com_responsividade:
    st.set_page_config = _set_page_config_com_responsividade

# O app importa este pacote antes de definir carregar_dados_pd(). Assim,
# somente a leitura da publicação CSV da PD recebe um parâmetro anti-cache;
# todas as demais URLs continuam usando o comportamento original.
if urllib.request.urlopen is not _urlopen_com_atualizacao_pd:
    urllib.request.urlopen = _urlopen_com_atualizacao_pd

# Correção pontual da ambiguidade DD/MM/AAAA na Data Emissão da PD.
if pd.to_datetime is not _to_datetime_data_emissao_pd:
    pd.to_datetime = _to_datetime_data_emissao_pd
