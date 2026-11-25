"""Tabela de credores expansível (tela Pagamentos / Liquidações NL).

Recebe o df_filtrado que o app já monta (colunas NL_Numero, NE_Chave,
Data_Emissao_Exibicao, Credor_Tratado, Valor_Retido_Limpo, Valor_Total_Limpo e
Natureza_NL) e renderiza o layout da prévia UI/UX: credor expansível, chips
CORRENTE / RP / RPNP / DEA e filtros por natureza.

A coluna Natureza_NL é criada em carregar_dados_integrados() pela função
classificar_natureza_nl(), usando o Elemento da despesa que vem da base do
QlikView (cruzamento pela NE).
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

TEMPLATE = Path(__file__).with_name("tabela_credores_template.html")

# Elemento de despesa que identifica Despesas de Exercícios Anteriores
ELEMENTO_DEA = 92


def codigo_elemento(texto) -> int | None:
    """'92-DESPESAS DE EXERCÍCIOS ANTERIORES' -> 92 ; '04-CONTRATAÇÃO...' -> 4"""
    m = re.match(r"\s*(\d+)", "" if pd.isna(texto) else str(texto))
    return int(m.group(1)) if m else None


def _sem_acento_maiusculo(valor) -> str:
    texto = unicodedata.normalize("NFKD", "" if pd.isna(valor) else str(valor))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto.upper()).strip()


def classificar_natureza_nl(ne, elemento, ano_emissao=None, texto_status="") -> str:
    """Natureza da NL a partir da NE e do Elemento da despesa (QlikView).

    Regra (espelha a da tela Pagamentos OB):
      - sem elemento (NE não achada no QlikView) ....... SEM_CLASSE
      - elemento 92 .................................... DEA
      - NE de exercício anterior ao da emissão da NL ... RP
          (e RPNP se o status/tipo da NL indicar "não processado")
      - demais ......................................... CORRENTE

    AJUSTAR AQUI se a regra de RP/RPNP da planilha for outra.
    """
    if elemento is None:
        return "SEM_CLASSE"
    if elemento == ELEMENTO_DEA:
        return "DEA"

    m = re.match(r"\s*(\d{4})NE", "" if pd.isna(ne) else str(ne).upper())
    ano_ne = int(m.group(1)) if m else None
    if ano_ne and ano_emissao and ano_ne < ano_emissao:
        if re.search(r"RPNP|RESTOS? NAO PROCESSAD|NAO PROCESSAD", _sem_acento_maiusculo(texto_status)):
            return "RPNP"
        return "RP"
    return "CORRENTE"


def _brl(v: float) -> str:
    s = f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def montar_credores(df: pd.DataFrame) -> list[dict]:
    """Agrupa o df_filtrado por credor -> lista de dicts consumida pelo template."""
    if df.empty:
        return []

    nat = df["Natureza_NL"] if "Natureza_NL" in df.columns else "SEM_CLASSE"
    base = df.assign(natureza_tmp=nat)

    sub = (
        base.groupby(
            ["Credor_Tratado", "NL_Numero", "NE_Chave", "Data_Emissao_Exibicao", "natureza_tmp"],
            as_index=False,
        )
        .agg({"Valor_Retido_Limpo": "sum", "Valor_Total_Limpo": "sum"})
        .sort_values("NL_Numero")
    )
    totais = (
        base.groupby("Credor_Tratado")[["Valor_Retido_Limpo", "Valor_Total_Limpo"]]
        .sum()
        .sort_values("Valor_Total_Limpo", ascending=False)
    )

    credores = []
    for i, (credor, tot) in enumerate(totais.iterrows(), start=1):
        itens = sub[sub["Credor_Tratado"] == credor]
        credores.append({
            "id": i,
            "name": str(credor),
            "valRet": _brl(tot["Valor_Retido_Limpo"]),
            "valTotal": _brl(tot["Valor_Total_Limpo"]),
            "expanded": False,
            "items": [
                {
                    "nl": str(r.NL_Numero),
                    "ne": str(r.NE_Chave),
                    "emissao": str(r.Data_Emissao_Exibicao),
                    "tipo": str(r.natureza_tmp),
                    "ret": _brl(r.Valor_Retido_Limpo),
                    "total": _brl(r.Valor_Total_Limpo),
                }
                for r in itens.itertuples(index=False)
            ],
        })
    return credores


def renderizar_html(credores: list[dict]) -> str:
    dados = json.dumps(credores, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.read_text(encoding="utf-8").replace("__DADOS_JSON__", dados)


def exibir_tabela_credores(df_filtrado: pd.DataFrame, altura: int = 820) -> None:
    import streamlit.components.v1 as components

    components.html(renderizar_html(montar_credores(df_filtrado)), height=altura, scrolling=True)
