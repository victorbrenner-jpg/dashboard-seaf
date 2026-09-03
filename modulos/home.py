"""Página inicial da versão 2."""

from urllib.parse import quote

import pandas as pd
import plotly.express as px
import streamlit as st


_PX_LINE_ORIGINAL = px.line


def _formatar_milhoes(valor):
    return f"R$ {float(valor) / 1_000_000:,.1f}M".replace(",", "X").replace(".", ",").replace("X", ".")


def _line_com_estatistica_mensal(*args, **kwargs):
    """Enriquece apenas a curva mensal do painel com média e desvio-padrão."""
    figura = _PX_LINE_ORIGINAL(*args, **kwargs)

    data_frame = kwargs.get("data_frame")
    if data_frame is None and args:
        data_frame = args[0]

    if (
        isinstance(data_frame, pd.DataFrame)
        and kwargs.get("x") == "Mês de Referência"
        and kwargs.get("y") == "Total_Liq"
        and {"Mês de Referência", "Total_Liq"}.issubset(data_frame.columns)
    ):
        valores = pd.to_numeric(data_frame["Total_Liq"], errors="coerce")
        meses = pd.to_datetime(data_frame["Mês de Referência"], errors="coerce", dayfirst=True)
        hoje = pd.Timestamp.now()
        mes_atual = hoje.to_period("M")
        mascara_mes_em_andamento = meses.dt.to_period("M").eq(mes_atual)
        valores_validos = valores[(valores > 0) & ~mascara_mes_em_andamento].dropna()
        mes_em_andamento_excluido = bool(mascara_mes_em_andamento.any())

        if not valores_validos.empty:
            media = float(valores_validos.mean())
            desvio = float(valores_validos.std(ddof=0)) if len(valores_validos) > 1 else 0.0
            limite_inferior = max(0.0, media - desvio)
            limite_superior = media + desvio
            observacao = " · mês atual excluído" if mes_em_andamento_excluido else ""

            st.markdown(
                f"""
                <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:2px 0 8px 0;">
                    <div style="border:1px solid #dbe5ee;border-radius:8px;padding:8px 10px;background:#f8fbfd;">
                        <div style="font-size:10px;color:#64748b;font-weight:700;letter-spacing:.03em;">MÉDIA MENSAL</div>
                        <div style="font-size:16px;color:#005691;font-weight:800;margin-top:2px;">{_formatar_milhoes(media)}</div>
                    </div>
                    <div style="border:1px solid #dbe5ee;border-radius:8px;padding:8px 10px;background:#f8fbfd;">
                        <div style="font-size:10px;color:#64748b;font-weight:700;letter-spacing:.03em;">DESVIO-PADRÃO</div>
                        <div style="font-size:16px;color:#475569;font-weight:800;margin-top:2px;">{_formatar_milhoes(desvio)}</div>
                    </div>
                    <div style="border:1px solid #dbe5ee;border-radius:8px;padding:8px 10px;background:#f8fbfd;">
                        <div style="font-size:10px;color:#64748b;font-weight:700;letter-spacing:.03em;">FAIXA DE REFERÊNCIA ±1 DP</div>
                        <div style="font-size:13px;color:#334155;font-weight:800;margin-top:3px;">{_formatar_milhoes(limite_inferior)} – {_formatar_milhoes(limite_superior)}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            figura.add_hrect(
                y0=limite_inferior,
                y1=limite_superior,
                fillcolor="rgba(2, 128, 144, 0.09)",
                line_width=0,
                layer="below",
            )
            figura.add_hline(
                y=media,
                line_width=1.5,
                line_dash="dash",
                line_color="#64748b",
                annotation_text=f"Média {_formatar_milhoes(media)}{observacao}",
                annotation_position="top left",
                annotation_font=dict(size=10, color="#475569"),
            )

    return figura


if px.line is not _line_com_estatistica_mensal:
    px.line = _line_com_estatistica_mensal


MODULOS = [
    ("📑", "Liquidação (NL)"),
    ("📅", "Programa de Desembolso (PD)"),
    ("💳", "Pagamentos (OB)"),
    ("🎯", "Planejar Priorização"),
    ("📊", "Relatório 009717"),
]


def render() -> None:
    st.markdown(
        """
        <style>
          .home-shell {width: min(1420px, calc(100vw - 4rem)); margin: 0 auto; padding: 8.6rem 0 0;}
          .home-title {margin: 0; color: #1d344d; font: 600 2.15rem/1.15 'Segoe UI', Arial, sans-serif; letter-spacing: -.035em;}
          .home-grid {display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 1rem; margin-top: clamp(3.5rem, 9vh, 7rem);}
          .home-module {
            min-height: 172px; box-sizing: border-box; background: #fff; border: 1px solid #d7e1eb;
            border-radius: 9px; box-shadow: 0 4px 13px rgba(25, 56, 85, .07); color: #173753 !important;
            text-decoration: none !important; display: flex; flex-direction: column; align-items: center;
            justify-content: center; gap: .9rem; padding: 1rem; position: relative; overflow: hidden;
            transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
          }
          .home-module::before {content:''; position:absolute; inset:0 0 auto; height:3px; background:#00919d; opacity:0; transition:opacity .18s ease;}
          .home-module:hover {border-color:#b7d5dc; box-shadow:0 10px 23px rgba(25, 56, 85, .16); transform:translateY(-3px);}
          .home-module:hover::before {opacity:1;}
          .home-icon {width:43px; height:43px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:1.22rem; background:#eef6f8; border:1px solid #d7e9ec;}
          .home-name {text-align:center; font:650 .94rem/1.25 'Segoe UI', Arial, sans-serif;}
          @media (max-width: 950px) {.home-grid {grid-template-columns: repeat(3, minmax(0, 1fr));}}
          @media (max-width: 640px) {.home-shell {width:calc(100vw - 2rem); padding-top:6.7rem;} .home-title {font-size:1.7rem;} .home-grid {grid-template-columns:repeat(2, minmax(0, 1fr)); margin-top:2.5rem;} .home-module {min-height:135px;}}
        </style>
        """,
        unsafe_allow_html=True,
    )

    botoes = "".join(
        f"""
        <a class='home-module' href='?tela={quote(nome)}' target='_self'>
            <span class='home-icon'>{icone}</span>
            <span class='home-name'>{nome}</span>
        </a>
        """
        for icone, nome in MODULOS
    )
    st.markdown(
        f"""
        <main class='home-shell'>
            <h1 class='home-title'>Painel de Controle Financeiro</h1>
            <section class='home-grid' aria-label='Módulos do sistema'>{botoes}</section>
        </main>
        """,
        unsafe_allow_html=True,
    )
