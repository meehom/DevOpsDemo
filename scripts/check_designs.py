#!/usr/bin/env python3
"""设计门禁：检查 designs/ 下每份高保真设计是否完整、是否可直接交客户演示。

在项目根目录执行：
    python scripts/check_designs.py

任何一项不合规就返回非 0，供 CI 拦截。告警不影响退出码。
"""
import re
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import check_specs  # noqa: E402  复用 front-matter 解析，保证口径一致

ROOT = SCRIPTS_DIR.parent
DESIGNS_DIR = ROOT / "designs"

DS_ID_PATTERN = re.compile(r"^DS-\d{3}$")
VALID_STATUS = ("draft", "review", "confirmed")
STATUS_LABEL = {"draft": "草稿", "review": "待确认", "confirmed": "客户已确认"}
REQUIRED_FIELDS = ("id", "title", "status", "tool", "owner")

# mockup 必须是纯静态自包含的，客户断网打开也不能白屏
EXTERNAL_RESOURCE = re.compile(r"""(?:src|href)\s*=\s*["']https?://""", re.I)
MIN_PROMPT_CHARS = 200


def check_design(design_dir: Path):
    """返回 (元信息, 错误列表, 告警列表)。"""
    errors = []
    warnings = []

    design_md = design_dir / "design.md"
    if not design_md.exists():
        return {}, ["缺少 design.md（设计说明与元信息）"], warnings

    meta, _ = check_specs.read_front_matter(design_md)
    for field in REQUIRED_FIELDS:
        if not meta.get(field):
            errors.append(f"design.md front-matter 缺少 {field}")

    design_id = meta.get("id", "")
    if design_id and not DS_ID_PATTERN.match(design_id):
        errors.append(f"id 格式应为 DS-三位数字，当前是 {design_id!r}")

    status = meta.get("status", "")
    if status and status not in VALID_STATUS:
        errors.append(f"status 只能是 {'/'.join(VALID_STATUS)}，当前是 {status!r}")

    prompt_md = design_dir / "prompt.md"
    if not prompt_md.exists():
        errors.append("缺少 prompt.md（m3e-canvas 导出的提示词，是唯一可版本化的设计源）")
    elif len(prompt_md.read_text(encoding="utf-8").strip()) < MIN_PROMPT_CHARS:
        errors.append(f"prompt.md 内容过短（少于 {MIN_PROMPT_CHARS} 字），确认提示词已完整存档")

    mockup = design_dir / "mockup.html"
    if not mockup.exists():
        errors.append("缺少 mockup.html（全假数据的客户演示页面）")
    else:
        content = mockup.read_text(encoding="utf-8")
        if "<html" not in content.lower():
            errors.append("mockup.html 不是完整的 HTML 页面")
        if len(content) < 500:
            errors.append("mockup.html 内容过短，疑似空文件")
        external = EXTERNAL_RESOURCE.findall(content)
        if external:
            warnings.append(f"mockup.html 引用了 {len(external)} 处外部 http 资源，客户断网演示会缺样式或图标")

    shots = sorted((design_dir / "shots").glob("*.png")) if (design_dir / "shots").is_dir() else []
    if not shots:
        errors.append("缺少 shots/ 下的界面截图（画布导出或 mockup 截图至少一张）")

    if status in ("draft", "review"):
        warnings.append(f"状态为「{STATUS_LABEL[status]}」，客户未确认前不应据此拆解需求、写实现")

    return meta, errors, warnings


def main() -> int:
    if not DESIGNS_DIR.is_dir():
        print(f"错误：找不到设计目录 {DESIGNS_DIR}")
        return 1

    design_dirs = [d for d in sorted(DESIGNS_DIR.iterdir()) if d.is_dir()]
    if not design_dirs:
        print(f"错误：{DESIGNS_DIR} 下没有任何设计（项目应当先出高保真设计）")
        return 1

    failed = False
    seen_ids = {}
    warnings_total = 0

    for design_dir in design_dirs:
        meta, errors, warnings = check_design(design_dir)
        design_id = meta.get("id", "")
        if design_id:
            if design_id in seen_ids:
                errors.append(f"id 与 {seen_ids[design_id].name} 重复")
            else:
                seen_ids[design_id] = design_dir

        warnings_total += len(warnings)
        if errors:
            failed = True
            print(f"✗ {design_dir.name}")
            for error in errors:
                print(f"    - {error}")
        else:
            status = meta.get("status", "?")
            label = STATUS_LABEL.get(status, status)
            shots = len(list((design_dir / "shots").glob("*.png")))
            print(f"✓ {design_dir.name}  [{design_id} / {label}]  截图 {shots} 张")
        for warning in warnings:
            print(f"    ! {warning}")

    print()
    if failed:
        print(f"门禁未通过：{len(design_dirs)} 份设计中存在问题，请先补齐再提交。")
        return 1
    print(f"门禁通过：{len(design_dirs)} 份设计齐全（其余提示 {warnings_total} 条）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())