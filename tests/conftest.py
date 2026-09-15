"""pytest 公共 fixture：每个用例前重置接口的内存状态。"""
import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture()
def client():
    """返回一个干净的 TestClient，并清空全局商品数据。"""
    main._items.clear()
    main._next_id = 1
    with TestClient(main.app) as c:
        yield c