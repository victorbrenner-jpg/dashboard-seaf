"""
modulos/ob_matriz_despesas.py

Matriz analítica por tipo de despesa (Correntes, Restos a Pagar e DEA),
no layout do mockup "Demonstrativo Analítico por Tipo de Despesa".
Substitui as três tabelas de despesas por um único componente HTML
(filtro GND, média 11m/meses ativos, Mi/R$ exato, expandir/recolher).

Uso no app.py:

    from modulos.ob_matriz_despesas import render_matriz_despesas, dados_de_dataframe

    dados = dados_de_dataframe(df_despesas, ano=2026)   # ou monte o dict à mão
    render_matriz_despesas(dados, ano=2026)

Formato de `dados` (valores em R$, uma lista por mês, Jan..último mês):
    {"correntes": {"gnd3": [...], "gnd4": [...]},
     "rp":        {"gnd3": [...], "gnd4": [...]},
     "dea":       {"gnd3": [...], "gnd4": [...]}}
"""
from __future__ import annotations

import json
import re

NOMES_MESES = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN",
               "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]
NATUREZAS = ("correntes", "rp", "dea")

# Aliases aceitos na coluna "natureza" do DataFrame (comparação em maiúsculas)
_ALIAS_NATUREZA = {
    "CORRENTES": "correntes", "CORRENTE": "correntes", "DESPESAS CORRENTES": "correntes",
    "RP": "rp", "RESTOS A PAGAR": "rp", "RESTOS A PAGAR - RP": "rp",
    "DEA": "dea", "DESPESAS DE EXERCICIOS ANTERIORES": "dea",
    "DESPESAS DE EXERCÍCIOS ANTERIORES": "dea",
}


def dados_de_dataframe(df, ano=2026, ultimo_mes=None,
                       col_natureza="natureza", col_gnd="gnd",
                       col_mes="mes", col_valor="valor"):
    """Agrega um DataFrame longo no dict esperado por render_matriz_despesas.

    Colunas esperadas (ajuste pelos parâmetros): natureza (Correntes/RP/DEA),
    gnd (3 ou 4), mes (1..12) e valor (R$). Meses sem lançamento viram 0,00.
    `ultimo_mes` limita o período (ex.: 11 = até NOV); por padrão usa o maior mês com dado.
    """
    import pandas as pd  # import local: o módulo funciona sem pandas se o dict vier pronto

    d = df.copy()
    d["_nat"] = d[col_natureza].astype(str).str.strip().str.upper().map(_ALIAS_NATUREZA)
    d["_gnd"] = pd.to_numeric(d[col_gnd], errors="coerce")
    d["_mes"] = pd.to_numeric(d[col_mes], errors="coerce")
    d["_val"] = pd.to_numeric(d[col_valor], errors="coerce").fillna(0.0)
    d = d[d["_nat"].notna() & d["_gnd"].isin([3, 4]) & d["_mes"].between(1, 12)]

    n = int(ultimo_mes or (d["_mes"].max() if len(d) else 1))
    saida = {}
    for nat in NATUREZAS:
        saida[nat] = {}
        for gnd in (3, 4):
            s = (d[(d["_nat"] == nat) & (d["_gnd"] == gnd)]
                 .groupby("_mes")["_val"].sum())
            saida[nat][f"gnd{gnd}"] = [round(float(s.get(m, 0.0)), 2) for m in range(1, n + 1)]
    return saida


def dados_de_pivot(df_matriz, meses_exibicao,
                   col_natureza="Despesa_Tratada", col_grupo="Grupo_Tratado"):
    """Converte o `df_matriz` do app.py (pivot natureza x grupo x meses) no dict da matriz.

    Natureza: CORRENTE / RP / DEA. Grupo: texto começando em "3" ou "4".
    Meses sem linha viram 0,00, na ordem de `meses_exibicao`.
    """
    mapa = {"CORRENTE": "correntes", "RP": "rp", "DEA": "dea"}
    saida = {nat: {"gnd3": [0.0] * len(meses_exibicao), "gnd4": [0.0] * len(meses_exibicao)}
             for nat in NATUREZAS}
    for _, row in df_matriz.iterrows():
        nat = mapa.get(str(row[col_natureza]).strip().upper())
        grupo = str(row[col_grupo]).strip()[:1]
        if nat is None or grupo not in ("3", "4"):
            continue
        chave = f"gnd{grupo}"
        for i, m in enumerate(meses_exibicao):
            try:
                saida[nat][chave][i] += float(row.get(m, 0.0) or 0.0)
            except (TypeError, ValueError):
                pass
    return saida


