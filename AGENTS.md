# 项目协作规则

本项目是 vibe coding 项目，采用「**先写需求 → 再写测试 → 最后交验收报告**」的流程。
以下规则对 AI coding agent 和人类开发者同样生效，且大部分由 CI 机器校验，不是建议。

## 铁律

1. **禁止先写实现代码。**
   任何功能新增或变更，必须先在 [specs/](specs/) 下创建需求文档（复制 [specs/TEMPLATE.md](specs/TEMPLATE.md)），
   需求 ID 形如 `REQ-001`，三位数字递增、不复用、不跳号。
   需求文档必须包含填好的「背景 / 目标 / 验收标准 / 影响范围」四节，验收标准每条都要能翻译成断言。

2. **每个需求必须同时有单元测试和端到端测试。**
   文件名必须包含小写的需求 ID，这是 CI 能关联到需求文档的唯一依据：
   - 单元测试：`tests/test_req_001_*.py`
   - 端到端测试：`tests/e2e/test_req_001_*.py`

   缺任何一项，CI 的 `Spec Check` 直接失败，后面的测试和发布全部不执行。

3. **端到端测试必须用 `step` 助手包裹每一步操作。**
   `tests/e2e/conftest.py` 提供的 `step` 会在每步结束（含失败）时自动截图，
   截图是验收报告的证据来源，手写 `page.screenshot()` 不算。

4. **交付前必须生成验收报告。**
   `python scripts/acceptance_report.py REQ-001`
   报告包含单测结果、E2E 结果和逐步截图。CI 会自动生成并作为 artifact 上传。
   结论为「未通过」时，不允许把需求状态标成 `done`。

5. **需求状态流转**：`draft`（有需求无实现）→ `in-progress`（在写代码）→ `done`（单测 + E2E 全绿且有验收报告）。

6. **禁止为了通过门禁而删测试、注释断言、或放宽需求文档里的验收标准。**
   需求变了就改需求文档并说明原因，不能倒过来迁就实现。

## 常用命令

```bash
# 需求门禁：检查每个需求是否有对应单测和 E2E
python scripts/check_specs.py

# 单元测试（不含 E2E）
.venv/bin/pytest -m "not e2e"

# 端到端测试（需要先启动服务）
.venv/bin/uvicorn app.main:app --port 8000   # 终端 1
.venv/bin/pytest -m e2e                      # 终端 2
.venv/bin/pytest -m e2e --headed --slowmo=300  # 有头模式，肉眼看执行过程

# 验收报告：跑测试并生成 reports/REQ-001/acceptance.html（截图内嵌，单文件可分享）
python scripts/acceptance_report.py REQ-001
python scripts/acceptance_report.py --all    # 全部需求

# 需求总览报告：横向看所有需求的状态、覆盖、缺口
python scripts/overview_report.py
```

## 目录约定

| 目录 | 用途 |
|---|---|
| `specs/` | 需求文档，一个需求一个文件，机器解析的元信息写在 YAML front-matter |
| `tests/` | 单元测试，按需求分文件 |
| `tests/e2e/` | 端到端测试，同样按需求分文件 |
| `scripts/` | 门禁脚本和报告生成脚本 |
| `reports/` | 验收报告和截图产物，不入库，由 CI 作为 artifact 上传 |
| `app/` | 应用代码 |

## 工作流

```
写需求文档 → 写单测 + E2E → 写实现 → 本地跑验收报告 → 提交 PR
   ↓                                          ↓
Spec Check（CI 门禁）                    单测 / E2E（CI 门禁）
                                                 ↓
                                        验收报告 + 镜像发布（仅 main）
```