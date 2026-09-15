"""FastAPI 应用入口，提供两个示例接口。"""
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import ui

app = FastAPI(
    title="DevOps Demo API",
    description="用于演示 GitHub Actions CI/CD 流程的示例接口",
    version="1.0.0",
)

# 内存中的数据，仅用于演示，重启后重置
_items: Dict[int, "Item"] = {}
_next_id = 1


class Item(BaseModel):
    """商品数据模型。"""

    name: str = Field(..., min_length=1, description="商品名称")
    price: float = Field(..., gt=0, description="商品价格，必须大于 0")


class ItemOut(BaseModel):
    """返回给客户端的商品数据。"""

    id: int
    name: str
    price: float


@app.get("/health", summary="健康检查")
def health() -> Dict[str, str]:
    """接口一：健康检查，用于 CI/CD 中的存活探测。"""
    return {"status": "ok"}


@app.get("/add", summary="两数相加")
def add(a: float, b: float) -> Dict[str, float]:
    """接口二：计算两数之和。"""
    return {"result": a + b}


@app.post("/items", response_model=ItemOut, summary="创建商品")
def create_item(item: Item) -> ItemOut:
    """接口三：创建商品并返回带 id 的结果。"""
    global _next_id
    new_item = ItemOut(id=_next_id, name=item.name, price=item.price)
    _items[_next_id] = new_item
    _next_id += 1
    return new_item


@app.get("/items", response_model=List[ItemOut], summary="查询商品列表")
def list_items() -> List[ItemOut]:
    """接口四：返回全部商品。"""
    return list(_items.values())


@app.get("/items/{item_id}", response_model=ItemOut, summary="查询单个商品")
def get_item(item_id: int) -> ItemOut:
    """接口五：按 id 查询商品，不存在时返回 404。"""
    item: Optional[ItemOut] = _items.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    return item


# 端到端测试用的演示页面
app.include_router(ui.router)