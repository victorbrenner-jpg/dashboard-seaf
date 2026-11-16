"""Acesso à base de Pagamentos (OB) por Ano do Exercício.

Origem dos dados:
- Meses fechados de 2026 (jan a MES_FINAL_BANCO): banco SQLite somente leitura em
  dados/ob_2026.db, gerado por criar_banco_ob_2026.py.
- Demais meses de 2026 (nov e dez) e todo o exercício de 2027: aba BASE da
  planilha Google, publicada como CSV, filtrada pela coluna "Ano".

Regra: se o banco tiver registros do ano pedido, os meses até MES_FINAL_BANCO
vêm dele e os meses seguintes vêm da planilha (nunca os dois para o mesmo mês,
então não há risco de contar em dobro). Sem banco, tudo vem da planilha.
"""
import datetime
import io
import sqlite3
import urllib.request
from pathlib import Path

import pandas as pd

ANOS_OB = (2026, 2027)

# Último mês de cada ano que está congelado no banco (2026: janeiro a outubro).
MES_FINAL_BANCO = {2026: 10}

LINK_BASE_OB = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vTD3b7L6byArEDgkVKOXXlc7RK0M2QKXLov83OydCaks3rDISWYWfgGNi6vG6pwy8t5Ul3Fd2wArhtT/"
    "pub?gid=1786485134&single=true&output=csv"
)

CAMINHO_DB_OB = Path(__file__).resolve().parent.parent / "dados" / "ob_2026.db"
TABELA_DB_OB = "ob_pagamentos"

_ABREV_MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def ordem_meses(ano):
    return [f"{m}/{ano}" for m in _ABREV_MESES]


def mapa_meses(ano):
    """Mapa "01" -> "Jan/<ano>", no formato usado pela coluna Mes_Num."""
    return {f"{i:02d}": f"{m}/{ano}" for i, m in enumerate(_ABREV_MESES, start=1)}


def ano_padrao():
    """Ano corrente se estiver disponível; senão, o primeiro da lista."""
    hoje = datetime.date.today().year
    return hoje if hoje in ANOS_OB else ANOS_OB[0]


def _ler_csv_publicado(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    with urllib.request.urlopen(req) as resposta:
        texto = resposta.read().decode("utf-8")
    return pd.read_csv(io.StringIO(texto))


def _ler_banco(ano):
    """Linhas do ano no banco local, ou None se não houver banco/registros."""
    if not CAMINHO_DB_OB.exists():
        return None
    try:
        con = sqlite3.connect(f"file:{CAMINHO_DB_OB}?mode=ro", uri=True)
    except sqlite3.Error:
        return None
    try:
        df = pd.read_sql_query(
            f'SELECT * FROM "{TABELA_DB_OB}" WHERE "Ano" = ?', con, params=(int(ano),)
        )
    except Exception:
        return None
    finally:
        con.close()
    return df if not df.empty else None


def _garantir_ano(df):
    """Garante a coluna Ano; onde faltar, deriva da Data Emissão (dd/mm/aaaa)."""
    if "Ano" in df.columns:
        ano = pd.to_numeric(df["Ano"], errors="coerce")
    else:
        ano = pd.Series(float("nan"), index=df.index)
    if ano.isna().any() and "Data Emissão" in df.columns:
        datas = pd.to_datetime(df["Data Emissão"], format="mixed", dayfirst=True, errors="coerce")
        ano = ano.fillna(datas.dt.year)
    df["Ano"] = ano
    return df


def _meses(df):
    """Mês (1-12) de cada linha, pela Data Emissão (dd/mm/aaaa)."""
    if "Data Emissão" not in df.columns:
        return pd.Series(float("nan"), index=df.index)
    datas = pd.to_datetime(df["Data Emissão"], format="mixed", dayfirst=True, errors="coerce")
    return datas.dt.month


def _preparar(df):
    df = df.loc[:, ~df.columns.duplicated()].copy()
    df.columns = [str(c).strip() for c in df.columns]
    return _garantir_ano(df)


def carregar_base_ob(ano):
    """Base bruta de OB do Ano do Exercício informado (mesmas colunas da BASE)."""
    ano = int(ano)
    do_banco = _ler_banco(ano)
    planilha = _ler_csv_publicado(LINK_BASE_OB)

    if planilha.empty:
        planilha = pd.DataFrame()
    else:
        planilha = _preparar(planilha)
        planilha = planilha[planilha["Ano"] == ano].copy()

    if do_banco is None:
        return planilha

    do_banco = _preparar(do_banco)
    do_banco = do_banco[_meses(do_banco) <= MES_FINAL_BANCO.get(ano, 12)]
    if planilha.empty:
        return do_banco
    # Da planilha, só o que vem depois dos meses congelados no banco.
    planilha = planilha[_meses(planilha) > MES_FINAL_BANCO.get(ano, 12)]
    return pd.concat([do_banco, planilha], ignore_index=True)
