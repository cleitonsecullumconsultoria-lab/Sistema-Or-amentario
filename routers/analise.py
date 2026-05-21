from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import DB
from tmpl import templates

router = APIRouter(prefix="/analise", tags=["analise"])

MESES_NOME = ["", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
              "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def _fmt_mil(v) -> str:
    try:
        return f"{float(v)/1000:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"


def _fmt_pct(v) -> str:
    try:
        return f"{float(v):.1f}%"
    except Exception:
        return "—"


@router.get("/bvsr")
async def bvsr(request: Request, ano: int = 2024, mes: int | None = None):
    db = DB()
    versoes = db.tabela("BudgetVersoes")
    bud_df = db.tabela("BudgetLinhas")
    real_df = db.tabela("Realizado")
    filiais_df = db.tabela("Filiais")
    contas_df = db.tabela("PlanoContas")

    # Versão aprovada do ano
    aprov = versoes[(versoes["status"] == "aprovado") & (versoes["ano"] == ano)]
    versao_id = int(aprov["id"].max()) if not aprov.empty else int(versoes["id"].max())

    bud = bud_df[bud_df["versao_id"] == versao_id].copy()
    real = real_df[real_df["ano"] == ano].copy()

    if mes:
        bud = bud[bud["mes"] == mes]
        real = real[real["mes"] == mes]

    bud_g = bud.groupby(["filial_id", "conta_id"])["valor"].sum().reset_index().rename(columns={"valor": "Budget"})
    real_g = real.groupby(["filial_id", "conta_id"])["valor"].sum().reset_index().rename(columns={"valor": "Realizado"})

    merged = pd.merge(bud_g, real_g, on=["filial_id", "conta_id"], how="outer").fillna(0)
    merged["var_rs"] = merged["Realizado"] - merged["Budget"]
    merged["var_pct"] = merged.apply(
        lambda r: round(r["var_rs"] / r["Budget"] * 100, 1) if r["Budget"] != 0 else None, axis=1
    )

    filiais_map = {r["id"]: r.to_dict() for _, r in filiais_df.iterrows()}
    contas_map = {r["id"]: r.to_dict() for _, r in contas_df.iterrows()}

    # Por filial
    por_filial_raw = merged.groupby("filial_id").agg(
        Budget=("Budget", "sum"), Realizado=("Realizado", "sum"), var_rs=("var_rs", "sum")
    ).reset_index()

    por_filial = []
    for _, r in por_filial_raw.iterrows():
        f = filiais_map.get(r["filial_id"], {})
        vp = round(r["var_rs"] / r["Budget"] * 100, 1) if r["Budget"] != 0 else None
        ating = f"{(r['Realizado']/r['Budget']*100):.1f}%" if r["Budget"] != 0 else "—"
        por_filial.append({
            "filial_codigo": f.get("codigo", "?") if f else "?",
            "filial_nome": f.get("nome", "?") if f else "?",
            "budget_fmt": _fmt_mil(r["Budget"]),
            "real_fmt": _fmt_mil(r["Realizado"]),
            "var_rs": float(r["var_rs"]),
            "var_rs_fmt": _fmt_mil(abs(r["var_rs"])),
            "var_pct": vp,
            "ating_fmt": ating,
        })
    por_filial.sort(key=lambda x: x["filial_codigo"])

    # Totais
    tot_b = merged["Budget"].sum()
    tot_r = merged["Realizado"].sum()
    tot_v = tot_r - tot_b
    tot_vp = round(tot_v / tot_b * 100, 1) if tot_b != 0 else None
    totais = {
        "budget_fmt": _fmt_mil(tot_b),
        "real_fmt": _fmt_mil(tot_r),
        "var_rs": float(tot_v),
        "var_rs_fmt": _fmt_mil(abs(tot_v)),
        "var_pct": tot_vp,
        "ating_fmt": f"{(tot_r/tot_b*100):.1f}%" if tot_b != 0 else "—",
    }

    # KPIs
    melhor = max(por_filial, key=lambda x: (x["var_pct"] or -999), default={"filial_codigo": "—", "var_pct": None})
    kpis = {
        "budget_fmt": _fmt_mil(tot_b),
        "real_fmt": _fmt_mil(tot_r),
        "var_pct": tot_vp or 0,
        "var_fmt": _fmt_pct(abs(tot_vp)) if tot_vp else "—",
        "ating_fmt": f"{(tot_r/tot_b*100):.1f}%" if tot_b != 0 else "—",
        "n_filiais": len(por_filial),
        "melhor_filial": melhor["filial_codigo"],
        "melhor_var": f"+{melhor['var_pct']:.1f}%" if melhor.get("var_pct") is not None and melhor["var_pct"] > 0 else "—",
    }

    # Detalhe por conta
    detalhe = []
    for _, r in merged.iterrows():
        f = filiais_map.get(r["filial_id"], {})
        c = contas_map.get(r["conta_id"], {})
        detalhe.append({
            "filial_codigo": f.get("codigo", "?") if f else "?",
            "conta_codigo": c.get("codigo", "?") if c else "?",
            "conta_nome": c.get("nome", "?") if c else "?",
            "budget_fmt": _fmt_mil(r["Budget"]),
            "real_fmt": _fmt_mil(r["Realizado"]),
            "var_rs": float(r["var_rs"]),
            "var_rs_fmt": _fmt_mil(abs(r["var_rs"])),
            "var_pct": float(r["var_pct"]) if r["var_pct"] is not None else None,
        })
    detalhe.sort(key=lambda x: abs(x["var_rs"]), reverse=True)

    return templates.TemplateResponse(request, "analise/bvsr.html", {
        "por_filial": por_filial,
        "totais": totais,
        "detalhe": detalhe,
        "kpis": kpis,
        "ano": ano,
        "mes": mes,
        "mes_nome": MESES_NOME[mes] if mes else "Acum.",
        "anos_disponiveis": [2024, 2023],
        "active_page": "bvsr",
    })


@router.get("/dre")
async def dre(request: Request, ano: int = 2024, mes: int = 12, filial_id: int | None = None):
    db = DB()
    filiais_df = db.tabela("Filiais")
    real_df = db.tabela("Realizado")
    versoes = db.tabela("BudgetVersoes")
    bud_df = db.tabela("BudgetLinhas")
    contas_df = db.tabela("PlanoContas")

    filial_nome = "Grupo"
    if filial_id:
        f = filiais_df[filiais_df["id"] == filial_id]
        filial_nome = f.iloc[0]["nome"] if not f.empty else "Grupo"

    real = real_df[(real_df["ano"] == ano) & (real_df["mes"] == mes)]
    if filial_id:
        real = real[real["filial_id"] == filial_id]

    aprov = versoes[(versoes["status"] == "aprovado") & (versoes["ano"] == ano)]
    versao_id = int(aprov["id"].max()) if not aprov.empty else None

    if versao_id is not None:
        bud = bud_df[(bud_df["versao_id"] == versao_id) & (bud_df["mes"] == mes)]
        if filial_id:
            bud = bud[bud["filial_id"] == filial_id]
    else:
        bud = pd.DataFrame()

    # Agrega por conta
    real_g = real.groupby("conta_id")["valor"].sum()
    bud_g = bud.groupby("conta_id")["valor"].sum() if not bud.empty else pd.Series(dtype=float)

    def soma_cat(cat):
        contas_cat = contas_df[contas_df["categoria"] == cat]["id"].tolist()
        r = real_g[real_g.index.isin(contas_cat)].sum()
        b = bud_g[bud_g.index.isin(contas_cat)].sum() if not bud_g.empty else 0
        return float(r), float(b)

    rec_r, rec_b = soma_cat("receita")
    cus_r, cus_b = soma_cat("custo")
    des_r, des_b = soma_cat("despesa")

    lucro_r = rec_r - cus_r
    lucro_b = rec_b - cus_b
    ebitda_r = lucro_r - des_r
    ebitda_b = lucro_b - des_b

    def vp(r, b):
        if b == 0:
            return None
        return round((r - b) / b * 100, 1)

    linhas = [
        {"label": "(+) Receita Bruta", "real_fmt": _fmt_mil(rec_r), "bud_fmt": _fmt_mil(rec_b), "var_pct": vp(rec_r, rec_b), "classe": "", "indent": ""},
        {"label": "(-) Custo dos produtos/serviços", "real_fmt": _fmt_mil(-cus_r), "bud_fmt": _fmt_mil(-cus_b), "var_pct": vp(-cus_r, -cus_b), "classe": "", "indent": "indent"},
        {"label": "(=) Lucro Bruto", "real_fmt": _fmt_mil(lucro_r), "bud_fmt": _fmt_mil(lucro_b), "var_pct": vp(lucro_r, lucro_b), "classe": "dre-result", "indent": ""},
        {"label": "(-) Despesas operacionais", "real_fmt": _fmt_mil(-des_r), "bud_fmt": _fmt_mil(-des_b), "var_pct": vp(-des_r, -des_b), "classe": "", "indent": "indent"},
        {"label": "(=) EBITDA", "real_fmt": _fmt_mil(ebitda_r), "bud_fmt": _fmt_mil(ebitda_b), "var_pct": vp(ebitda_r, ebitda_b), "classe": "dre-ebitda", "indent": ""},
    ]

    margem_bruta = round(lucro_r / rec_r * 100, 1) if rec_r != 0 else 0
    margem_ebitda = round(ebitda_r / rec_r * 100, 1) if rec_r != 0 else 0

    dre_data = {
        "linhas": linhas,
        "receita_bruta_fmt": _fmt_mil(rec_r),
        "lucro_bruto_fmt": _fmt_mil(lucro_r),
        "ebitda_fmt": _fmt_mil(ebitda_r),
        "resultado": float(ebitda_r),
        "resultado_fmt": _fmt_mil(ebitda_r),
        "margem_bruta_fmt": _fmt_pct(margem_bruta),
        "margem_ebitda_fmt": _fmt_pct(margem_ebitda),
        "var_rec": vp(rec_r, rec_b) or 0,
    }

    return templates.TemplateResponse(request, "analise/dre.html", {
        "dre": dre_data,
        "filiais": filiais_df[filiais_df["ativo"] == 1].to_dict("records"),
        "filial_id": filial_id,
        "filial_nome": filial_nome,
        "ano": ano,
        "mes": mes,
        "mes_nome": MESES_NOME[mes],
        "anos_disponiveis": [2024, 2023],
        "active_page": "dre",
    })


@router.get("/forecast")
async def forecast(request: Request, ano: int = 2024):
    db = DB()
    filiais_df = db.tabela("Filiais")
    real_df = db.tabela("Realizado")
    versoes = db.tabela("BudgetVersoes")
    bud_df = db.tabela("BudgetLinhas")

    real_ano = real_df[real_df["ano"] == ano]
    meses_com_real = sorted(real_ano["mes"].unique())
    n_meses = len(meses_com_real)
    ate_mes = MESES_NOME[max(meses_com_real)] if meses_com_real else "—"

    aprov = versoes[(versoes["status"] == "aprovado") & (versoes["ano"] == ano)]
    versao_id = int(aprov["id"].max()) if not aprov.empty else None

    bud = bud_df[bud_df["versao_id"] == versao_id] if versao_id else pd.DataFrame()

    filiais = filiais_df[filiais_df["ativo"] == 1].to_dict("records")
    por_filial = []
    tot_bud = tot_real = 0

    for f in filiais:
        fid = f["id"]
        b = float(bud[bud["filial_id"] == fid]["valor"].sum()) if not bud.empty else 0
        r = float(real_ano[real_ano["filial_id"] == fid]["valor"].sum())
        media = r / n_meses if n_meses > 0 else 0
        proj = media * 12
        desvio_rs = proj - b
        desvio_pct = round(desvio_rs / b * 100, 1) if b != 0 else 0
        tot_bud += b
        tot_real += r
        por_filial.append({
            "filial_codigo": f["codigo"],
            "filial_nome": f["nome"],
            "budget_fmt": _fmt_mil(b),
            "real_fmt": _fmt_mil(r),
            "media_fmt": _fmt_mil(media),
            "projecao_fmt": _fmt_mil(proj),
            "desvio_rs": desvio_rs,
            "desvio_rs_fmt": _fmt_mil(abs(desvio_rs)),
            "desvio_pct": desvio_pct,
        })

    tot_media = tot_real / n_meses if n_meses > 0 else 0
    tot_proj = tot_media * 12
    tot_desvio = tot_proj - tot_bud
    tot_pct = round(tot_desvio / tot_bud * 100, 1) if tot_bud != 0 else 0

    totais = {
        "budget_fmt": _fmt_mil(tot_bud),
        "real_fmt": _fmt_mil(tot_real),
        "media_fmt": _fmt_mil(tot_media),
        "projecao_fmt": _fmt_mil(tot_proj),
        "desvio_rs": tot_desvio,
        "desvio_rs_fmt": _fmt_mil(abs(tot_desvio)),
        "desvio_pct": tot_pct,
    }

    kpis = {
        "budget_fmt": _fmt_mil(tot_bud),
        "real_fmt": _fmt_mil(tot_real),
        "projecao_fmt": _fmt_mil(tot_proj),
        "meses_real": n_meses,
        "ate_mes": ate_mes,
        "desvio_pct": tot_pct,
    }

    return templates.TemplateResponse(request, "analise/forecast.html", {
        "por_filial": por_filial,
        "totais": totais,
        "kpis": kpis,
        "ano": ano,
        "anos_disponiveis": [2024, 2023],
        "active_page": "forecast",
    })
