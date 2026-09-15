#!/usr/bin/env python3
"""生成需求验收报告：单元测试结果 + 端到端测试结果 + 每步截图。

本地（会先跑测试）：
    python scripts/acceptance_report.py REQ-001
    python scripts/acceptance_report.py --all            # 全部需求

CI（测试已在别的 job 跑过，只渲染报告）：
    python scripts/acceptance_report.py --all --skip-run

产物：
    reports/REQ-001/acceptance.html   # 自包含单文件，截图已内嵌，可直接分享
    reports/REQ-001/acceptance.md     # 纯文本版，便于检索和 diff
"""
import argparse
import base64
import html
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECS_DIR = ROOT / "specs"
REPORTS_DIR = ROOT / "reports"

ICON = {"passed": "✅", "failed": "", "error": "💥", "skipped": "⏭️"}
LABEL = {"passed": "通过", "failed": "失败", "error": "错误", "skipped": "跳过"}

CSS = """
* { box-sizing: border-box; }
body {
  margin: 0; padding: 32px 20px 60px;
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
  background: #f5f6f8; color: #1f2328; line-height: 1.6;
}
.wrap { max-width: 1080px; margin: 0 auto; }
header {
  background: #fff; border-radius: 12px; padding: 28px 32px;
  box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 20px;
}
h1 { margin: 0 0 6px; font-size: 22px; }
.sub { color: #656d76; font-size: 13px; margin-bottom: 20px; }
.verdict {
  display: inline-block; padding: 8px 18px; border-radius: 999px;
  font-size: 15px; font-weight: 600;
}
.verdict.ok { background: #e7f6ec; color: #1a7f37; }
.verdict.bad { background: #fdeceb; color: #c93c37; }
.verdict.warn { background: #fff5e0; color: #9a6700; }
.cards { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 22px; }
.card {
  flex: 1 1 150px; background: #f9fafb; border: 1px solid #e6e8eb;
  border-radius: 10px; padding: 14px 16px;
}
.card .label { font-size: 12px; color: #656d76; }
.card .value { font-size: 22px; font-weight: 700; margin-top: 2px; }
.card .value.ok { color: #1a7f37; }
.card .value.bad { color: #c93c37; }
section {
  background: #fff; border-radius: 12px; padding: 24px 32px;
  box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 20px;
}
h2 { font-size: 17px; margin: 0 0 16px; padding-bottom: 10px; border-bottom: 1px solid #e6e8eb; }
ul.criteria { margin: 0; padding-left: 22px; }
ul.criteria li { margin-bottom: 6px; }
code {
  background: #eff1f3; padding: 1px 6px; border-radius: 5px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px;
}
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #eaecef; }
th { color: #656d76; font-weight: 600; font-size: 13px; }
td.status.ok { color: #1a7f37; }
td.status.bad { color: #c93c37; }
.case { border: 1px solid #e6e8eb; border-radius: 10px; padding: 16px 18px; margin-bottom: 16px; }
.case > .head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.case .name { font-weight: 600; font-family: ui-monospace, Menlo, monospace; font-size: 14px; }
.case .time { color: #656d76; font-size: 12px; margin-left: auto; }
.shots { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; margin-top: 14px; }
.shot { margin: 0; }
.shot img {
  width: 100%; border: 1px solid #d8dbe0; border-radius: 8px; display: block;
  cursor: zoom-in; background: #fff;
}
.shot figcaption { font-size: 12px; color: #656d76; margin-top: 6px; word-break: break-all; }
.failure {
  background: #fff5f5; border-left: 3px solid #c93c37; border-radius: 6px;
  padding: 12px 14px; margin-top: 12px; font-size: 13px;
  font-family: ui-monospace, Menlo, monospace; white-space: pre-wrap; color: #4b1113;
}
.empty { color: #8b949e; font-size: 14px; }
#lightbox {
  display: none; position: fixed; inset: 0; background: rgba(0,0,0,.82);
  z-index: 99; padding: 30px; cursor: zoom-out; align-items: center; justify-content: center;
}
#lightbox.open { display: flex; }
#lightbox img { max-width: 100%; max-height: 100%; border-radius: 8px; }
"""

