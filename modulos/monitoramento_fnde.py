"""Monitoramento da execução FNDE destinada às cooperativas da fonte 552."""

from __future__ import annotations

import json
import unicodedata

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components


URL_BASE_PAGAMENTOS = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vTD3b7L6byArEDgkVKOXXlc7RK0M2QKXLov83OydCaks3rDISWYWfgGNi6vG6pwy8t5Ul3Fd2wArhtT/"
    "pub?gid=1786485134&single=true&output=csv"
)
# Nova base SIAFIM 2026 (aba gid=1358142076)
URL_BASE_SIAFIM_2026 = (
    "https://docs.google.com/spreadsheets/d/"
    "1os31zZGkNqKM3hE29Z8lCni9WhG0f9yB/"
    "export?format=csv&gid=1358142076"
)

TOTAL_RECEBIDO = 18_881_868.00
PERCENTUAL_COOPERATIVAS = 0.45
META_COOPERATIVAS = TOTAL_RECEBIDO * PERCENTUAL_COOPERATIVAS

MESES = [
    "Jan/2026", "Fev/2026", "Mar/2026", "Abr/2026", "Mai/2026", "Jun/2026",
    "Jul/2026", "Ago/2026", "Set/2026", "Out/2026", "Nov/2026", "Dez/2026",
]

MESES_SIAFIM_MAP = [
    ("Mar", ["MAR", "MARCO", "MAR/2026"]),
    ("Abr", ["ABR", "ABRIL", "ABR/2026"]),
    ("Mai", ["MAI", "MAIO", "MAI/2026"]),
    ("Jun", ["JUN", "JUNHO", "JUN/2026"]),
    ("Jul", ["JUL", "JULHO", "JUL/2026"]),
    ("Ago", ["AGO", "AGOSTO", "AGO/2026"]),
    ("Set", ["SET", "SETEMBRO", "SET/2026"]),
    ("Out", ["OUT", "OUTUBRO", "OUT/2026"]),
    ("Nov", ["NOV", "NOVEMBRO", "NOV/2026"]),
]

COOPERATIVAS = {
    "COODAPISJG — Cooperativa de Jaboatão dos Guararapes": ("COODAPISJG",),
    "ASSOCENE — Associação de Orientação às Cooperativas do Nordeste": ("ASSOCENE",),
    "COOPANORTE — Cooperativa dos Pequenos Agricultores Familiares da Mata Norte": ("MATA NORTE", "COOPANORTE"),
    "COPAF — Cooperativa da Agricultura Familiar de Pernambuco": ("COPAF",),
}
NOME_COOPANORTE_ANTERIOR = "Cooperativa dos Pequenos Agricultores Familiares da Mata Norte"
NOME_COOPANORTE = "COOPANORTE — Cooperativa dos Pequenos Agricultores Familiares da Mata Norte"

META_COOP_SIAFIM = {
    "ASSOCENE": {
        "contrato": "Contrato 1401.4086.2025",
        "corBadge": "bg-indigo-50 text-indigo-700 border-indigo-200",
        "nome_completo": "ASSOCENE — Associação de Orientação às Cooperativas do Nordeste",
    },
    "COODAPISJG": {
        "contrato": "Contrato 1401.4088.2025",
        "corBadge": "bg-amber-50 text-amber-800 border-amber-200",
        "nome_completo": "COODAPISJG — Cooperativa de Jaboatão dos Guararapes",
    },
    "COOPANORTE": {
        "contrato": "Contrato 1401.4089.2025",
        "corBadge": "bg-emerald-50 text-emerald-700 border-emerald-200",
        "nome_completo": "COOPANORTE — Cooperativa dos Pequenos Agricultores Familiares da Mata Norte",
    },
    "COPAF": {
        "contrato": "Contrato 1401.4087.2025",
        "corBadge": "bg-teal-50 text-teal-700 border-teal-200",
        "nome_completo": "COPAF — Cooperativa da Agricultura Familiar de Pernambuco",
    },
}

# Dados de contingência (valores exatos da aba Execução SIAFIM 2026 caso a rede oscile)
FALLBACK_SIAFIM_2026 = [
    {
        "cooperativa": "ASSOCENE",
        "contrato": "Contrato 1401.4086.2025",
        "corBadge": "bg-indigo-50 text-indigo-700 border-indigo-200",
        "produtos": [
            {
                "nome": "Bolo",
                "vu": 6.59,
                "unidade": "UND.",
                "valores": [513782.76, 526448.74, 514646.05, 79053.64, 0, 0, 0, 0, 0],
                "qtds": [77964, 79886, 78095, 11996, 0, 0, 0, 0, 0],
            },
            {
                "nome": "Pão Nutritivo",
                "vu": 3.72,
                "unidade": "UND.",
                "valores": [61324.20, 93033.48, 89250.24, 44662.32, 59572.08, 14262.48, 0, 0, 0],
                "qtds": [16485, 25009, 23992, 12006, 16014, 3834, 0, 0, 0],
            },
        ],
    },
    {
        "cooperativa": "COODAPISJG",
        "contrato": "Contrato 1401.4088.2025",
        "corBadge": "bg-amber-50 text-amber-800 border-amber-200",
        "produtos": [
            {
                "nome": "Manga Tommy",
                "vu": 9.49,
                "unidade": "KG",
                "valores": [57148.78, 302275.48, 342266.34, 228215.52, 72266.35, 54377.70, 0, 110643.91, 105253.59],
                "qtds": [6022, 31852, 36066, 24048, 7615, 5730, 0, 11659, 11091],
            },
            {
                "nome": "Creme de Frutas",
                "vu": 3.65,
                "unidade": "UND.",
                "valores": [97871.10, 199052.75, 183310.30, 183310.30, 84811.40, 0, 0, 84811.40, 106671.25],
                "qtds": [26814, 54535, 50222, 50222, 23236, 0, 0, 23236, 29225],
            },
            {
                "nome": "Gelado de Frutas",
                "vu": 3.27,
                "unidade": "UND.",
                "valores": [40263.51, 121774.80, 78453.84, 78496.35, 39828.60, 79657.20, 0, 39828.60, 27706.71],
                "qtds": [12313, 37240, 23992, 24005, 12180, 24360, 0, 12180, 8473],
            },
        ],
    },
    {
        "cooperativa": "COOPANORTE",
        "contrato": "Contrato 1401.4089.2025",
        "corBadge": "bg-emerald-50 text-emerald-700 border-emerald-200",
        "produtos": [
            {
                "nome": "Goiaba",
                "vu": 1.21,
                "unidade": "KG",
                "valores": [98980.42, 96662.06, 93806.46, 93379.33, 0, 190306.38, 0, 95153.19, 161283.32],
                "qtds": [81802, 79886, 77526, 77173, 0, 157278, 0, 78639, 133292],
            },
            {
                "nome": "Abacaxi Pérola",
                "vu": 9.70,
                "unidade": "KG",
                "valores": [34367.10, 105215.90, 101035.20, 90287.60, 34241.00, 91568.00, 0, 34211.90, 69878.80],
                "qtds": [3543, 10847, 10416, 9308, 3530, 9440, 0, 3527, 7204],
            },
            {
                "nome": "Uva Itália",
                "vu": 16.26,
                "unidade": "UND.",
                "valores": [0, 197672.82, 0, 162014.64, 0, 20292.48, 0, 0, 87804.00],
                "qtds": [0, 12157, 0, 9964, 0, 1248, 0, 0, 5400],
            },
            {
                "nome": "Tangerina",
                "vu": 1.50,
                "unidade": "UND.",
                "valores": [0, 18768.00, 53982.00, 40834.50, 117958.50, 30789.00, 0, 18270.00, 25218.00],
                "qtds": [0, 12512, 35988, 27223, 78639, 20526, 0, 12180, 16812],
            },
        ],
    },
    {
        "cooperativa": "COPAF",
        "contrato": "Contrato 1401.4087.2025",
        "corBadge": "bg-teal-50 text-teal-700 border-teal-200",
        "produtos": [
            {
                "nome": "Graviola",
                "vu": 15.66,
                "unidade": "KG",
                "valores": [54387.18, 84376.08, 51020.28, 25619.76, 0, 0, 0, 23677.92, 29221.56],
                "qtds": [3473, 5388, 3258, 1636, 0, 0, 0, 1512, 1866],
            },
            {
                "nome": "Abacate",
                "vu": 12.24,
                "unidade": "KG",
                "valores": [46756.80, 71420.40, 43488.72, 21836.16, 0, 0, 0, 20159.28, 25055.28],
                "qtds": [3820, 5835, 3553, 1784, 0, 0, 0, 1647, 2047],
            },
        ],
    },
]


