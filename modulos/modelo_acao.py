"""Relatório Ação/Subação preenchendo o MODELO Excel do usuário.

O modelo (modelos/modelo_Relatorio_por_ Ação_ e_Subação.xlsx) é preenchido com as NLs
filtradas; a tabela dinâmica é mantida e usa um intervalo nomeado dinâmico como origem.
"""
from __future__ import annotations

import datetime
import io
import re
import unicodedata
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Relatório a partir do MODELO Excel do usuário (modelos/modelo_Relatorio_por_*.xlsx)
# ---------------------------------------------------------------------------
NOME_INTERVALO_DINAMICO = "Dados_Relatorio_Acao"
_ABA_RESUMO = "xl/worksheets/sheet1.xml"
_ABA_DETALHE = "xl/worksheets/sheet2.xml"


def localizar_modelo_relatorio() -> Path:
    pasta = Path(__file__).resolve().parent.parent / "modelos"
    achados = sorted(pasta.glob("modelo_Relatorio_por*A*o*Suba*o*.xlsx"))
    if not achados:
        raise FileNotFoundError(
            "Modelo do relatório não encontrado na pasta 'modelos' "
            "(modelo_Relatorio_por_ Ação_ e_Subação.xlsx)."
        )
    return achados[0]


def preencher_modelo_relatorio(df: pd.DataFrame, caminho_modelo=None) -> bytes:
    """Preenche o modelo do usuário com as NLs filtradas na tela.

    - Aba 'Detalhe NL': uma linha por NL (mesma ordem de colunas do modelo).
    - Aba 'Resumo': tabela dinâmica reconstruída com os dados e configurada para
      atualizar ao abrir; a origem é um intervalo nomeado dinâmico, então
      linhas incluídas/excluídas na aba Detalhe entram na tabela ao atualizar.
    """
    import zipfile
    from xml.sax.saxutils import escape, quoteattr

    if df.empty:
        raise ValueError("Não há liquidações para o recorte escolhido.")

    caminho = Path(caminho_modelo) if caminho_modelo else localizar_modelo_relatorio()
    with zipfile.ZipFile(caminho) as z:
        arq = {n: z.read(n) for n in z.namelist()}

    # ---------- dados ----------
    base = df.sort_values(
        ["Acao_Relacao", "SubAcao_Relacao", "Credor_Tratado", "NL_Numero"], kind="stable"
    )
    nat = {"SEM_CLASSE": "N/C"}

    def s(v, padrao=""):
        if v is None or (not isinstance(v, str) and pd.isna(v)):
            return padrao
        return str(v)

    linhas = []
    for r in base.to_dict("records"):
        d = pd.to_datetime(r.get("Data_DT"), errors="coerce")
        serial = None if pd.isna(d) else (d.to_pydatetime().date() - datetime.date(1899, 12, 30)).days
        ret = r.get("Valor_Retido_Limpo")
        tot = r.get("Valor_Total_Limpo")
        linhas.append([
            s(r.get("Acao_Relacao"), "NÃO INFORMADA"),
            s(r.get("SubAcao_Relacao"), "NÃO INFORMADA"),
            s(r.get("Credor_Tratado")),
            s(r.get("Objeto_Relacao")),
            s(r.get("Grupo_Classificado"), "N/C"),
            s(r.get("NL_Numero")),
            s(r.get("NE_Chave")),
            serial,
            nat.get(s(r.get("Natureza_NL")), s(r.get("Natureza_NL"))),
            s(r.get("Status_Filtro")),
            s(r.get("Fonte_Relacao")),
            s(r.get("Marcador_Fonte_Relacao"), "0000-SEM MARCADOR"),
            0.0 if ret is None or pd.isna(ret) else float(ret),
            0.0 if tot is None or pd.isna(tot) else float(tot),
        ])
    n = len(linhas)
    ultima = n + 1
    letras = "ABCDEFGHIJKLMN"

    # ---------- aba Detalhe NL ----------
    xml = arq[_ABA_DETALHE].decode("utf-8")
    m_dados = re.search(r"<sheetData>(.*)</sheetData>", xml, re.S)
    todas = re.findall(r"<row r=\"\d+\".*?</row>", m_dados.group(1), re.S)
    cabecalho = todas[0]
    modelo_linha = todas[1] if len(todas) > 1 else None
    estilos = (
        {c: st for c, st in re.findall(r'<c r="([A-N])\d+" s="(\d+)"', modelo_linha)}
        if modelo_linha else {}
    )
    novas = [cabecalho]
    for i, lin in enumerate(linhas, start=2):
        cel = []
        for c, v in enumerate(lin):
            ref = f"{letras[c]}{i}"
            st = f' s="{estilos[letras[c]]}"' if letras[c] in estilos else ""
            if c >= 12 or c == 7:
                if v is None:
                    cel.append(f'<c r="{ref}"{st}/>')
                else:
                    cel.append(f'<c r="{ref}"{st}><v>{format(v, ".15g")}</v></c>')
            else:
                cel.append(f'<c r="{ref}"{st} t="inlineStr"><is><t>{escape(v)}</t></is></c>')
        novas.append(f'<row r="{i}" spans="1:14" ht="20.1" customHeight="1">{"".join(cel)}</row>')
    xml = xml[:m_dados.start()] + "<sheetData>" + "".join(novas) + "</sheetData>" + xml[m_dados.end():]
    xml = re.sub(r'<dimension ref="[^"]*"', f'<dimension ref="A1:N{ultima}"', xml, count=1)
    xml = re.sub(r'(<autoFilter ref=")[^"]*"', rf'\1A1:N{ultima}"', xml, count=1)
    arq[_ABA_DETALHE] = xml.encode("utf-8")

    # ---------- cache da tabela dinâmica (com registros) ----------
    campos_eixo = {0: None, 1: None, 4: None, 11: None}  # Ação, Subação, GD, Marcador
    for k in campos_eixo:
        campos_eixo[k] = sorted({lin[k] for lin in linhas})
    indice = {k: {v: i for i, v in enumerate(vs)} for k, vs in campos_eixo.items()}

    cd = arq["xl/pivotCache/pivotCacheDefinition1.xml"].decode("utf-8")
    campos = re.findall(r"<cacheField\b[^>]*?name=\"[^\"]*\"[^>]*>.*?</cacheField>", cd, re.S)
    novos = []
    datas = [lin[7] for lin in linhas if lin[7] is not None]

    def iso(serial):
        return (datetime.date(1899, 12, 30) + datetime.timedelta(days=serial)).strftime("%Y-%m-%dT00:00:00")

    for k, cf in enumerate(campos):
        abre = re.match(r"<cacheField\b[^>]*>", cf).group(0)
        if k in campos_eixo:
            itens = "".join(f"<s v={quoteattr(v)}/>" for v in campos_eixo[k])
            sh = f'<sharedItems count="{len(campos_eixo[k])}">{itens}</sharedItems>'
        elif k == 7:
            if datas:
                sh = ('<sharedItems containsSemiMixedTypes="0" containsNonDate="0" containsDate="1" '
                      f'containsString="0" minDate="{iso(min(datas))}" maxDate="{iso(max(datas)+1)}"/>')
            else:
                sh = "<sharedItems/>"
        elif k >= 12:
            vals = [lin[k] for lin in linhas]
            sh = ('<sharedItems containsSemiMixedTypes="0" containsString="0" containsNumber="1" '
                  f'minValue="{format(min(vals), ".15g")}" maxValue="{format(max(vals), ".15g")}"/>')
        else:
            sh = "<sharedItems/>"
        novos.append(f"{abre}{sh}</cacheField>")
    bloco = re.search(r"<cacheFields\b[^>]*>.*</cacheFields>", cd, re.S)
    cd = cd[:bloco.start()] + f'<cacheFields count="14">{"".join(novos)}</cacheFields>' + cd[bloco.end():]
    cd = re.sub(r'recordCount="\d+"', f'recordCount="{n}"', cd, count=1)
    cd = cd.replace(
        '<cacheSource type="worksheet"><worksheetSource ref="A1:N18" sheet="Detalhe NL"/></cacheSource>',
        f'<cacheSource type="worksheet"><worksheetSource name="{NOME_INTERVALO_DINAMICO}"/></cacheSource>',
    )
    assert NOME_INTERVALO_DINAMICO in cd, "origem do cache não encontrada no modelo"
    cd = re.sub(r"<pivotCacheDefinition\b", '<pivotCacheDefinition refreshOnLoad="1"', cd, count=1)
    arq["xl/pivotCache/pivotCacheDefinition1.xml"] = cd.encode("utf-8")

    regs = []
    for lin in linhas:
        cel = []
        for k, v in enumerate(lin):
            if k in campos_eixo:
                cel.append(f'<x v="{indice[k][v]}"/>')
            elif k == 7:
                cel.append(f'<d v="{iso(v)}"/>' if v is not None else "<m/>")
            elif k >= 12:
                cel.append(f'<n v="{format(v, ".15g")}"/>')
            else:
                cel.append(f"<s v={quoteattr(v)}/>")
        regs.append(f'<r>{"".join(cel)}</r>')
    arq["xl/pivotCache/pivotCacheRecords1.xml"] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<pivotCacheRecords xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        f'count="{n}">{"".join(regs)}</pivotCacheRecords>'
    ).encode("utf-8")

    # ---------- tabela dinâmica (layout) e células do Resumo ----------
    grupos = {}
    for lin in linhas:
        chave = (lin[0], lin[1], lin[11], lin[4])
        grupos[chave] = grupos.get(chave, 0.0) + lin[13]
    chaves = sorted(
        grupos,
        key=lambda c: tuple(indice[k][c[j]] for j, k in enumerate((0, 1, 11, 4))),
    )
    pt = arq["xl/pivotTables/pivotTable1.xml"].decode("utf-8")
    campos_pt = re.findall(r"<pivotField\b[^>]*/>|<pivotField\b[^>]*[^/]>.*?</pivotField>", re.search(
        r"<pivotFields\b[^>]*>(.*)</pivotFields>", pt, re.S).group(1), re.S)
    campos_pt_novos = []
    for k, pf in enumerate(campos_pt):
        if k in campos_eixo:
            itens = "".join(f'<item x="{i}"/>' for i in range(len(campos_eixo[k])))
            pf = re.sub(r"<items\b.*?</items>", "", pf, flags=re.S)
            pf = re.sub(r"<pivotField\b([^>]*?)/>", r"<pivotField\1></pivotField>", pf)
            pf = pf.replace("</pivotField>", f'<items count="{len(campos_eixo[k])}">{itens}</items></pivotField>')
        campos_pt_novos.append(pf)
    pt = re.sub(r"<pivotFields\b[^>]*>.*</pivotFields>",
                f'<pivotFields count="14">{"".join(campos_pt_novos)}</pivotFields>', pt, flags=re.S)

    ordem_campos = (0, 1, 11, 4)
    itens_linha, anterior = [], None
    for c in chaves:
        pos = [indice[k][c[j]] for j, k in enumerate(ordem_campos)]
        rep = 0
        if anterior is not None:
            while rep < 3 and pos[rep] == anterior[rep]:
                rep += 1
        xs = "".join("<x/>" if p == 0 else f'<x v="{p}"/>' for p in pos[rep:])
        itens_linha.append(f'<i r="{rep}">{xs}</i>' if rep else f"<i>{xs}</i>")
        anterior = pos
    itens_linha.append('<i t="grand"><x/></i>')
    pt = re.sub(r"<rowItems\b.*?</rowItems>",
                f'<rowItems count="{len(itens_linha)}">{"".join(itens_linha)}</rowItems>', pt, flags=re.S)
    ultima_pivo = 4 + len(chaves) + 1
    pt = re.sub(r'(<location ref=")[^"]*"', rf'\1A4:E{ultima_pivo}"', pt, count=1)
    arq["xl/pivotTables/pivotTable1.xml"] = pt.encode("utf-8")

    xr = arq[_ABA_RESUMO].decode("utf-8")
    hoje = datetime.date.today().strftime("%d/%m/%Y")
    xr = re.sub(r"(<c r=\"A2\"[^>]*?) t=\"s\"><v>1</v></c>",
                rf'\1 t="inlineStr"><is><t>Recorte do painel · gerado em {hoje}</t></is></c>', xr, count=1)
    linhas_piv = []
    for j, c in enumerate(chaves):
        r = 5 + j
        txt = "".join(
            f'<c r="{col}{r}" t="inlineStr"><is><t>{escape(v)}</t></is></c>'
            for col, v in zip("ABCD", c)
        )
        linhas_piv.append(f'<row r="{r}" spans="1:5">{txt}<c r="E{r}" s="8"><v>{format(grupos[c], ".15g")}</v></c></row>')
    rt = 5 + len(chaves)
    total = sum(grupos.values())
    linhas_piv.append(
        f'<row r="{rt}" spans="1:5"><c r="A{rt}" t="inlineStr"><is><t>Total Geral</t></is></c>'
        f'<c r="E{rt}" s="8"><v>{format(total, ".15g")}</v></c></row>'
    )
    corte = re.search(r'<row r="5".*?</row>.*</sheetData>', xr, re.S)
    xr = xr[:corte.start()] + "".join(linhas_piv) + "</sheetData>" + xr[corte.end():]
    xr = re.sub(r'<dimension ref="[^"]*"', f'<dimension ref="A1:E{rt}"', xr, count=1)
    arq[_ABA_RESUMO] = xr.encode("utf-8")

    # ---------- nomes definidos ----------
    wb = arq["xl/workbook.xml"].decode("utf-8")
    wb = re.sub(r"('Detalhe NL'!\$A\$1:\$N\$)\d+", rf"\g<1>{ultima}", wb)
    novo_nome = (
        f'<definedName name="{NOME_INTERVALO_DINAMICO}">'
        "OFFSET('Detalhe NL'!$A$1,0,0,COUNTA('Detalhe NL'!$A:$A),14)</definedName>"
    )
    if NOME_INTERVALO_DINAMICO not in wb:
        wb = wb.replace("<definedNames>", "<definedNames>" + novo_nome, 1)
    arq["xl/workbook.xml"] = wb.encode("utf-8")

    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in arq.items():
            z.writestr(nome, conteudo)
    return saida.getvalue()


def filtrar_por_busca(df: pd.DataFrame, busca: str) -> pd.DataFrame:
    """Aplica a busca digitada na tabela (ação ou subação, sem acento/maiúscula)."""
    def limpa(valor) -> str:
        texto = unicodedata.normalize("NFD", str(valor))
        return "".join(c for c in texto if not unicodedata.combining(c)).lower()

    q = limpa(busca or "").strip()
    if not q:
        return df
    acao = df["Acao_Relacao"].map(limpa)
    sub = df["SubAcao_Relacao"].map(limpa)
    return df[acao.str.contains(q, regex=False) | sub.str.contains(q, regex=False)]
