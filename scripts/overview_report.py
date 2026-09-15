#!/usr/bin/env python3
"""需求总览报告：横向汇总所有需求的状态、测试覆盖、缺口和验收报告入口。

在项目根目录执行：
    python scripts/overview_report.py

产物：
    reports/overview.html   # 自包含单文件
    reports/overview.md     # 纯文本版
"""
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import check_specs  # noqa: E402  复用门禁的解析逻辑，保证口径一致
from acceptance_report import (  # noqa: E402
    CSS as BASE_CSS,
    esc,
    parse_junit,
)

ROOT = SCRIPTS_DIR.parent
SPECS_DIR = ROOT / "specs"
TESTS_DIR = ROOT / "tests"
REPORTS_DIR = ROOT / "reports"

STATUS_CLASS = {"done": "done", "in-progress": "wip", "draft": "draft"}
STATUS_LABEL = {"done": "已完成", "in-progress": "进行中", "draft": "草稿"}

EXTRA_CSS = """
a { color: #0969da; text-decoration: none; }
a:hover { text-decoration: underline; }
.badge { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 12px; }
.badge.done { background: #e7f6ec; color: #1a7f37; }
.badge.wip { background: #fff5e0; color: #9a6700; }
.badge.draft { background: #eff1f3; color: #656d76; }
table.tight td, table.tight th { font-size: 13px; padding: 10px 8px; vertical-align: top; }
table.tight td:first-child { min-width: 190px; }
.file { display: block; color: #656d76; font-size: 12px; word-break: break-all; }
.num { font-variant-numeric: tabular-nums; color: #656d76; font-size: 12px; }
ul.gaps { margin: 0; padding-left: 20px; }
ul.gaps li { margin-bottom: 8px; }
ul.gaps li.err { color: #c93c37; }
ul.gaps li.warn { color: #9a6700; }
ul.gaps li.info { color: #656d76; }
.ok-text { color: #1a7f37; }
.bad-text { color: #c93c37; }
"""


def count_test_cases(paths):
    """静态统计测试文件里的用例数量。"""
    total = 0
    for path in paths:
        total += len(re.findall(r"^\s*def test_", path.read_text(encoding="utf-8"), re.M))
    return total


def collect_requirements():
    """扫描 specs/ 汇总每个需求的信息。"""
    requirements = []
    for spec_path in sorted(SPECS_DIR.glob("*.md")):
        if spec_path.name == check_specs.TEMPLATE_NAME:
            continue

        meta, body = check_specs.read_front_matter(spec_path)
        criteria = check_specs.acceptance_criteria(body)
        req_id = meta.get("id", "")
        keyword = req_id.lower().replace("-", "_")

        unit_files = sorted(TESTS_DIR.glob(f"test_{keyword}*.py")) if req_id else []
        e2e_files = sorted(TESTS_DIR.glob(f"e2e/test_{keyword}*.py")) if req_id else []

        unit_cases = parse_junit(REPORTS_DIR / "junit-unit.xml", keyword) if req_id else None
        e2e_cases = parse_junit(REPORTS_DIR / "junit-e2e.xml", keyword) if req_id else None

        report_path = REPORTS_DIR / req_id / "acceptance.html" if req_id else None

        requirements.append(
            {
                "id": req_id or "(缺少 id)",
                "title": meta.get("title", ""),
                "status": meta.get("status", "draft"),
                "owner": meta.get("owner", ""),
                "spec": spec_path,
                "criteria": len(criteria),
                "unit_files": unit_files,
                "e2e_files": e2e_files,
                "unit_count": count_test_cases(unit_files),
                "e2e_count": count_test_cases(e2e_files),
                "unit_cases": unit_cases,
                "e2e_cases": e2e_cases,
                "report": report_path if report_path and report_path.exists() else None,
                "gate_errors": (check_specs.check_test_files(req_id) if req_id else ["front-matter 缺少 id"]),
            }
        )
    return requirements


def collect_unmanaged_tests(requirements):
    """找出没有关联到任何需求文档的测试文件。"""
    managed = set()
    for req in requirements:
        managed.update(req["unit_files"])
        managed.update(req["e2e_files"])

    known_ids = {req["id"].lower().replace("-", "_") for req in requirements}
    unmanaged = []
    for path in sorted(TESTS_DIR.rglob("test_*.py")):
        if path in managed:
            continue
        matched = re.search(r"req_(\d{3})", path.name)
        if matched and f"req_{matched.group(1)}" in known_ids:
            continue
        reason = f"引用了不存在的需求 REQ-{matched.group(1)}" if matched else "没有任何需求文档引用"
        unmanaged.append({"path": path, "cases": count_test_cases([path]), "reason": reason})
    return unmanaged


