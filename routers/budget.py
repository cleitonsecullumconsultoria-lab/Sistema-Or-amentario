from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import DB
from tmpl import templates

router = APIRouter(prefix="/budget", tags=["budget"])

MESES = [
    {"num": 1, "nome": "Jan"}, {"num": 2, "nome": "Fev"}, {"num": 3, "nome": "Mar"},
    {"num": 4, "nome": "Abr"}, {"num": 5, "nome": "Mai"}, {"num": 6, "nome": "Jun"},
    {"num": 7, "nome": "Jul"}, {"num": 8, "nome": "Ago"}, {"num": 9, "nome": "Set"},
    {"num": 10, "nome": "Out"}, {"num": 11, "nome": "Nov"}, {"num": 12, "nome": "Dez"},
]


def _fmt(v) -> str:
    try:
        f = float(v)
        return f"{f:,.0f}".replace(",", ".")
    except Exception:
        return ""


@router.get("/ciclo")
async def ciclo(request: Request):
    db = DB()
    versoes = db.tabela("BudgetVersoes")
    filiais = db.tabela("Filiais")
    bud = db.tabela("BudgetLinhas")
    versao_ativa = versoes[versoes["status"] == "aprovado"]["id"].max() if not versoes.empty else None

    status_filiais = []
    for _, f in filiais.iterrows():
        linhas = len(bud[bud["filial_id"] == f["id"]])
        status_filiais.append({
            "id": f["id"], "codigo": f["codigo"], "nome": f["nome"],
            "linhas": linhas, "versao": f"v{int(versao_ativa)}" if versao_ativa else "—",
        })

    return templates.TemplateResponse(request, "budget/ciclo.html", {
        "status_filiais": status_filiais,
        "ano_atual": 2026,
        "active_page": "ciclo",
    })


@router.get("/versoes")
async def versoes_list(request: Request):
    db = DB()
    versoes = db.tabela("BudgetVersoes").to_dict("records")
    return templates.TemplateResponse(request, "budget/versoes.html", {
        "versoes": versoes,
        "active_page": "versoes",
    })


@router.get("/aprovacao")
async def aprovacao(request: Request):
    db = DB()
    versoes = db.tabela("BudgetVersoes")
    bud = db.tabela("BudgetLinhas")

    pendentes = versoes[versoes["status"] == "em_revisao"].to_dict("records")
    aprovadas = versoes[versoes["status"] == "aprovado"].to_dict("records")

    for v in pendentes + aprovadas:
        v["n_linhas"] = len(bud[bud["versao_id"] == v["id"]])

    return templates.TemplateResponse(request, "budget/aprovacao.html", {
        "versoes_pendentes": pendentes,
        "versoes_aprovadas": aprovadas,
        "active_page": "aprovacao",
    })


@router.post("/aprovar/{versao_id}")
async def aprovar(request: Request, versao_id: int):
    db = DB()
    df = db.tabela("BudgetVersoes")
    df.loc[df["id"] == versao_id, "status"] = "aprovado"
    db.salvar("BudgetVersoes", df)
    return RedirectResponse("/budget/aprovacao", status_code=303)


@router.post("/devolver/{versao_id}")
async def devolver(request: Request, versao_id: int):
    db = DB()
    df = db.tabela("BudgetVersoes")
    df.loc[df["id"] == versao_id, "status"] = "rascunho"
    db.salvar("BudgetVersoes", df)
    return RedirectResponse("/budget/aprovacao", status_code=303)


