#!/usr/bin/env python3
"""需求门禁：检查 specs/ 下每个需求文档是否都有对应的单元测试和端到端测试。

在项目根目录执行：
    python scripts/check_specs.py

任何一项不合规就返回非 0，供 CI 拦截。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECS_DIR = ROOT / "specs"
TESTS_DIR = ROOT / "tests"

REQ_ID_PATTERN = re.compile(r"^REQ-\d{3}$")
TEMPLATE_NAME = "TEMPLATE.md"


def read_front_matter(path: Path):
    """返回 (元信息字典, 正文)。没有 front-matter 时元信息为空字典。"""
    text = path.read_text(encoding="utf-8")
    matched = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not matched:
        return {}, text
    meta = {}
    for line in matched.group(1).splitlines():
        key, separator, value = line.partition(":")
        if separator:
            meta[key.strip()] = value.strip()
    return meta, text[matched.end():]


def acceptance_criteria(body: str):
    """提取「验收标准」小节下的列表条目。"""
    section = re.search(r"^##\s*验收标准\s*$(.*?)(?=^##\s|\Z)", body, re.S | re.M)
    if not section:
        return []
    return [
        line.strip()
        for line in section.group(1).splitlines()
        if re.match(r"^\s*[-*]\s+\S", line)
    ]


def collect_specs():
    """返回 [(需求文档路径, 元信息, 验收标准列表, 错误列表)]。"""
    results = []
    for path in sorted(SPECS_DIR.glob("*.md")):
        if path.name == TEMPLATE_NAME:
            continue
        meta, body = read_front_matter(path)
        criteria = acceptance_criteria(body)
        errors = []

        req_id = meta.get("id", "")
        if not req_id:
            errors.append("front-matter 缺少 id")
        elif not REQ_ID_PATTERN.match(req_id):
            errors.append(f"id 格式应为 REQ-三位数字，当前是 {req_id!r}")

        for field in ("title", "status", "owner"):
            if not meta.get(field):
                errors.append(f"front-matter 缺少 {field}")

        if not criteria:
            errors.append("「验收标准」小节为空或格式不对（需要 - 开头的列表条目）")

        results.append((path, meta, criteria, errors))
    return results


def check_test_files(req_id: str):
    """返回该需求缺失的测试类型列表。"""
    lower = req_id.lower().replace("-", "_")
    missing = []

    unit = list(TESTS_DIR.glob(f"test_{lower}*.py"))
    e2e = list(TESTS_DIR.glob(f"e2e/test_{lower}*.py"))
    if not unit:
        missing.append(f"缺少单元测试 tests/test_{lower}*.py")
    if not e2e:
        missing.append(f"缺少端到端测试 tests/e2e/test_{lower}*.py")
    return missing


def main() -> int:
    if not SPECS_DIR.is_dir():
        print(f"错误：找不到需求目录 {SPECS_DIR}")
        return 1

    specs = collect_specs()
    if not specs:
        print(f"错误：{SPECS_DIR} 下没有任何需求文档（模板 {TEMPLATE_NAME} 不算）")
        return 1

    failed = False
    seen_ids = {}

    for path, meta, criteria, errors in specs:
        req_id = meta.get("id", "")
        if req_id:
            if req_id in seen_ids:
                errors.append(f"id 与 {seen_ids[req_id].name} 重复")
            else:
                seen_ids[req_id] = path
        if not errors:
            errors.extend(check_test_files(req_id))

        if errors:
            failed = True
            print(f"✗ {path.name}")
            for error in errors:
                print(f"    - {error}")
        else:
            status = meta.get("status", "?")
            print(f"✓ {path.name}  [{req_id} / {status}]  验收标准 {len(criteria)} 条")

    print()
    if failed:
        print(f"门禁未通过：{len(specs)} 个需求文档存在问题，请先补齐再提交。")
        return 1
    print(f"门禁通过：{len(specs)} 个需求文档均有单测与端到端测试。")
    return 0


if __name__ == "__main__":
    sys.exit(main())