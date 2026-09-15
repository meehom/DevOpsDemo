"""REQ-001 的端到端测试：用真实浏览器操作 /ui 页面。

本地运行前先启动服务（另开一个终端）：
    uvicorn app.main:app --port 8000
再执行：
    pytest -m e2e
"""
import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def test_page_loads(page: Page, step):
    """AC-4：页面能打开，标题和按钮都渲染出来。"""
    with step("打开 /ui 页面"):
        page.goto("/ui")
    with step("断言页面标题"):
        expect(page).to_have_title("两数相加")
    with step("断言计算按钮可见"):
        expect(page.get_by_role("button", name="计算")).to_be_visible()


def test_click_calc_shows_result(page: Page, step):
    """AC-5：输入 2 和 3，点击计算，页面显示 5。"""
    with step("打开 /ui 页面"):
        page.goto("/ui")
    with step("填入数字 A=2"):
        page.fill("#a", "2")
    with step("填入数字 B=3"):
        page.fill("#b", "3")
    with step("点击计算按钮"):
        page.click("#calc")
    with step("断言结果显示 5"):
        expect(page.locator("#result")).to_have_text("5")


def test_page_result_matches_api(page: Page, step):
    """AC-6：页面上展示的结果与后端接口返回一致。"""
    with step("打开 /ui 页面"):
        page.goto("/ui")
    with step("填入 A=1.5 与 B=-0.5"):
        page.fill("#a", "1.5")
        page.fill("#b", "-0.5")
    with step("点击计算并拦截 /add 请求"):
        with page.expect_response("**/add?*") as response:
            page.click("#calc")
    with step("断言接口返回 result=1.0"):
        assert response.value.json() == {"result": 1.0}
    with step("断言页面显示 1"):
        expect(page.locator("#result")).to_have_text("1")