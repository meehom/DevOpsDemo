"""REQ-001 的单元测试：两数相加接口、演示页面、健康检查。"""
import pytest
from app import main


def test_health_ok(client):
    """AC-7：健康检查接口返回 ok。"""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_add_integers(client):
    """AC-1：两数相加，整数场景。"""
    resp = client.get("/add", params={"a": 2, "b": 3})
    assert resp.status_code == 200
    assert resp.json() == {"result": 5.0}


def test_add_floats_and_negatives(client):
    """AC-2：两数相加，浮点与负数场景。"""
    resp = client.get("/add", params={"a": 1.5, "b": -0.5})
    assert resp.status_code == 200
    assert resp.json() == {"result": 1.0}


def test_add_missing_param(client):
    """AC-3：缺少参数时返回 422。"""
    resp = client.get("/add", params={"a": 1})
    assert resp.status_code == 422


def test_ui_page_renders(client):
    """AC-4：演示页面返回 200，且包含计算结果所需的元素。"""
    resp = client.get("/ui")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    for element_id in ('id="a"', 'id="b"', 'id="calc"', 'id="result"'):
        assert element_id in resp.text