JS = """
document.querySelectorAll('.shot img').forEach(function (img) {
  img.addEventListener('click', function () {
    var box = document.getElementById('lightbox');
    box.querySelector('img').src = img.src;
    box.classList.add('open');
  });
});
document.getElementById('lightbox').addEventListener('click', function () {
  this.classList.remove('open');
});
"""


def find_spec(req_id: str):
    """按需求 ID 找到需求文档。"""
    for path in sorted(SPECS_DIR.glob("*.md")):
        if path.name == "TEMPLATE.md":
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(rf"^id:\s*{re.escape(req_id)}\s*$", text, re.M):
            return path
    return None


def spec_meta(spec_path: Path):
    """返回 (需求标题, 验收标准列表)。"""
    text = spec_path.read_text(encoding="utf-8")
    title = ""
    for line in text.splitlines():
        if line.startswith("title:"):
            title = line.partition(":")[2].strip()
            break
    section = re.search(r"^##\s*验收标准\s*$(.*?)(?=^##\s|\Z)", text, re.S | re.M)
    criteria = []
    if section:
        for line in section.group(1).splitlines():
            if re.match(r"^\s*[-*]\s+\S", line):
                criteria.append(re.sub(r"^[-*]\s*(\[[ x]\]\s*)?", "", line).strip())
    return title, criteria


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
        detail = ""
        for tag in ("failure", "error", "skipped"):
            node = case.find(tag)
            if node is not None:
                status = tag
                detail = (node.get("message") or "").strip() or (node.text or "").strip()
                break
        cases.append(
            {
                "name": re.sub(r"\[.*\]$", "", case.get("name", "")),
                "status": status,
                "duration": float(case.get("time") or 0),
                "detail": detail,
            }
        )
    return cases


def collect_screenshots(req_id: str):
    """返回 {用例名: [截图文件路径, ...]}。"""
    root = REPORTS_DIR / req_id / "screenshots"
    shots = {}
    if not root.is_dir():
        return shots
    for case_dir in sorted(root.iterdir()):
        if case_dir.is_dir():
            shots[case_dir.name] = sorted(case_dir.glob("*.png"))
    return shots


def summarize(cases):
    """返回 (总数, 通过数, 失败数, 总耗时秒)。"""
    cases = cases or []
    passed = sum(1 for c in cases if c["status"] == "passed")
    return len(cases), passed, len(cases) - passed, sum(c["duration"] for c in cases)


def relative_spec(spec_path: Path) -> Path:
    return Path("..", "..", spec_path.relative_to(ROOT))


# ---------------- Markdown ----------------

def markdown_case_section(cases, shots):
    if not cases:
        return "未找到该需求的用例（可能没跑测试）。\n"
    total, passed, failed, _ = summarize(cases)
    lines = [f"共 {total} 个：{passed} 通过 / {failed} 未通过", ""]
    lines += ["| 用例 | 结果 | 耗时 |", "|---|---|---|"]
    for case in cases:
        lines.append(
            f"| {case['name']} | {ICON.get(case['status'], '')} {case['status']} | {case['duration']:.2f}s |"
        )
    lines.append("")
    for case in cases:
        images = shots.get(case["name"])
        if not images:
            continue
        lines += [f"### {ICON.get(case['status'], '')} {case['name']}", "", "| 步骤截图 |", "|---|"]
        for image in images:
            step_name = image.stem
            lines.append(f"| ![{step_name}](screenshots/{case['name']}/{image.name}) |")
        lines.append("")
    return "\n".join(lines)


