from fastapi import APIRouter, Request
from tmpl import templates

router = APIRouter(prefix="/headcount", tags=["headcount"])


@router.get("/")
async def headcount_index(request: Request):
    return templates.TemplateResponse(request, "em_construcao.html", {
        "modulo": "Headcount & Folha",
        "active_page": "headcount",
    })
