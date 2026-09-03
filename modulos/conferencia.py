"""Conferência entre o PDF do SIAFIM e a base consolidada de Pagamentos (OB)."""

import datetime
import io
import re
import unicodedata
import urllib.request

import numpy as np
import pandas as pd
import streamlit as st

try:
    import pdfplumber
except ImportError:  # A mensagem para o usuário é tratada ao executar a conferência.
    pdfplumber = None


LINK_BASE_OB_CONFERENCIA = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vTD3b7L6byArEDgkVKOXXlc7RK0M2QKXLov83OydCaks3rDISWYWfgGNi6vG6pwy8t5Ul3Fd2wArhtT/"
    "pub?gid=1786485134&single=true&output=csv"
)
_CREDOR_RETENCAO = "PREFEITURA DA CIDADE DO RECIFE - RETENÇÃO"
_PAGAMENTOS_COLETIVOS = (
    ("BOLSA ATLETA", "BOLSA ATLETA"),
    ("BOLSA ESCOLA", "BOLSA ESCOLA"),
)


def _brl(valor):
    if pd.isna(valor):
        return "R$ 0,00"
    return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _valor(serie):
    texto = pd.Series(serie).fillna("").astype(str).str.strip()
    texto = texto.str.replace(r"[^0-9,.-]", "", regex=True)
    ambos = texto.str.contains(r"\.", regex=True) & texto.str.contains(",", regex=False)
    texto.loc[ambos] = texto.loc[ambos].str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    somente_virgula = ~ambos & texto.str.contains(",", regex=False)
    texto.loc[somente_virgula] = texto.loc[somente_virgula].str.replace(",", ".", regex=False)
    return pd.to_numeric(texto, errors="coerce").fillna(0.0)


def _normalizar(valor):
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]+", " ", texto.upper()).strip()


def _gd(valor):
    texto = _normalizar(valor)
    return "4" if "INVEST" in texto or re.search(r"(^| )(GD|GND)?4($| )", texto) else "3"


def _tipo_item(valor):
    return "RETENÇÃO" if "RETEN" in _normalizar(valor) else "ITEM"


def _fonte(valor):
    achado = re.search(r"(?<!\d)(\d{3})(?!\d)", str(valor or ""))
    return achado.group(1) if achado else ""


def _consolidar_pagamentos_coletivos(pdf, base):
    """Agrupa beneficiários individuais quando o PDF usa um credor coletivo.

    Bolsa Atleta e Bolsa Escola aparecem no PDF como um único credor, mas na
    Base OB cada beneficiário é uma linha separada. O objeto da despesa
    identifica esses casos sem interferir nos demais pagamentos.
    """
    if base.empty or "Objeto_Conferencia" not in base.columns:
        return base

    objetos = base["Objeto_Conferencia"].fillna("").astype(str).map(_normalizar)
    itens = base["Tipo_Item_Conferencia"].eq("ITEM")

    for marcador_pdf, marcador_objeto in _PAGAMENTOS_COLETIVOS:
        linhas_pdf = pdf[
            pdf["Credor_Chave"].fillna("").astype(str).str.contains(
                re.escape(marcador_pdf), regex=True, na=False
            )
        ]
        if linhas_pdf.empty:
            continue

        alvo = objetos.str.contains(re.escape(marcador_objeto), regex=True, na=False) & itens
        if not alvo.any():
            continue

        credor_pdf = str(linhas_pdf.iloc[0]["Credor"]).strip()
        chave_pdf = str(linhas_pdf.iloc[0]["Credor_Chave"]).strip()
        base.loc[alvo, ["Credor_Exibicao", "Credor_Chave"]] = [credor_pdf, chave_pdf]

    return base


