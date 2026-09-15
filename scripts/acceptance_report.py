#!/usr/bin/env python3
"""生成需求验收报告：单元测试结果 + 端到端测试结果 + 每步截图。

本地（会先跑测试）：
    python scripts/acceptance_report.py REQ-001

CI（测试已在别的 job 跑过，只渲染报告）：
    python scripts/acceptance_report.py REQ-001 --skip-run

产物：
    reports/REQ-001/acceptance.md
"""
import argparse
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECS_DIR = ROOT / "specs"
REPORTS_DIR = ROOT / "reports"

ICON = {"passed": "✅", "failed": "❌", "error": "", "skipped": "⏭️"}


def find_spec(req_id: str):
    """按需求 ID 找到需求文档。"""
    for path in sorted(SPECS_DIR.glob("*.md")):
        if path.name == "TEMPLATE.md":
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(rf"^id:\s*{re.escape(req_id)}\s*$", text, re.M):
            return path
    return None


def spec_criteria(spec_path: Path):
    """提取需求文档里的验收标准条目。"""
    body = spec_path.read_text(encoding="utf-8")
    section = re.search(r"^##\s*验收标准\s*$(.*?)(?=^##\s|\Z)", body, re.S | re.M)
    if not section:
        return []
    return [
        re.sub(r"^[-*]\s*(\[[ x]\]\s*)?", "", line).strip()
        for line in section.group(1).splitlines()
        if re.match(r"^\s*[-*]\s+\S", line)
    ]


def run(command, title):
    """执行测试命令，输出直接透传到终端。"""
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}", flush=True)
    return subprocess.run(command, cwd=ROOT).returncode


def parse_junit(path: Path, keyword: str):
    """解析 junit XML，只保留文件名含 keyword 的用例。"""
    if not path.exists():
        return None
    cases = []
    for case in ET.parse(path).iter("testcase"):
        haystack = " ".join(
            filter(None, (case.get("classname"), case.get("file"), case.get("name")))
        ).lower()
        if keyword not in haystack:
            continue
        status = "passed"
        for tag in ("failure", "error", "skipped"):
            if case.find(tag) is not None:
                status = tag
                break
        cases.append(
            {
                "name": re.sub(r"\[.*\]$", "", case.get("name", "")),
                "status": status,
                "duration": float(case.get("time") or 0),
            }
        )
    return cases


def collect_screenshots(req_id: str):
    """返回 {用例名: [截图相对路径]}，路径相对于报告文件所在目录。"""
    root = REPORTS_DIR / req_id / "screenshots"
    shots = {}
    if not root.is_dir():
        return shots
    for case_dir in sorted(root.iterdir()):
        if case_dir.is_dir():
            shots[case_dir.name] = [f"screenshots/{case_dir.name}/{p.name}" for p in sorted(case_dir.glob("*.png"))]
    return shots


def render_case_section(cases, shots):
    """渲染一个测试类型的明细小节。"""
    lines = []
    if not cases:
        return "未找到该需求的用例（可能没跑测试）。\n"
    passed = sum(1 for c in cases if c["status"] == "passed")
    lines.append(f"共 {len(cases)} 个：{passed} 通过 / {len(cases) - passed} 未通过\n")
    lines.append("| 用例 | 结果 | 耗时 |")
    lines.append("|---|---|---|")
    for case in cases:
        lines.append(f"| {case['name']} | {ICON.get(case['status'], case['status'])} {case['status']} | {case['duration']:.2f}s |")
    lines.append("")

    for case in cases:
        shots_for_case = shots.get(case["name"])
        if not shots_for_case:
            continue
        lines.append(f"### {ICON.get(case['status'], '')} {case['name']}")
        lines.append("")
        lines.append("| 步骤截图 |")
        lines.append("|---|")
        for shot in shots_for_case:
            step_name = Path(shot).stem
            lines.append(f"| ![{step_name}]({shot}) |")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="生成需求验收报告")
    parser.add_argument("req_id", help="需求 ID，例如 REQ-001")
    parser.add_argument("--skip-run", action="store_true", help="跳过测试执行，只用已有结果渲染报告")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="端到端测试访问的地址")
    args = parser.parse_args()

    req_id = args.req_id.upper()
    spec_path = find_spec(req_id)
    if spec_path is None:
        print(f"错误：在 {SPECS_DIR} 下找不到 id 为 {req_id} 的需求文档")
        return 1

    keyword = req_id.lower().replace("-", "_")
    report_dir = REPORTS_DIR / req_id
    report_dir.mkdir(parents=True, exist_ok=True)
    junit_unit = REPORTS_DIR / "junit-unit.xml"
    junit_e2e = REPORTS_DIR / "junit-e2e.xml"

    if not args.skip_run:
        run(
            [
                sys.executable, "-m", "pytest", "tests",
                "-m", "not e2e", "-k", keyword,
                "-o", "addopts=-v",
                f"--junitxml={junit_unit}",
            ],
            f"运行单元测试 ({req_id})",
        )
        run(
            [
                sys.executable, "-m", "pytest", "tests/e2e",
                "-m", "e2e", "-k", keyword,
                "-o", "addopts=-v",
                f"--base-url={args.base_url}",
                f"--junitxml={junit_e2e}",
                "--screenshot=only-on-failure",
                "--tracing=retain-on-failure",
            ],
            f"运行端到端测试 ({req_id})",
        )

    unit_cases = parse_junit(junit_unit, keyword)
    e2e_cases = parse_junit(junit_e2e, keyword)
    shots = collect_screenshots(req_id)

    all_cases = (unit_cases or []) + (e2e_cases or [])
    failed = [c for c in all_cases if c["status"] != "passed"]
    if not all_cases:
        verdict = "⚠️ 无测试结果"
    elif failed:
        verdict = f"❌ 未通过（{len(failed)} 个用例失败）"
    else:
        verdict = "✅ 全部通过"

    criteria = spec_criteria(spec_path)
    relative_spec = Path("..", "..", spec_path.relative_to(ROOT))

    lines = [
        f"# {req_id} 验收报告",
        "",
        "| 项目 | 值 |",
        "|---|---|",
        f"| 需求文档 | [{spec_path.name}]({relative_spec}) |",
        f"| 生成时间 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |",
        f"| 结论 | {verdict} |",
        "",
        "## 验收标准",
        "",
    ]
    lines += [f"- {item}" for item in criteria] or ["（需求文档中未填写）"]
    lines += ["", "## 单元测试", "", render_case_section(unit_cases or [], {})]
    lines += ["", "## 端到端测试", "", render_case_section(e2e_cases or [], shots)]

    report_path = report_dir / "acceptance.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n验收报告已生成：{report_path.relative_to(ROOT)}")
    print(f"结论：{verdict}")

    return 1 if failed or not all_cases else 0


if __name__ == "__main__":
    sys.exit(main())