def _normalizar(valor: object) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.upper().split())


def _moeda(valor: float) -> str:
    return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _valor_numero(valor: object) -> float:
    if pd.isna(valor) or str(valor).strip() in ("", "-", "—"):
        return 0.0
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return float(valor)
    texto = str(valor).replace("R$", "").replace(" ", "").strip()
    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")
    try:
        return float(texto)
    except (TypeError, ValueError):
        return 0.0


def _localizar_coluna(colunas: pd.Index, *nomes: str) -> str | None:
    mapa = {_normalizar(coluna): coluna for coluna in colunas}
    return next((mapa[_normalizar(nome)] for nome in nomes if _normalizar(nome) in mapa), None)


def _nome_cooperativa(nome: object) -> str | None:
    texto = _normalizar(nome)
    for exibicao, termos in COOPERATIVAS.items():
        if any(termo in texto for termo in termos):
            return exibicao
    return None


def _sigla_cooperativa(nome: object) -> str | None:
    texto = _normalizar(nome)
    for sigla in ("ASSOCENE", "COODAPISJG", "COOPANORTE", "COPAF"):
        if sigla in texto:
            return sigla
    if "MATA NORTE" in texto:
        return "COOPANORTE"
    return None


def _padronizar_nome_produto(nome: str) -> str:
    chave = _normalizar(nome)
    mapa_nomes = {
        "BOLO": "Bolo",
        "PAO NUTRITIVO": "Pão Nutritivo",
        "MANGA TOMMY": "Manga Tommy",
        "CREME DE FRUTAS": "Creme de Frutas",
        "GELADO DE FRUTAS": "Gelado de Frutas",
        "GOIABA": "Goiaba",
        "ABACAXI PEROLA": "Abacaxi Pérola",
        "UVA ITALIA": "Uva Itália",
        "TANGERINA": "Tangerina",
        "GRAVIOLA": "Graviola",
        "ABACATE": "Abacate",
    }
    return mapa_nomes.get(chave, nome.strip())


@st.cache_data(ttl=60, show_spinner=False)
def _carregar_pagamentos() -> pd.DataFrame:
    dados = pd.read_csv(URL_BASE_PAGAMENTOS)
    dados.columns = [str(coluna).strip() for coluna in dados.columns]
    coluna_fonte = _localizar_coluna(dados.columns, "Fonte")
    coluna_valor = _localizar_coluna(dados.columns, "Valor")
    coluna_data = _localizar_coluna(dados.columns, "Data Emissão", "Data Emissao", "Data")
    coluna_credor = _localizar_coluna(dados.columns, "Nome do Credor", "Credor")
    if not all((coluna_fonte, coluna_valor, coluna_data, coluna_credor)):
        raise ValueError("A base de pagamentos não contém as colunas necessárias para o monitoramento FNDE.")

    base = dados.copy()
    fonte = base[coluna_fonte].fillna("").astype(str)
    base = base[fonte.str.contains(r"(?<!\d)552(?!\d)", regex=True, na=False)].copy()
    base["Cooperativa"] = base[coluna_credor].map(_nome_cooperativa)
    base = base[base["Cooperativa"].notna()].copy()
    base["Valor executado"] = base[coluna_valor].map(_valor_numero)
    base["Data"] = pd.to_datetime(base[coluna_data], errors="coerce", dayfirst=True)
    base = base[(base["Data"].isna()) | (base["Data"].dt.year == 2026)].copy()
    base["Mês"] = base["Data"].dt.month.map(
        {1: "Jan/2026", 2: "Fev/2026", 3: "Mar/2026", 4: "Abr/2026", 5: "Mai/2026", 6: "Jun/2026",
         7: "Jul/2026", 8: "Ago/2026", 9: "Set/2026", 10: "Out/2026", 11: "Nov/2026", 12: "Dez/2026"}
    ).fillna("Sem mês informado")
    return base