def build_gaps(requirements, unmanaged):
    """汇总缺口与风险，按严重程度分成 err / warn / info。"""
    gaps = []
    for req in requirements:
        for error in req["gate_errors"]:
            gaps.append(("err", f'{req["id"]} {error}（Spec Check 会拦下流水线）'))
        if req["criteria"] == 0:
            gaps.append(("err", f'{req["id"]} 验收标准为空，无法判定是否做完'))
        if req["status"] != "done" and not req["gate_errors"]:
            label = STATUS_LABEL.get(req["status"], req["status"])
            gaps.append(("warn", f'{req["id"]} 状态为「{label}」，尚未交付'))
        if not req["report"] and not req["gate_errors"]:
            gaps.append(("info", f'{req["id"]} 还没有验收报告产物，本地跑一次 acceptance_report.py 即可生成'))
        for cases, kind in ((req["unit_cases"], "单元测试"), (req["e2e_cases"], "端到端测试")):
            failed = [c for c in (cases or []) if c["status"] != "passed"]
            if failed:
                gaps.append(("err", f'{req["id"]} 最近一次{kind}有 {len(failed)} 个用例失败'))
    for item in unmanaged:
        gaps.append(
            ("warn", f'{item["path"].relative_to(ROOT)} 未纳入需求管理（{item["reason"]}，{item["cases"]} 个用例）')
        )
    return gaps


def summarize_status(requirements):
    """返回 {状态: 数量}。"""
    counts = {}
    for req in requirements:
        counts[req["status"]] = counts.get(req["status"], 0) + 1
    return counts


def result_cell(cases):
    """渲染「最近一次测试结果」单元格。"""
    if cases is None:
        return '<span class="num">无记录</span>'
    passed = sum(1 for c in cases if c["status"] == "passed")
    if passed == len(cases):
        return f'<span class="ok-text">✅ {passed}/{len(cases)}</span>'
    return f'<span class="bad-text"> {passed}/{len(cases)}</span>'


def files_cell(files, count):
    """渲染测试文件与用例数单元格。"""
    if not files:
        return '<span class="bad-text">缺失</span>'
    names = "".join(f'<span class="file">{esc(f.name)}</span>' for f in files)
    return f'{names}<span class="num">{count} 个用例</span>'


