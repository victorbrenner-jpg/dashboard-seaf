"""Troca as 3 tabelas de despesas (Correntes, RP, DEA) da tela de OB pela matriz nova.
Uso (na raiz do repositório):  python aplicar_matriz_no_app.py
Faz backup em app.py.antes_matriz e altera só o que é necessário. Reversível: copie o backup de volta.
"""
import re, shutil, sys

ARQ = sys.argv[1] if len(sys.argv) > 1 else "app.py"
s = open(ARQ, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in s else "\n"
s = s.replace("\r\n", "\n")

if "ob_matriz_despesas" in s:
    sys.exit("app.py já usa ob_matriz_despesas. Nada a fazer.")

# 1) import
alvo_imp = "relatorio_credores, ob_base, ob_ritmo_fontes\n"
if alvo_imp not in s:
    sys.exit("Linha de import esperada não encontrada.")
s = s.replace(alvo_imp, "relatorio_credores, ob_base, ob_ritmo_fontes, ob_matriz_despesas\n", 1)

# 2) as três chamadas seguidas viram uma só
padrao = re.compile(
    r'(?P<ind> +)renderizar_tabela_simetrica_html\(\n\s+df_matriz,\n\s+"CORRENTE",.*?'
    r'renderizar_tabela_simetrica_html\(\n\s+df_matriz,\n\s+"RP",.*?'
    r'renderizar_tabela_simetrica_html\(\n\s+df_matriz,\n\s+"DEA",.*?\n(?P=ind)\)\n',
    re.S)
m = padrao.search(s)
if not m:
    sys.exit("Bloco das três chamadas não encontrado (o app.py mudou?).")
i = m.group("ind")
novo = (
    f"{i}ob_matriz_despesas.render_matriz_despesas(\n"
    f"{i}    ob_matriz_despesas.dados_de_pivot(df_matriz, meses_exibicao),\n"
    f"{i}    ano=ano_ob,\n"
    f"{i}    meses=meses_exibicao,\n"
    f"{i})\n"
)
s = s[:m.start()] + novo + s[m.end():]

shutil.copyfile(ARQ, ARQ + ".antes_matriz")
open(ARQ, "w", encoding="utf-8", newline="").write(s.replace("\n", nl))
print("OK: app.py atualizado. Backup em", ARQ + ".antes_matriz")