@st.cache_data(ttl=60, show_spinner=False)
def _carregar_siafim_2026() -> list[dict]:
    """Lê a nova planilha SIAFIM 2026 (gid=1358142076) mantendo a estrutura da tabela interativa."""
    try:
        bruto = pd.read_csv(URL_BASE_SIAFIM_2026, header=None)
        if bruto.empty:
            return FALLBACK_SIAFIM_2026

        # Identifica a linha de cabeçalho que contém os meses (Mar, Abr, Mai...)
        linha_cabecalho = None
        colunas_meses: dict[int, int] = {}
        col_produto_idx = None
        col_vu_idx = None
        col_unid_idx = None
        col_coop_idx = None

        for idx, row in bruto.iterrows():
            celulas = [_normalizar(v) for v in row.tolist()]
            encontrados_mes: dict[int, int] = {}
            for m_idx, (_, aliases) in enumerate(MESES_SIAFIM_MAP):
                for c_idx, texto in enumerate(celulas):
                    if texto in aliases or any(texto.startswith(a + " ") or texto.startswith(a + "/") for a in aliases):
                        if m_idx not in encontrados_mes:
                            encontrados_mes[m_idx] = c_idx
            if len(encontrados_mes) >= 5:
                linha_cabecalho = idx
                colunas_meses = encontrados_mes
                for c_idx, texto in enumerate(celulas):
                    if any(k in texto for k in ("PRODUTO", "ITEM", "GENERO", "ALIMENTO")):
                        col_produto_idx = c_idx
                    elif texto in ("VU", "V. UNIT", "V. UNIT.", "VALOR UNITARIO", "V UNIT"):
                        col_vu_idx = c_idx
                    elif texto in ("UNID", "UNID.", "UND", "UND.", "UNIDADE"):
                        col_unid_idx = c_idx
                    elif "COOPERATIVA" in texto:
                        col_coop_idx = c_idx
                break

        if linha_cabecalho is None or len(colunas_meses) < 5:
            return FALLBACK_SIAFIM_2026

        grupos: dict[str, dict] = {}
        coop_atual: str | None = None

        for idx in range(linha_cabecalho + 1, len(bruto)):
            row = bruto.iloc[idx].tolist()
            textos_linha = [_normalizar(v) for v in row]

            # Verifica se a linha marca o início de uma cooperativa
            sigla_encontrada = None
            if col_coop_idx is not None and col_coop_idx < len(row):
                sigla_encontrada = _sigla_cooperativa(row[col_coop_idx])
            if sigla_encontrada is None:
                for t in textos_linha[:3]:
                    s = _sigla_cooperativa(t)
                    if s and not any(x in t for x in ("TOTAL", "SUBTOTAL")):
                        sigla_encontrada = s
                        break

            if sigla_encontrada:
                coop_atual = sigla_encontrada
                if coop_atual not in grupos:
                    meta = META_COOP_SIAFIM[coop_atual]
                    grupos[coop_atual] = {
                        "cooperativa": coop_atual,
                        "contrato": meta["contrato"],
                        "corBadge": meta["corBadge"],
                        "produtos": [],
                    }

            if not coop_atual:
                continue

            # Extrai nome do produto
            nome_bruto = ""
            if col_produto_idx is not None and col_produto_idx < len(row):
                nome_bruto = str(row[col_produto_idx] or "").strip()
            else:
                for c_idx in range(min(3, len(row))):
                    cand = str(row[c_idx] or "").strip()
                    if cand and cand.lower() != "nan" and _sigla_cooperativa(cand) is None:
                        nome_bruto = cand
                        break

            nome_norm = _normalizar(nome_bruto)
            if (
                not nome_bruto
                or nome_bruto.lower() == "nan"
                or _sigla_cooperativa(nome_bruto) is not None
                or any(p in nome_norm for p in ("TOTAL", "SUBTOTAL", "CONTRATO", "FONTE", "OBSERVA", "SALDO"))
            ):
                continue

            vu = _valor_numero(row[col_vu_idx]) if (col_vu_idx is not None and col_vu_idx < len(row)) else 0.0
            unidade = (
                str(row[col_unid_idx] or "").strip().upper()
                if (col_unid_idx is not None and col_unid_idx < len(row) and str(row[col_unid_idx] or "").strip().lower() != "nan")
                else "UND."
            )
            if unidade in ("", "NAN"):
                unidade = "UND."

            valores = [0.0] * 9
            qtds = [0] * 9
            tem_valor = False
            for m_idx, c_idx in colunas_meses.items():
                if c_idx < len(row):
                    val = round(_valor_numero(row[c_idx]), 2)
                    valores[m_idx] = val
                    if val > 0:
                        tem_valor = True
                        qtds[m_idx] = int(round(val / vu)) if vu > 0 else 0

            if not tem_valor and vu == 0:
                continue

            grupos[coop_atual]["produtos"].append({
                "nome": _padronizar_nome_produto(nome_bruto),
                "vu": vu,
                "unidade": unidade,
                "valores": valores,
                "qtds": qtds,
            })

        ordem_coops = ["ASSOCENE", "COODAPISJG", "COOPANORTE", "COPAF"]
        resultado = [grupos[c] for c in ordem_coops if c in grupos and grupos[c]["produtos"]]
        return resultado if resultado else FALLBACK_SIAFIM_2026
    except Exception:
        return FALLBACK_SIAFIM_2026


def _card(titulo: str, valor: float, detalhe: str, classe: str) -> None:
    st.markdown(
        f"""<div class="fnde-card {classe}"><div class="fnde-card-title">{titulo}</div>
        <div class="fnde-card-value">{_moeda(valor)}</div><div class="fnde-card-detail">{detalhe}</div></div>""",
        unsafe_allow_html=True,
    )


def _html_tabela_siafim_2026(dados_cooperativas: list[dict], filtro_inicial: str = "TODAS") -> str:
    """Gera o componente HTML interativo da Execução SIAFIM 2026 para embutir no Streamlit."""
    dados_json = json.dumps(dados_cooperativas, ensure_ascii=False)
    filtro_json = json.dumps(filtro_inicial, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background-color: transparent;
            color: #0F172A;
            font-variant-numeric: tabular-nums;
            margin: 0;
            padding: 0;
        }}
        .table-wrapper::-webkit-scrollbar {{
            height: 8px;
            width: 8px;
        }}
        .table-wrapper::-webkit-scrollbar-track {{
            background: #F1F5F9;
            border-radius: 4px;
        }}
        .table-wrapper::-webkit-scrollbar-thumb {{
            background: #CBD5E1;
            border-radius: 4px;
        }}
        .table-wrapper::-webkit-scrollbar-thumb:hover {{
            background: #94A3B8;
        }}
        .sticky-col-produto {{
            position: sticky;
            left: 0;
            z-index: 10;
        }}
        thead .sticky-col-produto {{
            z-index: 20;
        }}
    </style>
