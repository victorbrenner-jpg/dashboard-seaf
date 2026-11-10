# -*- coding: utf-8 -*-
"""
Inclui o filtro "Marcador de Fonte" na tela de Liquidação (NL) do PAG_SEAF.py.

Uso (na pasta do repositório):
    python aplicar_filtro_marcador_fonte.py PAG_SEAF.py

- Só altera trechos da tela NL; nada mais é tocado.
- Cada trecho precisa existir EXATAMENTE uma vez; se algum falhar, nada é gravado.
- Cria PAG_SEAF.py.bak antes de gravar e preserva as quebras de linha originais.
"""
import shutil
import sys

caminho = sys.argv[1] if len(sys.argv) > 1 else "PAG_SEAF.py"
bruto = open(caminho, "rb").read().decode("utf-8")
usa_crlf = "\r\n" in bruto
s = bruto.replace("\r\n", "\n")

if "mem_nl_marcador_fonte" in s:
    sys.exit("O filtro de Marcador de Fonte já existe neste arquivo. Nada foi alterado.")

edicoes = []

def sub(rotulo, antigo, novo):
    if s.count(antigo) != 1:
        sys.exit(f"ABORTADO: trecho '{rotulo}' encontrado {s.count(antigo)}x (esperado 1x). Nada foi gravado.")
    edicoes.append((rotulo, antigo, novo))

# 1) Memória do filtro aplicado
sub("memória", '''if "mem_nl_objetos" not in st.session_state:
    st.session_state["mem_nl_objetos"] = []
''', '''if "mem_nl_marcador_fonte" not in st.session_state:
    st.session_state["mem_nl_marcador_fonte"] = []
if "mem_nl_objetos" not in st.session_state:
    st.session_state["mem_nl_objetos"] = []
''')

# 2) Carga: coluna "Marcador de Fonte" da base de NL (reserva: planilha de relação)
sub("carga-df1", '''        df1["NL_Numero"] = (
            df1[col_nl].fillna("NL NÃO INFORMADA").astype(str).str.strip()
        )
        df1["NE_Chave"] = limpar_chave_ne(df1[col_ne1])''', '''        def localizar_col_marcador_fonte(df):
            # Prioriza colunas com MARCADOR e FONTE no nome; aceita apenas
            # "MARCADOR" quando for a única coluna com esse termo.
            cands = [c for c in df.columns if "MARCADOR" in str(c).upper()]
            com_fonte = [c for c in cands if "FONTE" in str(c).upper()]
            if com_fonte:
                return com_fonte[0]
            return cands[0] if len(cands) == 1 else None

        col_marc_fonte1 = localizar_col_marcador_fonte(df1)
        col_marc_fonte2 = localizar_col_marcador_fonte(df2)

        df1["Marcador_Fonte_Base1"] = (
            df1[col_marc_fonte1].fillna("").astype(str).str.strip()
            if col_marc_fonte1
            else ""
        )

        df1["NL_Numero"] = (
            df1[col_nl].fillna("NL NÃO INFORMADA").astype(str).str.strip()
        )
        df1["NE_Chave"] = limpar_chave_ne(df1[col_ne1])''')

sub("carga-merge", '''        df2_dedup = df2[df2["NE_Chave"] != ""].drop_duplicates(
            subset=["NE_Chave"]
        )

        df_merged = pd.merge(
            df1,
            df2_dedup[
                ["NE_Chave", "Fonte_Relacao", "Objeto_Relacao", "Grupo_Relacao"]
            ],
            on="NE_Chave",
            how="left",
        )
''', '''        df2["Marcador_Fonte_Base2"] = (
            df2[col_marc_fonte2].fillna("").astype(str).str.strip()
            if col_marc_fonte2
            else ""
        )

        df2_dedup = df2[df2["NE_Chave"] != ""].drop_duplicates(
            subset=["NE_Chave"]
        )

        df_merged = pd.merge(
            df1,
            df2_dedup[
                [
                    "NE_Chave", "Fonte_Relacao", "Objeto_Relacao",
                    "Grupo_Relacao", "Marcador_Fonte_Base2",
                ]
            ],
            on="NE_Chave",
            how="left",
        )

        # O Marcador de Fonte é atributo da própria NL (coluna da base de NL).
        # A planilha de relação por NE serve apenas de reserva.
        df_merged["Marcador_Fonte_Base2"] = (
            df_merged["Marcador_Fonte_Base2"].fillna("").astype(str).str.strip()
        )
        df_merged["Marcador_Fonte_Relacao"] = df_merged["Marcador_Fonte_Base1"].where(
            df_merged["Marcador_Fonte_Base1"] != "",
            df_merged["Marcador_Fonte_Base2"],
        )
        df_merged["Marcador_Fonte_Relacao"] = (
            df_merged["Marcador_Fonte_Relacao"]
            .replace("", "NÃO INFORMADO")
            .fillna("NÃO INFORMADO")
        )
''')

