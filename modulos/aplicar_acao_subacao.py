"""Remove o título azul 'Ação e Subação' e reduz o botão do relatório.

Uso (na pasta do repositório):  python ajustar_visual_acao.py
Faz backup em app.py.bak_visual e só grava se o trecho for encontrado exatamente uma vez.
"""
import io
import shutil
import sys
from pathlib import Path

ARQ = Path("app.py")

ANTIGO = """            st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
            st.markdown(
                "<p style='font-weight: 700; color: #002b49; margin: 0 0 6px 0; font-size: 16px;'>"
                "Ação e Subação</p>",
                unsafe_allow_html=True,
            )
            tabela_acoes.exibir_tabela_acoes(df_filtrado, altura=520)
            if st.button(
                "📊 Gerar Relatório Ação/Subação",
                use_container_width=True,
                key="btn_gerar_relatorio_acao_nl",
            ):
                janela_relatorio_acao_nl()
"""

NOVO = """            st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
            tabela_acoes.exibir_tabela_acoes(df_filtrado, altura=520)
            _, col_botao_acao = st.columns([2.2, 1])
            with col_botao_acao:
                if st.button(
                    "📊 Gerar Relatório Ação/Subação",
                    use_container_width=True,
                    key="btn_gerar_relatorio_acao_nl",
                ):
                    janela_relatorio_acao_nl()
"""

texto = io.open(ARQ, encoding="utf-8", newline="").read()
crlf = "\r\n" in texto
if crlf:
    texto = texto.replace("\r\n", "\n")

if ANTIGO not in texto:
    if NOVO in texto:
        sys.exit("O ajuste já foi aplicado. Nada a fazer.")
    sys.exit("Trecho não encontrado no app.py (o botão já foi movido para baixo da tabela?). Nada foi alterado.")
if texto.count(ANTIGO) != 1:
    sys.exit("Trecho encontrado mais de uma vez. Nada foi alterado.")

shutil.copyfile(ARQ, "app.py.bak_visual")
texto = texto.replace(ANTIGO, NOVO, 1)
if crlf:
    texto = texto.replace("\n", "\r\n")
io.open(ARQ, "w", encoding="utf-8", newline="").write(texto)
print("OK: título removido e botão reduzido. Backup em app.py.bak_visual")