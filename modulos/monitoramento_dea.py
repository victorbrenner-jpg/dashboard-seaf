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
    bruto = dados["Valor"].copy()

    def _valor_numero(v):
        if pd.isna(v) or str(v).strip() == "":
            return 0.0
        # Se o CSV já entregou número, não altera separadores.
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
        s = str(v).strip()
        # Remove R$, espaços comuns e espaços não separáveis do Google Sheets.
        s = s.replace("R$", "").replace("\u00a0", "").replace(" ", "").strip()
        negativo = s.startswith("(") and s.endswith(")")
        s = s.strip("()")
        # Formato brasileiro: 1.234.567,89
        if "," in s:
            s = s.replace(".", "").replace(",", ".")
        # Formato internacional/numérico: 1234567.89 permanece como está.
        try:
            n = float(s)
            return -n if negativo else n
        except (TypeError, ValueError):
            return 0.0

    dados["Valor"] = bruto.map(_valor_numero)
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

def render():
    st.markdown("""<style>
    .dea-head{display:flex;justify-content:space-between;align-items:center;margin:.1rem 0 .7rem}
    .dea-cabecalho{padding:4px 0 14px}
    .dea-cabecalho h1{margin:0 0 14px;color:#1f3655;font-size:2rem;font-weight:800;line-height:1.2}
    .dea-subtitulo{color:#637387;font-size:1.08rem;line-height:1.75}
    .dea-divisor{border:0;border-top:1px solid #d9dfe6;margin:6px 0 18px}
    /* O app global reserva um espaço vertical grande para outras telas.
       Na DEA anulamos esse espaçamento para o conteúdo começar logo abaixo do menu. */
    section.main > div.block-container,
    [data-testid="stMainBlockContainer"]{padding-top:1.15rem !important;}
    .dea-head h2{margin:0;color:#063b70;font-size:1.72rem}.dea-tag{background:#eef7ff;border:1px solid #cfe3f6;border-radius:9px;padding:8px 12px;color:#28557d;font-size:.78rem}
    .dea-card{background:white;border:1px solid #d7e3ee;border-radius:8px;padding:13px 16px;min-height:96px;box-shadow:0 1px 2px #00000008}
    .dea-card-title{font-size:.78rem;font-weight:700;color:#174d7c}.dea-card-value{font-size:1.32rem;font-weight:800;color:#063b70;margin-top:4px}.dea-card-sub{font-size:.76rem;color:#63788d;margin-top:3px}
    .dea-card.verde .dea-card-value{color:#16865b}.dea-card.amarelo .dea-card-value{color:#c37a00}.dea-card.dourado .dea-card-value{color:#a96d00}
    .dea-box-title{background:linear-gradient(90deg,#075b88,#08749a);color:white;font-weight:700;padding:7px 10px;border-radius:7px 7px 0 0;margin-top:5px}
    .dea-resumo{border:1px solid #d7e3ee;border-top:0;padding:4px 8px 8px;border-radius:0 0 7px 7px;background:#fff}
    .dea-resumo-row{display:grid;grid-template-columns:1.25fr .8fr 1.05fr .35fr;gap:7px;align-items:center;font-size:.72rem;padding:5px 0;border-bottom:1px solid #edf2f6}
    .dea-bar{height:10px;background:#e9f1f7}.dea-bar span{display:block;height:100%;background:#2782c5}.dea-resumo-valor{text-align:right}.dea-resumo-pct{text-align:right;font-weight:700}
    div[data-testid="stDataFrame"]{border:1px solid #d7e3ee;border-radius:0 0 7px 7px}
    .dea-detalhe-card{border:1px solid #cbddeb;border-radius:7px;margin-top:12px;overflow:hidden;background:#fff}
    .dea-lista-credores [data-testid="stExpander"]{border:0;border-bottom:1px solid #dce7ef;border-radius:0;background:#fff}
    .dea-lista-credores [data-testid="stExpander"] summary{font-size:.75rem;color:#173e5e;min-height:38px}
    .dea-lista-credores [data-testid="stExpander"] summary:hover{background:#f4f9fc}
    .dea-exp-resumo{display:grid;grid-template-columns:.6fr 1.25fr 1.5fr .8fr;gap:10px;background:#073b61;color:#fff;padding:9px 12px;margin-bottom:2px}
    .dea-exp-resumo small{display:block;font-size:.58rem;font-weight:700;margin-bottom:3px}.dea-exp-resumo strong{font-size:.7rem}
    .dea-detalhe-credor{display:grid;grid-template-columns:1fr 110px 180px;align-items:center;background:#073b61;color:#fff;padding:12px 16px;gap:12px}
    .dea-detalhe-credor small{display:block;font-size:.65rem;font-weight:700;margin-bottom:4px}.dea-detalhe-credor strong{font-size:.82rem}
    .dea-detalhe-meta{text-align:right}.dea-detalhe-tabela{padding:7px 10px 10px;overflow-x:auto}
    .dea-detalhe-tabela table{width:100%;border-collapse:collapse;font-size:.72rem;color:#163b5b}
    .dea-detalhe-tabela th{background:#edf4f8;padding:8px 9px;font-size:.63rem;text-align:left;white-space:nowrap}
    .dea-detalhe-tabela td{padding:8px 9px;border-bottom:1px solid #dce7ef;vertical-align:top}
    .dea-detalhe-tabela tbody tr:last-child td{border-bottom:0}.dea-det-valor{text-align:right;font-weight:700;white-space:nowrap}
    </style>""",unsafe_allow_html=True)

    st.markdown(
        """
        <div class="dea-cabecalho">
          <h1>▣ Painel de Controle DEA — Exercício 2026</h1>
          <div class="dea-subtitulo"><em>Secretaria Executiva de Administração e Finanças (SEAF)</em></div>
          <div class="dea-subtitulo"><em>Gerência Financeira (GFIN)</em></div>
        </div>
        <hr class="dea-divisor">
        """,
        unsafe_allow_html=True,
    )

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

    filtrado=_filtrar(dados,st.session_state.dea_filtros_aplicados)
    termo=st.session_state.get("dea_credor_aplicado","")
    if termo: filtrado=filtrado[filtrado["Credor"].str.contains(termo,case=False,na=False)]


    total=filtrado["Valor"].sum()
    aguarda=filtrado[filtrado["Status CPF"].str.contains("AGUARD",case=False,na=False)]["Valor"].sum()
    pago_mask=filtrado["Status pagamento"].str.upper().eq("PAGO")
    pagos=filtrado.loc[pago_mask,"Valor"].sum()
    prio=filtrado.loc[filtrado.get("Prioritário",pd.Series("",index=filtrado.index)).str.upper().eq("SIM"),"Valor"].sum()

    c1,c2,c3,c4=st.columns(4)
    with c1:_card("◉  Valor total monitorado",_moeda(total),f"{len(filtrado):,} registros".replace(",","."),"azul")
    with c2:_card("◷  Aguardando CPF",_moeda(aguarda),f"{_pct(aguarda,total):.1f}% do total","amarelo")
    with c3:_card("✓  Pagos",_moeda(pagos),f"{_pct(pagos,total):.1f}% do total","verde")
    with c4:_card("★  Prioritários",_moeda(prio),f"{_pct(prio,total):.1f}% do total","dourado")


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
            # Lista expansível: cada credor abre seus processos logo abaixo da própria linha.
            # Mais de um credor pode permanecer aberto ao mesmo tempo.
            st.markdown('<div class="dea-lista-credores">', unsafe_allow_html=True)
            for _, linha in resumo.iterrows():
                nome_credor = linha["Credor"]
                qtd = int(linha.get("Processos", 0) or 0)
                valor_total = float(linha.get("Valor total", 0) or 0)
                sipr = linha.get("SIPR 2026", "Não")
                status_cpf = linha.get("Status CPF", "") or "—"
                status_pag = linha.get("Status Pagamento", "") or "—"
                processos_credor = filtrado[filtrado["Credor"].eq(nome_credor)].copy()
                mascara_aguardando = processos_credor["Status CPF"].str.contains(
                    "AGUARD", case=False, na=False
                )
                valor_aguardando = float(processos_credor.loc[mascara_aguardando, "Valor"].sum())
                possui_pendencia = valor_aguardando > 0

                # A lista principal é de cobrança: somente quem ainda aguarda
                # aprovação recebe alerta e valor. Credores já aprovados ficam
                # limpos, sem valor destacado, para leitura rápida do gestor.
                rotulo = f'{int(linha["#"])}  |  {nome_credor}'
                if possui_pendencia:
                    rotulo = (
                        f'{int(linha["#"])}  |  **🟠 {nome_credor}**'
                        f'  |  **AGUARDANDO APROVAÇÃO: {_moeda(valor_aguardando)}**'
                    )

                with st.expander(rotulo, expanded=False):
                    st.markdown(
                        f"""
                        <div class="dea-exp-resumo">
                          <div><small>SIPR 2026</small><strong>{sipr}</strong></div>
                          <div><small>STATUS CPF</small><strong>{status_cpf}</strong></div>
                          <div><small>STATUS PAGAMENTO</small><strong>{status_pag}</strong></div>
                          <div><small>{"VALOR AGUARDANDO" if possui_pendencia else "SITUAÇÃO"}</small><strong>{_moeda(valor_aguardando) if possui_pendencia else "APROVADO"}</strong></div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    processos = processos_credor
                    processos = processos.sort_values(
                        ["Processo / SEI"] if "Processo / SEI" in processos.columns else ["Valor"]
                    )
                    linhas_html = []
                    for _, proc in processos.iterrows():
                        sei = proc.get("Processo / SEI", "") or "—"
                        objeto = proc.get("Objeto", "") or "—"
                        ano = proc.get("Ano DEA", "") or "—"
                        sipr_proc = proc.get("SIPR 2026", "") or "—"
                        status_cpf_proc = proc.get("Status CPF", "") or "—"
                        status_pag_proc = proc.get("Status pagamento", "") or "—"
                        valor_proc = _moeda(proc.get("Valor", 0))
                        linhas_html.append(
                            f"""<tr>
                                <td><b>{sei}</b></td><td>{objeto}</td><td>{ano}</td>
                                <td>{sipr_proc}</td><td>{status_cpf_proc}</td>
                                <td>{status_pag_proc}</td><td class="dea-det-valor">{valor_proc}</td>
                            </tr>"""
                        )
                    st.markdown(
                        f"""
                        <div class="dea-detalhe-tabela">
                          <table>
                            <thead><tr><th>PROCESSO / SEI</th><th>OBJETO</th><th>ANO DEA</th>
                            <th>SIPR 2026</th><th>STATUS CPF</th><th>STATUS PAGAMENTO</th><th>VALOR</th></tr></thead>
                            <tbody>{"".join(linhas_html)}</tbody>
                          </table>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            st.markdown('</div>', unsafe_allow_html=True)

    with lateral:
        _painel_resumo("◉  Status do pagamento",filtrado,"Status pagamento",total,4)
        _painel_resumo("★  Status CPF",filtrado,"Status CPF",total,4)
        _painel_resumo("◫  Grupo de despesa",filtrado,"Grupo de despesa",total,6)
        _painel_resumo("▣  Por Executiva",filtrado,"Executiva",total,6)