def render_markdown(req_id, spec_path, title, criteria, unit_cases, e2e_cases, shots, verdict, now):
    lines = [
        f"# {req_id} 验收报告",
        "",
        f"> {title}" if title else "",
        "",
        "| 项目 | 值 |",
        "|---|---|",
        f"| 需求文档 | [{spec_path.name}]({relative_spec(spec_path)}) |",
        f"| 生成时间 | {now} |",
        f"| 结论 | {verdict['text']} |",
        "",
        "## 验收标准",
        "",
    ]
    lines += [f"- {item}" for item in criteria] or ["（需求文档中未填写）"]
    lines += ["", "## 单元测试", "", markdown_case_section(unit_cases, {})]
    lines += ["", "## 端到端测试", "", markdown_case_section(e2e_cases, shots)]
    return "\n".join(lines)


# ---------------- HTML ----------------

def esc(text: str) -> str:
    return html.escape(text)


def esc_code(text: str) -> str:
    """转义并把 `反引号` 转成 <code>。"""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(text))


def data_uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def html_case_cards(cases, shots, embed):
    if not cases:
        return '<p class="empty">未找到该需求的用例（可能没跑测试）。</p>'
    parts = []
    for case in cases:
        ok = case["status"] == "passed"
        parts.append('<div class="case">')
        parts.append(
            '<div class="head">'
            f'<span>{"✅" if ok else ""}</span>'
            f'<span class="name">{esc(case["name"])}</span>'
            f'<span class="time">{case["duration"]:.2f}s</span>'
            "</div>"
        )
        if not ok and case["detail"]:
            parts.append(f'<div class="failure">{esc(case["detail"])}</div>')
        images = shots.get(case["name"])
        if images:
            parts.append('<div class="shots">')
            for image in images:
                src = data_uri(image) if embed else f"screenshots/{case['name']}/{image.name}"
                parts.append(
                    '<figure class="shot">'
                    f'<img src="{src}" alt="{esc(image.stem)}">'
                    f"<figcaption>{esc(image.stem)}</figcaption>"
                    "</figure>"
                )
            parts.append("</div>")
        parts.append("</div>")
    return "\n".join(parts)


