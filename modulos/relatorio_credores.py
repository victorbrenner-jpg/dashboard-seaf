"""Exportação da mesma matriz de credores apresentada na tela de OB."""

import html
import io

import xlsxwriter


TITULO = "Detalhamento de Pagamentos por Credor"
SUBTITULO = "Distribuição Mensal de Recursos por Fornecedor / Prestador de Serviço"


def descrever_filtros(estado):
    partes = []
    if estado.get("mem_ob_tipo_data", "Por Mês de Competência") != "Por Mês de Competência":
        partes.append(f"Período: {estado.get('mem_ob_dt_ini')} a {estado.get('mem_ob_dt_fim')}")
    else:
        meses = estado.get("mem_ob_meses", [])
        if meses:
            partes.append("Meses: " + ", ".join(map(str, meses)))
    for chave, rotulo in [("despesa", "Despesa"), ("grupos", "Grupo"),
                          ("tipo_item", "Tipo item"), ("fontes", "Fonte"),
                          ("marcadores_fonte", "Marcador fonte"),
                          ("objetos", "Objeto"), ("credores", "Credor")]:
        valores = estado.get("mem_ob_" + chave, [])
        if valores:
            partes.append(rotulo + ": " + ", ".join(map(str, valores)))
    return " | ".join(partes) or "Sem filtros — relação completa"


def gerar_excel(matriz, meses, filtros):
    colunas = list(meses) + ["Total Geral"]
    saida = io.BytesIO()
    with xlsxwriter.Workbook(saida, {"in_memory": True, "strings_to_formulas": False,
                                    "strings_to_urls": False}) as livro:
        aba = livro.add_worksheet("Pagamentos por Credor")
        base = {"font_name": "Calibri", "font_size": 11, "font_color": "#002B49",
                "border": 1, "border_color": "#E2E8F0", "valign": "vcenter"}
        titulo = livro.add_format({**base, "bold": True, "bg_color": "#002B49", "font_color": "white", "text_wrap": True})
        texto = livro.add_format({**base, "text_wrap": True})
        cabecalho = livro.add_format({**base, "bold": True, "bg_color": "#F1F5F9", "align": "center"})
        moeda = livro.add_format({**base, "num_format": '"R$" #,##0.00', "align": "right"})
        total = livro.add_format({**base, "num_format": '"R$" #,##0.00', "bold": True, "bg_color": "#F1F5F9", "top": 2})
        total_texto = livro.add_format({**base, "bold": True, "bg_color": "#F1F5F9", "top": 2, "text_wrap": True})
        ultima = len(colunas)
        aba.merge_range(0, 0, 0, ultima, TITULO, titulo)
        aba.merge_range(1, 0, 1, ultima, SUBTITULO, titulo)
        aba.merge_range(2, 0, 2, ultima, filtros, texto)
        aba.set_row(0, 28)
        aba.set_row(1, 28)
        aba.set_row(2, max(32, 16 * (len(filtros) // 130 + 1)))
        aba.write_row(3, 0, ["RAZÃO SOCIAL / CREDOR"] + [c.upper() for c in colunas], cabecalho)
        for linha, (_, registro) in enumerate(matriz.iterrows(), 4):
            aba.write_string(linha, 0, str(registro["Credor_Nome_Tratado"]), texto)
            aba.set_row(linha, max(38, 15 * (len(str(registro["Credor_Nome_Tratado"])) // 38 + 1)))
            for coluna, nome in enumerate(colunas, 1):
                aba.write_number(linha, coluna, float(registro[nome]), total if nome == "Total Geral" else moeda)
        rodape = len(matriz) + 4
        aba.write_string(rodape, 0, "TOTAL CONSOLIDADO DO FILTRO", total_texto)
        aba.set_row(rodape, 34)
        for coluna, nome in enumerate(colunas, 1):
            aba.write_number(rodape, coluna, float(matriz[nome].sum()), total)
        aba.set_column(0, 0, 43)
        aba.set_column(1, ultima, 20)
        aba.freeze_panes(4, 1)
        aba.set_landscape()
        aba.set_paper(9)
        aba.fit_to_pages(1, 0)
        aba.repeat_rows(0, 3)
        aba.print_area(0, 0, rodape, ultima)
        aba.set_footer("&CPágina &P de &N")
    return saida.getvalue()


def gerar_impressao(tabela_html, filtros):
    return """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<style>
body {font-family:Arial,sans-serif;color:#002b49;margin:0}
button {box-sizing:border-box;width:100%;height:38px;margin:0;border:1px solid #007b84;
border-radius:7px;background:linear-gradient(135deg,#005691 0%,#028090 100%);
color:#fff;font-family:Arial,sans-serif;font-size:14px;font-weight:700;cursor:pointer;
box-shadow:0 4px 10px rgba(0,86,145,.22);transition:background .16s ease}
button:hover {background:linear-gradient(135deg,#004a7c 0%,#01757d 100%)}
button:focus-visible {outline:2px solid #028090;outline-offset:-3px}
#relatorio {display:none}
@page {size:A4 landscape;margin:10mm}
@media print {
button {display:none} #relatorio {display:block}
h1 {font-size:18px} p {font-size:10px;overflow-wrap:anywhere}
.subtitulo-tabela-html {padding:12px;color:white;background:#002b49!important;font-size:12px;font-weight:bold}
table {width:100%;border-collapse:collapse;table-layout:fixed;font-size:9px}
th,td {border:1px solid #dce3eb;padding:7px 4px;text-align:right;overflow-wrap:anywhere}
th {background:#f1f5f9;text-align:center} th:first-child {width:23%!important}
th:not(:first-child) {width:auto!important} td:first-child {text-align:left}
td:last-child,.linha-total-html {font-weight:bold;background:#f1f5f9}
.linha-total-html {border-top:2px solid #002b49}
thead {display:table-header-group} tr {break-inside:avoid}
* {print-color-adjust:exact;-webkit-print-color-adjust:exact}
}
</style></head><body><button title="Imprimir relação por credor conforme os filtros aplicados" onclick="window.print()">🖨️ Imprimir relação</button>
<section id="relatorio"><h1>""" + TITULO + "</h1><p>" + html.escape(filtros) + "</p>" + tabela_html + "</section></body></html>"