def render_html(requirements, unmanaged, gaps, now):
    total_criteria = sum(r["criteria"] for r in requirements)
    total_unit = sum(r["unit_count"] for r in requirements)
    total_e2e = sum(r["e2e_count"] for r in requirements)
    passed_gate = sum(1 for r in requirements if not r["gate_errors"])
    status_counts = summarize_status(requirements)
    errors = [g for g in gaps if g[0] == "err"]

    def card(label, value, state=""):
        return (
            f'<div class="card"><div class="label">{label}</div>'
            f'<div class="value {state}">{value}</div></div>'
        )

    cards = "".join(
        [
            card("需求总数", str(len(requirements))),
            card("验收标准", str(total_criteria)),
            card("单测用例", str(total_unit)),
            card("E2E 用例", str(total_e2e)),
            card(
                "门禁合规",
                f"{passed_gate}/{len(requirements)}",
                "ok" if passed_gate == len(requirements) else "bad",
            ),
        ]
    )

    status_tags = "".join(
        f'<span class="badge {STATUS_CLASS.get(status, "draft")}">'
        f'{STATUS_LABEL.get(status, status)} {count}</span> '
        for status, count in sorted(status_counts.items())
    )

    rows = []
    for req in requirements:
        status = req["status"]
        report_cell = (
            f'<a href="{req["id"]}/acceptance.html">acceptance.html</a>'
            if req["report"]
            else '<span class="num">未生成</span>'
        )
        rows.append(
            "<tr>"
            f'<td><code>{esc(req["id"])}</code><br>{esc(req["title"])}</td>'
            f'<td><span class="badge {STATUS_CLASS.get(status, "draft")}">'
            f'{STATUS_LABEL.get(status, status)}</span></td>'
            f'<td class="num">{req["criteria"]} 条</td>'
            f'<td>{files_cell(req["unit_files"], req["unit_count"])}</td>'
            f'<td>{files_cell(req["e2e_files"], req["e2e_count"])}</td>'
            f'<td>{result_cell(req["unit_cases"])}</td>'
            f'<td>{result_cell(req["e2e_cases"])}</td>'
            f"<td>{report_cell}</td>"
            "</tr>"
        )
    table = (
        "<table class='tight'><thead><tr>"
        "<th>需求</th><th>状态</th><th>验收标准</th><th>单元测试</th><th>端到端测试</th>"
        "<th>单测结果</th><th>E2E 结果</th><th>验收报告</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )

    if gaps:
        gaps_html = "<ul class='gaps'>" + "".join(
            f"<li class='{level}'>{esc(text)}</li>" for level, text in gaps
        ) + "</ul>"
    else:
        gaps_html = '<p class="empty">没有任何缺口，全部需求都有单测、E2E 和验收报告。</p>'

    if unmanaged:
        unmanaged_html = (
            "<table class='tight'><thead><tr><th>测试文件</th><th>用例数</th><th>原因</th></tr></thead><tbody>"
            + "".join(
                f'<tr><td><code>{esc(str(item["path"].relative_to(ROOT)))}</code></td>'
                f'<td class="num">{item["cases"]}</td><td>{esc(item["reason"])}</td></tr>'
                for item in unmanaged
            )
            + "</tbody></table>"
        )
    else:
        unmanaged_html = '<p class="empty">所有测试文件都已关联到需求文档。</p>'

    verdict_cls = "bad" if errors else ("warn" if gaps else "ok")
    verdict_text = (
        f"{len(errors)} 项门禁级问题" if errors else ("全部正常" if not gaps else f"{len(gaps)} 项待办")
    )
    verdict_icon = "❌" if errors else ("⚠️" if gaps else "✅")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>需求总览报告</title>
<style>{BASE_CSS}{EXTRA_CSS}</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>需求总览报告</h1>
    <div class="sub">生成时间 {esc(now)} · 共 {len(requirements)} 个需求</div>
    <span class="verdict {verdict_cls}">{verdict_icon} {esc(verdict_text)}</span>
    <div class="cards">{cards}</div>
    <div style="margin-top:16px">{status_tags}</div>
  </header>

  <section>
    <h2>需求明细</h2>
    {table}
  </section>

  <section>
    <h2>缺口与风险（{len(gaps)}）</h2>
    {gaps_html}
  </section>

  <section>
    <h2>未纳入需求管理的测试（{len(unmanaged)}）</h2>
    {unmanaged_html}
  </section>
</div>
</body>
</html>"""


def render_markdown(requirements, unmanaged, gaps, now):
    total_unit = sum(r["unit_count"] for r in requirements)
    total_e2e = sum(r["e2e_count"] for r in requirements)
    passed_gate = sum(1 for r in requirements if not r["gate_errors"])

    lines = [
        "# 需求总览报告",
        "",
        f"- 生成时间：{now}",
        f"- 需求总数：{len(requirements)}（门禁合规 {passed_gate}/{len(requirements)}）",
        f"- 用例总数：单测 {total_unit} / E2E {total_e2e}",
        "",
        "## 需求明细",
        "",
        "| 需求 | 标题 | 状态 | 验收标准 | 单测用例 | E2E 用例 | 验收报告 |",
        "|---|---|---|---|---|---|---|",
    ]
    for req in requirements:
        report = f"[acceptance.html]({req['id']}/acceptance.html)" if req["report"] else "未生成"
        lines.append(
            f"| {req['id']} | {req['title']} | {req['status']} | {req['criteria']} 条 "
            f"| {req['unit_count']} | {req['e2e_count']} | {report} |"
        )

    lines += ["", f"## 缺口与风险（{len(gaps)}）", ""]
    lines += [f"- [{level}] {text}" for level, text in gaps] or ["- 无"]

    lines += ["", f"## 未纳入需求管理的测试（{len(unmanaged)}）", ""]
    lines += [
        f"- {item['path'].relative_to(ROOT)}：{item['reason']}，{item['cases']} 个用例"
        for item in unmanaged
    ] or ["- 无"]
    return "\n".join(lines)


def main() -> int:
    requirements = collect_requirements()
    if not requirements:
        print(f"错误：{SPECS_DIR} 下没有任何需求文档")
        return 1

    unmanaged = collect_unmanaged_tests(requirements)
    gaps = build_gaps(requirements, unmanaged)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    html_path = REPORTS_DIR / "overview.html"
    html_path.write_text(render_html(requirements, unmanaged, gaps, now), encoding="utf-8")
    md_path = REPORTS_DIR / "overview.md"
    md_path.write_text(render_markdown(requirements, unmanaged, gaps, now), encoding="utf-8")

    errors = [g for g in gaps if g[0] == "err"]
    non_compliant = [r for r in requirements if r["gate_errors"]]
    print(f"需求总数 {len(requirements)}：门禁合规 {len(requirements) - len(non_compliant)}/{len(requirements)}")
    print(f"总览报告已生成：{html_path.relative_to(ROOT)}")
    print(f"                {md_path.relative_to(ROOT)}")
    if errors:
        print(f"\n门禁级问题 {len(errors)} 项：")
        for _, text in errors:
            print(f"  - {text}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())