</head>
<body class="w-full">
    <div class="w-full">
        <!-- Cabeçalho e Filtro Rápido por Cooperativa -->
        <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3 mb-4">
            <div>
                <div class="flex items-center gap-2">
                    <h2 class="text-base sm:text-lg font-bold text-slate-900 tracking-tight">
                        Execução SIAFIM — Agricultura Familiar 2026
                    </h2>
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                        Mar – Nov 2026
                    </span>
                </div>
                <p class="text-xs text-slate-500 mt-0.5">
                    Demonstrativo mensal por cooperativa e portfólio de produtos contratados
                </p>
            </div>

            <div class="flex flex-wrap items-center gap-2">
                <div class="flex items-center bg-slate-50 border border-slate-200 rounded-xl p-1 overflow-x-auto max-w-full" id="coopFilterGroup">
                    <button type="button" data-coop="TODAS" class="coop-btn px-3 py-1.5 rounded-lg text-xs font-semibold transition-all bg-slate-900 text-white shadow-xs cursor-pointer">
                        Todas (4)
                    </button>
                    <button type="button" data-coop="ASSOCENE" class="coop-btn px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:text-slate-900 transition-all cursor-pointer">
                        ASSOCENE
                    </button>
                    <button type="button" data-coop="COODAPISJG" class="coop-btn px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:text-slate-900 transition-all cursor-pointer">
                        COODAPISJG
                    </button>
                    <button type="button" data-coop="COOPANORTE" class="coop-btn px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:text-slate-900 transition-all cursor-pointer">
                        COOPANORTE
                    </button>
                    <button type="button" data-coop="COPAF" class="coop-btn px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:text-slate-900 transition-all cursor-pointer">
                        COPAF
                    </button>
                </div>
            </div>
        </div>

        <!-- Cartão Único da Tabela Executiva -->
        <section class="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
            <div class="table-wrapper overflow-x-auto">
                <table class="w-full border-collapse text-left">
                    <thead class="sticky top-0 z-20 bg-slate-50 border-b border-slate-200 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                        <tr>
                            <th class="sticky-col-produto bg-slate-50 py-3 pl-4 pr-3 min-w-[240px] border-r border-slate-200/80">
                                Cooperativa / Produto
                            </th>
                            <th class="py-3 px-2.5 text-right min-w-[80px]">V. Unit.</th>
                            <th class="py-3 px-2.5 text-right min-w-[114px]">Março</th>
                            <th class="py-3 px-2.5 text-right min-w-[114px]">Abril</th>
                            <th class="py-3 px-2.5 text-right min-w-[114px]">Maio</th>
                            <th class="py-3 px-2.5 text-right min-w-[114px]">Junho</th>
                            <th class="py-3 px-2.5 text-right min-w-[114px]">Julho</th>
                            <th class="py-3 px-2.5 text-right min-w-[114px]">Agosto</th>
                            <th class="py-3 px-2.5 text-right min-w-[92px]">Setembro</th>
                            <th class="py-3 px-2.5 text-right min-w-[114px]">Outubro</th>
                            <th class="py-3 px-2.5 text-right min-w-[114px]">Novembro</th>
                            <th class="py-3 pl-3 pr-4 text-right min-w-[142px] bg-slate-100/80 text-slate-700 border-l border-slate-200">
                                Total (Mar–Nov)
                            </th>
                        </tr>
                    </thead>
                    <tbody id="tabelaCorpo" class="divide-y divide-slate-100 text-xs sm:text-[13px]">
                    </tbody>
                    <tfoot id="tabelaRodape" class="bg-slate-900 text-white text-xs sm:text-[13px] font-semibold">
                    </tfoot>
                </table>
            </div>

            <!-- Legenda discreta -->
            <div class="px-4 py-2 bg-slate-50 border-t border-slate-200 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500">
                <div class="flex items-center gap-4">
                    <span class="inline-flex items-center gap-1.5">
                        <span class="w-2.5 h-2.5 rounded-sm bg-emerald-100 border border-emerald-400 inline-block"></span>
                        Pico mensal de execução do produto
                    </span>
                    <span class="inline-flex items-center gap-1.5">
                        <span class="text-slate-300 font-bold">—</span>
                        Sem execução registrada no mês
                    </span>
                </div>
                <span>Fonte: Planilha Execução SIAFIM — Agricultura Familiar 2026</span>
            </div>
        </section>
    </div>

    <script>
        const iconesProdutos = {{
            "Bolo": `
                <svg viewBox="0 0 36 36" class="w-7 h-7" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect width="36" height="36" rx="9" fill="#FEF3C7"/>
                    <path d="M7 18.5L28 13.5V25.5C28 26.3 27.3 27 26.5 27H8.5C7.7 27 7 26.3 7 25.5V18.5Z" fill="#D97706"/>
                    <path d="M7 21.5L28 17.5V19.5L7 23.5V21.5Z" fill="#FEF08A"/>
                    <path d="M7 18.5C7 16.5 14 11.5 21 11.5C24.5 11.5 28 12.5 28 13.5L7 18.5Z" fill="#78350F"/>
                    <path d="M7 18.5C8.5 19.5 10 18.2 11.5 19.2C13 20.2 14.5 18 16 19C17.5 20 19 17.8 20.5 18.8C22 19.8 23.5 17.5 25 18.5C26.5 19.2 27.5 17.8 28 17.5V13.5L7 18.5Z" fill="#92400E"/>
                    <circle cx="19.5" cy="11" r="2.7" fill="#DC2626"/>
                    <circle cx="18.7" cy="10.2" r="0.8" fill="#FCA5A5"/>
                    <path d="M20 8.5C20.5 7 22 6.5 23 6.8" stroke="#15803D" stroke-width="1.3" stroke-linecap="round"/>
                </svg>`,
            "Pão Nutritivo": `
                <svg viewBox="0 0 36 36" class="w-7 h-7" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect width="36" height="36" rx="9" fill="#FFEDD5"/>
                    <path d="M7 21.5C7 16.5 11.8 12.5 18 12.5C24.2 12.5 29 16.5 29 21.5C29 24 27.2 25.5 24.5 25.5H11.5C8.8 25.5 7 24 7 21.5Z" fill="#D97706"/>
                    <path d="M8.5 20.5C8.5 16.5 12.6 13.5 18 13.5C23.4 13.5 27.5 16.5 27.5 20.5C27.5 22.3 26.2 23.5 24 23.5H12C9.8 23.5 8.5 22.3 8.5 20.5Z" fill="#F59E0B"/>
                    <path d="M13 15.2C14 16.5 14.5 17.8 14.5 19" stroke="#FEF3C7" stroke-width="1.6" stroke-linecap="round"/>
                    <path d="M18 14.5C18.8 16 19.2 17.5 19.2 18.8" stroke="#FEF3C7" stroke-width="1.6" stroke-linecap="round"/>
                    <path d="M22.8 15.5C23.4 16.8 23.7 18 23.7 19" stroke="#FEF3C7" stroke-width="1.6" stroke-linecap="round"/>
                </svg>`,
            "Manga Tommy": `
                <svg viewBox="0 0 36 36" class="w-7 h-7" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect width="36" height="36" rx="9" fill="#FEF9C3"/>
                    <defs>
                        <linearGradient id="mangaGrad" x1="9" y1="10" x2="27" y2="27" gradientUnits="userSpaceOnUse">
                            <stop offset="0%" stop-color="#EF4444"/>
                            <stop offset="52%" stop-color="#F97316"/>
                            <stop offset="100%" stop-color="#EAB308"/>
                        </linearGradient>
                    </defs>
                    <path d="M21.5 10.5C25.5 11.5 27.5 16.2 25.8 21.2C24.2 25.8 19.2 28.2 14.8 27C10.8 25.9 9.2 22.8 10.8 19.5C12.2 16.6 13.2 13.8 15.8 11.6C17.5 10.2 19.6 10 21.5 10.5Z" fill="url(#mangaGrad)"/>
                    <path d="M20.5 10.5C21.5 7.8 24.5 7 26.8 8.2C25 10.4 22.5 11 20.5 10.5Z" fill="#16A34A"/>
                    <ellipse cx="15.5" cy="16" rx="1.6" ry="3.2" transform="rotate(25 15.5 16)" fill="#FEF08A" fill-opacity="0.55"/>
                </svg>`,
            "Creme de Frutas": `
                <svg viewBox="0 0 36 36" class="w-7 h-7" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect width="36" height="36" rx="9" fill="#FCE7F3"/>
                    <path d="M10.5 16C10.5 12.8 13.8 10.5 18 10.5C22.2 10.5 25.5 12.8 25.5 16H10.5Z" fill="#FB7185"/>
                    <path d="M12.5 13.5C13.5 11.2 15.8 9.8 18 9.8C20.2 9.8 22.5 11.2 23.5 13.5H12.5Z" fill="#FDBA74"/>
                    <path d="M9.5 16H26.5L24 23.2C23.5 24.6 22.2 25.5 20.7 25.5H15.3C13.8 25.5 12.5 24.6 12 23.2L9.5 16Z" fill="#38BDF8" fill-opacity="0.28" stroke="#0284C7" stroke-width="1.4"/>
                    <path d="M18 25.5V28.5M13.5 28.5H22.5" stroke="#0284C7" stroke-width="1.6" stroke-linecap="round"/>
                    <circle cx="18" cy="8.8" r="2" fill="#E11D48"/>
                </svg>`,
            "Gelado de Frutas": `
                <svg viewBox="0 0 36 36" class="w-7 h-7" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect width="36" height="36" rx="9" fill="#E0F2FE"/>
                    <rect x="16.2" y="21" width="3.6" height="8.5" rx="1.8" fill="#D97706"/>
                    <path d="M12 13C12 9.7 14.7 7 18 7C21.3 7 24 9.7 24 13V21.5C24 22.3 23.3 23 22.5 23H13.5C12.7 23 12 22.3 12 21.5V13Z" fill="#F43F5E"/>
                    <path d="M12 16.5H24V21.5C24 22.3 23.3 23 22.5 23H13.5C12.7 23 12 22.3 12 21.5V16.5Z" fill="#FACC15"/>
                    <rect x="14.5" y="10.5" width="1.6" height="8" rx="0.8" fill="#FFFFFF" fill-opacity="0.6"/>
                </svg>`,
            "Goiaba": `
                <svg viewBox="0 0 36 36" class="w-7 h-7" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect width="36" height="36" rx="9" fill="#DCFCE7"/>
                    <circle cx="16.5" cy="19.5" r="8.5" fill="#22C55E"/>
                    <circle cx="20.5" cy="20.5" r="7" fill="#86EFAC"/>
                    <circle cx="20.5" cy="20.5" r="5.3" fill="#F43F5E"/>
                    <circle cx="19" cy="19.5" r="0.7" fill="#FEF08A"/>
                    <circle cx="21.5" cy="19" r="0.7" fill="#FEF08A"/>
                    <circle cx="20.5" cy="21.8" r="0.7" fill="#FEF08A"/>
                    <circle cx="22.2" cy="21.2" r="0.7" fill="#FEF08A"/>
                    <path d="M15.5 11C15.5 8.5 18 7.5 20.5 8.5C19 10.5 17 11.2 15.5 11Z" fill="#15803D"/>
                </svg>`,
            "Uva Itália": `
                <svg viewBox="0 0 36 36" class="w-7 h-7" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect width="36" height="36" rx="9" fill="#ECFCCB"/>
                    <path d="M18 11V7.5M18 8.5C20.5 8 22.5 9 23.5 10.5" stroke="#15803D" stroke-width="1.6" stroke-linecap="round"/>
                    <circle cx="14.5" cy="14" r="3.1" fill="#84CC16"/>
                    <circle cx="18" cy="14" r="3.1" fill="#A3E635"/>
                    <circle cx="21.5" cy="14" r="3.1" fill="#84CC16"/>
                    <circle cx="16" cy="18.5" r="3.1" fill="#A3E635"/>
                    <circle cx="20" cy="18.5" r="3.1" fill="#65A30D"/>
                    <circle cx="18" cy="23" r="3.1" fill="#84CC16"/>
                    <circle cx="18" cy="27" r="2.6" fill="#A3E635"/>
                </svg>`,
            "Abacaxi Pérola": `
                <svg viewBox="0 0 36 36" class="w-7 h-7" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect width="36" height="36" rx="9" fill="#FEF3C7"/>
                    <path d="M18 7L15.5 13.5H20.5L18 7Z" fill="#16A34A"/>
                    <path d="M13.5 9L14.5 14H17.5L13.5 9Z" fill="#15803D"/>
                    <path d="M22.5 9L21.5 14H18.5L22.5 9Z" fill="#15803D"/>
                    <rect x="12" y="13.5" width="12" height="15.5" rx="5.5" fill="#F59E0B"/>
                    <path d="M14 17L22 25M22 17L14 25M13.5 21H22.5" stroke="#B45309" stroke-width="1.1" stroke-linecap="round" stroke-opacity="0.65"/>
                </svg>`,
            "Tangerina": `
                <svg viewBox="0 0 36 36" class="w-7 h-7" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect width="36" height="36" rx="9" fill="#FFEDD5"/>
                    <ellipse cx="18" cy="19.5" rx="9.2" ry="8" fill="#F97316"/>
                    <ellipse cx="18" cy="19" rx="8.2" ry="6.8" fill="#FB923C"/>
                    <path d="M18 11.5V9.5" stroke="#15803D" stroke-width="1.6" stroke-linecap="round"/>
                    <path d="M18 10.5C19.5 8 22.8 8 24.5 9.8C22.5 11.4 19.8 11.4 18 10.5Z" fill="#16A34A"/>
                    <circle cx="14.5" cy="16.5" r="1.2" fill="#FED7AA" fill-opacity="0.7"/>
                </svg>`,
            "Graviola": `
                <svg viewBox="0 0 36 36" class="w-7 h-7" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect width="36" height="36" rx="9" fill="#D1FAE5"/>
                    <path d="M18 9.5C22.8 9.5 25.5 14 25 19.5C24.5 24.8 21.2 28 17.5 27.8C13.8 27.6 11 24 11.2 18.8C11.4 13.8 14 9.5 18 9.5Z" fill="#16A34A"/>
                    <circle cx="15.5" cy="15.5" r="0.9" fill="#065F46"/>
                    <circle cx="20.5" cy="15" r="0.9" fill="#065F46"/>
                    <circle cx="18" cy="19" r="0.9" fill="#065F46"/>
                    <circle cx="14.5" cy="21.5" r="0.9" fill="#065F46"/>
                    <circle cx="21" cy="22" r="0.9" fill="#065F46"/>
                    <path d="M18 9.5V7.2" stroke="#78350F" stroke-width="1.8" stroke-linecap="round"/>
                </svg>`,
            "Abacate": `
                <svg viewBox="0 0 36 36" class="w-7 h-7" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect width="36" height="36" rx="9" fill="#ECFCCB"/>
                    <path d="M18 8C21.5 8 25.5 14.5 25.5 20.5C25.5 25.2 22.2 28.5 18 28.5C13.8 28.5 10.5 25.2 10.5 20.5C10.5 14.5 14.5 8 18 8Z" fill="#15803D"/>
                    <path d="M18 10C20.6 10 23.8 15.3 23.8 20.3C23.8 24.1 21.2 26.8 18 26.8C14.8 26.8 12.2 24.1 12.2 20.3C12.2 15.3 15.4 10 18 10Z" fill="#BEF264"/>
                    <circle cx="18" cy="21.2" r="4" fill="#78350F"/>
                    <circle cx="16.8" cy="20" r="1.1" fill="#B45309"/>
                </svg>`
        }};

        const iconePadrao = `
            <svg viewBox="0 0 36 36" class="w-7 h-7" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect width="36" height="36" rx="9" fill="#E0F2FE"/>
                <circle cx="18" cy="18" r="7" fill="#0284C7"/>
            </svg>`;

        const cooperativasData = {dados_json};
        const fmtBRL = new Intl.NumberFormat('pt-BR', {{ style: 'currency', currency: 'BRL' }});
        const fmtInt = new Intl.NumberFormat('pt-BR', {{ maximumFractionDigits: 0 }});

        let filtroCoopAtual = {filtro_json};

        function formatarCelulaDupla(valor, qtd, unidade = "", isDestaque = false) {{
            if (!valor || valor === 0) {{
                return '<span class="text-slate-300 font-normal">—</span>';
            }}
            const suf = unidade ? ` ${{unidade.toLowerCase()}}` : " itens";
            const corQtd = isDestaque ? "text-emerald-700/80" : "text-slate-400";
            return `
                <div class="leading-tight">
                    <div>${{fmtBRL.format(valor)}}</div>
                    <div class="text-[11px] font-normal ${{corQtd}} mt-0.5">${{fmtInt.format(qtd)}}${{suf}}</div>
                </div>
            `;
        }}

        function atualizarBotoesFiltro() {{
            document.querySelectorAll('.coop-btn').forEach(b => {{
                const ativo = b.getAttribute('data-coop') === filtroCoopAtual;
                b.className = ativo
                    ? "coop-btn px-3 py-1.5 rounded-lg text-xs font-semibold transition-all bg-slate-900 text-white shadow-xs cursor-pointer"
                    : "coop-btn px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:text-slate-900 transition-all cursor-pointer";
            }});
        }}

        function ajustarAlturaIframe() {{
            if (window.frameElement) {{
                const altura = document.documentElement.scrollHeight;
                window.frameElement.style.height = (altura + 12) + "px";
            }}
        }}

        function renderizarTabela() {{
            const tbody = document.getElementById("tabelaCorpo");
            const tfoot = document.getElementById("tabelaRodape");

            const gruposVisiveis = filtroCoopAtual === "TODAS"
                ? cooperativasData
                : cooperativasData.filter(g => g.cooperativa === filtroCoopAtual);

            let totalGeralMesesVal = Array(9).fill(0);
            let totalGeralMesesQtd = Array(9).fill(0);
            let totalGeralPeriodoVal = 0;
            let totalGeralPeriodoQtd = 0;

            gruposVisiveis.forEach(grupo => {{
                grupo.produtos.forEach(prod => {{
                    prod.valores.forEach((v, idx) => {{
                        totalGeralMesesVal[idx] += v;
                        totalGeralPeriodoVal += v;
                    }});
                    prod.qtds.forEach((q, idx) => {{
                        totalGeralMesesQtd[idx] += q;
                        totalGeralPeriodoQtd += q;
                    }});
                }});
            }});

            let htmlBody = "";

            gruposVisiveis.forEach(grupo => {{
                let subMesesVal = Array(9).fill(0);
                let subMesesQtd = Array(9).fill(0);
                let subTotalCoopVal = 0;
                let subTotalCoopQtd = 0;

                grupo.produtos.forEach(prod => {{
                    prod.valores.forEach((v, idx) => {{
                        subMesesVal[idx] += v;
                        subTotalCoopVal += v;
                    }});
                    prod.qtds.forEach((q, idx) => {{
                        subMesesQtd[idx] += q;
                        subTotalCoopQtd += q;
                    }});
                }});

                htmlBody += `
                    <tr class="bg-slate-100/90 border-t-2 border-slate-200 font-semibold text-slate-800">
                        <td class="sticky-col-produto bg-slate-100 py-2.5 pl-4 pr-3 border-r border-slate-200/80">
                            <div class="flex flex-wrap items-center gap-2">
                                <span class="text-xs sm:text-sm font-bold tracking-tight text-slate-900">${{grupo.cooperativa}}</span>
                                <span class="text-[10px] font-medium px-2 py-0.5 rounded-md border ${{grupo.corBadge}}">
                                    ${{grupo.contrato}}
                                </span>
                            </div>
                        </td>
                        <td class="py-2.5 px-2.5 text-right text-[11px] text-slate-400 font-normal">Subtotal</td>
                        ${{subMesesVal.map((val, idx) => `
                            <td class="py-2.5 px-2.5 text-right text-slate-800">
                                ${{formatarCelulaDupla(val, subMesesQtd[idx], "itens")}}
                            </td>
                        `).join('')}}
                        <td class="py-2.5 pl-3 pr-4 text-right font-bold text-slate-900 bg-slate-200/60 border-l border-slate-200">
                            ${{formatarCelulaDupla(subTotalCoopVal, subTotalCoopQtd, "itens")}}
                        </td>
                    </tr>
                `;

                grupo.produtos.forEach(prod => {{
                    const totalProdVal = prod.valores.reduce((a, b) => a + b, 0);
                    const totalProdQtd = prod.qtds.reduce((a, b) => a + b, 0);
                    const maxMesProd = Math.max(...prod.valores);
                    const iconeSvg = iconesProdutos[prod.nome] || iconePadrao;

                    htmlBody += `
                        <tr class="hover:bg-slate-50/90 transition-colors group">
                            <td class="sticky-col-produto bg-white group-hover:bg-slate-50 py-2.5 pl-5 pr-3 border-r border-slate-200/80">
                                <div class="flex items-center gap-3">
                                    <div class="flex-shrink-0 shadow-2xs rounded-[9px]">
                                        ${{iconeSvg}}
                                    </div>
                                    <div class="min-w-0">
                                        <p class="font-medium text-slate-800 truncate leading-tight">${{prod.nome}}</p>
                                        <p class="text-[11px] text-slate-400 mt-0.5">${{prod.unidade}}</p>
                                    </div>
                                </div>
                            </td>
                            <td class="py-2.5 px-2.5 text-right text-slate-600 font-medium text-xs">
                                ${{fmtBRL.format(prod.vu)}}
                            </td>
                            ${{prod.valores.map((val, idx) => {{
                                const qtd = prod.qtds[idx];
                                const isPico = val > 0 && val === maxMesProd;
                                const classeCelula = isPico
                                    ? "bg-emerald-50/85 text-emerald-800 font-semibold"
                                    : (val > 0 ? "text-slate-800 font-medium" : "text-slate-300");
                                return `
                                    <td class="py-2.5 px-2.5 text-right ${{classeCelula}}">
                                        ${{formatarCelulaDupla(val, qtd, prod.unidade, isPico)}}
                                    </td>
                                `;
                            }}).join('')}}
                            <td class="py-2.5 pl-3 pr-4 text-right font-semibold text-slate-900 bg-slate-50/80 border-l border-slate-200">
                                ${{formatarCelulaDupla(totalProdVal, totalProdQtd, prod.unidade)}}
                            </td>
                        </tr>
                    `;
                }});
            }});

            tbody.innerHTML = htmlBody;

            tfoot.innerHTML = `
                <tr>
                    <td class="sticky-col-produto bg-slate-900 py-3 pl-4 pr-3 border-r border-slate-700">
                        TOTAL GERAL EXECUTADO
                    </td>
                    <td class="py-3 px-2.5 text-right text-slate-400 font-normal">—</td>
                    ${{totalGeralMesesVal.map((val, idx) => `
                        <td class="py-3 px-2.5 text-right">
                            ${{val === 0 ? '<span class="text-slate-500">—</span>' : `
                                <div class="leading-tight">
                                    <div>${{fmtBRL.format(val)}}</div>
                                    <div class="text-[11px] font-normal text-slate-400 mt-0.5">${{fmtInt.format(totalGeralMesesQtd[idx])}} itens</div>
                                </div>
                            `}}
                        </td>
                    `).join('')}}
                    <td class="py-3 pl-3 pr-4 text-right text-emerald-300 font-bold bg-slate-800 border-l border-slate-700">
                        <div class="leading-tight">
                            <div>${{fmtBRL.format(totalGeralPeriodoVal)}}</div>
                            <div class="text-[11px] font-normal text-emerald-200/80 mt-0.5">${{fmtInt.format(totalGeralPeriodoQtd)}} itens</div>
                        </div>
                    </td>
                </tr>
            `;

            atualizarBotoesFiltro();
            ajustarAlturaIframe();
        }}

        document.querySelectorAll('.coop-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                filtroCoopAtual = btn.getAttribute('data-coop');
                renderizarTabela();
            }});
        }});

        window.addEventListener('load', renderizarTabela);
        window.addEventListener('resize', ajustarAlturaIframe);
    </script>
