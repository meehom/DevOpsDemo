"""院校数据与筛选接口（REQ-002）。

院校清单为演示用虚构数据，不代表任何真实学校的招生信息。
目标清单存在内存里，与现有 items 的口径一致，重启后重置。
"""
from typing import List, Literal, Optional, Set

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(tags=["schools"])

# 筛选器用的行政区候选值，顺序即页面上的展示顺序
DISTRICTS: List[str] = [
    "徐汇", "黄浦", "浦东", "静安", "杨浦", "闵行", "普陀", "虹口",
    "长宁", "宝山", "嘉定", "松江", "青浦", "奉贤", "金山", "崇明",
]

SCHOOL_TYPES: List[str] = ["公办", "民办"]


class School(BaseModel):
    """院校基础信息。"""

    id: int
    name: str
    district: str
    school_type: str


class SchoolOut(School):
    """返回给客户端的院校数据，额外带上是否已加入目标清单。"""

    is_target: bool


class SchoolOptions(BaseModel):
    """筛选器候选值。"""

    districts: List[str]
    school_types: List[str]


SCHOOLS: List[School] = [
    School(id=1, name="徐汇区汇文初级中学", district="徐汇", school_type="公办"),
    School(id=2, name="徐汇区启明外国语初级中学", district="徐汇", school_type="民办"),
    School(id=3, name="徐汇区蒲汇塘实验初级中学", district="徐汇", school_type="公办"),
    School(id=4, name="黄浦区明德初级中学", district="黄浦", school_type="公办"),
    School(id=5, name="黄浦区南浦初级中学", district="黄浦", school_type="民办"),
    School(id=6, name="浦东新区华夏初级中学", district="浦东", school_type="公办"),
    School(id=7, name="浦东新区金桥外国语初级中学", district="浦东", school_type="民办"),
    School(id=8, name="浦东新区临港实验初级中学", district="浦东", school_type="公办"),
    School(id=9, name="静安区彭浦初级中学", district="静安", school_type="公办"),
    School(id=10, name="静安区博雅初级中学", district="静安", school_type="民办"),
    School(id=11, name="杨浦区定海初级中学", district="杨浦", school_type="公办"),
    School(id=12, name="杨浦区同舟初级中学", district="杨浦", school_type="民办"),
    School(id=13, name="闵行区莘庄初级中学", district="闵行", school_type="公办"),
    School(id=14, name="闵行区文绮初级中学", district="闵行", school_type="民办"),
    School(id=15, name="普陀区真如初级中学", district="普陀", school_type="公办"),
    School(id=16, name="虹口区提篮桥初级中学", district="虹口", school_type="公办"),
    School(id=17, name="长宁区天山初级中学", district="长宁", school_type="公办"),
    School(id=18, name="长宁区新世纪初级中学", district="长宁", school_type="民办"),
    School(id=19, name="宝山区顾村初级中学", district="宝山", school_type="公办"),
    School(id=20, name="嘉定区疁城初级中学", district="嘉定", school_type="公办"),
    School(id=21, name="松江区九峰初级中学", district="松江", school_type="公办"),
    School(id=22, name="青浦区淀山湖初级中学", district="青浦", school_type="公办"),
    School(id=23, name="奉贤区南桥初级中学", district="奉贤", school_type="公办"),
    School(id=24, name="金山区枫泾初级中学", district="金山", school_type="公办"),
    School(id=25, name="崇明区城桥初级中学", district="崇明", school_type="公办"),
]

# 已加入目标清单的院校 id
_targets: Set[int] = set()


def _to_out(school: School) -> SchoolOut:
    return SchoolOut(**school.model_dump(), is_target=school.id in _targets)


def _find(school_id: int) -> School:
    for school in SCHOOLS:
        if school.id == school_id:
            return school
    raise HTTPException(status_code=404, detail="school not found")


@router.get("/schools", response_model=List[SchoolOut], summary="筛选院校列表")
def list_schools(
    district: Optional[List[str]] = Query(None, description="行政区，可重复传参多选，多个之间为「或」"),
    school_type: Optional[Literal["公办", "民办"]] = Query(None, description="办学性质"),
    target_only: bool = Query(False, description="只返回已加入目标清单的院校"),
) -> List[SchoolOut]:
    """按行政区与办学性质筛选院校，两个维度之间为「且」。"""
    rows = SCHOOLS
    if district:
        rows = [school for school in rows if school.district in district]
    if school_type:
        rows = [school for school in rows if school.school_type == school_type]
    if target_only:
        rows = [school for school in rows if school.id in _targets]
    return [_to_out(school) for school in rows]


@router.get("/schools/options", response_model=SchoolOptions, summary="筛选器候选值")
def school_options() -> SchoolOptions:
    """返回页面筛选器需要的行政区与办学性质候选值。"""
    return SchoolOptions(districts=DISTRICTS, school_types=SCHOOL_TYPES)


@router.post("/schools/{school_id}/target", response_model=SchoolOut, summary="加入目标清单")
def add_target(school_id: int) -> SchoolOut:
    """把院校加入目标清单。"""
    school = _find(school_id)
    _targets.add(school.id)
    return _to_out(school)


@router.delete("/schools/{school_id}/target", response_model=SchoolOut, summary="移出目标清单")
def remove_target(school_id: int) -> SchoolOut:
    """把院校移出目标清单。"""
    school = _find(school_id)
    _targets.discard(school.id)
    return _to_out(school)