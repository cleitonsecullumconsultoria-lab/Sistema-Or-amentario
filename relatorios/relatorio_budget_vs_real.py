"""
Relatório: Budget × Realizado
Faz JOIN nas tabelas relacionais, consolida por Filial/Conta/Mês e calcula variação.

Uso:
    python relatorios/relatorio_budget_vs_real.py
    python relatorios/relatorio_budget_vs_real.py --versao 3 --filiais CBA AGB --ano 2024
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import DB

SAIDA_DIR = Path(__file__).parent / "saida"
SAIDA_DIR.mkdir(exist_ok=True)

MESES = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}


# ---------------------------------------------------------------------------
# Extração e enriquecimento
# ---------------------------------------------------------------------------

def enriquecer_budget(db: DB, versao_id: int | None = None) -> pd.DataFrame:
    """BudgetLinhas + joins para nomes legíveis."""
    bud = db.tabela("BudgetLinhas")
    versoes = db.tabela("BudgetVersoes")[["id", "ano", "cenario", "status"]].rename(
        columns={"id": "versao_id", "cenario": "versao_cenario", "status": "versao_status"}
    )
    filiais = db.tabela("Filiais")[["id", "codigo", "nome"]].rename(
        columns={"id": "filial_id", "codigo": "filial_codigo", "nome": "filial_nome"}
    )
    contas = db.tabela("PlanoContas")[["id", "codigo", "nome", "categoria", "tipo"]].rename(
        columns={"id": "conta_id", "codigo": "conta_codigo", "nome": "conta_nome"}
    )
    ccus = db.tabela("CentrosCusto")[["id", "codigo", "nome", "tipo"]].rename(
        columns={"id": "ccu_id", "codigo": "ccu_codigo", "nome": "ccu_nome", "tipo": "ccu_tipo"}
    )

    df = (
        bud
        .merge(versoes, on="versao_id", how="left")
        .merge(filiais, on="filial_id", how="left")
        .merge(contas, on="conta_id", how="left")
        .merge(ccus, on="ccu_id", how="left")
    )
    if versao_id:
        df = df[df["versao_id"] == versao_id]

    df = df.rename(columns={"valor": "Budget"})
    df["Budget"] = pd.to_numeric(df["Budget"], errors="coerce").fillna(0)
    return df


def enriquecer_realizado(db: DB, ano: int | None = None) -> pd.DataFrame:
    """Realizado + joins para nomes legíveis."""
    real = db.tabela("Realizado")
    filiais = db.tabela("Filiais")[["id", "codigo", "nome"]].rename(
        columns={"id": "filial_id", "codigo": "filial_codigo", "nome": "filial_nome"}
    )
    contas = db.tabela("PlanoContas")[["id", "codigo", "nome", "categoria", "tipo"]].rename(
        columns={"id": "conta_id", "codigo": "conta_codigo", "nome": "conta_nome"}
    )
    ccus = db.tabela("CentrosCusto")[["id", "codigo", "nome", "tipo"]].rename(
        columns={"id": "ccu_id", "codigo": "ccu_codigo", "nome": "ccu_nome", "tipo": "ccu_tipo"}
    )

    df = (
        real
        .merge(filiais, on="filial_id", how="left")
        .merge(contas, on="conta_id", how="left")
        .merge(ccus, on="ccu_id", how="left")
    )
    if ano:
        df = df[df["ano"] == ano]

    df = df.rename(columns={"valor": "Realizado"})
    df["Realizado"] = pd.to_numeric(df["Realizado"], errors="coerce").fillna(0)
    return df


# ---------------------------------------------------------------------------
# Consolidação
# ---------------------------------------------------------------------------

CHAVES = ["filial_codigo", "filial_nome", "conta_codigo", "conta_nome",
          "categoria", "ccu_codigo", "ccu_nome", "ano", "mes"]


def consolidar(bud: pd.DataFrame, real: pd.DataFrame,
               filiais_filtro: list[str] | None = None) -> pd.DataFrame:
    """Merge Budget × Realizado nas chaves comuns."""
    bud_g = (
        bud[CHAVES + ["Budget"]]
        .groupby(CHAVES, as_index=False)["Budget"].sum()
    )
    real_g = (
        real[CHAVES + ["Realizado"]]
        .groupby(CHAVES, as_index=False)["Realizado"].sum()
    )

    df = pd.merge(bud_g, real_g, on=CHAVES, how="outer").fillna(0)

    if filiais_filtro:
        filtro_upper = [f.upper() for f in filiais_filtro]
        df = df[df["filial_codigo"].str.upper().isin(filtro_upper)]

    df["Variacao_R$"] = df["Realizado"] - df["Budget"]
    df["Variacao_%"] = df.apply(
        lambda r: round(r["Variacao_R$"] / r["Budget"] * 100, 2) if r["Budget"] != 0 else None,
        axis=1,
    )
    df["Mes_Nome"] = df["mes"].map(MESES)
    df = df.sort_values(["filial_codigo", "ano", "mes", "conta_codigo"])
    return df


def resumo_filial(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["filial_codigo", "filial_nome"], as_index=False).agg(
        Budget=("Budget", "sum"),
        Realizado=("Realizado", "sum"),
        Variacao_RS=("Variacao_R$", "sum"),
    )
    g["Variacao_%"] = g.apply(
        lambda r: round(r["Variacao_RS"] / r["Budget"] * 100, 2) if r["Budget"] != 0 else None,
        axis=1,
    )
    return g.rename(columns={"Variacao_RS": "Variacao_R$"})


def resumo_mes(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["ano", "mes", "Mes_Nome"], as_index=False).agg(
        Budget=("Budget", "sum"),
        Realizado=("Realizado", "sum"),
        Variacao_RS=("Variacao_R$", "sum"),
    )
    g["Variacao_%"] = g.apply(
        lambda r: round(r["Variacao_RS"] / r["Budget"] * 100, 2) if r["Budget"] != 0 else None,
        axis=1,
    )
    return g.rename(columns={"Variacao_RS": "Variacao_R$"}).sort_values(["ano", "mes"])


def pivot_mensal(df: pd.DataFrame) -> pd.DataFrame:
    """Tabela pivotada: linhas = conta, colunas = Jan…Dez Budget/Real/Var."""
    grp = df.groupby(
        ["filial_codigo", "conta_codigo", "conta_nome", "categoria", "mes"],
        as_index=False
    ).agg(Budget=("Budget", "sum"), Realizado=("Realizado", "sum"))

    bud_piv = grp.pivot_table(
        index=["filial_codigo", "conta_codigo", "conta_nome", "categoria"],
        columns="mes", values="Budget", fill_value=0
    ).rename(columns=lambda m: f"{MESES[m]}_Bud")

    real_piv = grp.pivot_table(
        index=["filial_codigo", "conta_codigo", "conta_nome", "categoria"],
        columns="mes", values="Realizado", fill_value=0
    ).rename(columns=lambda m: f"{MESES[m]}_Real")

    combined = bud_piv.join(real_piv, how="outer").fillna(0).reset_index()

    # intercala colunas por mês
    meses_presentes = sorted(grp["mes"].unique())
    cols_base = ["filial_codigo", "conta_codigo", "conta_nome", "categoria"]
    cols_mes = []
    for m in meses_presentes:
        b_col = f"{MESES[m]}_Bud"
        r_col = f"{MESES[m]}_Real"
        if b_col in combined.columns:
            cols_mes.append(b_col)
        if r_col in combined.columns:
            cols_mes.append(r_col)

    return combined[cols_base + cols_mes]


# ---------------------------------------------------------------------------
# Exportação Excel
# ---------------------------------------------------------------------------

COR_HEADER = "#1F3864"
COR_SUBTOTAL = "#D6E4F0"
COR_POSITIVO = "#C6EFCE"
COR_NEGATIVO = "#FFC7CE"


def _fmt_moeda(wb):
    return wb.add_format({"num_format": "R$ #,##0.00", "align": "right"})


def _fmt_pct(wb):
    return wb.add_format({"num_format": '0.00"%"', "align": "right"})


def _fmt_header(wb):
    return wb.add_format({
        "bold": True, "bg_color": COR_HEADER, "font_color": "white",
        "border": 1, "align": "center", "valign": "vcenter", "text_wrap": True,
    })


def _fmt_titulo(wb):
    return wb.add_format({"bold": True, "font_size": 14, "font_color": COR_HEADER})


def _escrever_aba(writer, nome_aba, df, titulo, colunas_valor=None, colunas_pct=None):
    df.to_excel(writer, sheet_name=nome_aba, index=False, startrow=2)
    ws = writer.sheets[nome_aba]
    wb = writer.book

    ws.write(0, 0, titulo, _fmt_titulo(wb))
    ws.write(1, 0, f"Gerado em {date.today()}", wb.add_format({"italic": True, "font_size": 9}))

    hdr = _fmt_header(wb)
    for col_num, col_name in enumerate(df.columns):
        ws.write(2, col_num, col_name, hdr)

    moeda = _fmt_moeda(wb)
    pct = _fmt_pct(wb)
    colunas_valor = colunas_valor or []
    colunas_pct = colunas_pct or []

    for i, col in enumerate(df.columns):
        max_len = max(df[col].astype(str).str.len().max() if len(df) else 0, len(col)) + 3
        if col in colunas_valor:
            ws.set_column(i, i, max(max_len, 16), moeda)
        elif col in colunas_pct:
            ws.set_column(i, i, 12, pct)
        else:
            ws.set_column(i, i, min(max_len, 35))

    ws.freeze_panes(3, 0)


def exportar(detalhe, r_filial, r_mes, pivot, tag_filiais: str) -> Path:
    nome = SAIDA_DIR / f"budget_vs_real_{tag_filiais}_{date.today()}.xlsx"

    colunas_valor = ["Budget", "Realizado", "Variacao_R$", "Variacao_RS"]
    colunas_pct = ["Variacao_%"]

    with pd.ExcelWriter(nome, engine="xlsxwriter") as writer:
        _escrever_aba(
            writer, "Detalhe", detalhe,
            "ROV — Budget vs Realizado | Detalhe por Conta/Mês",
            colunas_valor, colunas_pct,
        )
        _escrever_aba(
            writer, "Por Filial", r_filial,
            "ROV — Budget vs Realizado | Resumo por Filial",
            colunas_valor, colunas_pct,
        )
        _escrever_aba(
            writer, "Por Mês", r_mes,
            "ROV — Budget vs Realizado | Resumo por Mês",
            colunas_valor, colunas_pct,
        )
        _escrever_aba(
            writer, "Pivot Mensal", pivot,
            "ROV — Budget vs Realizado | Pivot Jan→Dez",
        )

    return nome


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Budget vs Realizado — ROV")
    p.add_argument("--versao", type=int, default=None, help="versao_id do budget (padrão: maior aprovado)")
    p.add_argument("--ano", type=int, default=None, help="ano do realizado (padrão: todos)")
    p.add_argument("--filiais", nargs="+", default=None,
                   help="códigos de filiais, ex: CBA AGB (padrão: todas)")
    return p.parse_args()


def main():
    args = parse_args()
    db = DB()
    print(f"Fonte: {db.caminho.name}")

    # versão padrão: maior versao_id com status 'aprovado'
    versao_id = args.versao
    if not versao_id:
        versoes = db.tabela("BudgetVersoes")
        aprov = versoes[versoes["status"] == "aprovado"]
        versao_id = int(aprov["id"].max()) if not aprov.empty else None

    print(f"Versão de budget: {versao_id}  |  Ano realizado: {args.ano or 'todos'}  |  Filiais: {args.filiais or 'todas'}")

    bud = enriquecer_budget(db, versao_id)
    real = enriquecer_realizado(db, args.ano)

    detalhe = consolidar(bud, real, filiais_filtro=args.filiais)

    if detalhe.empty:
        print("Nenhum dado encontrado para os filtros informados.")
        return

    r_filial = resumo_filial(detalhe)
    r_mes = resumo_mes(detalhe)
    piv = pivot_mensal(detalhe)

    tag = "_".join(args.filiais) if args.filiais else "todas"
    saida = exportar(detalhe, r_filial, r_mes, piv, tag)
    print(f"\nRelatório gerado: {saida}")

    print("\n--- Resumo por Filial ---")
    print(r_filial.to_string(index=False))
    print("\n--- Resumo por Mês ---")
    print(r_mes.to_string(index=False))


if __name__ == "__main__":
    main()