# 3) Função de filtragem (parâmetro novo no final: chamadas antigas não mudam)
sub("filtrar-assinatura", "ign_fnt=False, ign_obj=False):\n            d = df.copy()",
    "ign_fnt=False, ign_obj=False, ign_mrc=False):\n            d = df.copy()")

sub("filtrar-bloco", '''            # Objeto
            if not ign_obj and st.session_state["mem_nl_objetos"]:
                d = d[d["Objeto_Relacao"].isin(st.session_state["mem_nl_objetos"])]

            return d
''', '''            # Marcador de Fonte
            if not ign_mrc and st.session_state["mem_nl_marcador_fonte"]:
                d = d[d["Marcador_Fonte_Relacao"].isin(st.session_state["mem_nl_marcador_fonte"])]

            # Objeto
            if not ign_obj and st.session_state["mem_nl_objetos"]:
                d = d[d["Objeto_Relacao"].isin(st.session_state["mem_nl_objetos"])]

            return d
''')

# 4) Opções em cascata + valores válidos
sub("opcoes", '''        df_para_obj = filtrar_df_nl(df_base, ign_obj=True)
        objetos = sorted([''', '''        df_para_mrc = filtrar_df_nl(df_base, ign_mrc=True)
        marcadores_fonte = sorted([
            m for m in df_para_mrc["Marcador_Fonte_Relacao"].unique() if m != "NÃO INFORMADO"
        ]) if not df_para_mrc.empty else []

        df_para_obj = filtrar_df_nl(df_base, ign_obj=True)
        objetos = sorted([''')

sub("validos", '''        validos_obj_nl = [o for o in st.session_state["mem_nl_objetos"] if o in objetos]
''', '''        validos_mrc_nl = [m for m in st.session_state["mem_nl_marcador_fonte"] if m in marcadores_fonte]
        validos_obj_nl = [o for o in st.session_state["mem_nl_objetos"] if o in objetos]
''')

# 5) Limpar filtros
sub("limpar-mem", '''            st.session_state["mem_nl_fonte"] = []
            st.session_state["mem_nl_objetos"] = []
            st.session_state["w_nl_tipo_periodo"]''', '''            st.session_state["mem_nl_fonte"] = []
            st.session_state["mem_nl_marcador_fonte"] = []
            st.session_state["mem_nl_objetos"] = []
            st.session_state["w_nl_tipo_periodo"]''')

sub("limpar-widget", '''            st.session_state["w_nl_fonte"] = []
            st.session_state["w_nl_objetos"] = []''', '''            st.session_state["w_nl_fonte"] = []
            st.session_state["w_nl_marcador_fonte"] = []
            st.session_state["w_nl_objetos"] = []''')

# 6) Widget no formulário, logo após "Fonte de Recurso"
sub("widget", '''                key="w_nl_fonte",
            )

            st.divider()
            objeto_sel = st.multiselect(''', '''                key="w_nl_fonte",
            )

            st.divider()
            marcador_fonte_sel = st.multiselect(
                "Filtrar por Marcador de Fonte:",
                options=marcadores_fonte,
                default=validos_mrc_nl,
                placeholder="Todos os marcadores (Exibe tudo)",
                key="w_nl_marcador_fonte",
            )

            st.divider()
            objeto_sel = st.multiselect(''')

# 7) Aplicar filtros
sub("aplicar", '''                st.session_state["mem_nl_fonte"] = list(fontes_selecionadas_nl)
                st.session_state["mem_nl_objetos"] = list(objeto_sel)''', '''                st.session_state["mem_nl_fonte"] = list(fontes_selecionadas_nl)
                st.session_state["mem_nl_marcador_fonte"] = list(marcador_fonte_sel)
                st.session_state["mem_nl_objetos"] = list(objeto_sel)''')

for _, antigo, novo in edicoes:
    s = s.replace(antigo, novo)

compile(s, caminho, "exec")  # garante que o resultado é Python válido antes de gravar
shutil.copyfile(caminho, caminho + ".bak")
open(caminho, "wb").write((s.replace("\n", "\r\n") if usa_crlf else s).encode("utf-8"))
print(f"OK: {len(edicoes)} trechos alterados em {caminho} (backup: {caminho}.bak)")
