from fastapi import APIRouter, Request
from tmpl import templates

router = APIRouter(prefix="/opex", tags=["opex"])


@router.get("/")
async def opex_index(request: Request):
    return templates.TemplateResponse(request, "em_construcao.html", {
        "modulo": "OPEX",
        "active_page": "opex",
    })
