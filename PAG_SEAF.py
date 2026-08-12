import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os
import io
import datetime
import urllib.request
import streamlit.components.v1 as components

# 1. CONFIGURAÇÃO DA PÁGINA (Deve ser a primeira linha executável do Streamlit)
st.set_page_config(
    page_title="Painel de Controle Financeiro SEAF - 2026", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------------------
# GERENCIAMENTO DE ESTADO E NAVEGAÇÃO ENTRE TELAS
# -------------------------------------------------------------------------
if "tela_atual" not in st.session_state:
    st.session_state["tela_atual"] = "Pagamentos (OB)"

# Estilização CSS de Alto Padrão e Padronização
st.markdown("""
    <style>
    /* Estilização dos Títulos e Subtítulos Padronizados */
    .titulo-pagina {
        color: #002b49;
        font-size: 2.25rem !important;
        font-weight: 700 !important;
        margin-bottom: 4px !important;
        font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
    }
    .subtitulo-pagina {
        color: #6c757d;
        font-size: 1.25rem !important;
        font-style: italic;
        margin-top: 0px !important;
        margin-bottom: 2px !important;
        font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
    }

    /* Estilização Geral do Fundo e Cards de Métrica */
    .metric-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border-left: 6px solid #002b49;
        padding: 12px 16px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 43, 73, 0.05);
        border: 1px solid #e2e8f0;
    }
    .div-titulo {
        font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
        color: #002b49;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    
    /* Arquitetura de Tabelas Modernas com Vida e Contraste */
    .tabela-container {
        width: 100% !important;
        margin-bottom: 30px !important;
        overflow-x: auto !important; 
        overflow-y: hidden !important;
        background-color: #ffffff;
        border-radius: 6px;
        border: 1px solid #e2e8f0;
    }
    .subtitulo-tabela-html {
        font-family: 'Inter', 'Segoe UI', Arial, sans-serif !important;
        font-size: 14.5px !important;
        font-weight: 700 !important;
        padding: 14px 20px !important;
        color: #ffffff !important;
        margin: 0px !important;
        letter-spacing: 0.5px;
    }
    .html-executiva {
        width: 100% !important;
        min-width: 1350px !important; 
        border-collapse: collapse !important;
        font-family: 'Inter', 'Segoe UI', Arial, sans-serif !important;
        font-size: 13px !important;
    }
    .html-executiva th {
        font-weight: 700 !important;
        padding: 14px 12px !important;
        text-align: center !important;
        border-bottom: 2px solid #cbd5e1 !important;
        background-color: #f8fafc !important;
        color: #475569 !important;
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 0.7px;
        white-space: nowrap !important; 
    }
    .html-executiva th:first-child {
        text-align: left !important;
        padding-left: 20px !important;
        width: 250px !important; 
    }
    .html-executiva td {
        padding: 12px 12px !important;
        border-bottom: 1px solid #f1f5f9 !important;
        text-align: center !important;
        color: #334155 !important;
        white-space: nowrap !important;
    }
    .html-executiva td:first-child {
        text-align: left !important;
        padding-left: 20px !important;
        font-weight: 600;
        color: #0f172a !important;
        white-space: normal !important;
    }
    .html-executiva th:last-child, 
    .html-executiva td:last-child {
        font-weight: bold !important;
        background-color: #f8fafc !important;
        text-align: right !important;
        padding-right: 20px !important;
        width: 140px !important;
    }
    .gnd-badge {
        display: inline-block;
        width: 9px;
        height: 9px;
        border-radius: 50%;
        margin-right: 10px;
        vertical-align: middle;
    }
    .html-executiva tbody tr:nth-child(even) {
        background-color: #fdfdfd !important;
    }
    .html-executiva tbody tr:hover {
        background-color: #f1f5f9 !important;
    }
    .linha-total-html {
        font-weight: bold !important;
        background-color: #f8fafc !important;
    }
    .linha-total-html td {
        border-top: 2px solid #002b49 !important;
        border-bottom: 3px double #002b49 !important;
        color: #002b49 !important;
        font-size: 13.5px !important;
        font-weight: 700 !important;
    }

    /* CSS Tela 2 - Liquidação */
    .tabela-dinamica-container {
        width: 100%;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        background: #ffffff;
        overflow: hidden;
        font-family: 'Segoe UI', sans-serif;
        font-size: 13px;
    }
    .tabela-dinamica-header {
        display: grid;
        grid-template-columns: 2.2fr 1fr 1fr;
        background-color: #092e4d;
        padding: 10px 14px;
        border-bottom: 2px solid #005691;
        font-weight: 700;
        font-size: 11px;
        color: #ffffff;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        align-items: center;
    }
    details.credor-group {
        border-bottom: 1px solid #e2e8f0;
        background-color: #ffffff;
        transition: background-color 0.2s ease;
    }
    details.credor-group:hover {
        background-color: #f8fafc;
    }
    summary.credor-summary {
        display: grid;
        grid-template-columns: 2.2fr 1fr 1fr;
        padding: 10px 14px;
        cursor: pointer;
        font-weight: 700;
        color: #002b49;
        user-select: none;
        align-items: center;
    }
    summary.credor-summary::-webkit-details-marker {
        display: inline-block;
        margin-right: 6px;
    }
    .subtabela-container {
        padding: 6px 10px 10px 10px;
        background: #f8fafc;
        border-top: 1px solid #e2e8f0;
    }
    .subtabela-detalhe {
        width: 100%;
        border-collapse: collapse;
        font-size: 12px;
        table-layout: fixed;
    }
    .subtabela-detalhe th {
        background-color: #edf2f7;
        color: #475569;
        font-size: 10px;
        text-transform: uppercase;
        padding: 6px 8px;
        border-bottom: 1px solid #cbd5e1;
        vertical-align: middle;
        text-align: center;
    }
    .subtabela-detalhe td {
        padding: 7px 8px;
        border-bottom: 1px solid #e2e8f0;
        color: #334155;
        vertical-align: middle;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        text-align: center;
    }
    .tabela-simples-container {
        width: 100%;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        background: #ffffff;
        overflow: hidden;
    }
    .tabela-simples {
        width: 100%;
        border-collapse: collapse;
        font-family: 'Segoe UI', sans-serif;
        font-size: 13px;
        table-layout: auto;
    }
    .tabela-simples th {
        color: #ffffff;
        font-weight: 700;
        font-size: 11px;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        padding: 10px 12px;
        border-bottom: 2px solid #092e4d;
        background-color: #092e4d;
        vertical-align: middle;
    }
    .tabela-simples td {
        padding: 8px 12px;
        border-bottom: 1px solid #f1f5f9;
        color: #334155;
        vertical-align: middle;
    }
    .tabela-simples tr.total-row td {
        color: #002b49;
        font-weight: 800;
        border-top: 2px solid #005691;
        border-bottom: none;
        background-color: #f1f5f9;
        padding: 8px 12px;
        vertical-align: middle;
    }
    </style>
""", unsafe_allow_html=True)

# Função Auxiliar Global de Formatação
def formatar_brl(valor):
    val_str = f"{valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    return f"R$ {val_str}"

# Função genérica para requisições com User-Agent
def ler_csv_url(url):
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    with urllib.request.urlopen(req) as response:
        csv_data = response.read().decode('utf-8')
    return pd.read_csv(io.StringIO(csv_data))

# -------------------------------------------------------------------------
# BOTÃO DE TRANSIÇÃO DAS TELAS LOGO ABAIXO DO NOME "FILTROS GLOBAIS"
# -------------------------------------------------------------------------
st.sidebar.markdown("### 🏛️ Filtros Globais")

tela_selecionada = st.sidebar.radio(
    "Selecione o Painel:",
    options=["Pagamentos (OB)", "Liquidação (NL)"],
    index=0 if st.session_state["tela_atual"] == "Pagamentos (OB)" else 1,
    horizontal=True,
    key="seletor_tela_global"
)
st.session_state["tela_atual"] = tela_selecionada

st.sidebar.markdown("---")

# -------------------------------------------------------------------------
# RENDERIZAÇÃO CONDICIONAL DAS TELAS
# -------------------------------------------------------------------------
if st.session_state["tela_atual"] == "Pagamentos (OB)":
    # ---------------------------------------------------------------------
    # CÓDIGO DA TELA 1 (PAINEL DE PAGAMENTOS)
    # ---------------------------------------------------------------------
    def atualizar_banco_via_csv():
        caminho_csv = r"C:\Users\victor.brenner\Desktop\Pagamentos_2026\02_Bases_Novas_Fontes\base_2026.csv"
        caminho_db = 'pagamentos2026.db'
        
        if not os.path.exists(caminho_csv):
            st.sidebar.error("Arquivo CSV não encontrado no caminho especificado.")
            return False
            
        try:
            df_novo = None
            for enc in ['utf-8-sig', 'latin-1', 'cp1252', 'utf-8']:
                for sep_tentativa in [';', ',']:
                    try:
                        df_novo = pd.read_csv(caminho_csv, sep=sep_tentativa, encoding=enc)
                        if df_novo is not None and len(df_novo.columns) > 1:
                            break
                    except:
                        continue
                if df_novo is not None and len(df_novo.columns) > 1:
                    break

            if df_novo is None:
                st.sidebar.error("Não foi possível ler o arquivo CSV.")
                return False

            df_novo.columns = [str(c).strip() for c in df_novo.columns]
            
            col_data = next((c for c in df_novo.columns if c.lower() in ["data emissão", "data emissao", "data", "dt_emissao"]), df_novo.columns[0])
            col_ob = next((c for c in df_novo.columns if c == 'DocumentoGD' or 'OB' in c.upper() or 'NÚMERO' in c.upper() or 'NUMERO' in c.upper()), df_novo.columns[0])
            col_valor = next((c for c in df_novo.columns if 'VALOR' in c.upper() or 'PAGAMENTO' in c.upper()), df_novo.columns[-1])
            
            df_novo = df_novo.dropna(subset=[col_data, col_ob, col_valor])
            df_novo['id_controle'] = df_novo[col_data].astype(str).str.strip() + "_" + df_novo[col_valor].astype(str).str.strip() + "_" + df_novo.index.astype(str)
            df_novo = df_novo.drop_duplicates(subset=['id_controle'])

            conn = sqlite3.connect(caminho_db)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pagamentos'")
            if not cursor.fetchone():
                df_novo.to_sql('pagamentos', conn, if_exists='replace', index=False)
                cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_pag_controle ON pagamentos(id_controle)")
                conn.commit()
                st.sidebar.success(f"Banco inicializado com {len(df_novo)} registros.")
            else:
                cursor.execute("PRAGMA table_info(pagamentos)")
                colunas_bd = [info[1] for info in cursor.fetchall()]
                if 'id_controle' not in colunas_bd:
                    cursor.execute("ALTER TABLE pagamentos ADD COLUMN id_controle TEXT")
                    conn.commit()
                
                ids_existentes = pd.read_sql_query("SELECT id_controle FROM pagamentos", conn)['id_controle'].dropna().tolist()
                df_inserir = df_novo[~df_novo['id_controle'].isin(ids_existentes)].copy()
                
                if not df_inserir.empty:
                    for col in colunas_bd:
                        if col not in df_inserir.columns:
                            df_inserir[col] = None
                    df_inserir = df_inserir[colunas_bd]
                    df_inserir.to_sql('pagamentos', conn, if_exists='append', index=False)
                    st.sidebar.success(f"Sucesso! {len(df_inserir)} novos pagamentos adicionados.")
                else:
                    st.sidebar.info("Nenhum registro novo detectado no CSV.")
                    
            conn.close()
            st.cache_data.clear()
            return True
        except Exception as e:
            st.sidebar.error(f"Erro ao processar atualização: {e}")
            return False

    @st.cache_data(ttl=60)
    def carregar_dados_auditoria():
        LINK_PUBLICADO = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT6mS4X1SSJWjVhFxNdTstSWgRdn_AFSGf9ZzdGqZ1GjZNeT7GSUZDqoB_4q5JnZPbgd2gJ2Jq0g4YJ/pub?gid=0&single=true&output=csv"
        try:
            df = ler_csv_url(LINK_PUBLICADO)
        except Exception as e:
            st.error(f"Erro ao conectar com a aba 'BASE' do Google Sheets: {e}")
            return pd.DataFrame()
            
        if df.empty:
            return df

        df = df.loc[:, ~df.columns.duplicated()]
        df.columns = [str(c).strip() for c in df.columns]

        colunas_obrigatorias = [
            "Número", "UG Emitente", "UG Pagadora", "Data Emissão", "Status", "Tipo de OB", 
            "NE", "Credor", "Nome do Credor", "Valor", "Fonte", "Natureza", "Status de Envio", 
            "RE", "PD", "GRUPO", "Elemento", "Despesa", "OBJETO", "DocumentoGD"
        ]
        for col in colunas_obrigatorias:
            if col not in df.columns:
                df[col] = None

        df = df.dropna(subset=["Valor"])

        df['Despesa_Tratada'] = 'CORRENTE'
        if 'Despesa' in df.columns:
            serie_despesa = df['Despesa']
            if isinstance(serie_despesa, pd.DataFrame):
                serie_despesa = serie_despesa.iloc[:, 0]
            amostra = serie_despesa.fillna('').astype(str).str.upper()
            
            def classificar_texto(val):
                v = str(val).upper().strip()
                if 'DEA' in v or 'EXERC' in v or 'ANTERIOR' in v or 'RECONHECIMENTO' in v: 
                    return 'DEA'
                elif 'RP' in v or 'RESTO' in v or 'PAGAR' in v: 
                    return 'RP'
                else: 
                    return 'CORRENTE'
            df['Despesa_Tratada'] = amostra.apply(classificar_texto)

        df['Grupo_Tratado'] = '3 - OUTRAS DESPESAS CORRENTES'
        if 'GRUPO' in df.columns:
            serie_grupo = df['GRUPO']
            if isinstance(serie_grupo, pd.DataFrame):
                serie_grupo = serie_grupo.iloc[:, 0]
            amostra_grupo = serie_grupo.fillna('').astype(str).str.strip().str.upper()
            df['Grupo_Tratado'] = amostra_grupo.apply(
                lambda v: '4 - INVESTIMENTOS' if 'INVEST' in v or '4' in v else '3 - OUTRAS DESPESAS CORRENTES'
            )
        
        if 'Valor' in df.columns:
            serie_valor = df['Valor']
            if isinstance(serie_valor, pd.DataFrame):
                serie_valor = serie_valor.iloc[:, 0]
            valores_str = serie_valor.fillna('0').astype(str)
            valores_str = valores_str.str.replace(r'[R$\s.]', '', regex=True).str.replace(',', '.')
            df['Valor_Limpo'] = pd.to_numeric(valores_str, errors='coerce').fillna(0.0)
        else:
            df['Valor_Limpo'] = 0.0
            
        if 'Data Emissão' in df.columns:
            serie_data = df['Data Emissão']
            if isinstance(serie_data, pd.DataFrame):
                serie_data = serie_data.iloc[:, 0]
            datas_convertidas = pd.to_datetime(serie_data, errors='coerce', dayfirst=True)
            df['Mes_Num'] = datas_convertidas.dt.month.fillna(0).astype(int).astype(str).str.zfill(2)
            mapa_meses = {
                '01': 'Jan/2026', '02': 'Fev/2026', '03': 'Mar/2026', '04': 'Abr/2026', 
                '05': 'Mai/2026', '06': 'Jun/2026', '07': 'Jul/2026', '08': 'Ago/2026',
                '09': 'Set/2026', '10': 'Out/2026', '11': 'Nov/2026', '12': 'Dez/2026'
            }
            df['Mes_Extenso'] = df['Mes_Num'].map(mapa_meses).fillna('Não Identificado')
        else:
            df['Mes_Extenso'] = 'Não Identificado'
        
        df['Credor_Nome_Tratado'] = df['Nome do Credor'].fillna(df['Credor']).fillna('NÃO IDENTIFICADO').astype(str).str.strip().str.upper()
        df['Fonte_Tratada'] = df['Fonte'].fillna('NÃO INFORMADA').astype(str).str.strip()
        df['DocumentoGD_Tratado'] = df['DocumentoGD'].fillna('NÃO CONSTA').astype(str).str.strip()
            
        return df

    try:
        df_base = carregar_dados_auditoria()
    except Exception as e:
        st.error(f"Erro ao carregar colunas do banco: {e}")
        st.stop()

    ordem_meses_ano = ['Jan/2026', 'Fev/2026', 'Mar/2026', 'Abr/2026', 'Mai/2026', 'Jun/2026', 'Jul/2026', 'Ago/2026', 'Set/2026', 'Out/2026', 'Nov/2026', 'Dez/2026']
    lista_meses_fixa = []
    if not df_base.empty and 'Mes_Extenso' in df_base.columns:
        lista_meses_fixa = [m for m in ordem_meses_ano if m in df_base['Mes_Extenso'].unique()]

    if not lista_meses_fixa:
        lista_meses_fixa = ['Jan/2026', 'Fev/2026', 'Mar/2026', 'Abr/2026', 'Mai/2026', 'Jun/2026']

    # FILTROS DA TELA 1 NA SIDEBAR
    tipo_filtro_data = st.sidebar.radio(
        "Como deseja filtrar o período?",
        options=["Por Mês de Competência", "Por Intervalo de Datas"],
        index=0,
        key="tipo_filtro_periodo_ob"
    )

    coluna_data = 'Data Emissão'
    meses_selecionados = []
    data_inicio = None
    data_fim = None

    if tipo_filtro_data == "Por Mês de Competência":
        meses_selecionados = st.sidebar.multiselect(
            "Filtrar Período de Competência:", 
            options=lista_meses_fixa, 
            default=[]
        )
    else:
        if not df_base.empty and coluna_data in df_base.columns:
            datas_convertidas = pd.to_datetime(df_base[coluna_data], format='mixed', dayfirst=True, errors='coerce').dt.date.dropna()
            data_min = datas_convertidas.min() if not datas_convertidas.empty else datetime.date(2026, 1, 1)
            data_max = datas_convertidas.max() if not datas_convertidas.empty else datetime.date(2026, 12, 31)
        else:
            data_min = datetime.date(2026, 1, 1)
            data_max = datetime.date(2026, 12, 31)

        col_dt1, col_dt2 = st.sidebar.columns(2)
        with col_dt1:
            data_inicio = st.date_input("Data Inicial:", value=data_min, format="DD/MM/YYYY", key="dt_ini_input_ob")
        with col_dt2:
            data_fim = st.date_input("Data Final:", value=data_max, format="DD/MM/YYYY", key="dt_fim_input_ob")

    st.sidebar.markdown("---")

    opcao_despesa = st.sidebar.selectbox(
        "Filtrar por Tipo de Despesa:",
        options=["Todas as Despesas", "CORRENTE (Dotação do Ano)", "RP (Restos a Pagar)", "DEA (Exercícios Anteriores)"],
        index=0,
        key="opcao_despesa_ob"
    )

    st.sidebar.markdown("---")

    nomes_disponiveis = sorted([str(n).strip() for n in df_base['Credor_Nome_Tratado'].unique() if n and str(n).lower() != 'nan']) if not df_base.empty else []
    nomes_selecionados = st.sidebar.multiselect("Filtrar por Entidade / Credor:", options=nomes_disponiveis, default=[], key="credor_ob")

    st.sidebar.markdown("---")
    lista_fontes = sorted([str(f).strip() for f in df_base['Fonte_Tratada'].unique() if f and str(f).lower() != 'nan']) if not df_base.empty else []

    fontes_selecionadas = st.sidebar.multiselect(
        "Filtrar por Fonte de Recurso:",
        options=lista_fontes,
        default=[],
        placeholder="Todas as fontes (Exibe tudo)",
        key="fonte_ob"
    )

    st.sidebar.markdown("---")
    coluna_objeto = 'OBJETO'

    if not df_base.empty and coluna_objeto in df_base.columns:
        lista_objetos = sorted([str(obj).strip() for obj in df_base[coluna_objeto].dropna().unique() if str(obj).lower() != 'nan'])
        objeto_selecionado = st.sidebar.multiselect(
            "Filtrar por Objeto de Despesa:",
            options=lista_objetos,
            default=[],
            placeholder="Todos os objetos",
            key="objeto_ob"
        )
    else:
        objeto_selecionado = []

    st.sidebar.markdown("---")

    df_filtrado = df_base.copy() if not df_base.empty else pd.DataFrame()

    if not df_filtrado.empty:
        if tipo_filtro_data == "Por Mês de Competência":
            if meses_selecionados:
                df_filtrado = df_filtrado[df_filtrado['Mes_Extenso'].isin(meses_selecionados)]
        else:
            serie_datas = pd.to_datetime(df_filtrado[coluna_data], format='mixed', dayfirst=True, errors='coerce').dt.date
            df_filtrado = df_filtrado[(serie_datas >= data_inicio) & (serie_datas <= data_fim)]

    if opcao_despesa == "CORRENTE (Dotação do Ano)":
        df_filtrado = df_filtrado[df_filtrado['Despesa_Tratada'] == 'CORRENTE']
    elif opcao_despesa == "RP (Restos a Pagar)":
        df_filtrado = df_filtrado[df_filtrado['Despesa_Tratada'] == 'RP']
    elif opcao_despesa == "DEA (Exercícios Anteriores)":
        df_filtrado = df_filtrado[df_filtrado['Despesa_Tratada'] == 'DEA']

    if nomes_selecionados:
        df_filtrado = df_filtrado[df_filtrado['Credor_Nome_Tratado'].isin(nomes_selecionados)]
    if fontes_selecionadas:
        df_filtrado = df_filtrado[df_filtrado['Fonte_Tratada'].isin(fontes_selecionadas)]
    if objeto_selecionado and coluna_objeto in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado[coluna_objeto].isin(objeto_selecionado)]

    st.sidebar.markdown("### 🔄 Atualizar Dados do Painel")
    if st.sidebar.button("🔄 Incorporar Novos Pagamentos do CSV", key="btn_csv_ob"):
        atualizar_banco_via_csv()
        st.rerun()

    # CABEÇALHO TELA 1
    st.markdown("<h2 class='titulo-pagina'>📊 Painel de Controle de Pagamentos — Exercício 2026</h2>", unsafe_allow_html=True)
    st.markdown("<p class='subtitulo-pagina'>Secretaria Executiva de Administração e Finanças (SEAF)</p>", unsafe_allow_html=True)
    st.markdown("<p class='subtitulo-pagina'>Gerência Financeira (GFIN)</p>", unsafe_allow_html=True)
    st.markdown("---")

    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)

    if not df_filtrado.empty:
        total_real_calculado = float(df_filtrado['Valor_Limpo'].sum())
        total_corrente = float(df_filtrado[df_filtrado['Despesa_Tratada'] == 'CORRENTE']['Valor_Limpo'].sum())
        total_rp = float(df_filtrado[df_filtrado['Despesa_Tratada'] == 'RP']['Valor_Limpo'].sum())
        total_dea = float(df_filtrado[df_filtrado['Despesa_Tratada'] == 'DEA']['Valor_Limpo'].sum())
        qtd_registros = int(df_filtrado.shape[0])
    else:
        total_real_calculado = total_corrente = total_rp = total_dea = 0.0
        qtd_registros = 0

    with col_kpi1:
        qtd_formatada_br = f"{qtd_registros:,}".replace(",", ".")
        st.markdown(f"<div class='metric-card'><p style='color: #6c757d; font-size: 11px; font-weight: bold; margin:0;'>VALOR TOTAL PAGO</p><h3 style='color: #002b49; margin: 5px 0;'>{formatar_brl(total_real_calculado)}</h3><p style='color: #28a745; font-size: 11px; margin:0;'>📋 Registros: {qtd_formatada_br}</p></div>", unsafe_allow_html=True)
    with col_kpi2:
        st.markdown(f"<div class='metric-card'><p style='color: #6c757d; font-size: 11px; font-weight: bold; margin:0;'>CORRENTE</p><h3 style='color: #028090; margin: 5px 0;'>{formatar_brl(total_corrente)}</h3><p style='color: #6c757d; font-size: 11px; margin:0;'>Dotação do Ano</p></div>", unsafe_allow_html=True)
    with col_kpi3:
        st.markdown(f"<div class='metric-card'><p style='color: #f77f00; font-size: 11px; font-weight: bold; margin:0;'>RESTOS A PAGAR (RP)</p><h3 style='color: #f77f00; margin: 5px 0;'>{formatar_brl(total_rp)}</h3><p style='color: #6c757d; font-size: 11px; margin:0;'>Exercícios Anteriores</p></div>", unsafe_allow_html=True)
    with col_kpi4:
        st.markdown(f"<div class='metric-card'><p style='color: #d62828; font-size: 11px; font-weight: bold; margin:0;'>EXERC. ANTERIORES (DEA)</p><h3 style='color: #d62828; margin: 5px 0;'>{formatar_brl(total_dea)}</h3><p style='color: #6c757d; font-size: 11px; margin:0;'>Reconhecimento de Passivo</p></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("### 📋 1. Demonstrativo Analítico por tipo de Despesa")

    if not df_filtrado.empty:
        if tipo_filtro_data == "Por Mês de Competência" and meses_selecionados:
            meses_exibicao = [m for m in lista_meses_fixa if m in meses_selecionados]
        else:
            meses_presentes = df_filtrado['Mes_Extenso'].unique()
            meses_exibicao = [m for m in lista_meses_fixa if m in meses_presentes]

        if not meses_exibicao:
            meses_exibicao = lista_meses_fixa

        df_matriz = df_filtrado.pivot_table(
            index=['Despesa_Tratada', 'Grupo_Tratado'],
            columns='Mes_Extenso',
            values='Valor_Limpo',
            aggfunc='sum',
            fill_value=0.0
        ).reset_index()

        for m in meses_exibicao:
            if m not in df_matriz.columns:
                df_matriz[m] = 0.0
                
        df_matriz['Total Geral'] = df_matriz[meses_exibicao].sum(axis=1)

        def renderizar_tabela_simetrica_html(df_origem, chave_natureza, grupos_obrigatorios, titulo_bloco, cor_hexa):
            linhas = []
            for gnd in grupos_obrigatorios:
                match = df_origem[(df_origem['Despesa_Tratada'] == chave_natureza) & (df_origem['Grupo_Tratado'] == gnd)]
                if not match.empty:
                    linhas.append(match.iloc[0].to_dict())
                else:
                    nova_linha = {'Despesa_Tratada': chave_natureza, 'Grupo_Tratado': gnd}
                    for col_m in meses_exibicao + ['Total Geral']:
                        nova_linha[col_m] = 0.0
                    linhas.append(nova_linha)
            
            linhas_corpo_html = ""
            totais_colunas = {m: 0.0 for m in meses_exibicao + ['Total Geral']}
            
            for row in linhas:
                colunas_valores = ""
                for m in meses_exibicao + ['Total Geral']:
                    val = float(row.get(m, 0.0))
                    totais_colunas[m] += val
                    colunas_valores += f"<td>{formatar_brl(val)}</td>"
                
                linhas_corpo_html += f"<tr><td><span class='gnd-badge' style='background-color: {cor_hexa};'></span>{row['Grupo_Tratado']}</td>{colunas_valores}</tr>"
                
            valores_totais_gnd = ""
            for m in meses_exibicao + ['Total Geral']:
                valores_totais_gnd += f"<td>{formatar_brl(totais_colunas[m])}</td>"
                
            cabecalhos_meses_html = "".join([f"<th>{mes}</th>" for mes in meses_exibicao])

            html_completo = (
                f"<div class='tabela-container'>"
                f"<div class='subtitulo-tabela-html' style='background: linear-gradient(90deg, {cor_hexa} 0%, #002b49 100%);'>{titulo_bloco}</div>"
                f"<table class='html-executiva'>"
                f"<thead><tr>"
                f"<th style='width: 30%;'>GRUPO DO GASTO (GND)</th>"
                f"{cabecalhos_meses_html}"
                f"<th>Total Geral</th>"
                f"</tr></thead>"
                f"<tbody>{linhas_corpo_html}"
                f"<tr class='linha-total-html'><td>📊 TOTAL GERAL DA NATUREZA</td>{valores_totais_gnd}</tr>"
                f"</tbody></table></div>"
            )
            st.markdown(html_completo, unsafe_allow_html=True)

        renderizar_tabela_simetrica_html(df_matriz, 'CORRENTE', ['3 - OUTRAS DESPESAS CORRENTES', '4 - INVESTIMENTOS'], "🔵 DESPESAS CORRENTES (Dotação Ordinária do Ano)", "#028090")
        renderizar_tabela_simetrica_html(df_matriz, 'RP', ['3 - OUTRAS DESPESAS CORRENTES', '4 - INVESTIMENTOS'], "🟠 RESTOS A PAGAR - RP (Compromissos de Anos Anteriores)", "#f77f00")
        renderizar_tabela_simetrica_html(df_matriz, 'DEA', ['3 - OUTRAS DESPESAS CORRENTES', '4 - INVESTIMENTOS'], "🔴 DESPESAS DE EXERCÍCIOS ANTERIORES - DEA (Reconhecimento de Passivo)", "#d62828")

    else:
        st.info("Nenhum registro financeiro localizado. Verifique os filtros.")

    st.markdown("---")

    st.markdown("### 🏦 2. Distribuição Mensal Consolidada por Fonte de Recurso")

    if not df_filtrado.empty:
        df_matriz_fonte = df_filtrado.pivot_table(
            index='Fonte_Tratada',
            columns='Mes_Extenso',
            values='Valor_Limpo',
            aggfunc='sum',
            fill_value=0.0
        ).reset_index()

        for m in lista_meses_fixa:
            if m not in df_matriz_fonte.columns:
                df_matriz_fonte[m] = 0.0
                
        df_matriz_fonte['Total Geral'] = df_matriz_fonte[lista_meses_fixa].sum(axis=1)
        df_matriz_fonte = df_matriz_fonte.sort_values(by='Total Geral', ascending=False)

        linhas_fonte_html = ""
        totais_meses_fonte = {m: 0.0 for m in lista_meses_fixa + ['Total Geral']}

        for _, row in df_matriz_fonte.iterrows():
            colunas_valores = ""
            for m in lista_meses_fixa + ['Total Geral']:
                val = float(row[m])
                totais_meses_fonte[m] += val
                colunas_valores += f"<td>{formatar_brl(val)}</td>"
            linhas_fonte_html += f"<tr><td>🏛️ {row['Fonte_Tratada']}</td>{colunas_valores}</tr>"

        valores_totais_fonte = ""
        for m in lista_meses_fixa + ['Total Geral']:
            valores_totais_fonte += f"<td>{formatar_brl(totais_meses_fonte[m])}</td>"

        cabecalhos_meses_fonte = "".join([f"<th style='width: 10%;'>{mes}</th>" for mes in lista_meses_fixa])

        html_fontes_resumo = (
            f"<div class='tabela-container'>"
            f"<div class='subtitulo-tabela-html' style='background: linear-gradient(90deg, #1d3557 0%, #002b49 100%);'>💰 Origem dos Recursos e Fluxo de Saída Monetária</div>"
            f"<table class='html-executiva'>"
            f"<thead><tr>"
            f"<th style='width: 30%;'>FONTE DE RECURSO</th>"
            f"{cabecalhos_meses_fonte}"
            f"<th style='width: 10%;'>Total Geral</th>"
            f"</tr></thead>"
            f"<tbody>{linhas_fonte_html}"
            f"<tr class='linha-total-html'><td>💰 TOTAL CONSOLIDADO POR FONTE</td>{valores_totais_fonte}</tr>"
            f"</tbody></table></div>"
        )
        st.markdown(html_fontes_resumo, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("### 📊 3. Análise Temporal e Desembolso Mensal")

    if not df_filtrado.empty:
        df_agrupado_mes = df_filtrado.groupby("Mes_Extenso").agg(
            Qtd_Docs=("Valor_Limpo", "count"),
            Total_Liq=("Valor_Limpo", "sum")
        ).reset_index()

        df_agrupado_mes = df_agrupado_mes.rename(columns={"Mes_Extenso": "Mês de Referência"})
        df_agrupado_mes["Mês de Referência"] = pd.Categorical(df_agrupado_mes["Mês de Referência"], categories=lista_meses_fixa, ordered=True)
        df_agrupado_mes = df_agrupado_mes.sort_values("Mês de Referência").fillna(0)

        for m in lista_meses_fixa:
            if m not in df_agrupado_mes["Mês de Referência"].values:
                nova_linha_vazia = pd.DataFrame([{"Mês de Referência": m, "Qtd_Docs": 0, "Total_Liq": 0.0}])
                df_agrupado_mes = pd.concat([df_agrupado_mes, nova_linha_vazia], ignore_index=True)

        df_agrupado_mes["Mês de Referência"] = pd.Categorical(df_agrupado_mes["Mês de Referência"], categories=lista_meses_fixa, ordered=True)
        df_agrupado_mes = df_agrupado_mes.sort_values("Mês de Referência")

        with st.container(border=True):
            col_grafico, col_tabela = st.columns([1.1, 0.9], gap="large")
            
            with col_grafico:
                st.markdown("<p style='font-weight: 700; color: #002b49; margin-bottom: 5px; font-family: sans-serif;'>Curva Crítica de Desembolso Mensal</p>", unsafe_allow_html=True)
                
                def formatar_dinamico_br(x):
                    if x >= 1_000_000:
                        valor_m = x / 1_000_000
                        return f"R$ {valor_m:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".") + "M"
                    elif x >= 1_000:
                        valor_k = int(x / 1_000)
                        return f"R$ {valor_k:,}".replace(",", ".") + "K"
                    elif x > 0:
                        return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    return "R$ 0"

                fig = px.line(
                    df_agrupado_mes, 
                    x="Mês de Referência", 
                    y="Total_Liq",
                    markers=True,
                    text=df_agrupado_mes["Total_Liq"].apply(formatar_dinamico_br),
                    hover_data={"Qtd_Docs": True, "Total_Liq": ":,.2f"}
                )
                
                fig.update_traces(
                    line=dict(color="#028090", width=4),
                    marker=dict(size=10, color="#f77f00", symbol="circle"),
                    textposition="top center"
                )
                
                fig.update_layout(
                    xaxis=dict(title=None, showgrid=False, tickfont=dict(size=11, color="#475569")),
                    yaxis=dict(
                        title=None, 
                        showgrid=True, 
                        gridcolor="rgba(218, 224, 233, 0.6)", 
                        tickfont=dict(size=11, color="#475569"),
                        tickformat=",.0f" 
                    ),
                    margin=dict(l=10, r=10, t=30, b=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    height=320
                )
                
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                
            with col_tabela:
                st.markdown("<p style='font-weight: 700; color: #002b49; margin-bottom: 12px; font-family: sans-serif;'>Resumo Gerencial por Mês</p>", unsafe_allow_html=True)
                
                total_documentos = int(df_agrupado_mes["Qtd_Docs"].sum())
                total_financeiro = float(df_agrupado_mes["Total_Liq"].sum())
                
                total_docs_formatado_br = f"{total_documentos:,}".replace(",", ".")
                
                linhas_tabela_html = ""
                for _, row in df_agrupado_mes.iterrows():
                    valor_formatado = formatar_brl(row['Total_Liq'])
                    qtd_docs_br = f"{int(row['Qtd_Docs']):,}".replace(",", ".")
                    linhas_tabela_html += f'<tr style="border-bottom: 1px solid #f1f5f9;"><td style="padding: 10px 15px; text-align: left; color: #334155; font-family: sans-serif; font-size: 13px;">{row["Mês de Referência"]}</td><td style="padding: 10px 15px; text-align: center; color: #334155; font-family: sans-serif; font-size: 13px;">{qtd_docs_br}</td><td style="padding: 10px 15px; text-align: right; color: #0f172a; font-family: sans-serif; font-size: 13px; font-weight: 600;">{valor_formatado}</td></tr>'
                    
                html_tabela_gerencial = (
                    f'<div style="border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; background-color: #ffffff; width: 100%;">'
                    f'<table style="width: 100%; border-collapse: collapse; text-align: left; margin: 0; padding: 0;">'
                    f'<thead>'
                    f'<tr style="background-color: #f8fafc; border-bottom: 1px solid #e2e8f0;">'
                    f'<th style="padding: 12px 15px; font-family: sans-serif; font-size: 11px; font-weight: 700; color: #475569; text-align: left;">MÊS DE REFERÊNCIA</th>'
                    f'<th style="padding: 12px 15px; font-family: sans-serif; font-size: 11px; font-weight: 700; color: #475569; text-align: center;">QTD. DOCS</th>'
                    f'<th style="padding: 12px 15px; font-family: sans-serif; font-size: 11px; font-weight: 700; color: #475569; text-align: right;">TOTAL PAGO</th>'
                    f'</tr>'
                    f'</thead>'
                    f'<tbody>{linhas_tabela_html}</tbody>'
                    f'<tfoot>'
                    f'<tr style="background-color: #f8fafc; border-top: 2px solid #002b49; font-weight: 700;">'
                    f'<td style="padding: 12px 15px; font-family: sans-serif; font-size: 13px; color: #002b49; text-align: left;">📊 TOTAL GERAL</td>'
                    f'<td style="padding: 12px 15px; font-family: sans-serif; font-size: 13px; color: #002b49; text-align: center;">{total_docs_formatado_br}</td>'
                    f'<td style="padding: 12px 15px; font-family: sans-serif; font-size: 13px; color: #002b49; text-align: right;">{formatar_brl(total_financeiro)}</td>'
                    f'</tr>'
                    f'</tfoot>'
                    f'</table>'
                    f'</div>'
                )
                st.html(html_tabela_gerencial)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 🏢 4. Detalhamento de Pagamentos por Credor")
        
        df_matriz_credor = df_filtrado.pivot_table(
            index='Credor_Nome_Tratado',
            columns='Mes_Extenso',
            values='Valor_Limpo',
            aggfunc='sum',
            fill_value=0.0
        ).reset_index()

        for m in lista_meses_fixa:
            if m not in df_matriz_credor.columns:
                df_matriz_credor[m] = 0.0
                
        df_matriz_credor['Total Geral'] = df_matriz_credor[lista_meses_fixa].sum(axis=1)
        df_matriz_credor = df_matriz_credor.sort_values(by='Total Geral', ascending=False)

        linhas_credor_html = ""
        totais_meses_credor = {m: 0.0 for m in lista_meses_fixa + ['Total Geral']}

        for _, row in df_matriz_credor.iterrows():
            colunas_valores = ""
            for m in lista_meses_fixa + ['Total Geral']:
                val = float(row[m])
                totais_meses_credor[m] += val
                colunas_valores += f"<td>{formatar_brl(val)}</td>"
            linhas_credor_html += f"<tr><td>{row['Credor_Nome_Tratado']}</td>{colunas_valores}</tr>"

        valores_totais_credor = ""
        for m in lista_meses_fixa + ['Total Geral']:
            valores_totais_credor += f"<td>{formatar_brl(totais_meses_credor[m])}</td>"

        cabecalhos_meses_credor = "".join([f"<th style='width: 10%;'>{mes}</th>" for mes in lista_meses_fixa])

        html_credores = (
            f"<div class='tabela-container'>"
            f"<div class='subtitulo-tabela-html' style='background: linear-gradient(90deg, #3a537d 0%, #002b49 100%);'>🏢 Distribuição Mensal de Recursos por Fornecedor / Prestador de Serviço</div>"
            f"<table class='html-executiva'>"
            f"<thead><tr>"
            f"<th style='width: 30%;'>RAZÃO SOCIAL / CREDOR</th>"
            f"{cabecalhos_meses_credor}"
            f"<th style='width: 10%;'>Total Geral</th>"
            f"</tr></thead>"
            f"<tbody>{linhas_credor_html}"
            f"<tr class='linha-total-html'><td>🏢 TOTAL CONSOLIDADO DO FILTRO</td>{valores_totais_credor}</tr>"
            f"</tbody></table></div>"
        )
        st.markdown(html_credores, unsafe_allow_html=True)

elif st.session_state["tela_atual"] == "Liquidação (NL)":
    # ---------------------------------------------------------------------
    # CÓDIGO DA TELA 2 (PAINEL DE LIQUIDAÇÃO)
    # ---------------------------------------------------------------------
    LINK_PLANILHA_1 = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTWnQkc7oF-YdXKoVTiYeUPYDHGzaeQaiEGqX6fNmB29mkzcd1kAvZVMujFDf02y7j1X8UJzqglAzTL/pub?gid=1892412645&single=true&output=csv"
    LINK_PLANILHA_2 = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTDHDK6dPnS9favMwwkNSLYZ5i9yjQrJjCEGxpifdQfD9_8dAsHSVlc8TECEyKJi0hWy3Wi5gEM_tI0/pub?gid=1866981074&single=true&output=csv"

    def converter_para_float(coluna):
        valores_str = coluna.fillna('0').astype(str)
        valores_str = valores_str.str.replace(r'[R$\s.]', '', regex=True).str.replace(',', '.')
        return pd.to_numeric(valores_str, errors='coerce').fillna(0.0)

    def limpar_chave_ne(serie):
        return (
            serie.fillna('')
            .astype(str)
            .str.strip()
            .str.upper()
            .str.replace(r'\.0$', '', regex=True)
            .str.replace(r'[^A-Z0-9]', '', regex=True)
        )

    @st.cache_data(ttl=60)
    def carregar_dados_integrados():
        try:
            df1 = ler_csv_url(LINK_PLANILHA_1)
            df2 = ler_csv_url(LINK_PLANILHA_2)
        except Exception as e:
            st.error(f"Erro no carregamento das planilhas: {e}")
            return pd.DataFrame()

        if df1.empty:
            return df1

        df1.columns = [str(c).strip() for c in df1.columns]
        df2.columns = [str(c).strip() for c in df2.columns]

        col_nl = 'Número' if 'Número' in df1.columns else df1.columns[0]
        col_ne1 = next((c for c in df1.columns if any(p in c.upper() for p in ['NE', 'EMPENHO', 'DOCUMENTONE'])), df1.columns[0])
        col_credor = 'Nome do Credor' if 'Nome do Credor' in df1.columns else df1.columns[0]
        col_retido = next((c for c in df1.columns if 'retido' in c.lower()), None)
        col_valor = 'Valor' if 'Valor' in df1.columns else df1.columns[-1]

        df1['NL_Numero'] = df1[col_nl].fillna('NL NÃO INFORMADA').astype(str).str.strip()
        df1['NE_Chave'] = limpar_chave_ne(df1[col_ne1])
        df1['Credor_Tratado'] = df1[col_credor].fillna('NÃO IDENTIFICADO').astype(str).str.strip().str.upper()

        col_data = next((c for c in df1.columns if 'data' in c.lower()), None)
        if col_data:
            df1['Data_DT'] = pd.to_datetime(df1[col_data], errors='coerce')
            df1['Competencia'] = df1['Data_DT'].dt.strftime('%m/%Y')
        else:
            df1['Data_DT'] = pd.NaT
            df1['Competencia'] = 'Não informada'

        df1['Grupo_Filtro'] = df1['Grupo'].fillna('Todos').astype(str).str.strip() if 'Grupo' in df1.columns else 'Todos'
        df1['Despesa_Filtro'] = df1['Despesa'].fillna('Todos').astype(str).str.strip() if 'Despesa' in df1.columns else 'Todos'
        df1['Status_Filtro'] = df1['Status'].fillna('Todos').astype(str).str.strip() if 'Status' in df1.columns else 'Todos'

        df1['Valor_Total_Limpo'] = converter_para_float(df1[col_valor])
        df1['Valor_Retido_Limpo'] = converter_para_float(df1[col_retido]) if col_retido else 0.0

        col_ne2 = 'DocumentoNE' if 'DocumentoNE' in df2.columns else next((c for c in df2.columns if 'NE' in c.upper()), df2.columns[0])
        col_fonte2 = 'Fonte' if 'Fonte' in df2.columns else next((c for c in df2.columns if 'FONTE' in c.upper()), None)
        col_objeto2 = 'Objeto da Despesa' if 'Objeto da Despesa' in df2.columns else next((c for c in df2.columns if 'OBJETO' in c.upper()), None)
        col_grupo2 = 'Grupo' if 'Grupo' in df2.columns else next((c for c in df2.columns if 'GRUPO' in c.upper()), None)

        df2['NE_Chave'] = limpar_chave_ne(df2[col_ne2])
        
        df2['Fonte_Relacao'] = df2[col_fonte2].fillna('NÃO INFORMADA').astype(str).str.strip() if col_fonte2 else 'NÃO INFORMADA'
        df2['Objeto_Relacao'] = df2[col_objeto2].fillna('NÃO INFORMADO').astype(str).str.strip() if col_objeto2 else 'NÃO INFORMADO'
        df2['Grupo_Relacao'] = df2[col_grupo2].fillna('NÃO INFORMADO').astype(str).str.strip() if col_grupo2 else 'NÃO INFORMADO'

        df2_dedup = df2[df2['NE_Chave'] != ''].drop_duplicates(subset=['NE_Chave'])

        df_merged = pd.merge(
            df1, 
            df2_dedup[['NE_Chave', 'Fonte_Relacao', 'Objeto_Relacao', 'Grupo_Relacao']], 
            on='NE_Chave', 
            how='left'
        )

        df_merged['Fonte_Relacao'] = df_merged['Fonte_Relacao'].fillna('NÃO INFORMADA')
        df_merged['Objeto_Relacao'] = df_merged['Objeto_Relacao'].fillna('NÃO INFORMADO')
        df_merged['Grupo_Relacao'] = df_merged['Grupo_Relacao'].fillna('NÃO INFORMADO')

        return df_merged

    def renderizar_tabela_credor_dinamica(df_filtrado):
        totais_credor = (
            df_filtrado.groupby('Credor_Tratado')
            .agg({'Valor_Retido_Limpo': 'sum', 'Valor_Total_Limpo': 'sum'})
            .sort_values(by='Valor_Total_Limpo', ascending=False)
        )

        tot_retido_geral = totais_credor['Valor_Retido_Limpo'].sum()
        tot_valor_geral = totais_credor['Valor_Total_Limpo'].sum()

        html_grupos = ""

        for credor, row_tot in totais_credor.iterrows():
            v_ret_credor = row_tot['Valor_Retido_Limpo']
            v_tot_credor = row_tot['Valor_Total_Limpo']

            df_cred = df_filtrado[df_filtrado['Credor_Tratado'] == credor]
            df_sub = (
                df_cred.groupby(['NL_Numero', 'NE_Chave'], as_index=False)
                .agg({'Valor_Retido_Limpo': 'sum', 'Valor_Total_Limpo': 'sum'})
                .sort_values(by='NL_Numero', ascending=True)
            )

            linhas_subtabela = ""
            for _, r in df_sub.iterrows():
                linhas_subtabela += f"""
<tr>
    <td style='width: 25%; text-align: center; font-family: monospace; font-weight: 600; color: #005691;'>{r['NL_Numero']}</td>
    <td style='width: 25%; text-align: center; font-family: monospace; color: #475569;'>{r['NE_Chave']}</td>
    <td style='width: 25%; text-align: center; color: #d97706;'>{formatar_brl(r['Valor_Retido_Limpo'])}</td>
    <td style='width: 25%; text-align: center; font-weight: 600; color: #002b49;'>{formatar_brl(r['Valor_Total_Limpo'])}</td>
</tr>"""

            html_grupos += f"""
<details class='credor-group'>
    <summary class='credor-summary'>
        <span>{credor}</span>
        <span style='text-align: right; color: #d97706;'>{formatar_brl(v_ret_credor)}</span>
        <span style='text-align: right; color: #002b49;'>{formatar_brl(v_tot_credor)}</span>
    </summary>
    <div class='subtabela-container'>
        <table class='subtabela-detalhe'>
            <thead>
                <tr>
                    <th style='width: 25%; text-align: center;'>NL</th>
                    <th style='width: 25%; text-align: center;'>NE</th>
                    <th style='width: 25%; text-align: center;'>VAL. RET.</th>
                    <th style='width: 25%; text-align: center;'>VALOR TOTAL</th>
                </tr>
            </thead>
            <tbody>
                {linhas_subtabela}
            </tbody>
        </table>
    </div>
</details>"""

        # RODAPÉ CORRIGIDO E IGUALADO AO DA TABELA DE FONTE
        html_final = f"""
<div class='tabela-dinamica-container'>
    <div class='tabela-dinamica-header'>
        <div>CREDOR</div>
        <div style='text-align: right;'>VAL. RET.</div>
        <div style='text-align: right;'>VALOR TOTAL</div>
    </div>
    {html_grupos}
    <div class='tabela-dinamica-header' style='background: #f1f5f9; border-top: 2px solid #005691; border-bottom: none;'>
        <div style='color: #002b49; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px;'>TOTAL GERAL</div>
        <div style='text-align: right; color: #f77f00; font-weight: 800;'>{formatar_brl(tot_retido_geral)}</div>
        <div style='text-align: right; color: #028090; font-weight: 800;'>{formatar_brl(tot_valor_geral)}</div>
    </div>
</div>"""

        st.markdown(html_final, unsafe_allow_html=True)

    def renderizar_tabela_resumida(df_filtrado, coluna_grupo, titulo_coluna):
        df_agrupado = df_filtrado.groupby(coluna_grupo)['Valor_Total_Limpo'].sum().reset_index()
        df_agrupado = df_agrupado.sort_values(by='Valor_Total_Limpo', ascending=False)

        total_geral = df_agrupado['Valor_Total_Limpo'].sum()

        linhas_html = ""
        for _, row in df_agrupado.iterrows():
            item = row[coluna_grupo]
            valor = row['Valor_Total_Limpo']
            linhas_html += f"""
<tr>
<td style='text-align: left; font-weight: 500;'>{item}</td>
<td style='text-align: right; font-weight: 600; color: #002b49; white-space: nowrap;'>{formatar_brl(valor)}</td>
</tr>"""

        html = f"""<div class='tabela-simples-container'>
<table class='tabela-simples'>
<thead>
<tr>
<th style='text-align: left;'>{titulo_coluna}</th>
<th style='text-align: right;'>VALOR TOTAL</th>
</tr>
</thead>
<tbody>
{linhas_html}
<tr class='total-row'>
<td style='text-align: left;'>TOTAL GERAL</td>
<td style='text-align: right; color: #028090; white-space: nowrap;'>{formatar_brl(total_geral)}</td>
</tr>
</tbody>
</table>
</div>"""

        st.markdown(html, unsafe_allow_html=True)

    # CABEÇALHO TELA 2
    st.markdown("<h2 class='titulo-pagina'>📊 Painel de Controle Liquidação — Exercício 2026</h2>", unsafe_allow_html=True)
    st.markdown("<p class='subtitulo-pagina'>Secretaria Executiva de Administração e Finanças (SEAF)</p>", unsafe_allow_html=True)
    st.markdown("<p class='subtitulo-pagina'>Gerência Financeira (GFIN)</p>", unsafe_allow_html=True)
    st.markdown("---")

    df_base = carregar_dados_integrados()

    if not df_base.empty:
        tipo_periodo = st.sidebar.radio(
            "Como deseja filtrar o período?",
            options=["Por Mês de Competência", "Por Intervalo de Datas"],
            index=0,
            key="tipo_periodo_nl"
        )

        if tipo_periodo == "Por Mês de Competência":
            comps_unicas = df_base['Competencia'].dropna().astype(str).unique()
            comps = [c for c in comps_unicas if c.strip() not in ['Não informada', 'nan', 'None', '']]
            comp_sel = st.sidebar.multiselect("Filtrar Período de Competência:", options=sorted(comps), placeholder="Selecione as opções", key="comp_nl")
        else:
            data_min = df_base['Data_DT'].min() if not df_base['Data_DT'].isna().all() else None
            data_max = df_base['Data_DT'].max() if not df_base['Data_DT'].isna().all() else None
            datas_sel = st.sidebar.date_input("Filtrar Intervalo de Datas:", value=(data_min, data_max) if data_min and data_max else None, key="dt_input_nl")

        st.sidebar.divider()

        grupos = sorted([g for g in df_base['Grupo_Filtro'].unique() if g != "Todos"])
        grupo_sel = st.sidebar.selectbox("Filtrar por Grupo:", options=["Todos"] + grupos, key="grupo_nl")

        despesas = sorted([d for d in df_base['Despesa_Filtro'].unique() if d != "Todos"])
        despesa_sel = st.sidebar.selectbox("Filtrar por Tipo de Despesa:", options=["Todas as Despesas"] + despesas, key="despesa_nl")

        statuses = sorted([s for s in df_base['Status_Filtro'].unique() if s != "Todos"])
        status_sel = st.sidebar.selectbox("Filtrar por Status:", options=["Todos"] + statuses, key="status_nl")

        st.sidebar.divider()

        credores = sorted(df_base['Credor_Tratado'].unique())
        credor_sel = st.sidebar.multiselect("Filtrar por Entidade / Credor:", options=credores, placeholder="Selecione as opções", key="credor_nl")

        st.sidebar.divider()

        fontes = sorted([f for f in df_base['Fonte_Relacao'].unique() if f != 'NÃO INFORMADA'])
        fonte_sel = st.sidebar.selectbox("Filtrar por Fonte de Recurso:", options=["Todas as fontes (Exibe tudo)"] + fontes, key="fonte_nl")

        st.sidebar.divider()

        objetos = sorted([o for o in df_base['Objeto_Relacao'].unique() if o != 'NÃO INFORMADO'])
        objeto_sel = st.sidebar.selectbox("Filtrar por Objeto de Despesa:", options=["Todos os objetos"] + objetos, key="objeto_nl")

        st.sidebar.divider()

        st.sidebar.markdown("### ⚙️ Atualizar Dados do Painel")
        if st.sidebar.button("🔄 Recarregar Dados das Liquidações", use_container_width=True, key="btn_recarregar_nl"):
            st.cache_data.clear()
            st.rerun()

        df_filtrado = df_base.copy()

        if tipo_periodo == "Por Mês de Competência" and 'comp_sel' in locals() and comp_sel:
            df_filtrado = df_filtrado[df_filtrado['Competencia'].astype(str).isin(comp_sel)]
        elif tipo_periodo == "Por Intervalo de Datas" and 'datas_sel' in locals() and isinstance(datas_sel, (tuple, list)) and len(datas_sel) == 2:
            df_filtrado = df_filtrado[(df_filtrado['Data_DT'] >= pd.to_datetime(datas_sel[0])) & (df_filtrado['Data_DT'] <= pd.to_datetime(datas_sel[1]))]

        if grupo_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado['Grupo_Filtro'] == grupo_sel]
        if despesa_sel != "Todas as Despesas":
            df_filtrado = df_filtrado[df_filtrado['Despesa_Filtro'] == despesa_sel]
        if status_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado['Status_Filtro'] == status_sel]
        if credor_sel:
            df_filtrado = df_filtrado[df_filtrado['Credor_Tratado'].isin(credor_sel)]
        if fonte_sel != "Todas as fontes (Exibe tudo)":
            df_filtrado = df_filtrado[df_filtrado['Fonte_Relacao'] == fonte_sel]
        if objeto_sel != "Todos os objetos":
            df_filtrado = df_filtrado[df_filtrado['Objeto_Relacao'] == objeto_sel]

        qtd_liquidada = len(df_filtrado)
        valor_total = df_filtrado['Valor_Total_Limpo'].sum()

        grupo_serie = df_filtrado['Grupo_Relacao'].astype(str)
        mask_gd3 = grupo_serie.str.contains(r'^3|-3\b|\bGD3\b|\bGND3\b|3-OUTRAS', regex=True, case=False)
        mask_gd4 = grupo_serie.str.contains(r'^4|-4\b|\bGD4\b|\bGND4\b|4-INVESTIMENTOS', regex=True, case=False)

        valor_gd3 = df_filtrado.loc[mask_gd3, 'Valor_Total_Limpo'].sum()
        valor_gd4 = df_filtrado.loc[mask_gd4, 'Valor_Total_Limpo'].sum()

        # CARDS DE KPI (TELA 2 - LIQUIDAÇÃO)
        col_k1, col_k2, col_k3, col_k4 = st.columns(4)
        
        with col_k1:
            qtd_formatada_br = f"{qtd_liquidada:,}".replace(",", ".")
            st.markdown(f"""
                <div class='metric-card'>
                    <p style='color: #6c757d; font-size: 11px; font-weight: bold; margin:0;'>QTD DE LIQUIDAÇÕES</p>
                    <h3 style='color: #002b49; margin: 5px 0;'>{qtd_formatada_br}</h3>
                    <p style='color: #28a745; font-size: 11px; margin:0;'>📋 Documentos NL</p>
                </div>
            """, unsafe_allow_html=True)

        with col_k2:
            st.markdown(f"""
                <div class='metric-card'>
                    <p style='color: #6c757d; font-size: 11px; font-weight: bold; margin:0;'>VALOR TOTAL</p>
                    <h3 style='color: #028090; margin: 5px 0;'>{formatar_brl(valor_total)}</h3>
                    <p style='color: #6c757d; font-size: 11px; margin:0;'>Total Liquidado</p>
                </div>
            """, unsafe_allow_html=True)

        with col_k3:
            st.markdown(f"""
                <div class='metric-card'>
                    <p style='color: #6c757d; font-size: 11px; font-weight: bold; margin:0;'>VALOR TOTAL GD3</p>
                    <h3 style='color: #f77f00; margin: 5px 0;'>{formatar_brl(valor_gd3)}</h3>
                    <p style='color: #6c757d; font-size: 11px; margin:0;'>Grupo GD3</p>
                </div>
            """, unsafe_allow_html=True)

        with col_k4:
            st.markdown(f"""
                <div class='metric-card'>
                    <p style='color: #6c757d; font-size: 11px; font-weight: bold; margin:0;'>VALOR TOTAL GD4</p>
                    <h3 style='color: #2563eb; margin: 5px 0;'>{formatar_brl(valor_gd4)}</h3>
                    <p style='color: #6c757d; font-size: 11px; margin:0;'>Grupo GD4</p>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        col_credor, col_objeto, col_fonte = st.columns([1.6, 1, 1])

        with col_credor:
            renderizar_tabela_credor_dinamica(df_filtrado)

        with col_objeto:
            renderizar_tabela_resumida(df_filtrado, 'Objeto_Relacao', 'OBJETO')

        with col_fonte:
            renderizar_tabela_resumida(df_filtrado, 'Fonte_Relacao', 'FONTE')
    else:
        st.warning("Aguardando carregamento e relacionamento das planilhas...")