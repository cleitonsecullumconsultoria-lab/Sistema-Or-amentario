from fastapi import APIRouter, Request
from tmpl import templates

router = APIRouter(prefix="/receitas", tags=["receitas"])


@router.get("/")
async def receitas_index(request: Request):
    return templates.TemplateResponse(request, "em_construcao.html", {
        "modulo": "Receitas Pós-Venda",
        "active_page": "receitas",
    })
