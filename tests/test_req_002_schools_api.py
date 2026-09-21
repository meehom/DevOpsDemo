"""REQ-002 的单元测试：院校筛选接口与目标清单接口。"""
import pytest

from app import schools


@pytest.fixture(autouse=True)
def clean_targets():
    """每个用例前清空目标清单，避免用例之间互相影响。"""
    schools._targets.clear()
    yield
    schools._targets.clear()


def test_list_all_schools(client):
    """AC-1：不带筛选参数时返回全部院校，每条字段齐全。"""
    resp = client.get("/schools")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == len(schools.SCHOOLS)
    assert rows[0].keys() == {"id", "name", "district", "school_type", "is_target"}
    assert len({row["district"] for row in rows}) == 16


def test_filter_by_single_district(client):
    """AC-2：按单个行政区筛选，只返回该区院校。"""
    resp = client.get("/schools", params={"district": "徐汇"})
    assert resp.status_code == 200
    rows = resp.json()
    assert rows, "徐汇区应当有院校，空结果说明筛选没生效"
    assert {row["district"] for row in rows} == {"徐汇"}


def test_filter_by_multiple_districts(client):
    """AC-3：行政区多选，多个区之间是「或」关系。"""
    resp = client.get("/schools", params=[("district", "徐汇"), ("district", "黄浦")])
    assert resp.status_code == 200
    rows = resp.json()
    assert {row["district"] for row in rows} == {"徐汇", "黄浦"}


def test_filter_by_school_type(client):
    """AC-4：按办学性质筛选，只返回民办院校。"""
    resp = client.get("/schools", params={"school_type": "民办"})
    assert resp.status_code == 200
    rows = resp.json()
    assert rows, "民办院校应当存在，空结果说明筛选没生效"
    assert {row["school_type"] for row in rows} == {"民办"}


def test_district_and_type_are_combined_with_and(client):
    """AC-5：行政区与办学性质同时传时按「且」过滤。"""
    resp = client.get("/schools", params={"district": "徐汇", "school_type": "民办"})
    assert resp.status_code == 200
    rows = resp.json()
    assert rows
    assert all(row["district"] == "徐汇" and row["school_type"] == "民办" for row in rows)


def test_invalid_school_type_returns_422(client):
    """AC-6：办学性质传非法值返回 422。"""
    resp = client.get("/schools", params={"school_type": "技校"})
    assert resp.status_code == 422


def test_target_only_returns_marked_schools(client):
    """AC-7：target_only=true 时只返回已加入目标清单的院校。"""
    assert client.get("/schools", params={"target_only": "true"}).json() == []

    client.post("/schools/1/target")
    client.post("/schools/4/target")

    rows = client.get("/schools", params={"target_only": "true"}).json()
    assert {row["id"] for row in rows} == {1, 4}
    assert all(row["is_target"] is True for row in rows)


def test_add_school_to_targets(client):
    """AC-8：加入目标清单后，该校 is_target 变为 true。"""
    resp = client.post("/schools/2/target")
    assert resp.status_code == 200
    assert resp.json()["is_target"] is True

    rows = client.get("/schools", params={"district": "徐汇"}).json()
    marked = {row["id"] for row in rows if row["is_target"]}
    assert marked == {2}


def test_remove_school_from_targets(client):
    """AC-9：移出目标清单后，该校 is_target 回到 false。"""
    client.post("/schools/2/target")
    resp = client.delete("/schools/2/target")
    assert resp.status_code == 200
    assert resp.json()["is_target"] is False

    rows = client.get("/schools").json()
    assert all(row["is_target"] is False for row in rows)


def test_add_target_on_unknown_school_returns_404(client):
    """AC-10：对不存在的院校 id 执行加入目标清单返回 404。"""
    resp = client.post("/schools/9999/target")
    assert resp.status_code == 404


def test_remove_target_on_unknown_school_returns_404(client):
    """AC-10：对不存在的院校 id 执行移出目标清单返回 404。"""
    resp = client.delete("/schools/9999/target")
    assert resp.status_code == 404


def test_options_returns_filter_candidates(client):
    """AC-11：options 接口返回行政区与办学性质候选值。"""
    resp = client.get("/schools/options")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["districts"]) == 16
    assert set(data["school_types"]) == {"公办", "民办"}

    listed = {row["district"] for row in client.get("/schools").json()}
    assert set(data["districts"]) == listed