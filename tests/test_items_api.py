"""商品管理接口的单元测试。

注意：这组接口尚未编写需求文档（specs/ 下没有对应 REQ），
按 AGENTS.md 的规则，补文档时需要同步补端到端测试。
"""
import pytest
from pydantic import ValidationError

from app import main


def test_create_item_success(client):
    """创建商品成功并返回自增 id。"""
    resp = client.post("/items", json={"name": "book", "price": 9.9})
    assert resp.status_code == 200
    assert resp.json() == {"id": 1, "name": "book", "price": 9.9}

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