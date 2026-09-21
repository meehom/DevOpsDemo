"""REQ-002 的端到端测试：用真实浏览器操作 /ui/schools 页面。

本地运行前先启动服务（另开一个终端）：
    uvicorn app.main:app --port 8000
再执行：
    pytest -m e2e
"""
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e

TITLE = "目标院校筛选"


@pytest.fixture(autouse=True)
def clean_targets(base_url):
    """清空服务端的目标清单，保证用例之间互不影响。"""
    with httpx.Client(base_url=base_url) as api:
        for row in api.get("/schools").json():
            if row["is_target"]:
                api.delete(f"/schools/{row['id']}/target")
    yield


def card_subs(page: Page):
    """返回当前列表里每张卡片的副标题文本。"""
    return page.locator("#list .card-sub").all_inner_texts()


def test_page_shows_all_schools(page: Page, step):
    """AC-12、AC-13：页面能打开，默认展示全部院校卡片。"""
    with step("打开 /ui/schools 页面"):
        page.goto("/ui/schools")
    with step("断言页面标题"):
        expect(page).to_have_title(TITLE)
    with step("断言结果计数为全部院校"):
        expect(page.locator("#count")).to_have_text("共 25 所")
    with step("断言卡片副标题格式为「行政区 · 办学性质」"):
        expect(page.locator("#list .card").first.locator(".card-sub")).to_have_text("徐汇 · 公办")


def test_filter_by_district(page: Page, step):
    """AC-14：勾选行政区后列表只剩该区院校，且请求带上 district 参数。"""
    with step("打开 /ui/schools 页面"):
        page.goto("/ui/schools")
    with step("勾选行政区「徐汇」并拦截 /schools 请求"):
        with page.expect_response(
            lambda r: "/schools" in r.url and r.request.method == "GET"
        ) as response:
            page.click('#district-chips .chip[data-district="徐汇"]')
    with step("断言请求带上 district=徐汇"):
        query = parse_qs(urlparse(response.value.url).query)
        assert query.get("district") == ["徐汇"]
    with step("断言列表只剩 3 所徐汇区院校"):
        expect(page.locator("#list .card")).to_have_count(3)
        assert all("徐汇" in sub for sub in card_subs(page))


def test_filter_by_school_type(page: Page, step):
    """AC-15：选择「民办」后列表只剩民办院校。"""
    with step("打开 /ui/schools 页面"):
        page.goto("/ui/schools")
    with step("点击办学性质「民办」"):
        page.click('#type-chips .chip[data-school-type="民办"]')
    with step("断言结果计数变为民办院校数量"):
        expect(page.locator("#count")).to_have_text("共 7 所")
    with step("断言每张卡片副标题都是民办"):
        assert card_subs(page)
        assert all(sub.endswith("民办") for sub in card_subs(page))


def test_mark_school_as_target(page: Page, step):
    """AC-16：点击星形按钮会发起加入目标清单请求，并切换按钮状态。"""
    with step("打开 /ui/schools 页面"):
        page.goto("/ui/schools")
    star = page.locator('#list .card[data-school-id="1"] .star')
    with step("断言按钮初始为未加入状态"):
        expect(star).to_have_attribute("aria-pressed", "false")
    with step("点击「加入目标清单」并拦截请求"):
        with page.expect_response(lambda r: "/schools/1/target" in r.url) as response:
            star.click()
    with step("断言请求为 POST /schools/1/target"):
        assert response.value.request.method == "POST"
        assert response.value.ok
    with step("断言按钮变为已加入状态"):
        expect(star).to_have_attribute("aria-pressed", "true")


def test_target_only_filters_list(page: Page, step):
    """AC-17：开启「只看目标清单」后只显示已加入的院校。"""
    with step("打开 /ui/schools 页面"):
        page.goto("/ui/schools")
    with step("把 1 号院校加入目标清单"):
        with page.expect_response(lambda r: "/schools/1/target" in r.url):
            page.click('#list .card[data-school-id="1"] .star')
    with step("把 4 号院校加入目标清单"):
        with page.expect_response(lambda r: "/schools/4/target" in r.url):
            page.click('#list .card[data-school-id="4"] .star')
    with step("开启「只看目标清单」"):
        page.click("#target-only")
    with step("断言列表只剩这 2 所院校"):
        expect(page.locator("#list .card")).to_have_count(2)
        expect(page.locator("#count")).to_have_text("共 2 所")
        assert page.locator("#list .card-title").all_inner_texts() == [
            "徐汇区汇文初级中学",
            "黄浦区明德初级中学",
        ]


def test_empty_state(page: Page, step):
    """AC-18：筛选结果为空时展示空态提示。"""
    with step("打开 /ui/schools 页面"):
        page.goto("/ui/schools")
    with step("勾选行政区「崇明」"):
        page.click('#district-chips .chip[data-district="崇明"]')
    with step("点击办学性质「民办」"):
        page.click('#type-chips .chip[data-school-type="民办"]')
    with step("断言列表清空且计数为 0"):
        expect(page.locator("#list .card")).to_have_count(0)
        expect(page.locator("#count")).to_have_text("共 0 所")
    with step("断言展示空态提示"):
        expect(page.locator("#empty")).to_be_visible()
        expect(page.locator("#empty .title")).to_have_text("没有符合条件的院校")
    with step("点击「重置」恢复全量列表"):
        page.click("#reset")
        expect(page.locator("#count")).to_have_text("共 25 所")
        expect(page.locator("#empty")).to_be_hidden()