def montar_html_matriz(dados, ano=2026, meses=None):
    """Devolve o HTML completo da matriz (string).

    `meses`: rótulos das colunas (ex.: ["JAN/2026", ...]). Se omitido, usa JAN.. a partir do ano.
    """
    n = max(len(dados[nat][g]) for nat in NATUREZAS for g in ("gnd3", "gnd4"))
    limpo = {}
    for nat in NATUREZAS:
        limpo[nat] = {}
        for g in ("gnd3", "gnd4"):
            v = [float(x or 0) for x in dados.get(nat, {}).get(g, [])]
            limpo[nat][g] = (v + [0.0] * n)[:n]

    ano2 = str(ano)[-2:]
    if meses:
        n = len(meses)
        for nat in NATUREZAS:
            for g in ("gnd3", "gnd4"):
                limpo[nat][g] = (limpo[nat][g] + [0.0] * n)[:n]
        meses = [re.sub(r"/(\d{4})$", lambda mo: "/" + mo.group(1)[-2:], str(m)) for m in meses]
    else:
        meses = [f"{NOMES_MESES[i]}/{ano2}" for i in range(n)]
    periodo = meses[0] if n == 1 else f"{meses[0]} a {meses[-1]}"
    th = "\n                        ".join(
        f'<th class="py-3.5 px-2.5 text-right min-w-[68px]">{m}</th>' for m in meses)

    return (_TEMPLATE
            .replace("__MONTHS__", json.dumps(meses))
            .replace("__DADOS__", json.dumps(limpo))
            .replace("__TH_MESES__", th)
            .replace("__NM__", str(n))
            .replace("__PERIODO__", periodo)
            .replace("__ANO__", str(ano)))


def render_matriz_despesas(dados, ano=2026, altura=560, meses=None):
    """Renderiza a matriz no Streamlit (iframe com rolagem própria)."""
    import streamlit.components.v1 as components
    components.html(montar_html_matriz(dados, ano, meses), height=altura, scrolling=True)


