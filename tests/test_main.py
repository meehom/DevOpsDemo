"""针对 app.main 中接口的单元测试。"""
import pytest
from pydantic import ValidationError

from app import main


def test_health_ok(client):
    """健康检查接口返回 ok。"""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_add_integers(client):
    """两数相加：整数场景。"""
    resp = client.get("/add", params={"a": 2, "b": 3})
    assert resp.status_code == 200
    assert resp.json() == {"result": 5.0}


def test_add_floats_and_negatives(client):
    """两数相加：浮点与负数场景。"""
    resp = client.get("/add", params={"a": 1.5, "b": -0.5})
    assert resp.status_code == 200
    assert resp.json() == {"result": 1.0}


def test_add_missing_param(client):
    """缺少参数时返回 422。"""
    resp = client.get("/add", params={"a": 1})
    assert resp.status_code == 422


def test_create_item_success(client):
    """创建商品成功并返回自增 id。"""
    resp = client.post("/items", json={"name": "book", "price": 9.9})
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"id": 1, "name": "book", "price": 9.9}

    second = client.post("/items", json={"name": "pen", "price": 2.0}).json()
    assert second["id"] == 2


def test_create_item_invalid_price(client):
    """价格必须大于 0 且名称不能为空。"""
    assert client.post("/items", json={"name": "book", "price": 0}).status_code == 422
    assert client.post("/items", json={"name": "", "price": 1}).status_code == 422


def test_list_and_get_item(client):
    """列表接口返回全部商品，详情接口按 id 查询。"""
    client.post("/items", json={"name": "book", "price": 9.9})
    client.post("/items", json={"name": "pen", "price": 2.0})

    resp = client.get("/items")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    detail = client.get("/items/1")
    assert detail.status_code == 200
    assert detail.json()["name"] == "book"


def test_get_item_not_found(client):
    """查询不存在的商品返回 404。"""
    resp = client.get("/items/999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "item not found"


def test_item_model_validates_input():
    """Pydantic 模型层面的校验。"""
    model = main.Item(name="book", price=1.0)
    assert model.price == 1.0

    with pytest.raises(ValidationError):
        main.Item(name="book", price=-1)