@router.get("/entrada")
async def entrada(request: Request, versao_id: int | None = None, filial_id: int | None = None):
    db = DB()
    versoes_df = db.tabela("BudgetVersoes")
    filiais_df = db.tabela("Filiais")
    contas_df = db.tabela("PlanoContas")
    bud_df = db.tabela("BudgetLinhas")
    real_df = db.tabela("Realizado")

    # Seleciona versão
    if versao_id:
        versao_row = versoes_df[versoes_df["id"] == versao_id].iloc[0]
    else:
        aprov = versoes_df[versoes_df["status"] == "aprovado"]
        if not aprov.empty:
            versao_row = versoes_df.loc[aprov["id"].idxmax()]
        else:
            versao_row = versoes_df.iloc[0]
    versao = versao_row.to_dict()

    filial_sel = None
    if filial_id:
        row = filiais_df[filiais_df["id"] == filial_id]
        if not row.empty:
            filial_sel = row.iloc[0].to_dict()

    filiais = filiais_df[filiais_df["ativo"] == 1].to_dict("records")

    # Filtra budget e realizado
    bud_v = bud_df[bud_df["versao_id"] == versao["id"]]
    real_ano = real_df[real_df["ano"] == versao["ano"] - 1]  # referência ano anterior

    if filial_sel:
        bud_v = bud_v[bud_v["filial_id"] == filial_sel["id"]]
        real_ano = real_ano[real_ano["filial_id"] == filial_sel["id"]]
        grupos_filiais = [filial_sel]
    else:
        grupos_filiais = filiais

    # Constrói grid por filial
    grid = []
    for f in grupos_filiais:
        fid = f["id"]
        bud_f = bud_v[bud_v["filial_id"] == fid]
        real_f = real_ano[real_ano["filial_id"] == fid]

        # Linhas de budget agrupadas por conta
        bud_rows = []
        subtotal = {}
        subtotal_total = 0
        for conta_id in bud_f["conta_id"].unique():
            conta_row = contas_df[contas_df["id"] == conta_id]
            if conta_row.empty:
                continue
            conta = conta_row.iloc[0]
            linhas_conta = bud_f[bud_f["conta_id"] == conta_id]
            valores = {}
            total = 0
            for _, bl in linhas_conta.iterrows():
                m = int(bl["mes"])
                v = float(bl["valor"]) if pd.notna(bl["valor"]) else 0
                valores[m] = _fmt(v / 1000) if v else ""
                total += v
                subtotal[m] = subtotal.get(m, 0) + v
                subtotal_total += v
            bud_rows.append({
                "conta_id": int(conta_id),
                "conta_codigo": conta["codigo"],
                "conta_nome": conta["nome"],
                "valores": valores,
                "total": _fmt(total / 1000),
            })

        # Referência realizado ano anterior
        ref_rows = []
        for conta_id in real_f["conta_id"].unique()[:5]:  # máximo 5 contas ref
            conta_row = contas_df[contas_df["id"] == conta_id]
            if conta_row.empty:
                continue
            conta = conta_row.iloc[0]
            linhas_real = real_f[real_f["conta_id"] == conta_id]
            valores_r = {}
            total_r = 0
            for _, rl in linhas_real.iterrows():
                m = int(rl["mes"])
                v = float(rl["valor"]) if pd.notna(rl["valor"]) else 0
                valores_r[m] = _fmt(v / 1000) if v else ""
                total_r += v
            ref_rows.append({
                "conta_codigo": conta["codigo"],
                "conta_nome": conta["nome"],
                "valores": valores_r,
                "total": _fmt(total_r / 1000),
            })

        sub_fmt = {m: _fmt(v / 1000) for m, v in subtotal.items()}
        grid.append({
            "filial_id": fid,
            "filial_codigo": f["codigo"],
            "filial_nome": f["nome"],
            "bud_rows": bud_rows,
            "ref_rows": ref_rows,
            "subtotal": sub_fmt,
            "subtotal_total": _fmt(subtotal_total / 1000),
        })

    return templates.TemplateResponse(request, "budget/entrada.html", {
        "versao": versao,
        "versoes": versoes_df.to_dict("records"),
        "filiais": filiais,
        "filial_sel": filial_sel,
        "grid": grid,
        "meses": MESES,
        "active_page": "entrada",
    })


@router.post("/entrada/salvar")
async def entrada_salvar(request: Request):
    form = await request.form()
    versao_id = int(form.get("versao_id", 0))
    filial_id = form.get("filial_id")

    db = DB()
    versoes_df = db.tabela("BudgetVersoes")
    versao = versoes_df[versoes_df["id"] == versao_id].iloc[0]

    if versao["status"] == "aprovado":
        return RedirectResponse(f"/budget/entrada?versao_id={versao_id}", status_code=303)

    df = db.tabela("BudgetLinhas")

    # Remove linhas existentes desta versão+filial e reinsere
    mask = df["versao_id"] == versao_id
    if filial_id:
        mask &= df["filial_id"] == int(filial_id)
    df = df[~mask]

    novas = []
    max_id = int(df["id"].max()) + 1 if not df.empty else 1
    for key, val in form.items():
        if key.startswith("v_") and val.strip():
            partes = key.split("_")
            if len(partes) == 4:
                _, fid, cid, mes = partes
                try:
                    valor = float(str(val).replace(".", "").replace(",", ".")) * 1000
                    novas.append({
                        "id": max_id, "versao_id": versao_id,
                        "filial_id": int(fid), "ccu_id": None,
                        "conta_id": int(cid), "mes": int(mes),
                        "valor": valor, "obs": None,
                        "created_by": "sistema", "created_at": None,
                    })
                    max_id += 1
                except ValueError:
                    pass

    if novas:
        df = pd.concat([df, pd.DataFrame(novas)], ignore_index=True)
        db.salvar("BudgetLinhas", df)

    acao = form.get("acao", "rascunho")
    if acao == "enviar":
        versoes_df.loc[versoes_df["id"] == versao_id, "status"] = "em_revisao"
        db.salvar("BudgetVersoes", versoes_df)

    url = f"/budget/entrada?versao_id={versao_id}"
    if filial_id:
        url += f"&filial_id={filial_id}"
    return RedirectResponse(url, status_code=303)
