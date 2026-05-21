from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import DB
from tmpl import templates

router = APIRouter(prefix="/headcount", tags=["headcount"])


def _fmt(v) -> str:
    try:
        return f"R$ {float(v):,.0f}".replace(",", ".")
    except Exception:
        return "—"


@router.get("/colaboradores")
async def colaboradores(request: Request):
    db = DB()
    colab_df = db.tabela("Colaboradores")
    filiais_df = db.tabela("Filiais")
    filiais_map = {r["id"]: r.to_dict() for _, r in filiais_df.iterrows()}

    colab = []
    total_sal = total_enc = total_ben = total_mes = 0
    for _, c in colab_df.iterrows():
        f = filiais_map.get(c.get("filial_id"))
        sal = float(c.get("salario_base", 0) or 0)
        enc = sal * 0.5
        ben = float(c.get("beneficios", 0) or 0) if "beneficios" in c else 0
        tot = sal + enc + ben
        total_sal += sal; total_enc += enc; total_ben += ben; total_mes += tot
        colab.append({
            "id": int(c["id"]),
            "nome": c.get("nome", ""),
            "cargo": c.get("cargo", ""),
            "filial_id": int(c.get("filial_id") or 0),
            "filial_codigo": f["codigo"] if f else "—",
            "ccu_nome": c.get("ccu_nome", ""),
            "ativo": int(c.get("ativo", 1)),
            "salario_base": sal,
            "beneficios": ben,
            "salario_fmt": _fmt(sal),
            "encargos_fmt": _fmt(enc),
            "beneficios_fmt": _fmt(ben),
            "total_mes_fmt": _fmt(tot),
        })

    n = len(colab)
    stats = {
        "total": n,
        "ativos": sum(1 for c in colab if c["ativo"] == 1),
        "custo_total_fmt": _fmt(total_mes * 12),
        "custo_medio_fmt": _fmt(total_mes / n) if n else "—",
        "total_salario_fmt": _fmt(total_sal),
        "total_encargos_fmt": _fmt(total_enc),
        "total_beneficios_fmt": _fmt(total_ben),
        "total_mes_fmt": _fmt(total_mes),
    }

    return templates.TemplateResponse(request, "headcount/colaboradores.html", {
        "colaboradores": colab,
        "filiais": filiais_df[filiais_df["ativo"] == 1].to_dict("records"),
        "stats": stats,
        "ano": 2026,
        "active_page": "colaboradores",
    })


@router.post("/colaboradores/editar/{colab_id}")
async def colaboradores_editar(
    request: Request,
    colab_id: int,
    nome: str = Form(...),
    cargo: str = Form(...),
    filial_id: int = Form(...),
    salario_base: str = Form("0"),
    beneficios: str = Form("0"),
    ativo: str = Form("1"),
):
    db = DB()
    df = db.tabela("Colaboradores")
    sal = float(salario_base.replace(".", "").replace(",", ".") or 0)
    ben = float(beneficios.replace(".", "").replace(",", ".") or 0)
    mask = df["id"] == colab_id
    df.loc[mask, "nome"] = nome.strip()
    df.loc[mask, "cargo"] = cargo.strip()
    df.loc[mask, "filial_id"] = filial_id
    df.loc[mask, "salario_base"] = sal
    df.loc[mask, "beneficios"] = ben
    df.loc[mask, "ativo"] = 1 if ativo == "1" else 0
    db.salvar("Colaboradores", df)
    return RedirectResponse("/headcount/colaboradores", status_code=303)


@router.post("/colaboradores/excluir/{colab_id}")
async def colaboradores_excluir(request: Request, colab_id: int):
    db = DB()
    df = db.tabela("Colaboradores")
    df = df[df["id"] != colab_id]
    db.salvar("Colaboradores", df)
    return RedirectResponse("/headcount/colaboradores", status_code=303)


@router.post("/colaboradores/criar")
async def colaboradores_criar(
    request: Request,
    nome: str = Form(...),
    cargo: str = Form(...),
    filial_id: int = Form(...),
    salario_base: str = Form("0"),
    beneficios: str = Form("0"),
    ativo: str = Form("1"),
):
    db = DB()
    df = db.tabela("Colaboradores")
    novo_id = int(df["id"].max()) + 1 if not df.empty else 1
    sal = float(salario_base.replace(".", "").replace(",", ".") or 0)
    ben = float(beneficios.replace(".", "").replace(",", ".") or 0)
    nova = pd.DataFrame([{
        "id": novo_id, "nome": nome.strip(), "cargo": cargo.strip(),
        "filial_id": filial_id, "salario_base": sal, "beneficios": ben,
        "ativo": 1 if ativo == "1" else 0,
    }])
    df = pd.concat([df, nova], ignore_index=True)
    db.salvar("Colaboradores", df)
    return RedirectResponse("/headcount/colaboradores", status_code=303)


@router.get("/folha")
async def folha(request: Request):
    db = DB()
    colab_df = db.tabela("Colaboradores")
    filiais_df = db.tabela("Filiais")
    filiais_map = {r["id"]: r.to_dict() for _, r in filiais_df.iterrows()}

    por_filial = {}
    for _, c in colab_df.iterrows():
        if int(c.get("ativo", 1)) != 1:
            continue
        fid = c.get("filial_id")
        f = filiais_map.get(fid, {})
        codigo = f.get("codigo", "?") if f else "?"
        nome = f.get("nome", "?") if f else "?"
        sal = float(c.get("salario_base", 0) or 0)
        enc = sal * 0.5
        ben = float(c.get("beneficios", 0) or 0) if "beneficios" in c else 0
        if codigo not in por_filial:
            por_filial[codigo] = {"filial_codigo": codigo, "filial_nome": nome, "n_colab": 0,
                                   "sal": 0, "enc": 0, "ben": 0, "mes": 0}
        por_filial[codigo]["n_colab"] += 1
        por_filial[codigo]["sal"] += sal
        por_filial[codigo]["enc"] += enc
        por_filial[codigo]["ben"] += ben
        por_filial[codigo]["mes"] += sal + enc + ben

    rows = []
    tot = {"n_colab": 0, "sal": 0, "enc": 0, "ben": 0, "mes": 0}
    for v in sorted(por_filial.values(), key=lambda x: x["filial_codigo"]):
        rows.append({
            "filial_codigo": v["filial_codigo"], "filial_nome": v["filial_nome"],
            "n_colab": v["n_colab"],
            "salarios_fmt": _fmt(v["sal"]),
            "encargos_fmt": _fmt(v["enc"]),
            "beneficios_fmt": _fmt(v["ben"]),
            "total_mes_fmt": _fmt(v["mes"]),
            "total_ano_fmt": _fmt(v["mes"] * 12),
        })
        for k in ["n_colab", "sal", "enc", "ben", "mes"]:
            tot[k] += v[k]

    totais = {
        "n_colab": tot["n_colab"],
        "salarios_fmt": _fmt(tot["sal"]),
        "encargos_fmt": _fmt(tot["enc"]),
        "beneficios_fmt": _fmt(tot["ben"]),
        "total_mes_fmt": _fmt(tot["mes"]),
        "total_ano_fmt": _fmt(tot["mes"] * 12),
    }

    return templates.TemplateResponse(request, "headcount/folha.html", {
        "por_filial": rows,
        "totais": totais,
        "ano": 2026,
        "active_page": "folha",
    })
