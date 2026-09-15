"""E2E 测试公共设施：按步骤操作页面并自动截图，作为验收报告的证据。"""
import itertools
import re
from contextlib import contextmanager
from pathlib import Path

import pytest
from playwright.sync_api import Page

REPORTS_ROOT = Path(__file__).resolve().parents[2] / "reports"


def _requirement_id(request) -> str:
    """从测试文件名提取需求 ID，例如 test_req_001_ui.py -> REQ-001。"""
    matched = re.search(r"req_(\d{3})", Path(str(request.node.fspath)).stem)
    return f"REQ-{matched.group(1)}" if matched else "UNKNOWN"


def _slug(text: str) -> str:
    """把步骤描述转成安全的文件名片段，保留中文。"""
    return re.sub(r"[^\w\u4e00-\u9fff-]+", "_", text).strip("_")


@pytest.fixture
def step(page: Page, request):
    """按步骤操作页面，每步结束自动截图（失败时也会截）。

    用法：
        with step("点击计算"):
            page.click("#calc")

    截图保存到 reports/<需求ID>/screenshots/<用例名>/<序号>_<步骤名>.png
    """
    counter = itertools.count(1)
    case_name = re.sub(r"\[.*\]$", "", request.node.name)
    shot_dir = REPORTS_ROOT / _requirement_id(request) / "screenshots" / case_name

    @contextmanager
    def _step(description: str):
        try:
            yield
        finally:
            shot_dir.mkdir(parents=True, exist_ok=True)
            index = next(counter)
            page.screenshot(path=str(shot_dir / f"{index:02d}_{_slug(description)}.png"))

    return _step