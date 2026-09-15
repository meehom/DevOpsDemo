"""演示用的极简 HTML 页面，作为 Playwright 端到端测试的目标。"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["ui"])

PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>两数相加</title>
</head>
<body>
  <h1>两数相加</h1>
  <p>
    <label for="a">数字 A</label>
    <input id="a" name="a" type="number" value="1">
    <label for="b">数字 B</label>
    <input id="b" name="b" type="number" value="2">
    <button id="calc" type="button">计算</button>
  </p>
  <p>结果：<span id="result">-</span></p>
  <script>
    const result = document.getElementById("result");
    document.getElementById("calc").addEventListener("click", async () => {
      const a = document.getElementById("a").value;
      const b = document.getElementById("b").value;
      const resp = await fetch(`/add?a=${a}&b=${b}`);
      const data = await resp.json();
      result.textContent = data.result;
    });
  </script>
</body>
</html>
"""


@router.get("/ui", response_class=HTMLResponse, summary="演示页面")
def ui_page() -> HTMLResponse:
    """返回用于端到端测试的极简页面。"""
    return HTMLResponse(content=PAGE)