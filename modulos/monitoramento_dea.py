"""Monitoramento gerencial de DEA integrado ao Painel SEAF."""

from __future__ import annotations

import io
import unicodedata
import pandas as pd
import streamlit as st

URL_BASE_DEA = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRFcspPcERcq_Eu2bFM5uHRa6thMKvCKf5zs_87QzokzZe3W5QYZFsWoK2m4seEkA/pub?gid=1881579019&single=true&output=csv"

def _normalizar(v):
    return " ".join(unicodedata.normalize("NFKD", str(v)).encode("ASCII","ignore").decode().upper().replace("/"," ").split())

def _col(cols, *nomes):
    mapa={_normalizar(c):c for c in cols}
    for n in nomes:
        if _normalizar(n) in mapa: return mapa[_normalizar(n)]
    return None

def _moeda(v):
    return f"R$ {float(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")

def _pct(v,total):
    return 0 if not total else (float(v)/float(total))*100

def _preparar(dados):
    dados=dados.dropna(how="all").copy()
    dados.columns=[str(c).strip() for c in dados.columns]
    campos={
        "Credor":("CREDOR",),"Processo / SEI":("SEI","PROCESSO","PROCESSO SEI"),
        "Valor":("VALOR",),"Ano DEA":("ANO DO DEA","ANO DO DEA2"),
        "Executiva":("EXECUTIVA",),"Grupo de despesa":("GRUPO DE DESPESA",),
        "Objeto":("OBJETO","DESCRIÇÃO DO OBJETO"),"Status pagamento":("STATUS PAGAMENTO",),
        "Status CPF":("STATUS CPF",),"SIPR 2026":("Nº SIPR 2026","N SIPR 2026"),
        "Prioritário":("PRIORITÁRIO","PRIORITARIO"),
    }
    ren={}
    for destino, nomes in campos.items():
        origem=_col(dados.columns,*nomes)
        if origem: ren[origem]=destino
    dados=dados.rename(columns=ren)
    obrig={"Credor","Valor","Status pagamento","Status CPF"}
    if obrig-set(dados.columns):
        raise ValueError("Colunas obrigatórias não encontradas: "+", ".join(sorted(obrig-set(dados.columns))))
    for c in dados.columns:
        if c!="Valor": dados[c]=dados[c].fillna("").astype(str).str.strip()
    # A publicação CSV do Google Sheets traz os valores monetários no padrão
    # brasileiro (ex.: 1.234.567,89). pd.to_numeric direto transforma tudo em NaN.
    valor = (
        dados["Valor"]
        .astype(str)
        .str.replace("R$", "", regex=False)
        .str.replace("\\xa0", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    dados["Valor"] = pd.to_numeric(valor, errors="coerce").fillna(0.0)
    return dados

@st.cache_data(ttl=300, show_spinner=False)
def _carregar_publicada():
    # Publicação CSV é mais estável e leve que a página HTML.
    # A BASE oficial possui linhas de apresentação antes do cabeçalho.
    for header in (2, 0, 1, 3):
        t = pd.read_csv(URL_BASE_DEA, header=header)
        if any(_normalizar(c) == "CREDOR" for c in t.columns):
            return _preparar(t)
    raise ValueError("O cabeçalho da BASE não foi localizado na publicação CSV.")

def _carregar_upload(arq):
    xls=pd.ExcelFile(io.BytesIO(arq.getvalue()))
    aba="BASE" if "BASE" in xls.sheet_names else xls.sheet_names[0]
    # A base oficial possui cabeçalho após as linhas de apresentação.
    for header in (2,0,1,3):
        d=pd.read_excel(xls,sheet_name=aba,header=header)
        if any(_normalizar(c)=="CREDOR" for c in d.columns):
            return _preparar(d)
    raise ValueError("Cabeçalho da BASE não localizado.")

def _opts(df,c):
    if c not in df: return []
    return sorted([x for x in df[c].astype(str).unique() if x and x.lower()!="nan"])

def _filtrar(df, filtros):
    out=df.copy()
    for c, vals in filtros.items():
        if vals and c in out: out=out[out[c].isin(vals)]
    return out

def _card(titulo, valor, subtitulo, classe="azul"):
    st.markdown(f"""<div class="dea-card {classe}">
      <div class="dea-card-title">{titulo}</div><div class="dea-card-value">{valor}</div>
      <div class="dea-card-sub">{subtitulo}</div></div>""",unsafe_allow_html=True)

<<<<<<< HEAD
def _painel_titulo(titulo: str, complemento: str = "") -> None:
    st.markdown(
        f"""
        <div class="dea-painel-titulo">
            <span>{titulo}</span>
            <small>{complemento}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_resumo(dados: pd.DataFrame, coluna: str, titulo: str) -> None:
    if coluna not in dados.columns or dados.empty:
        linhas = "<tr><td colspan='3'>Aguardando base DEA</td></tr>"
    else:
        resumo = dados.groupby(coluna, dropna=False)["Valor"].sum().sort_values(ascending=False).head(7)
        maior = float(resumo.max()) if not resumo.empty else 0.0
        linhas = "".join(
            f"""
            <tr>
              <td>{str(rotulo) if str(rotulo) else "Não informado"}</td>
              <td><span class="dea-barra"><i style="width:{(float(valor) / maior * 100) if maior else 0:.0f}%"></i></span></td>
              <td>{_moeda(float(valor))}</td>
            </tr>
            """
            for rotulo, valor in resumo.items()
        )
    st.markdown(
        f"""
        <div class="dea-resumo">
            <div class="dea-resumo-titulo">{titulo}</div>
            <table>
              <thead><tr><th>Situação</th><th></th><th>Valor total</th></tr></thead>
              <tbody>{linhas}</tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render() -> None:
    st.markdown(
        """
        <style>
          .dea-titulo {display:flex;align-items:center;justify-content:space-between;margin:0 0 .65rem;}
          .dea-titulo h2 {margin:0;color:#073d67;font:700 2rem/1.1 'Segoe UI',Arial,sans-serif;}
          .dea-titulo p {margin:0;color:#3f6280;font-size:.78rem;border:1px solid #bddaf1;border-radius:8px;background:#f5fbff;padding:.55rem .8rem;}
          .dea-card {min-height:84px;border:1px solid #c8e0ef;border-radius:8px;background:#fff;display:flex;align-items:center;gap:.8rem;padding:.75rem 1rem;box-sizing:border-box;}
          .dea-card .icone {width:42px;height:42px;border-radius:50%;background:#eef7ff;display:flex;align-items:center;justify-content:center;font-size:1.45rem;flex:0 0 auto;}
          .dea-card .rotulo {font:700 .78rem/1.1 'Segoe UI',Arial,sans-serif;color:#154a72;text-transform:none;}
          .dea-card .valor {font:800 1.35rem/1.2 'Segoe UI',Arial,sans-serif;color:#073d67;margin-top:.25rem;}
          .dea-card .detalhe {font:600 .7rem/1.2 'Segoe UI',Arial,sans-serif;color:#58718a;margin-top:.18rem;}
          .dea-painel-titulo {background:linear-gradient(100deg,#003b5c,#007f94);color:#fff;border-radius:7px 7px 0 0;padding:.55rem .85rem;font:700 .93rem 'Segoe UI',Arial,sans-serif;display:flex;justify-content:space-between;align-items:center;}
          .dea-painel-titulo small {font:500 .68rem 'Segoe UI',Arial,sans-serif;opacity:.92;}
          .dea-quadro {border:1px solid #c9ddec;border-top:0;border-radius:0 0 7px 7px;padding:.1rem .1rem .35rem;background:#fff;}
          .dea-resumo {border:1px solid #bfdaeb;border-radius:7px;background:#fff;margin-bottom:.65rem;overflow:hidden;}
          .dea-resumo-titulo {background:#005473;color:#fff;padding:.42rem .65rem;font:700 .82rem 'Segoe UI',Arial,sans-serif;}
          .dea-resumo table {width:100%;border-collapse:collapse;font:600 .7rem 'Segoe UI',Arial,sans-serif;color:#173e5e;}
          .dea-resumo th {background:#f1f7fb;font-size:.63rem;text-align:left;padding:.32rem .45rem;color:#254f70;}
          .dea-resumo td {padding:.33rem .45rem;border-top:1px solid #e3edf4;}
          .dea-resumo td:last-child,.dea-resumo th:last-child {text-align:right;white-space:nowrap;}
          .dea-barra {display:block;height:10px;background:#e8f0f5;border-radius:2px;min-width:35px;}
          .dea-barra i {display:block;height:100%;border-radius:2px;background:linear-gradient(90deg,#26b39d,#0987aa);}
          .dea-sem-base {margin:.75rem 0 .6rem;border:1px solid #bddaf1;border-radius:7px;padding:.62rem .8rem;background:#f2f9ff;color:#14527c;font-size:.84rem;}
          [data-testid="stSidebar"] .dea-filtros-titulo {font:800 1.05rem 'Segoe UI',Arial,sans-serif;color:#073d67;margin:.1rem 0 .45rem;}
          [data-testid="stSidebar"] .stButton button {border-radius:7px;font-weight:700;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="dea-titulo">
          <h2>📋 Monitoramento de DEA</h2>
          <p>Planejamento e situação de pagamento das Despesas de Exercícios Anteriores (DEA)</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
=======
def _painel_resumo(titulo, df, campo, total, limite=6):
    st.markdown(f'<div class="dea-box-title">{titulo}</div>',unsafe_allow_html=True)
    if campo not in df or df.empty:
        st.caption("Sem dados")
        return
    g=df.groupby(campo,dropna=False)["Valor"].sum().sort_values(ascending=False).head(limite)
    linhas=[]
    for nome,v in g.items():
        p=_pct(v,total)
        linhas.append(f"""<div class="dea-resumo-row"><div class="dea-resumo-label">{nome or "Não informado"}</div>
        <div class="dea-bar"><span style="width:{min(p,100):.1f}%"></span></div>
        <div class="dea-resumo-valor">{_moeda(v)}</div><div class="dea-resumo-pct">{p:.1f}%</div></div>""")
    st.markdown('<div class="dea-resumo">'+"".join(linhas)+'</div>',unsafe_allow_html=True)
>>>>>>> 02e2d896b4ee3b1b02a8b7bc72c3fa577a39970b

def render():
    st.markdown("""<style>
    .dea-head{display:flex;justify-content:space-between;align-items:center;margin:.1rem 0 .7rem}
    .dea-head h2{margin:0;color:#063b70;font-size:1.72rem}.dea-tag{background:#eef7ff;border:1px solid #cfe3f6;border-radius:9px;padding:8px 12px;color:#28557d;font-size:.78rem}
    .dea-card{background:white;border:1px solid #d7e3ee;border-radius:8px;padding:13px 16px;min-height:96px;box-shadow:0 1px 2px #00000008}
    .dea-card-title{font-size:.78rem;font-weight:700;color:#174d7c}.dea-card-value{font-size:1.32rem;font-weight:800;color:#063b70;margin-top:4px}.dea-card-sub{font-size:.76rem;color:#63788d;margin-top:3px}
    .dea-card.verde .dea-card-value{color:#16865b}.dea-card.amarelo .dea-card-value{color:#c37a00}.dea-card.dourado .dea-card-value{color:#a96d00}
    .dea-box-title{background:linear-gradient(90deg,#075b88,#08749a);color:white;font-weight:700;padding:7px 10px;border-radius:7px 7px 0 0;margin-top:5px}
    .dea-resumo{border:1px solid #d7e3ee;border-top:0;padding:4px 8px 8px;border-radius:0 0 7px 7px;background:#fff}
    .dea-resumo-row{display:grid;grid-template-columns:1.25fr .8fr 1.05fr .35fr;gap:7px;align-items:center;font-size:.72rem;padding:5px 0;border-bottom:1px solid #edf2f6}
    .dea-bar{height:10px;background:#e9f1f7}.dea-bar span{display:block;height:100%;background:#2782c5}.dea-resumo-valor{text-align:right}.dea-resumo-pct{text-align:right;font-weight:700}
    div[data-testid="stDataFrame"]{border:1px solid #d7e3ee;border-radius:0 0 7px 7px}
    </style>""",unsafe_allow_html=True)

    st.markdown('<div class="dea-head"><h2>▣ Monitoramento de DEA</h2><div class="dea-tag">Planejamento e situação de pagamento dos Despesas de Exercícios Anteriores (DEA)</div></div>',unsafe_allow_html=True)

    try:
        dados=_carregar_publicada()
        origem="Base DEA publicada"
    except Exception as erro:
        st.error("Não foi possível atualizar a Base DEA conectada ao Google Sheets.")
        st.caption(f"Detalhe técnico: {erro}")
        if st.button("↻ Tentar atualizar a base", key="dea_retry"):
            _carregar_publicada.clear()
            st.rerun()
        return

    # Filtros só alteram o painel quando Aplicar filtros é acionado.
    with st.sidebar:
<<<<<<< HEAD
        st.markdown("<div class='dea-filtros-titulo'>⚱ Filtros</div>", unsafe_allow_html=True)
        col_aplicar, col_limpar = st.columns(2)
        with col_aplicar:
            st.button("⚑ Aplicar", key="dea_aplicar", use_container_width=True)
        with col_limpar:
            if st.button("↻ Limpar", key="dea_limpar", use_container_width=True):
                for chave in ("dea_anos", "dea_status_cpf", "dea_status_pagamento", "dea_grupos", "dea_executivas", "dea_prioritarios", "dea_credor"):
                    st.session_state.pop(chave, None)
                st.rerun()
        st.markdown("---")
        st.markdown("#### Base de acompanhamento DEA")
        arquivo = st.file_uploader(
            "Atualizar planilha DEA (.xlsx)", type=["xlsx"], key="arquivo_monitoramento_dea",
            help="Envie a planilha com a aba BASE para atualizar a consulta desta sessão.",
        )
=======
        st.markdown("## ⚱ Filtros")
        if "dea_filtros_aplicados" not in st.session_state: st.session_state.dea_filtros_aplicados={}
        with st.form("form_filtros_dea"):
            ano=st.multiselect("Ano do DEA",_opts(dados,"Ano DEA"),default=st.session_state.dea_filtros_aplicados.get("Ano DEA",[]))
            cpf=st.multiselect("Status CPF",_opts(dados,"Status CPF"),default=st.session_state.dea_filtros_aplicados.get("Status CPF",[]))
            pag=st.multiselect("Status do Pagamento",_opts(dados,"Status pagamento"),default=st.session_state.dea_filtros_aplicados.get("Status pagamento",[]))
            grupo=st.multiselect("Grupo de Despesa",_opts(dados,"Grupo de despesa"),default=st.session_state.dea_filtros_aplicados.get("Grupo de despesa",[]))
            exe=st.multiselect("Executiva",_opts(dados,"Executiva"),default=st.session_state.dea_filtros_aplicados.get("Executiva",[]))
            pri=st.multiselect("Prioritário",_opts(dados,"Prioritário"),default=st.session_state.dea_filtros_aplicados.get("Prioritário",[]))
            credor=st.text_input("Credor (buscar por nome)",value=st.session_state.get("dea_credor_aplicado",""))
            aplicar=st.form_submit_button("🔎 Aplicar filtros",use_container_width=True,type="primary")
        limpar=st.button("↻ Limpar filtros",use_container_width=True)
        st.caption(origem)
    if limpar:
        st.session_state.dea_filtros_aplicados={}; st.session_state.dea_credor_aplicado=""; st.rerun()
    if aplicar:
        st.session_state.dea_filtros_aplicados={"Ano DEA":ano,"Status CPF":cpf,"Status pagamento":pag,"Grupo de despesa":grupo,"Executiva":exe,"Prioritário":pri}
        st.session_state.dea_credor_aplicado=credor.strip(); st.rerun()
>>>>>>> 02e2d896b4ee3b1b02a8b7bc72c3fa577a39970b

    filtrado=_filtrar(dados,st.session_state.dea_filtros_aplicados)
    termo=st.session_state.get("dea_credor_aplicado","")
    if termo: filtrado=filtrado[filtrado["Credor"].str.contains(termo,case=False,na=False)]

<<<<<<< HEAD
    with st.sidebar:
        st.markdown("---")
        anos = st.multiselect("Ano do DEA", _opcoes(dados, "Ano DEA"), key="dea_anos", disabled=not base_carregada)
        status_cpf = st.multiselect("Status CPF", _opcoes(dados, "Status CPF"), key="dea_status_cpf", disabled=not base_carregada)
        status_pagamento = st.multiselect("Status do Pagamento", _opcoes(dados, "Status pagamento"), key="dea_status_pagamento", disabled=not base_carregada)
        grupos = st.multiselect("Grupo de Despesa", _opcoes(dados, "Grupo de despesa"), key="dea_grupos", disabled=not base_carregada)
        executivas = st.multiselect("Executiva", _opcoes(dados, "Executiva"), key="dea_executivas", disabled=not base_carregada)
        prioritarios = st.multiselect("Prioritário", _opcoes(dados, "Prioritário"), key="dea_prioritarios", disabled=not base_carregada)
        termo_credor = st.text_input("Credor (buscar por nome)", key="dea_credor", disabled=not base_carregada)
=======
    total=filtrado["Valor"].sum()
    aguarda=filtrado[filtrado["Status CPF"].str.contains("AGUARD",case=False,na=False)]["Valor"].sum()
    pago_mask=filtrado["Status pagamento"].str.upper().eq("PAGO")
    pagos=filtrado.loc[pago_mask,"Valor"].sum()
    prio=filtrado.loc[filtrado.get("Prioritário",pd.Series("",index=filtrado.index)).str.upper().eq("SIM"),"Valor"].sum()
>>>>>>> 02e2d896b4ee3b1b02a8b7bc72c3fa577a39970b

    c1,c2,c3,c4=st.columns(4)
    with c1:_card("◉  Valor total monitorado",_moeda(total),f"{len(filtrado):,} registros".replace(",","."),"azul")
    with c2:_card("◷  Aguardando CPF",_moeda(aguarda),f"{_pct(aguarda,total):.1f}% do total","amarelo")
    with c3:_card("✓  Pagos",_moeda(pagos),f"{_pct(pagos,total):.1f}% do total","verde")
    with c4:_card("★  Prioritários",_moeda(prio),f"{_pct(prio,total):.1f}% do total","dourado")

<<<<<<< HEAD
    total = float(filtrado["Valor"].sum())
    aguardando_cpf = filtrado[filtrado["Status CPF"].str.contains("AGUARD", case=False, na=False)]
    pagos = filtrado[
        filtrado["Status pagamento"].str.contains("PAGO", case=False, na=False)
        & ~filtrado["Status pagamento"].str.contains("NÃO PAGO|NAO PAGO", case=False, na=False)
    ]
    prioritarios_dados = filtrado[
        filtrado.get("Prioritário", pd.Series("", index=filtrado.index)).str.upper().eq("SIM")
    ]

    cards = [
        ("💰", "Valor total monitorado", total, f"{len(filtrado):,} registros".replace(",", ".")),
        ("⏱", "Aguardando CPF", float(aguardando_cpf["Valor"].sum()), f"{len(aguardando_cpf):,} registros".replace(",", ".")),
        ("✓", "Pagos", float(pagos["Valor"].sum()), f"{len(pagos):,} registros".replace(",", ".")),
        ("★", "Prioritários", float(prioritarios_dados["Valor"].sum()), f"{len(prioritarios_dados):,} registros".replace(",", ".")),
    ]
    for coluna, card in zip(st.columns(4), cards):
        icone, rotulo, valor, detalhe = card
        coluna.markdown(
            f"<div class='dea-card'><div class='icone'>{icone}</div><div><div class='rotulo'>{rotulo}</div><div class='valor'>{_moeda(valor)}</div><div class='detalhe'>{detalhe}</div></div></div>",
            unsafe_allow_html=True,
        )

    if not base_carregada:
        st.markdown("<div class='dea-sem-base'>A estrutura está pronta. Atualize a planilha DEA na lateral para preencher os cards, filtros e quadros com os dados reais.</div>", unsafe_allow_html=True)

    agrupamento = {
        "Processo / SEI": "nunique",
        "SIPR 2026": lambda serie: "Sim" if serie.astype(bool).any() else "Não",
        "Status CPF": lambda serie: ", ".join(sorted(valor for valor in serie.unique() if valor)),
        "Status pagamento": lambda serie: ", ".join(sorted(valor for valor in serie.unique() if valor)),
        "Valor": "sum",
    }
    agrupamento = {coluna: regra for coluna, regra in agrupamento.items() if coluna in filtrado.columns}
    resumo = filtrado.groupby("Credor", dropna=False).agg(agrupamento).reset_index().sort_values("Valor", ascending=False)
    resumo = resumo.rename(columns={"Processo / SEI": "Processos", "SIPR 2026": "SIPR 2026", "Status pagamento": "Status Pagamento", "Valor": "Valor total"})
    if "Valor total" in resumo:
        resumo["Valor total"] = resumo["Valor total"].map(_moeda)
    resumo.index = range(1, len(resumo) + 1)
    resumo.index.name = "#"

    esquerda, direita = st.columns([2.9, 1.2])
    with esquerda:
        _painel_titulo("▣  Planejamento DEA por Credor", "Todos os credores | Ordenado por valor (decrescente)")
        with st.container(border=True):
            st.dataframe(resumo, use_container_width=True, height=410)
        _painel_titulo("▣  Objetos de despesa com maior valor")
        objetos = filtrado.groupby("Objeto", dropna=False)["Valor"].sum().sort_values(ascending=False).head(8).reset_index()
        objetos["Valor"] = objetos["Valor"].map(_moeda)
        objetos.index = range(1, len(objetos) + 1)
        objetos.index.name = "#"
        with st.container(border=True):
            st.dataframe(objetos.rename(columns={"Valor": "Valor total"}), use_container_width=True, height=220)
    with direita:
        _render_resumo(filtrado, "Status pagamento", "◉  Status do pagamento")
        _render_resumo(filtrado, "Status CPF", "✧  Status CPF")
        _render_resumo(filtrado, "Grupo de despesa", "◉  Grupo de despesa")
        _render_resumo(filtrado, "Executiva", "▣  Por Executiva")
=======
    principal,lateral=st.columns([3.15,1.0],gap="small")
    with principal:
        st.markdown('<div class="dea-box-title">▣ &nbsp; Credor</div>',unsafe_allow_html=True)
        if filtrado.empty:
            st.info("Nenhum registro encontrado para os filtros aplicados.")
        else:
            agg={"Valor":"sum"}
            if "Processo / SEI" in filtrado: agg["Processo / SEI"]="nunique"
            if "SIPR 2026" in filtrado: agg["SIPR 2026"]=lambda s:"Sim" if s.replace("",pd.NA).notna().any() else "Não"
            if "Status CPF" in filtrado: agg["Status CPF"]=lambda s:", ".join(sorted(set(x for x in s if x)))
            if "Status pagamento" in filtrado: agg["Status pagamento"]=lambda s:", ".join(sorted(set(x for x in s if x)))
            resumo=filtrado.groupby("Credor",dropna=False).agg(agg).reset_index().sort_values("Valor",ascending=False)
            resumo=resumo.rename(columns={"Processo / SEI":"Processos","Status pagamento":"Status Pagamento","Valor":"Valor total"})
            resumo.insert(0,"#",range(1,len(resumo)+1))
            evento_credor = st.dataframe(
                resumo,
                use_container_width=True,
                hide_index=True,
                height=420,
                column_config={"Valor total":st.column_config.NumberColumn("Valor total",format="R$ %.2f")},
                on_select="rerun",
                selection_mode="single-row",
                key="dea_tabela_credores",
            )

            # Ao selecionar um credor, exibe abaixo todos os processos que compõem o agrupamento.
            linhas_selecionadas = evento_credor.selection.rows if evento_credor else []
            if linhas_selecionadas:
                idx = linhas_selecionadas[0]
                if 0 <= idx < len(resumo):
                    credor_selecionado = resumo.iloc[idx]["Credor"]
                    processos = filtrado[filtrado["Credor"].eq(credor_selecionado)].copy()

                    st.markdown(
                        f'<div class="dea-box-title">▣ &nbsp; Processos — {credor_selecionado}</div>',
                        unsafe_allow_html=True,
                    )
                    colunas_detalhe = [
                        "Processo / SEI", "Objeto", "Ano DEA", "Valor",
                        "SIPR 2026", "Status CPF", "Status pagamento",
                        "Executiva", "Grupo de despesa", "Prioritário",
                    ]
                    colunas_detalhe = [col for col in colunas_detalhe if col in processos.columns]
                    processos = processos[colunas_detalhe].copy()
                    if "Valor" in processos.columns:
                        processos = processos.sort_values(["Processo / SEI"] if "Processo / SEI" in processos.columns else ["Valor"])
                    st.dataframe(
                        processos,
                        use_container_width=True,
                        hide_index=True,
                        height=min(360, 38 + 35 * max(len(processos), 1)),
                        column_config={
                            "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                            "Status pagamento": "Status Pagamento",
                        },
                    )

    with lateral:
        _painel_resumo("◉  Status do pagamento",filtrado,"Status pagamento",total,4)
        _painel_resumo("★  Status CPF",filtrado,"Status CPF",total,4)
        _painel_resumo("◫  Grupo de despesa",filtrado,"Grupo de despesa",total,6)
        _painel_resumo("▣  Por Executiva",filtrado,"Executiva",total,6)
>>>>>>> 02e2d896b4ee3b1b02a8b7bc72c3fa577a39970b