def html_case_table(cases, shots):
    if not cases:
        return '<p class="empty">无。</p>'
    rows = []
    for case in cases:
        ok = case["status"] == "passed"
        images = shots.get(case["name"]) or []
        shots_cell = (
            f'<a href="#{esc(case["name"])}">{len(images)} 张</a>' if images else "—"
        )
        rows.append(
            "<tr>"
            f'<td id="{esc(case["name"])}"><code>{esc(case["name"])}</code></td>'
            f'<td class="status {"ok" if ok else "bad"}">'
            f'{ICON.get(case["status"], "")} {LABEL.get(case["status"], case["status"])}</td>'
            f'<td>{case["duration"]:.2f}s</td>'
            f"<td>{shots_cell}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>用例</th><th>结果</th><th>耗时</th><th>步骤截图</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def render_html(req_id, spec_path, title, criteria, unit_cases, e2e_cases, shots, verdict, now, embed):
    unit_total, unit_passed, unit_failed, unit_time = summarize(unit_cases)
    e2e_total, e2e_passed, e2e_failed, e2e_time = summarize(e2e_cases)
    shot_count = sum(len(v) for v in shots.values())

    criteria_html = (
        "<ul class='criteria'>"
        + "".join(f"<li>{esc_code(item)}</li>" for item in criteria)
        + "</ul>"
        if criteria
        else '<p class="empty">需求文档中未填写验收标准。</p>'
    )

    def card(label, value, state=""):
        return (
            f'<div class="card"><div class="label">{label}</div>'
            f'<div class="value {state}">{value}</div></div>'
        )

    cards = "".join(
        [
            card("单元测试", f"{unit_passed}/{unit_total}", "ok" if unit_failed == 0 and unit_total else "bad"),
            card("端到端测试", f"{e2e_passed}/{e2e_total}", "ok" if e2e_failed == 0 and e2e_total else "bad"),
            card("步骤截图", str(shot_count)),
            card("总耗时", f"{unit_time + e2e_time:.2f}s"),
        ]
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(req_id)} 验收报告</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>{esc(req_id)} 验收报告</h1>
    <div class="sub">{esc(title) if title else ""} · {esc(now)} · 需求文档 <code>{esc(spec_path.name)}</code></div>
    <span class="verdict {verdict['cls']}">{verdict['icon']} {esc(verdict['text'])}</span>
    <div class="cards">{cards}</div>
  </header>

  <section>
    <h2>验收标准</h2>
    {criteria_html}
  </section>

  <section>
    <h2>单元测试</h2>
    {html_case_table(unit_cases, {})}
  </section>

  <section>
    <h2>端到端测试</h2>
    {html_case_table(e2e_cases, shots)}
  </section>

  <section>
    <h2>端到端测试逐步截图</h2>
    {html_case_cards(e2e_cases, shots, embed)}
  </section>
</div>

<div id="lightbox"><img alt="放大截图"></div>
<script>{JS}</script>
</body>
</html>"""


def all_req_ids():
    """列出 specs/ 下所有需求 ID。"""
    ids = []
    for path in sorted(SPECS_DIR.glob("*.md")):
        if path.name == "TEMPLATE.md":
            continue
        matched = re.search(r"^id:\s*(\S+)\s*$", path.read_text(encoding="utf-8"), re.M)
        if matched:
            ids.append(matched.group(1))
    return ids


def build_report(req_id: str, args) -> bool:
    """生成单个需求的验收报告，返回是否存在问题（失败或无测试结果）。"""
    spec_path = find_spec(req_id)
    if spec_path is None:
        print(f"错误：在 {SPECS_DIR} 下找不到 id 为 {req_id} 的需求文档")
        return True

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
    title, criteria = spec_meta(spec_path)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    all_cases = (unit_cases or []) + (e2e_cases or [])
    failed = [c for c in all_cases if c["status"] != "passed"]
    if not all_cases:
        verdict = {"text": "无测试结果", "icon": "⚠️", "cls": "warn"}
    elif failed:
        verdict = {"text": f"未通过（{len(failed)} 个用例失败）", "icon": "❌", "cls": "bad"}
    else:
        verdict = {"text": "全部通过", "icon": "✅", "cls": "ok"}

    md_path = report_dir / "acceptance.md"
    md_path.write_text(
        render_markdown(req_id, spec_path, title, criteria, unit_cases, e2e_cases, shots, verdict, now),
        encoding="utf-8",
    )
    html_path = report_dir / "acceptance.html"
    html_path.write_text(
        render_html(
            req_id, spec_path, title, criteria, unit_cases, e2e_cases, shots, verdict, now,
            embed=not args.no_embed,
        ),
        encoding="utf-8",
    )

    size_kb = html_path.stat().st_size / 1024
    print(f"{req_id} 验收报告：{html_path.relative_to(ROOT)}  ({size_kb:.0f} KB)")
    print(f"{req_id} 结论：{verdict['icon']} {verdict['text']}")

    return bool(failed) or not all_cases


def main() -> int:
    parser = argparse.ArgumentParser(description="生成需求验收报告（HTML + Markdown）")
    parser.add_argument("req_id", nargs="?", help="需求 ID，例如 REQ-001；不填时需配合 --all")
    parser.add_argument("--all", action="store_true", help="为 specs/ 下的所有需求生成报告")
    parser.add_argument("--skip-run", action="store_true", help="跳过测试执行，只用已有结果渲染报告")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="端到端测试访问的地址")
    parser.add_argument("--no-embed", action="store_true", help="HTML 里用相对路径引用截图，不内嵌 base64")
    args = parser.parse_args()

    if args.all:
        targets = all_req_ids()
        if not targets:
            print(f"错误：{SPECS_DIR} 下没有任何需求文档")
            return 1
    elif args.req_id:
        targets = [args.req_id.upper()]
    else:
        parser.error("需要指定需求 ID，或使用 --all 为所有需求生成报告")

    problems = [build_report(req_id, args) for req_id in targets]
    print(f"\n共处理 {len(targets)} 个需求，其中 {sum(problems)} 个有问题。")
    return 1 if any(problems) else 0


if __name__ == "__main__":
    sys.exit(main())