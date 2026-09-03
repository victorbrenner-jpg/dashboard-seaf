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

    /* No mobile o trilho lateral de 28px do desktop desaparece por completo.
       Isso devolve toda a largura ao conteúdo e elimina a faixa branca lateral. */
    body [data-testid="stSidebar"] {
        display: none !important;
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
        padding-top: 168px !important;
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

    /* Navegação mobile em grade compacta, sem barra horizontal e sem cobrir
       o título da página. */
    body .st-key-seletor_tela_global {
        top: 42px !important;
        left: 0 !important;
        width: 100vw !important;
        max-width: 100vw !important;
        height: auto !important;
        overflow: visible !important;
        padding: 7px 8px 8px !important;
        margin: 0 !important;
        box-sizing: border-box !important;
    }

    body .st-key-seletor_tela_global [data-testid="stSegmentedControl"] [role="radiogroup"],
    body .st-key-seletor_tela_global [data-baseweb="button-group"] {
        display: grid !important;
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
        width: 100% !important;
        min-width: 0 !important;
        gap: 6px !important;
    }

    body .st-key-seletor_tela_global [data-testid="stSegmentedControl"] button,
    body .st-key-seletor_tela_global button[data-testid*="segmented_control"] {
        width: 100% !important;
        min-width: 0 !important;
        min-height: 36px !important;
        padding: 5px 8px !important;
        font-size: 11.5px !important;
        line-height: 1.15 !important;
        white-space: normal !important;
        overflow-wrap: anywhere !important;
        justify-content: center !important;
        box-sizing: border-box !important;
    }

    /* Colunas do conteúdo: até duas por linha no tablet. */
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
        padding-top: 172px !important;
    }

    /* Celular vertical: uma coluna real, usando 100% da tela. */
    body [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        flex: 1 1 100% !important;
        width: 100% !important;
        min-width: 0 !important;
        max-width: 100% !important;
    }

    body .barra-sistema { padding: 9px 8px !important; }
    body .barra-sistema .marca-sistema { font-size: 11.5px !important; }
    body .barra-sistema .exercicio-sistema { font-size: 9.5px !important; }

    body .st-key-seletor_tela_global [data-testid="stSegmentedControl"] button,
    body .st-key-seletor_tela_global button[data-testid*="segmented_control"] {
        min-height: 34px !important;
        padding: 4px 6px !important;
        font-size: 10.5px !important;
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

/* Celular deitado: usa duas colunas quando houver espaço e reduz o cabeçalho. */
@media (max-height: 500px) and (orientation: landscape) and (max-width: 950px) {
    body [data-testid="stSidebar"] { display: none !important; }

    body [data-testid="stMain"] {
        margin-left: 0 !important;
        width: 100vw !important;
    }

    body [data-testid="stMainBlockContainer"] {
        padding-top: 126px !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }

    body .barra-sistema {
        min-height: 36px !important;
        padding: 6px 12px !important;
    }

    body .st-key-seletor_tela_global {
        top: 36px !important;
        padding: 5px 8px 6px !important;
    }

    body .st-key-seletor_tela_global [data-testid="stSegmentedControl"] [role="radiogroup"],
    body .st-key-seletor_tela_global [data-baseweb="button-group"] {
        display: grid !important;
        grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
        gap: 5px !important;
    }

    body .st-key-seletor_tela_global [data-testid="stSegmentedControl"] button,
    body .st-key-seletor_tela_global button[data-testid*="segmented_control"] {
        min-height: 30px !important;
        padding: 3px 6px !important;
        font-size: 10px !important;
        white-space: normal !important;
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
        url = requisicao.full_url if isinstance(requisicao, urllib.request.Request) else str(requisicao)
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
    """Corrige apenas a leitura brasileira da Data Emissão usada na carga da PD."""
    try:
        nome_serie = getattr(arg, "name", None)
        if nome_serie == "Data Emissão" and kwargs.get("format") == "mixed" and kwargs.get("dayfirst") is False:
            kwargs = dict(kwargs)
            kwargs["dayfirst"] = True
    except Exception:
        pass
    return _PD_TO_DATETIME_ORIGINAL(arg, *args, **kwargs)


if st.set_page_config is not _set_page_config_com_responsividade:
    st.set_page_config = _set_page_config_com_responsividade

if urllib.request.urlopen is not _urlopen_com_atualizacao_pd:
    urllib.request.urlopen = _urlopen_com_atualizacao_pd

if pd.to_datetime is not _to_datetime_data_emissao_pd:
    pd.to_datetime = _to_datetime_data_emissao_pd
