"""Página inicial da versão 2."""

from urllib.parse import quote

import streamlit as st


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