_TEMPLATE = r'''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Matriz Analítica Consolidada — Execução por Natureza de Despesa (__ANO__)</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Fontes Inter & JetBrains Mono -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <!-- Lucide Icons -->
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        .matrix-scroll th, .matrix-scroll td { white-space: nowrap; }
        body {
            font-family: 'Inter', sans-serif;
            background-color: transparent;
            color: #0f172a;
        }
        /* Alinhamento numérico tabular com JetBrains Mono para leitura contábil de alta precisão */
        .tabular-nums {
            font-family: 'JetBrains Mono', monospace;
            font-variant-numeric: tabular-nums;
        }
        /* Barra de rolagem refinada */
        .matrix-scroll::-webkit-scrollbar {
            height: 8px;
            width: 8px;
        }
        .matrix-scroll::-webkit-scrollbar-track {
            background: #f8fafc;
        }
        .matrix-scroll::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 9999px;
        }
        .matrix-scroll::-webkit-scrollbar-thumb:hover {
            background: #94a3b8;
        }
        /* Sombras sutis nas colunas fixas (Sticky) */
        .sticky-left-shadow {
            box-shadow: 4px 0 8px -4px rgba(15, 23, 42, 0.08);
        }
        .sticky-right-shadow {
            box-shadow: -4px 0 8px -4px rgba(15, 23, 42, 0.08);
        }
        /* Degradês ricos inspirados na identidade visual original */
        .banner-correntes {
            background: linear-gradient(90deg, #007791 0%, #03395e 52%, #021d3a 100%);
        }
        .banner-rp {
            background: linear-gradient(90deg, #e66a00 0%, #5c3a1d 52%, #021d3a 100%);
        }
        .banner-dea {
            background: linear-gradient(90deg, #dc2626 0%, #4c1d3d 52%, #021d3a 100%);
        }
    </style>
</head>
<body class="antialiased py-2 px-1 sm:px-2 selection:bg-sky-100 selection:text-sky-900">

    <!-- Container Principal Único: Matriz Analítica por Tipo de Despesa -->
    <main class="w-full max-w-[1560px] mx-auto bg-white rounded-2xl shadow-lg shadow-slate-200/70 border border-slate-200/90 overflow-hidden">
        
        <!-- Cabeçalho Integrado do Cartão da Matriz -->
        <header class="p-5 sm:p-6 bg-gradient-to-r from-white via-white to-slate-50/80 border-b border-slate-200 flex flex-col xl:flex-row xl:items-center xl:justify-between gap-5">
            
            <!-- Título -->
            <div class="flex items-center gap-3.5">
                <div class="p-2.5 bg-teal-50 text-[#0f766e] rounded-xl border border-teal-100 shrink-0">
                    <i data-lucide="layers" class="w-6 h-6"></i>
                </div>
                <h1 class="text-lg sm:text-xl font-bold text-slate-900 tracking-tight">
                    Demonstrativo Analítico por Tipo de Despesa
                </h1>
            </div>

            <!-- Barra de Controles Interativos -->
            <div class="flex flex-wrap items-center gap-2.5 sm:gap-3">
                
                <!-- Pílulas de Filtro por Grupo de Gasto (GND) -->
                <div class="inline-flex flex-wrap items-center bg-slate-100/90 p-1 rounded-xl border border-slate-200/80" role="group" aria-label="Filtro por GND">
                    <button type="button" id="pillALL" onclick="setGndFilter('ALL')"
                        class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-white text-slate-900 shadow-sm transition-all">
                        Todos os GNDs
                    </button>
                    <button type="button" id="pillGND3" onclick="setGndFilter('GND3')"
                        class="px-3 py-1.5 text-xs font-medium rounded-lg text-slate-600 hover:text-slate-900 transition-all">
                        GND 3 - Custeio
                    </button>
                    <button type="button" id="pillGND4" onclick="setGndFilter('GND4')"
                        class="px-3 py-1.5 text-xs font-medium rounded-lg text-slate-600 hover:text-slate-900 transition-all">
                        GND 4 - Investimentos
                    </button>
                </div>

                <!-- Divisor vertical sutil -->
                <div class="hidden sm:block h-6 w-px bg-slate-200"></div>

                <!-- Base de Cálculo da Média Mensal -->
                <div class="inline-flex items-center bg-slate-100/90 p-1 rounded-xl border border-slate-200/80" role="group" aria-label="Base de Cálculo da Média">
                    <button type="button" id="btnAvgPeriod" onclick="setAvgBasis('period')" title="Divide o total acumulado pelos __NM__ meses do período (__PERIODO__)"
                        class="px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-white text-slate-900 shadow-sm transition-all">
                        Média __NM__m
                    </button>
                    <button type="button" id="btnAvgActive" onclick="setAvgBasis('active')" title="Divide o total acumulado apenas pelos meses com execução (> R$ 0,00)"
                        class="px-2.5 py-1.5 text-xs font-medium rounded-lg text-slate-600 hover:text-slate-900 transition-all">
                        Meses ativos
                    </button>
                </div>

                <!-- Alternador de Escala Numérica -->
                <div class="inline-flex items-center bg-slate-100/90 p-1 rounded-xl border border-slate-200/80" role="group" aria-label="Formato Numérico">
                    <button type="button" id="btnFormatShort" onclick="setFormatMode('short')"
                        class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-white text-[#0f766e] shadow-sm transition-all">
                        Abreviado (Mi)
                    </button>
                    <button type="button" id="btnFormatExact" onclick="setFormatMode('exact')"
                        class="px-3 py-1.5 text-xs font-medium rounded-lg text-slate-600 hover:text-slate-900 transition-all">
                        Contábil Exato (R$)
                    </button>
                </div>

                <!-- Botão Único Expandir / Recolher Todos -->
                <button type="button" id="btnToggleAll" onclick="toggleAllCategories()"
                    class="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-xl bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 shadow-2xs transition-all cursor-pointer">
                    <i data-lucide="chevrons-down-up" id="iconToggleAll" class="w-3.5 h-3.5 text-slate-500"></i>
                    <span id="labelToggleAll">Recolher tudo</span>
                </button>
            </div>
        </header>

        <!-- Área da Tabela com Rolagem Horizontal Responsiva -->
        <div class="matrix-scroll overflow-x-auto relative">
            <table class="w-full text-left border-collapse min-w-[1100px]">
                <thead>
                    <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold uppercase tracking-wider text-slate-500 select-none">
                        <!-- Coluna Fixa à Esquerda -->
                        <th class="py-3.5 px-4 sticky left-0 bg-slate-50 z-20 min-w-[250px] sticky-left-shadow" aria-label="Categoria"></th>
                        <!-- Meses JAN/26 a NOV/26 -->
                        __TH_MESES__
                        <!-- Colunas Fixas à Direita: Média Mensal e Total Acumulado -->
                        <th class="py-3.5 px-3.5 text-right bg-[#e9edfe] text-indigo-950 sticky right-[176px] z-20 w-[124px] min-w-[124px] sticky-right-shadow border-l border-slate-200/80">
                            <div class="flex flex-col items-end">
                                <span>MÉDIA MENSAL</span>
                                <span id="thAvgSublabel" class="text-[9px] font-semibold text-indigo-600/80 tracking-normal normal-case">Base: __NM__ meses</span>
                            </div>
                        </th>
                        <th class="py-3.5 px-4 text-right bg-slate-100 text-slate-800 sticky right-0 z-20 w-[176px] min-w-[176px] border-l border-slate-200/80">
                            TOTAL ACUMULADO
                        </th>
                    </tr>
                </thead>
                <tbody id="matrixTableBody" class="text-xs sm:text-[13px] tabular-nums">
                    <!-- Renderizado dinamicamente via JavaScript -->
                </tbody>
            </table>
        </div>

    </main>

    <script>
        // =========================================================================
        // 1. DADOS OFICIAIS DO DEMONSTRATIVO ANALÍTICO (JAN A NOV/2026)
        // =========================================================================
        const MONTHS = __MONTHS__;

        const MATRIX_DATA = [
            {
                id: 'correntes',
                title: 'DESPESAS CORRENTES',
                subtitle: 'Dotação Ordinária do Ano',
                totalLabel: 'TOTAL — DESPESAS CORRENTES',
                // Identidade Azul-Petróleo -> Azul-Marinho Profundo
                accentHex: '#007791',
                dotColor: 'bg-[#007791]',
                bannerClass: 'banner-correntes',
                headerStickyBg: 'bg-[#021d3a]',
                borderLeftClass: 'border-l-4 border-l-[#007791]',
                iconBg: 'bg-white/15 text-white border-white/30',
                totalRowBg: 'bg-[#007791]/[0.08]',
                totalStickyBg: 'bg-[#ebf5f7]',
                totalAvgStickyBg: 'bg-[#e1eff2]',
                totalValueColor: 'text-[#006075]',
                isCutOff: false,
                gnd3: [], gnd4: []
            },
            {
                id: 'rp',
                title: 'RESTOS A PAGAR - RP',
                subtitle: 'Compromissos de Anos Anteriores',
                totalLabel: 'TOTAL — RESTOS A PAGAR (RP)',
                // Identidade Laranja Intenso -> Azul-Marinho Profundo
                accentHex: '#e66a00',
                dotColor: 'bg-[#e66a00]',
                bannerClass: 'banner-rp',
                headerStickyBg: 'bg-[#021d3a]',
                borderLeftClass: 'border-l-4 border-l-[#e66a00]',
                iconBg: 'bg-white/15 text-white border-white/30',
                totalRowBg: 'bg-[#e66a00]/[0.08]',
                totalStickyBg: 'bg-[#fdf3eb]',
                totalAvgStickyBg: 'bg-[#faeadc]',
                totalValueColor: 'text-[#c25900]',
                isCutOff: false,
                gnd3: [], gnd4: []
            },
            {
                id: 'dea',
                title: 'DESPESAS DE EXERCÍCIOS ANTERIORES - DEA',
                subtitle: 'Reconhecimento de Passivo',
                totalLabel: 'TOTAL — DEA (PASSIVO)',
                // Identidade Vermelho Carmesim -> Azul-Marinho Profundo
                accentHex: '#dc2626',
                dotColor: 'bg-[#dc2626]',
                bannerClass: 'banner-dea',
                headerStickyBg: 'bg-[#021d3a]',
                borderLeftClass: 'border-l-4 border-l-[#dc2626]',
                iconBg: 'bg-white/15 text-white border-white/30',
                totalRowBg: 'bg-[#dc2626]/[0.08]',
                totalStickyBg: 'bg-[#fceded]',
                totalAvgStickyBg: 'bg-[#fae1e1]',
                totalValueColor: 'text-[#b91c1c]',
                isCutOff: false,
                gnd3: [], gnd4: []
            }
        ];

        const DADOS = __DADOS__;
        MATRIX_DATA.forEach(c => { c.gnd3 = DADOS[c.id].gnd3; c.gnd4 = DADOS[c.id].gnd4; });

        // Estado Interativo da Matriz
        let state = {
            formatMode: 'short', // 'short' (Mi) ou 'exact' (R$ Contábil)
            gndFilter: 'ALL',    // 'ALL', 'GND3', 'GND4'
            avgBasis: 'period',  // 'period' (11 meses) ou 'active' (meses com movimentação > 0)
            expanded: {
                correntes: true,
                rp: true,
                dea: true
            }
        };

        // =========================================================================
        // 2. FUNÇÕES AUXILIARES DE CÁLCULO E FORMATAÇÃO
        // =========================================================================
        const sumArray = (arr) => arr.reduce((acc, v) => acc + v, 0);

        function calculateMonthlyAverage(arr) {
            const total = sumArray(arr);
            if (total === 0) return { avg: 0, divisor: 0 };

            if (state.avgBasis === 'active') {
                const activeMonths = arr.filter(v => v > 0).length;
                return {
                    avg: activeMonths > 0 ? total / activeMonths : 0,
                    divisor: activeMonths
                };
            }
            return {
                avg: total / MONTHS.length,
                divisor: MONTHS.length
            };
        }

        function formatValue(val, mode = state.formatMode, showSymbol = false) {
            if (val === 0) {
                return showSymbol ? 'R$ 0,00' : '0,00';
            }
            if (mode === 'short') {
                const millions = val / 1_000_000;
                if (millions < 0.01) {
                    const thousands = val / 1_000;
                    const strK = thousands.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + ' mil';
                    return showSymbol ? `R$ ${strK}` : strK;
                }
                const strMi = millions.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' Mi';
                return showSymbol ? `R$ ${strMi}` : strMi;
            } else {
                const strExact = val.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                return showSymbol ? `R$ ${strExact}` : strExact;
            }
        }

        function formatPercent(pct) {
            return pct.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + '%';
        }

        function getRowStats(arr) {
            let maxVal = -1;
            let maxIdx = -1;
            arr.forEach((v, idx) => {
                if (v > maxVal) {
                    maxVal = v;
                    maxIdx = idx;
                }
            });
            return { maxVal, maxIdx };
        }

        // Calcula o sombreamento sutil de heatmap baseado na proporção em relação ao pico da linha
        function getHeatmapStyle(val, maxVal, isTotalRow) {
            if (val <= 0 || maxVal <= 0) return '';
            const ratio = val / maxVal;
            if (ratio === 1) {
                // Pico máximo da linha: destaque visual nítido
                return isTotalRow
                    ? 'bg-amber-100/90 text-slate-950 font-bold ring-1 ring-inset ring-amber-300'
                    : 'bg-amber-50/90 text-slate-950 font-semibold ring-1 ring-inset ring-amber-200/90';
            }
            if (ratio >= 0.80) {
                return isTotalRow ? 'bg-slate-200/50 font-semibold text-slate-900' : 'bg-slate-50/90 text-slate-800';
            }
            if (ratio >= 0.55) {
                return isTotalRow ? 'bg-slate-100/40 text-slate-800' : 'text-slate-700';
            }
            return '';
        }

        // =========================================================================
        // 3. RENDERIZAÇÃO DA MATRIZ POR NATUREZA INDEPENDENTE (SEM TOTAL GERAL)
        // =========================================================================
        function renderMatrix() {
            const thAvgSublabel = document.getElementById('thAvgSublabel');
            thAvgSublabel.textContent = state.avgBasis === 'period' ? `Base: ${MONTHS.length} meses` : 'Base: meses ativos';

            const tbody = document.getElementById('matrixTableBody');
            tbody.innerHTML = '';

            MATRIX_DATA.forEach((cat, blockIndex) => {
                const isExpanded = state.expanded[cat.id];

                // Total visível da natureza conforme filtro GND ativo
                const visibleMonthly = MONTHS.map((_, idx) => {
                    if (state.gndFilter === 'GND3') return cat.gnd3[idx];
                    if (state.gndFilter === 'GND4') return cat.gnd4[idx];
                    return cat.gnd3[idx] + cat.gnd4[idx];
                });
                const visibleTotal = sumArray(visibleMonthly);
                const visibleStats = getRowStats(visibleMonthly);
                const visibleAvgInfo = calculateMonthlyAverage(visibleMonthly);

                // --- 1. CABEÇALHO DO BLOCO DA NATUREZA (FAIXA DEGRADÊ INTENSA) ---
                const trHeader = document.createElement('tr');
                const topSeparatorClass = blockIndex > 0 ? 'border-t-4 border-white' : '';
                trHeader.className = `group ${cat.bannerClass} ${topSeparatorClass} hover:brightness-110 transition-all cursor-pointer select-none`;
                trHeader.onclick = () => toggleCategory(cat.id);

                let headerHtml = `
                    <td colspan="${MONTHS.length + 1}" class="py-3 px-4 sticky left-0 z-10 transition-colors">
                        <div class="flex items-center gap-2.5">
                            <span class="w-5 h-5 rounded-md flex items-center justify-center border shrink-0 ${cat.iconBg}">
                                <i data-lucide="${isExpanded ? 'chevron-down' : 'chevron-right'}" class="w-3.5 h-3.5"></i>
                            </span>
                            <div class="flex items-center flex-wrap gap-x-2">
                                <span class="text-xs font-bold text-white tracking-wide uppercase">${cat.title}</span>
                                <span class="text-[11px] font-medium text-white/80">(${cat.subtitle})</span>
                            </div>
                        </div>
                    </td>
                    <td class="py-3 px-3.5 text-right sticky right-[176px] z-10 ${cat.headerStickyBg} sticky-right-shadow border-l border-white/15 transition-colors">
                        <span class="text-[10px] font-semibold uppercase tracking-wider text-sky-200/90">Média Mensal</span>
                    </td>
                    <td class="py-3 px-4 text-right sticky right-0 z-10 ${cat.headerStickyBg} border-l border-white/15 transition-colors">
                        <span class="text-[10px] font-semibold uppercase tracking-wider text-white/80">Acumulado</span>
                    </td>
                `;
                trHeader.innerHTML = headerHtml;
                tbody.appendChild(trHeader);

                // --- 2. SUB-LINHAS (GND 3 - CUSTEIO E GND 4 - INVESTIMENTOS) ---
                if (isExpanded) {
                    const subItems = [
                        { key: 'GND3', code: '3', name: 'OUTRAS DESPESAS CORRENTES', values: cat.gnd3 },
                        { key: 'GND4', code: '4', name: 'INVESTIMENTOS', values: cat.gnd4 }
                    ];

                    subItems.forEach(sub => {
                        if (state.gndFilter !== 'ALL' && state.gndFilter !== sub.key) return;

                        const subTotal = sumArray(sub.values);
                        const subAvgInfo = calculateMonthlyAverage(sub.values);
                        const subStats = getRowStats(sub.values);

                        const trSub = document.createElement('tr');
                        trSub.className = 'group bg-white hover:bg-slate-50/90 border-b border-slate-100 transition-colors';

                        let subHtml = `
                            <td class="py-2.5 px-4 pl-7 sticky left-0 bg-white group-hover:bg-slate-50 z-10 sticky-left-shadow ${cat.borderLeftClass} transition-colors">
                                <div class="flex items-center gap-2.5">
                                    <span class="w-2.5 h-2.5 rounded-full shrink-0 ${cat.dotColor}"></span>
                                    <span class="text-xs font-semibold text-slate-700 truncate">${sub.code} - ${sub.name}</span>
                                </div>
                            </td>
                        `;

                        sub.values.forEach((val, idx) => {
                            const heatClass = getHeatmapStyle(val, subStats.maxVal, false);
                            const zeroClass = val === 0 ? 'text-slate-300' : 'text-slate-600';
                            const isPeak = val > 0 && idx === subStats.maxIdx;
                            const tooltipAttr = isPeak
                                ? `title="Pico mensal (${cat.title} • GND ${sub.code}): ${formatValue(val, 'exact', true)}"`
                                : `title="${formatValue(val, 'exact', true)}"`;

                            subHtml += `
                                <td ${tooltipAttr} class="py-2.5 px-2.5 text-right text-xs transition-colors ${zeroClass} ${heatClass}">
                                    ${formatValue(val)}
                                </td>
                            `;
                        });

                        // Média Mensal da Sub-linha (Fixo à Direita)
                        const subAvgTooltip = subAvgInfo.divisor > 0
                            ? `Média de ${formatValue(subAvgInfo.avg, 'exact', true)}/mês (${subAvgInfo.divisor} ${subAvgInfo.divisor === 1 ? 'mês' : 'meses'})`
                            : 'Sem execução no período';
                        subHtml += `
                            <td title="${subAvgTooltip}" class="py-2.5 px-3.5 text-right text-xs font-semibold text-indigo-900 bg-[#f5f7ff] group-hover:bg-[#e9edfe] sticky right-[176px] z-10 sticky-right-shadow border-l border-slate-200/80 transition-colors">
                                ${formatValue(subAvgInfo.avg, state.formatMode)}
                            </td>
                        `;

                        // Total da Sub-linha (Fixo à Direita)
                        subHtml += `
                            <td class="py-2.5 px-4 text-right text-xs font-semibold text-slate-800 bg-[#f8fafc] group-hover:bg-[#f1f5f9] sticky right-0 z-10 border-l border-slate-200/80 transition-colors">
                                ${formatValue(subTotal, 'exact')}
                            </td>
                        `;

                        trSub.innerHTML = subHtml;
                        tbody.appendChild(trSub);
                    });
                }

                // --- 3. LINHA DE TOTALIZAÇÃO INDIVIDUAL DA NATUREZA ---
                const trTotal = document.createElement('tr');
                trTotal.className = `group ${cat.totalRowBg} border-b border-slate-200 font-bold`;

                let totalHtml = `
                    <td class="py-3 px-4 pl-7 sticky left-0 ${cat.totalStickyBg} z-10 sticky-left-shadow ${cat.borderLeftClass}">
                        <div class="flex items-center gap-2">
                            <i data-lucide="calculator" class="w-3.5 h-3.5 ${cat.totalValueColor} shrink-0"></i>
                            <span class="text-xs uppercase tracking-wide ${cat.totalValueColor}">${cat.totalLabel}</span>
                        </div>
                    </td>
                `;

                visibleMonthly.forEach((val, idx) => {
                    const heatClass = getHeatmapStyle(val, visibleStats.maxVal, true);
                    const zeroClass = val === 0 ? 'text-slate-400 font-normal' : 'text-slate-900 font-bold';
                    const isPeak = val > 0 && idx === visibleStats.maxIdx;
                    const tooltipAttr = isPeak
                        ? `title="Pico mensal (${cat.title}): ${formatValue(val, 'exact', true)}"`
                        : `title="${formatValue(val, 'exact', true)}"`;

                    totalHtml += `
                        <td ${tooltipAttr} class="py-3 px-2.5 text-right text-xs transition-colors ${zeroClass} ${heatClass}">
                            ${formatValue(val)}
                        </td>
                    `;
                });

                // Média Mensal da Natureza (Fixo à Direita)
                const totalAvgTooltip = visibleAvgInfo.divisor > 0
                    ? `Média de ${formatValue(visibleAvgInfo.avg, 'exact', true)}/mês (${visibleAvgInfo.divisor} ${visibleAvgInfo.divisor === 1 ? 'mês' : 'meses'})`
                    : 'Sem execução no período';
                totalHtml += `
                    <td title="${totalAvgTooltip}" class="py-3 px-3.5 text-right text-xs sm:text-[13px] font-bold text-indigo-950 ${cat.totalAvgStickyBg} sticky right-[176px] z-10 sticky-right-shadow border-l border-slate-200/80">
                        ${formatValue(visibleAvgInfo.avg, state.formatMode, true)}
                    </td>
                `;

                // Total Acumulado Individual da Natureza (Fixo à Direita)
                totalHtml += `
                    <td class="py-3 px-4 text-right text-xs sm:text-[13px] font-bold ${cat.totalValueColor} ${cat.totalStickyBg} sticky right-0 z-10 border-l border-slate-200/80">
                        ${formatValue(visibleTotal, 'exact', true)}
                    </td>
                `;

                trTotal.innerHTML = totalHtml;
                tbody.appendChild(trTotal);
            });

            // Re-renderiza os ícones Lucide recém-inseridos no DOM
            lucide.createIcons();
            updateToggleAllButtonState();
        }

        // =========================================================================
        // 5. CONTROLES INTERATIVOS DO CABEÇALHO
        // =========================================================================
        function setAvgBasis(basis) {
            state.avgBasis = basis;
            const btnPeriod = document.getElementById('btnAvgPeriod');
            const btnActive = document.getElementById('btnAvgActive');

            if (basis === 'period') {
                btnPeriod.className = 'px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-white text-slate-900 shadow-sm transition-all';
                btnActive.className = 'px-2.5 py-1.5 text-xs font-medium rounded-lg text-slate-600 hover:text-slate-900 transition-all';
            } else {
                btnActive.className = 'px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-white text-slate-900 shadow-sm transition-all';
                btnPeriod.className = 'px-2.5 py-1.5 text-xs font-medium rounded-lg text-slate-600 hover:text-slate-900 transition-all';
            }
            renderMatrix();
        }

        function setFormatMode(mode) {
            state.formatMode = mode;
            const btnShort = document.getElementById('btnFormatShort');
            const btnExact = document.getElementById('btnFormatExact');

            if (mode === 'short') {
                btnShort.className = 'px-3 py-1.5 text-xs font-semibold rounded-lg bg-white text-[#0f766e] shadow-sm transition-all';
                btnExact.className = 'px-3 py-1.5 text-xs font-medium rounded-lg text-slate-600 hover:text-slate-900 transition-all';
            } else {
                btnExact.className = 'px-3 py-1.5 text-xs font-semibold rounded-lg bg-white text-[#0f766e] shadow-sm transition-all';
                btnShort.className = 'px-3 py-1.5 text-xs font-medium rounded-lg text-slate-600 hover:text-slate-900 transition-all';
            }
            renderMatrix();
        }

        function setGndFilter(filter) {
            state.gndFilter = filter;
            ['ALL', 'GND3', 'GND4'].forEach(key => {
                const pill = document.getElementById(`pill${key}`);
                if (key === filter) {
                    pill.className = 'px-3 py-1.5 text-xs font-semibold rounded-lg bg-white text-slate-900 shadow-sm transition-all';
                } else {
                    pill.className = 'px-3 py-1.5 text-xs font-medium rounded-lg text-slate-600 hover:text-slate-900 transition-all';
                }
            });
            renderMatrix();
        }

        function toggleCategory(catId) {
            state.expanded[catId] = !state.expanded[catId];
            renderMatrix();
        }

        function toggleAllCategories() {
            const anyExpanded = Object.values(state.expanded).some(v => v === true);
            const targetState = !anyExpanded;
            state.expanded.correntes = targetState;
            state.expanded.rp = targetState;
            state.expanded.dea = targetState;
            renderMatrix();
        }

        function updateToggleAllButtonState() {
            const anyExpanded = Object.values(state.expanded).some(v => v === true);
            const label = document.getElementById('labelToggleAll');
            const icon = document.getElementById('iconToggleAll');

            if (anyExpanded) {
                label.textContent = 'Recolher tudo';
                icon.setAttribute('data-lucide', 'chevrons-down-up');
            } else {
                label.textContent = 'Expandir tudo';
                icon.setAttribute('data-lucide', 'chevrons-up-down');
            }
            lucide.createIcons();
        }

        // Inicializa a matriz ao carregar a página
        function ajustarAlturaIframe() {
            try {
                const h = document.body.offsetHeight + 12;
                if (window.frameElement) {
                    window.frameElement.style.height = h + 'px';
                    window.frameElement.setAttribute('height', h);
                }
            } catch (e) { /* sem acesso ao iframe: mantém a altura padrão */ }
        }
        window.addEventListener('load', () => {
            ajustarAlturaIframe();
            if (window.ResizeObserver) new ResizeObserver(ajustarAlturaIframe).observe(document.body);
        });

        window.addEventListener('DOMContentLoaded', () => {
            renderMatrix();
        });
    </script>
</body>
</html>
'''
