"""目标院校筛选页面（REQ-002），作为端到端测试的操作目标。

页面本身只负责渲染，筛选与目标清单状态都由 app.schools 提供的接口负责。
"""
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["ui"])

TEMPLATE = Path(__file__).resolve().parent / "templates" / "schools.html"


@router.get("/ui/schools", response_class=HTMLResponse, summary="目标院校筛选页面")
def schools_page() -> HTMLResponse:
    """返回目标院校筛选页面。"""
    return HTMLResponse(content=TEMPLATE.read_text(encoding="utf-8"))