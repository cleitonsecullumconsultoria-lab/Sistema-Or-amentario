"""
Relatório: Budget × Realizado
Consolida BudgetLinhas vs Realizado por Filial / Conta / Mês e calcula variação.

Saída: exports/budget_vs_real_AAAA-MM-DD.xlsx
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd

# garante importação de db.py na raiz do projeto
sys.path.insert(0, str(Path(__file__).parent.parent))
from db import DB

EXPORTS_DIR = Path(__file__).parent.parent / "exports"
EXPORTS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Extração
# ---------------------------------------------------------------------------

def carregar_dados(db: DB, versao_budget: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    budget = db.budget(versao=versao_budget)
    realizado = db.realizado()
    return budget, realizado


# ---------------------------------------------------------------------------
# Transformação
# ---------------------------------------------------------------------------

def preparar_budget(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza colunas e garante tipos corretos."""
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    df["Valor"] = pd.to_numeric(df.get("Valor", df.get("ValorBudget", 0)), errors="coerce").fillna(0)
    return df[["Filial", "Conta", "Mes", "Ano", "Valor"]].rename(columns={"Valor": "Budget"})


def preparar_realizado(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    df["Valor"] = pd.to_numeric(df.get("Valor", df.get("ValorReal", 0)), errors="coerce").fillna(0)
    return df[["Filial", "Conta", "Mes", "Ano", "Valor"]].rename(columns={"Valor": "Realizado"})


def consolidar(budget: pd.DataFrame, realizado: pd.DataFrame) -> pd.DataFrame:
    chaves = ["Filial", "Conta", "Mes", "Ano"]

    bud = preparar_budget(budget).groupby(chaves, as_index=False)["Budget"].sum()
    real = preparar_realizado(realizado).groupby(chaves, as_index=False)["Realizado"].sum()

    df = pd.merge(bud, real, on=chaves, how="outer").fillna(0)
    df["Variacao"] = df["Realizado"] - df["Budget"]
    df["Variacao_%"] = df.apply(
        lambda r: (r["Variacao"] / r["Budget"] * 100) if r["Budget"] != 0 else None,
        axis=1,
    )
    df = df.sort_values(["Ano", "Mes", "Filial", "Conta"])
    return df


def resumo_por_filial(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("Filial", as_index=False).agg(
        Budget=("Budget", "sum"),
        Realizado=("Realizado", "sum"),
        Variacao=("Variacao", "sum"),
    )
    g["Variacao_%"] = g.apply(
        lambda r: (r["Variacao"] / r["Budget"] * 100) if r["Budget"] != 0 else None,
        axis=1,
    )
    return g


def resumo_por_mes(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["Ano", "Mes"], as_index=False).agg(
        Budget=("Budget", "sum"),
        Realizado=("Realizado", "sum"),
        Variacao=("Variacao", "sum"),
    )
    g["Variacao_%"] = g.apply(
        lambda r: (r["Variacao"] / r["Budget"] * 100) if r["Budget"] != 0 else None,
        axis=1,
    )
    return g.sort_values(["Ano", "Mes"])


# ---------------------------------------------------------------------------
# Carga — geração do Excel de saída
# ---------------------------------------------------------------------------

def formatar_excel(writer: pd.ExcelWriter, df_detalhe: pd.DataFrame,
                   df_filial: pd.DataFrame, df_mes: pd.DataFrame) -> None:
    """Escreve as 3 abas e aplica formatação básica."""
    wb = writer.book
    moeda_fmt = "#,##0.00"
    pct_fmt = "0.00%"

    sheets: list[tuple[str, pd.DataFrame]] = [
        ("Detalhe", df_detalhe),
        ("Por Filial", df_filial),
        ("Por Mês", df_mes),
    ]

    for nome, df in sheets:
        df.to_excel(writer, sheet_name=nome, index=False, startrow=1)
        ws = writer.sheets[nome]

        # cabeçalho destacado
        header_fmt = wb.add_format({
            "bold": True, "bg_color": "#1F3864", "font_color": "white",
            "border": 1, "align": "center", "valign": "vcenter",
        })
        for col_num, value in enumerate(df.columns):
            ws.write(1, col_num, value, header_fmt)

        # largura automática
        for i, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
            ws.set_column(i, i, min(max_len, 30))

        # formatação numérica para colunas de valor
        valor_fmt = wb.add_format({"num_format": moeda_fmt})
        pct_col_fmt = wb.add_format({"num_format": "0.00\"%\""})

        for i, col in enumerate(df.columns):
            if col in ("Budget", "Realizado", "Variacao"):
                ws.set_column(i, i, 16, valor_fmt)
            elif col == "Variacao_%":
                ws.set_column(i, i, 12, pct_col_fmt)

        # título no topo
        titulo_fmt = wb.add_format({"bold": True, "font_size": 13})
        ws.write(0, 0, f"ROV — Budget vs Realizado | {nome}", titulo_fmt)

        ws.freeze_panes(2, 0)


def exportar(df_detalhe: pd.DataFrame, df_filial: pd.DataFrame,
             df_mes: pd.DataFrame) -> Path:
    nome_arquivo = EXPORTS_DIR / f"budget_vs_real_{date.today()}.xlsx"
    with pd.ExcelWriter(nome_arquivo, engine="xlsxwriter") as writer:
        formatar_excel(writer, df_detalhe, df_filial, df_mes)
    return nome_arquivo


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def main(versao_budget: str | None = None) -> None:
    db = DB()
    print(f"Fonte de dados: {db.caminho}")

    print("Carregando Budget e Realizado...")
    budget_raw, realizado_raw = carregar_dados(db, versao_budget)

    print("Consolidando...")
    detalhe = consolidar(budget_raw, realizado_raw)
    por_filial = resumo_por_filial(detalhe)
    por_mes = resumo_por_mes(detalhe)

    saida = exportar(detalhe, por_filial, por_mes)
    print(f"Relatório gerado: {saida}")

    # preview no terminal
    print("\n--- Resumo por Filial ---")
    print(por_filial.to_string(index=False))
    print("\n--- Resumo por Mês ---")
    print(por_mes.to_string(index=False))


if __name__ == "__main__":
    # uso: python relatorio_budget_vs_real.py [versao]
    versao = sys.argv[1] if len(sys.argv) > 1 else None
    main(versao_budget=versao)
