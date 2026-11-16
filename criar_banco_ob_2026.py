"""Gera dados/ob_2026.db com os pagamentos de janeiro a outubro de 2026 da aba BASE.

Uso (PowerShell, na pasta do repositório):
    python criar_banco_ob_2026.py                       # baixa a BASE publicada
    python criar_banco_ob_2026.py caminho\\BASE.csv      # ou usa um CSV baixado

O corte (MES_FINAL_BANCO em modulos/ob_base.py) define o último mês congelado.
Novembro e dezembro continuam vindo da planilha. O banco é somente leitura para
o painel; para regerar, basta rodar de novo (o arquivo é recriado).
"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd

from modulos import ob_base

ANO = 2026
MES_FINAL = ob_base.MES_FINAL_BANCO[ANO]
SAIDA = ob_base.CAMINHO_DB_OB


def main():
    if len(sys.argv) > 1:
        df = pd.read_csv(sys.argv[1], dtype=str, keep_default_na=False)
    else:
        df = pd.read_csv(ob_base.LINK_BASE_OB, dtype=str, keep_default_na=False)

    df.columns = [str(c).strip() for c in df.columns]
    df = ob_base._garantir_ano(df)
    df = df[df["Ano"] == ANO].copy()
    df = df[ob_base._meses(df) <= MES_FINAL].copy()
    if df.empty:
        sys.exit(f"Nenhum registro de {ANO} (jan a mês {MES_FINAL}) encontrado. Banco não gerado.")
    df["Ano"] = df["Ano"].astype(int)

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    if SAIDA.exists():
        SAIDA.unlink()

    con = sqlite3.connect(SAIDA)
    df.to_sql(ob_base.TABELA_DB_OB, con, index=False)
    con.execute(f'CREATE INDEX idx_ob_ano ON "{ob_base.TABELA_DB_OB}" ("Ano")')
    con.commit()
    con.close()

    def _numero(texto):
        texto = str(texto).replace("R$", "").replace(" ", "")
        if "," in texto:  # padrão brasileiro: 1.234,56
            texto = texto.replace(".", "").replace(",", ".")
        return texto

    valores = df["Valor"].map(_numero)
    total = pd.to_numeric(valores, errors="coerce").sum()
    print(f"Banco gerado: {SAIDA}")
    print(f"Registros de {ANO} (jan a mês {MES_FINAL}): {len(df)} | total (Valor): R$ {total:,.2f}")
    por_mes = df.assign(_m=ob_base._meses(df).astype(int), _v=df["Valor"].map(_numero)).assign(
        _v=lambda d: pd.to_numeric(d["_v"], errors="coerce")).groupby("_m")["_v"].agg(["count", "sum"])
    for mes, linha in por_mes.iterrows():
        print(f"  {int(mes):02d}/{ANO}: {int(linha['count'])} registros | R$ {linha['sum']:,.2f}")
    print("Compare esses números com a BASE antes de limpar a planilha.")


if __name__ == "__main__":
    main()