@st.cache_data(ttl=60, show_spinner=False)
def carregar_base_ob():
    """Lê a mesma aba publicada que alimenta a tela de Pagamentos (OB)."""
    try:
        requisicao = urllib.request.Request(
            LINK_BASE_OB_CONFERENCIA,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        with urllib.request.urlopen(requisicao, timeout=30) as resposta:
            base = pd.read_csv(io.BytesIO(resposta.read()), dtype=str)
    except Exception:
        return pd.DataFrame()
    base = base.loc[:, ~base.columns.duplicated()].copy()
    base.columns = [str(c).strip() for c in base.columns]

    # A tela principal já aceita essas variações de cabeçalho. A conferência
    # usa a mesma tolerância para não depender de uma grafia única no CSV.
    coluna_objeto = next(
        (
            coluna
            for coluna in ("Objeto da Despesa", "Objeto Despesa", "Objeto de Despesa", "Objeto")
            if coluna in base.columns
        ),
        None,
    )

    for coluna in ("Número", "Data Emissão", "Valor", "Fonte", "Nome do Credor", "Credor", "Tipo Item", "GRUPO"):
        if coluna not in base:
            base[coluna] = ""

    base["Objeto_Conferencia"] = (
        base[coluna_objeto].fillna("").astype(str)
        if coluna_objeto is not None
        else ""
    )
    base["Data_Conferencia"] = pd.to_datetime(base["Data Emissão"], dayfirst=True, errors="coerce").dt.date
    base["Valor_Conferencia"] = _valor(base["Valor"])
    base["Credor_Exibicao"] = base["Nome do Credor"].fillna(base["Credor"]).fillna("NÃO IDENTIFICADO").astype(str).str.strip().str.upper()
    base["Credor_Chave"] = base["Credor_Exibicao"].map(_normalizar)
    base["GD_Conferencia"] = base["GRUPO"].map(_gd)
    base["Tipo_Item_Conferencia"] = base["Tipo Item"].map(_tipo_item)
    base["Fonte_Conferencia"] = base["Fonte"].map(_fonte)
    # A exportação pode repetir linhas idênticas; não se deve somá-las duas vezes.
    chave = ["Número", "Data Emissão", "Valor", "Fonte", "Nome do Credor", "Tipo Item"]
    return base.drop_duplicates(subset=chave, keep="first")


def _linhas_pdf(conteudo):
    """Extrai somente a tabela principal Credor / GD / Valor do relatório 009717."""
    if pdfplumber is None:
        raise RuntimeError("A biblioteca pdfplumber não está instalada. Atualize as dependências da aplicação.")
    padrao = re.compile(r"^(?P<credor>.+?)\s+(?P<gd>[34])\s+R\$\s*(?P<valor>[0-9.]+,[0-9]{2})(?:\s+.*)?$")
    padrao_sobreposto = re.compile(r"^(?P<ini>.+?)(?P<gd>[34])(?P<fim>\S+)\s+R\$\s*(?P<valor>[0-9.]+,[0-9]{2})(?:\s+.*)?$")
    padrao_total = re.compile(r"TOTAL GERAL\s+R\$\s*([0-9.]+,[0-9]{2})")
    registros, estruturais, fontes, total_declarado = [], [], [], None
    with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
        for pagina in pdf.pages:
            # Leitura estrutural: necessária quando um nome longo invade
            # visualmente a coluna GD/valor. A ordem dos caracteres preserva
            # o que foi desenhado primeiro pelo relatório.
            palavras = pagina.extract_words(x_tolerance=1.5, y_tolerance=3, use_text_flow=False) or []
            grupos_palavras = []
            for palavra in sorted(palavras, key=lambda p: (float(p["top"]), float(p["x0"]))):
                alvo = next((g for g in reversed(grupos_palavras[-5:]) if abs(float(palavra["top"]) - g["top"]) <= 3.5), None)
                if alvo is None:
                    alvo = {"top": float(palavra["top"]), "itens": []}
                    grupos_palavras.append(alvo)
                alvo["itens"].append(palavra)
                alvo["top"] = sum(float(x["top"]) for x in alvo["itens"]) / len(alvo["itens"])
            cabecalho = None
            for grupo in grupos_palavras:
                itens = grupo["itens"]
                texto_cab = _normalizar(" ".join(str(x["text"]) for x in itens))
                if "NOME DO CREDOR" in texto_cab and "GD" in texto_cab and "VALOR" in texto_cab:
                    gd = next((x for x in itens if str(x["text"]).upper() == "GD"), None)
                    valor = [x for x in itens if str(x["text"]).upper() in {"VALOR", "TOTAL"}]
                    if gd and valor:
                        cabecalho = {"fim": max(float(x["bottom"]) for x in itens), "gd_x": (float(gd["x0"]) + float(gd["x1"])) / 2, "limite": min(float(pagina.width) * .74, max(float(x["x1"]) for x in valor) + max(25, float(pagina.width) * .035))}
                    break
            if cabecalho:
                grupos_chars = []
                for ordem, char in enumerate(pagina.chars or []):
                    alvo = next((g for g in reversed(grupos_chars[-8:]) if abs(float(char["top"]) - g["top"]) <= 2.2), None)
                    if alvo is None:
                        alvo = {"top": float(char["top"]), "itens": []}
                        grupos_chars.append(alvo)
                    item = dict(char); item["ordem"] = ordem
                    alvo["itens"].append(item)
                    alvo["top"] = sum(float(x["top"]) for x in alvo["itens"]) / len(alvo["itens"])
                for grupo in grupos_chars:
                    if grupo["top"] <= cabecalho["fim"] + 1:
                        continue
                    itens = [x for x in grupo["itens"] if float(x["x0"]) < cabecalho["limite"]]
                    candidatos = [x for x in itens if str(x["text"]) in {"3", "4"} and abs(((float(x["x0"]) + float(x["x1"])) / 2) - cabecalho["gd_x"]) <= max(9, float(pagina.width) * .012)]
                    if not candidatos:
                        continue
                    gd_char = max(candidatos, key=lambda x: x["ordem"])
                    antes = [x for x in itens if x["ordem"] < gd_char["ordem"]]
                    depois = [x for x in itens if x["ordem"] > gd_char["ordem"]]
                    credor = "".join(str(x["text"]) for x in antes).strip()
                    valor = re.search(r"R\$\s*([0-9.]+,[0-9]{2})", "".join(str(x["text"]) for x in depois))
                    chave = _normalizar(credor)
                    if valor and chave and re.search(r"[A-Z]", chave) and not chave.startswith("TOTAL"):
                        estruturais.append({"Credor": credor, "Credor_Chave": chave, "GD": str(gd_char["text"]), "Valor_PDF": float(_valor([valor.group(1)]).iloc[0])})
            texto = pagina.extract_text() or ""
            # A segunda página não repete o cabeçalho; por isso a leitura da
            # lista principal começa habilitada em todas as páginas.
            em_tabela, credor_pendente = True, ""
            for linha in texto.splitlines():
                limpa = linha.strip()
                normal = _normalizar(limpa)
                totais = padrao_total.findall(limpa.upper())
                if totais:
                    total_declarado = max(total_declarado or 0, float(_valor(totais).iloc[0]))
                if "NOME DO CREDOR" in normal and "GD" in normal and "VALOR" in normal:
                    em_tabela, credor_pendente = True, ""
                    continue
                if "FONTE DESPESA TOTAL POR FONTE" in normal:
                    # Em alguns layouts o cabeçalho do quadro de fonte ocupa a
                    # mesma linha de um credor. A tabela principal continua.
                    pass
                # O código de fonte fica no quadro próprio, acompanhado de R$.
                achado_fonte = re.search(r"(?<!\d)(\d{3})\s+R\$\s*[0-9.]+,[0-9]{2}", limpa)
                if achado_fonte:
                    fontes.append(achado_fonte.group(1))
                if not em_tabela:
                    continue
                if normal.startswith("TOTAL GERAL"):
                    # Os quadros laterais também usam "TOTAL GERAL" antes de
                    # a lista de credores terminar. Ignoramos a linha, sem
                    # encerrar a tabela principal.
                    credor_pendente = ""
                    continue
                achado = padrao.match(limpa)
                if not achado:
                    achado = padrao_sobreposto.match(limpa)
                    if achado:
                        credor = (achado.group("ini") + achado.group("fim")).strip()
                        gd, valor = achado.group("gd"), achado.group("valor")
                    else:
                        quebrada = re.match(r"^([34])\s+R\$\s*([0-9.]+,[0-9]{2})", limpa)
                        if quebrada and credor_pendente:
                            credor, gd, valor = credor_pendente, quebrada.group(1), quebrada.group(2)
                        else:
                            if limpa and "R$" not in limpa and not normal.startswith(("TOTAL", "UG ", "GD ", "FONTE ")):
                                credor_pendente = limpa
                            continue
                else:
                    credor, gd, valor = achado.group("credor"), achado.group("gd"), achado.group("valor")
                chave = _normalizar(credor)
                if chave and re.search(r"[A-Z]", chave) and not chave.startswith("TOTAL"):
                    registros.append({"Credor": credor.strip(), "Credor_Chave": chave, "GD": gd, "Valor_PDF": float(_valor([valor]).iloc[0])})
                credor_pendente = ""
    tabela_estrutural = pd.DataFrame(estruturais)
    if not tabela_estrutural.empty:
        tabela_estrutural = tabela_estrutural.groupby(["Credor_Chave", "GD"], as_index=False).agg(Credor=("Credor", "first"), Valor_PDF=("Valor_PDF", "sum"))
        if total_declarado is None or abs(float(tabela_estrutural["Valor_PDF"].sum()) - total_declarado) <= .01:
            return tabela_estrutural, sorted(set(fontes))
    tabela = pd.DataFrame(registros)
    if tabela.empty:
        raise ValueError("Não foi possível localizar a tabela principal de credores no PDF.")
    tabela = tabela.groupby(["Credor_Chave", "GD"], as_index=False).agg(Credor=("Credor", "first"), Valor_PDF=("Valor_PDF", "sum"))
    if total_declarado is not None and abs(float(tabela["Valor_PDF"].sum()) - total_declarado) > 0.01:
        raise ValueError(f"A leitura do PDF ficou incompleta: total extraído ({_brl(tabela['Valor_PDF'].sum())}) não confere com o total declarado ({_brl(total_declarado)}).")
    return tabela, sorted(set(fontes))


def comparar(conteudo, data, classificacao):
    pdf, fontes = _linhas_pdf(conteudo)
    pdf = pdf[~pdf["Credor_Chave"].str.contains("INSS", na=False)].copy()
    base = carregar_base_ob().copy()
    if base.empty:
        raise ValueError("A base consolidada de Pagamentos (OB) está indisponível.")
    base = base[base["Data_Conferencia"] == data].copy()
    if classificacao != "TODAS":
        base = base[base["Tipo_Item_Conferencia"] == classificacao].copy()
    if fontes:
        base = base[base["Fonte_Conferencia"].isin(fontes)].copy()
    base = base[~base["Credor_Chave"].str.contains("INSS", na=False)].copy()

    # Pagamentos coletivos: o PDF apresenta Bolsa Atleta/Bolsa Escola em uma
    # única linha, enquanto a Base OB detalha um beneficiário por registro.
    # A consolidação ocorre somente quando o credor coletivo existe no PDF e
    # o objeto da despesa identifica o mesmo programa.
    base = _consolidar_pagamentos_coletivos(pdf, base)

    chave_ret = _normalizar(_CREDOR_RETENCAO)
    if pdf["Credor_Chave"].eq(chave_ret).any():
        ret = base["Tipo_Item_Conferencia"].eq("RETENÇÃO")
        base.loc[ret, ["Credor_Exibicao", "Credor_Chave"]] = [_CREDOR_RETENCAO, chave_ret]
    agrupada = base.groupby(["Credor_Chave", "GD_Conferencia"], as_index=False).agg(Credor_Base=("Credor_Exibicao", "first"), Valor_Base=("Valor_Conferencia", "sum"), Registros_Base=("Valor_Conferencia", "size")).rename(columns={"GD_Conferencia": "GD"})
    tipos = base.pivot_table(index=["Credor_Chave", "GD_Conferencia"], columns="Tipo_Item_Conferencia", values="Valor_Conferencia", aggfunc="sum", fill_value=0).reset_index().rename(columns={"GD_Conferencia": "GD"})
    for tipo in ("ITEM", "RETENÇÃO"):
        if tipo not in tipos:
            tipos[tipo] = 0.0
    resultado = pdf.merge(agrupada, on=["Credor_Chave", "GD"], how="outer").merge(tipos[["Credor_Chave", "GD", "ITEM", "RETENÇÃO"]], on=["Credor_Chave", "GD"], how="left")
    resultado["Credor"] = resultado["Credor"].fillna(resultado["Credor_Base"])
    for coluna in ("Valor_PDF", "Valor_Base", "ITEM", "RETENÇÃO"):
        resultado[coluna] = resultado[coluna].fillna(0.0)
    resultado["Registros_Base"] = resultado["Registros_Base"].fillna(0).astype(int)
    resultado["Diferença"] = resultado["Valor_Base"] - resultado["Valor_PDF"]
    resultado["Situação"] = np.select([resultado["Valor_PDF"].eq(0), resultado["Valor_Base"].eq(0), resultado["Diferença"].abs().le(.005)], ["Somente na Base OB", "Somente no PDF", "Conciliado"], default="Valor divergente")
    resultado["Indício"] = np.where(resultado["RETENÇÃO"] > .005, "Há retenção na base OB", "Verificar lançamento/credor")
    return resultado.sort_values(["Situação", "Credor"]).reset_index(drop=True), base, fontes


def _tabela(df, formatos=None):
    estilo = df.style.format(formatos or {}).set_table_styles([{"selector": "th", "props": [("background-color", "#003b5c"), ("color", "#fff"), ("font-weight", "700")]}])
    if "Situação" in df:
        cores = {"Conciliado": "background-color:#e8f7ee;color:#166534", "Valor divergente": "background-color:#fff7df;color:#92400e", "Somente no PDF": "background-color:#feecec;color:#b42318", "Somente na Base OB": "background-color:#feecec;color:#b42318"}
        estilo = estilo.apply(lambda linha: [cores.get(linha["Situação"], "")] * len(linha), axis=1)
    return estilo


def renderizar():
    st.markdown("### 🔎 Conferência de pagamentos")
    st.caption("Compare o PDF gerado pelo SIAFIM com a Base OB do mesmo dia. INSS é desconsiderado e retenções são consolidadas conforme o PDF.")
    with st.container(border=True):
        c_data, c_tipo, c_pdf = st.columns([.85, 1.05, 2.1], vertical_alignment="bottom")
        with c_data:
            data = st.date_input("Data do pagamento", value=datetime.date.today(), format="DD/MM/YYYY", key="data_conferencia_ob_009717")
        with c_tipo:
            tipo = st.selectbox("Classificação da base OB", ["ITEM", "RETENÇÃO", "TODAS"], key="classificacao_conferencia_ob_009717")
        with c_pdf:
            arquivo = st.file_uploader("PDF do Relatório de Pagamento", type=["pdf"], key="arquivo_conferencia_ob_009717")
        c_comp, c_voltar, _ = st.columns([1.1, .82, 3.03])
        with c_comp:
            executar = st.button("🔎 Comparar pagamentos", type="primary", use_container_width=True)
        with c_voltar:
            voltar = st.button("← Voltar ao relatório", use_container_width=True)
    if voltar:
        st.session_state["mostrar_conferencia_ob_009717"] = False
        st.session_state.pop("resultado_conferencia_ob_009717", None)
        st.rerun()
    if executar:
        if arquivo is None:
            st.warning("Selecione o PDF que será comparado.")
        else:
            try:
                with st.spinner("Lendo o PDF e conciliando com a base de Pagamentos (OB)..."):
                    comparacao, detalhe, fontes = comparar(arquivo.getvalue(), data, tipo)
                st.session_state["resultado_conferencia_ob_009717"] = {"comparacao": comparacao, "detalhe": detalhe, "fontes": fontes, "arquivo": arquivo.name, "data": data, "tipo": tipo}
            except Exception as erro:
                st.session_state.pop("resultado_conferencia_ob_009717", None)
                st.error(f"Não foi possível concluir a conferência: {erro}")
    resultado = st.session_state.get("resultado_conferencia_ob_009717")
    if not resultado:
        return
    comparacao, detalhe = resultado["comparacao"].copy(), resultado["detalhe"].copy()
    divergencias = comparacao[comparacao["Situação"] != "Conciliado"]
    total_pdf, total_base = comparacao["Valor_PDF"].sum(), comparacao["Valor_Base"].sum()
    if divergencias.empty and abs(total_base-total_pdf) <= .005:
        st.success("✅ Pagamentos conciliados: PDF SIAFIM e Base OB batem integralmente.")
    else:
        st.warning(f"⚠️ Foram encontradas {len(divergencias)} divergência(s). Use a aba de detalhes para identificar os registros.")
    for coluna, (titulo, valor, descricao, cor) in zip(st.columns(4), [("TOTAL PDF SIAFIM", _brl(total_pdf), "Valor extraído do PDF", "#005691"), ("TOTAL BASE OB", _brl(total_base), "Mesmo dia, classificação e fonte", "#028090"), ("DIFERENÇA", _brl(total_base-total_pdf), "Base OB menos PDF", "#d62828"), ("LINHAS DIVERGENTES", str(len(divergencias)), "Credor + GD para verificar", "#d97706")]):
        with coluna:
            st.markdown(f"<div class='metric-card'><p style='font-size:11px;font-weight:bold;margin:0'>{titulo}</p><h3 style='color:{cor};margin:5px 0'>{valor}</h3><p style='font-size:11px;margin:0'>{descricao}</p></div>", unsafe_allow_html=True)
    st.caption(f"Arquivo: {resultado['arquivo']} · Data: {resultado['data'].strftime('%d/%m/%Y')} · Classificação: {resultado['tipo']} · Fonte(s) do PDF: {', '.join(resultado['fontes']) or 'não identificada'}")
    colunas = ["Situação", "Credor", "GD", "Valor_PDF", "Valor_Base", "Diferença", "ITEM", "RETENÇÃO", "Registros_Base", "Indício"]
    formatos = {c: _brl for c in ["Valor_PDF", "Valor_Base", "Diferença", "ITEM", "RETENÇÃO"]}
    aba1, aba2, aba3 = st.tabs(["Resumo", "Divergências", "Detalhamento da Base OB"])
    with aba1:
        st.dataframe(_tabela(comparacao[colunas], formatos), use_container_width=True, hide_index=True, height=420)
    with aba2:
        st.dataframe(_tabela(divergencias[colunas], formatos), use_container_width=True, hide_index=True, height=420)
    with aba3:
        chaves = set(zip(divergencias["Credor_Chave"], divergencias["GD"]))
        mostrar = detalhe[detalhe.apply(lambda r: (r["Credor_Chave"], r["GD_Conferencia"]) in chaves, axis=1)].copy()
        if mostrar.empty:
            st.info("Não há detalhes adicionais para exibir.")
        else:
            mostrar["Valor"] = mostrar["Valor_Conferencia"].map(_brl)
            st.dataframe(mostrar[["Data Emissão", "Credor_Exibicao", "GRUPO", "Tipo_Item_Conferencia", "Fonte", "Número", "Valor"]].rename(columns={"Data Emissão":"Data", "Credor_Exibicao":"Credor", "GRUPO":"Grupo", "Tipo_Item_Conferencia":"Classificação", "Número":"OB"}), use_container_width=True, hide_index=True, height=420)