</body>
</html>"""


def render() -> None:
    st.markdown(
        """<style>
        .fnde-cabecalho{padding:4px 0 14px}.fnde-cabecalho h1{margin:0 0 10px;color:#1f3655;font-size:2rem;font-weight:800;line-height:1.2}
        .fnde-subtitulo{color:#637387;font-size:1.02rem;line-height:1.65}.fnde-divisor{border:0;border-top:1px solid #d9dfe6;margin:6px 0 18px}
        .fnde-card{background:#fff;border:1px solid #d7e3ee;border-radius:8px;padding:13px 16px;min-height:96px;box-shadow:0 1px 2px #00000008}
        .fnde-card-title{font-size:.78rem;font-weight:800;color:#174d7c;text-transform:uppercase}.fnde-card-value{font-size:1.38rem;font-weight:800;color:#063b70;margin-top:6px}.fnde-card-detail{font-size:.76rem;color:#63788d;margin-top:5px}
        .fnde-card.verde .fnde-card-value{color:#16865b}.fnde-card.laranja .fnde-card-value{color:#c97800}
        .fnde-box-title{background:linear-gradient(90deg,#075b88,#08749a);color:#fff;font-weight:700;padding:8px 11px;border-radius:7px 7px 0 0;margin-top:22px}
        .fnde-tabela{border:1px solid #d7e3ee;border-top:0;border-radius:0 0 7px 7px;overflow:auto;background:#fff;margin-bottom:6px}.fnde-tabela table{width:max-content;min-width:100%;border-collapse:collapse;font-size:.76rem;color:#163b5b}
        .fnde-tabela th{background:#edf4f8;padding:10px 12px;text-align:left;font-size:.67rem;white-space:nowrap;border-right:1px solid #dce7ef}.fnde-tabela td{padding:11px 12px;border-top:1px solid #e1eaf1;border-right:1px solid #edf2f6;white-space:nowrap}.fnde-tabela td:not(:first-child),.fnde-tabela th:not(:first-child){text-align:center}.fnde-tabela td:not(:first-child){font-weight:700;color:#063b70}.fnde-tabela .fnde-credor{font-weight:750;white-space:normal;min-width:290px}.fnde-tabela .fnde-valor{font-weight:800;color:#16865b}.fnde-tabela .fnde-total{font-weight:800;background:#f4f9fc;color:#073b61}
        .fnde-analise{border:1px solid #d7e3ee;border-radius:8px;padding:14px 16px 12px;margin-top:14px;background:#fff}.fnde-analise-titulo{font-size:1rem;font-weight:700;color:#fff;margin:28px 0 0;padding:8px 11px;border:0;border-radius:7px 7px 0 0;background:linear-gradient(90deg,#075b88,#08749a)}
        .st-key-analise_fnde{margin-top:-1rem!important;border-radius:0 0 8px 8px!important}
        .fnde-subtitulo-grafico{font-size:.9rem;font-weight:800;color:#073b61;margin:0 0 13px}
        .fnde-resumo-mes{border:1px solid #d7e3ee;border-radius:7px;overflow:hidden;background:#fff;height:fit-content!important;min-height:0!important;padding:0!important;margin:0!important}.fnde-resumo-mes table,body .fnde-resumo-mes table{width:100%;border-collapse:collapse;font-size:.75rem;color:#163b5b;margin:0!important;margin-bottom:0!important}.fnde-resumo-mes th{background:#edf4f8;padding:9px;text-align:left;font-size:.64rem}.fnde-resumo-mes td{padding:9px;border-top:1px solid #e1eaf1}.fnde-resumo-mes td:not(:first-child),.fnde-resumo-mes th:not(:first-child){text-align:center}.fnde-resumo-mes td:not(:first-child){font-weight:700;color:#063b70}.fnde-resumo-mes .fnde-total{font-weight:800;background:#f4f9fc;color:#073b61}
        .st-key-produtos_fnde{border:1px solid #d7e3ee!important;border-top:0!important;border-radius:0 0 8px 8px!important;padding:18px 16px 14px!important;margin-top:-1rem!important;background:#fff}
        </style>""",
        unsafe_allow_html=True,
    )
    st.markdown(
        """<div class="fnde-cabecalho"><h1>Monitoramento PNAE — Cooperativas</h1>
        <div class="fnde-subtitulo"><em>Execução da fonte 552 para as cooperativas da agricultura familiar.</em></div></div><hr class="fnde-divisor">""",
        unsafe_allow_html=True,
    )

    # Atualização manual das bases
    coluna_atualizacao, _ = st.columns([1, 4])
    with coluna_atualizacao:
        if st.button(
            "↻ Atualizar dados",
            key="fnde_atualizar_dados",
            use_container_width=True,
            help="Busca novamente os pagamentos e os dados da planilha SIAFIM 2026.",
        ):
            _carregar_pagamentos.clear()
            _carregar_siafim_2026.clear()
            st.rerun()
    st.caption("Atualização automática do cache: até 1 minuto. Use “Atualizar dados” para buscar as planilhas imediatamente.")

    try:
        pagamentos = _carregar_pagamentos()
        pagamentos["Cooperativa"] = pagamentos["Cooperativa"].replace(
            {NOME_COOPANORTE_ANTERIOR: NOME_COOPANORTE}
        )
    except Exception as erro:
        st.error("Não foi possível atualizar a base de pagamentos para o Monitoramento FNDE.")
        st.caption(f"Detalhe técnico: {erro}")
        if st.button("Atualizar conexão", key="fnde_atualizar_conexao"):
            _carregar_pagamentos.clear()
            _carregar_siafim_2026.clear()
            st.rerun()
        return

    if "fnde_filtros_aplicados" not in st.session_state:
        st.session_state.fnde_filtros_aplicados = {"meses": [], "credores": []}

    with st.sidebar:
        st.markdown("#### Filtros — Monitoramento FNDE")
        with st.form("form_filtros_fnde"):
            meses = st.multiselect(
                "Mês de pagamento",
                MESES,
                default=st.session_state.fnde_filtros_aplicados["meses"],
            )
            credores = st.multiselect(
                "Cooperativa",
                list(COOPERATIVAS),
                default=st.session_state.fnde_filtros_aplicados["credores"],
            )
            aplicar = st.form_submit_button("Aplicar filtros", use_container_width=True, type="primary")
        limpar = st.button("Limpar filtros", use_container_width=True, key="limpar_filtros_fnde")
        st.caption("Fonte fixa: 552")

    if aplicar:
        st.session_state.fnde_filtros_aplicados = {"meses": meses, "credores": credores}
        st.rerun()
    if limpar:
        st.session_state.fnde_filtros_aplicados = {"meses": [], "credores": []}
        st.rerun()

    filtros = st.session_state.fnde_filtros_aplicados
    filtrado = pagamentos.copy()
    if filtros["meses"]:
        filtrado = filtrado[filtrado["Mês"].isin(filtros["meses"])]
    if filtros["credores"]:
        filtrado = filtrado[filtrado["Cooperativa"].isin(filtros["credores"])]

    executado = float(filtrado["Valor executado"].sum()) if not filtrado.empty else 0.0
    saldo = max(META_COOPERATIVAS - executado, 0.0)
    percentual_executado = (executado / META_COOPERATIVAS * 100) if META_COOPERATIVAS else 0.0

    # Cards fixos e totais mantidos
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _card("Total recebido FNDE", TOTAL_RECEBIDO, "Receita anual de 2026", "azul")
    with c2:
        _card("Meta cooperativas", META_COOPERATIVAS, "45% do total recebido", "azul")
    with c3:
        _card("Executado", executado, f"{percentual_executado:.1f}% da meta anual", "verde")
    with c4:
        _card("Saldo a executar", saldo, "Meta anual ainda disponível", "laranja")

    st.markdown('<div class="fnde-box-title">Distribuição mensal de recursos por cooperativa</div>', unsafe_allow_html=True)
    matriz = pd.pivot_table(
        filtrado,
        index="Cooperativa",
        columns="Mês",
        values="Valor executado",
        aggfunc="sum",
        fill_value=0.0,
    ) if not filtrado.empty else pd.DataFrame()
    matriz = matriz.reindex(index=list(COOPERATIVAS), columns=MESES, fill_value=0.0)
    meses_exibidos = [mes for mes in MESES if float(matriz[mes].sum()) > 0]
    matriz = matriz[meses_exibidos]
    linhas = []
    for cooperativa, valores in matriz.iterrows():
        total_credor = float(valores.sum())
        celulas = "".join(f"<td>{_moeda(valor)}</td>" for valor in valores)
        linhas.append(f"<tr><td class='fnde-credor'>{cooperativa}</td>{celulas}<td class='fnde-total'>{_moeda(total_credor)}</td></tr>")
    totais_mes = matriz.sum(axis=0)
    total_geral = float(totais_mes.sum())
    rodape = "".join(f"<td class='fnde-total'>{_moeda(valor)}</td>" for valor in totais_mes)
    st.markdown(
        "<div class='fnde-tabela'><table><thead><tr><th>RAZÃO SOCIAL / CREDOR</th>"
        + "".join(f"<th>{mes.upper()}</th>" for mes in meses_exibidos)
        + "<th>TOTAL GERAL</th></tr></thead><tbody>" + "".join(linhas)
        + f"<tr><td class='fnde-total'>TOTAL CONSOLIDADO DO FILTRO</td>{rodape}<td class='fnde-total'>{_moeda(total_geral)}</td></tr>"
        + "</tbody></table></div>",
        unsafe_allow_html=True,
    )

    mensal = filtrado.groupby("Mês")["Valor executado"].sum() if not filtrado.empty else pd.Series(dtype=float)
    quantidade_mensal = filtrado.groupby("Mês").size() if not filtrado.empty else pd.Series(dtype=int)
    grafico = pd.DataFrame({"Mês": MESES, "Executado no mês": [float(mensal.get(mes, 0.0)) for mes in MESES]})
    grafico["Pagamentos"] = [int(quantidade_mensal.get(mes, 0)) for mes in MESES]
    st.markdown('<div class="fnde-analise-titulo">Análise temporal e execução mensal</div>', unsafe_allow_html=True)
    with st.container(key="analise_fnde", border=True):
        esquerda, direita = st.columns([1.18, .92], gap="large")
        with esquerda:
            st.markdown('<div class="fnde-subtitulo-grafico">Curva de execução mensal das cooperativas</div>', unsafe_allow_html=True)
            grafico_visual = grafico[grafico["Executado no mês"] > 0].copy()
            figura = go.Figure()
            figura.add_bar(
                name="Executado no mês",
                x=grafico_visual["Mês"],
                y=grafico_visual["Executado no mês"],
                text=[f"<b>{_moeda(valor)}</b>" for valor in grafico_visual["Executado no mês"]],
                textposition="outside",
                textfont=dict(family="Arial Black, Arial, sans-serif", size=12, color="#002b49"),
                cliponaxis=False,
                marker_color="#07879b",
                hovertemplate="<b>%{x}</b><br>Executado: R$ %{y:,.2f}<extra></extra>",
            )
            figura.update_layout(height=310, margin=dict(l=10, r=10, t=42, b=10), showlegend=False, bargap=.34, yaxis_tickprefix="R$ ", yaxis_tickformat=",.0f", plot_bgcolor="#fff", paper_bgcolor="#fff")
            figura.update_xaxes(showgrid=False, tickangle=0, tickfont=dict(size=11, color="#244b69"))
            figura.update_yaxes(gridcolor="#dce8ef", zerolinecolor="#dce8ef", rangemode="tozero", tickfont=dict(size=11, color="#244b69"))
            st.plotly_chart(figura, use_container_width=True, config={"displayModeBar": False})
        with direita:
            st.markdown('<div class="fnde-subtitulo-grafico">Execução por cooperativa</div>', unsafe_allow_html=True)
            por_credor = filtrado.groupby("Cooperativa")["Valor executado"].sum() if not filtrado.empty else pd.Series(dtype=float)
            qtde_pagamentos = filtrado.groupby("Cooperativa").size() if not filtrado.empty else pd.Series(dtype=int)
            linhas_resumo = "".join(
                f"<tr><td>{cooperativa}</td><td>{int(qtde_pagamentos.get(cooperativa, 0))}</td>"
                f"<td class='fnde-valor'>{_moeda(float(por_credor.get(cooperativa, 0.0)))}</td>"
                f"<td>{float(por_credor.get(cooperativa, 0.0)) / META_COOPERATIVAS * 100:.1f}%</td></tr>"
                for cooperativa in COOPERATIVAS
            )
            st.markdown(
                "<div class='fnde-resumo-mes'><table><thead><tr><th>CREDOR</th><th>PAGAMENTOS</th><th>EXECUTADO</th><th>% DA META FNDE</th></tr></thead><tbody>"
                + linhas_resumo
                + f"<tr><td class='fnde-total'>TOTAL GERAL</td><td class='fnde-total'>{int(qtde_pagamentos.sum())}</td><td class='fnde-total'>{_moeda(float(por_credor.sum()))}</td><td class='fnde-total'>{percentual_executado:.1f}%</td></tr>"
                + "</tbody></table></div>",
                unsafe_allow_html=True,
            )

    # Nova seção: Execução SIAFIM — Agricultura Familiar 2026 (substitui a antiga base Qlik)
    st.markdown('<div class="fnde-box-title">Produtos fornecidos por cooperativa — Execução SIAFIM 2026</div>', unsafe_allow_html=True)
    with st.container(key="produtos_fnde"):
        dados_siafim = _carregar_siafim_2026()

        # Sincroniza o filtro inicial caso o usuário tenha filtrado 1 cooperativa na barra lateral
        filtro_inicial_siafim = "TODAS"
        if len(filtros["credores"]) == 1:
            sigla_sel = _sigla_cooperativa(filtros["credores"][0])
            if sigla_sel:
                filtro_inicial_siafim = sigla_sel

        html_siafim = _html_tabela_siafim_2026(dados_siafim, filtro_inicial=filtro_inicial_siafim)
        components.html(html_siafim, height=1120, scrolling=True)
