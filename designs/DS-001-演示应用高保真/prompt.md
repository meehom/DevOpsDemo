# UI Specification: 演示应用高保真（两数相加 + 商品管理）

> 本文件是设计的可版本化源文件。编辑器（m3e-canvas）的数据只存在浏览器 localStorage，
> 换浏览器或清缓存就会丢失，所以**提示词原文必须存在这里**，画布只是编辑态。
>
> 说明：本文件当前是按 m3e-canvas 的输出格式手工整理的示例（画布导出后请整段替换，保留本说明区块）。

## 1. 页面结构

- Screen `Overview`（概览，桌面 1280×800 / 移动 412×892）：顶部应用栏 + 3 张统计卡片 + 最近商品列表
- Screen `Items`（商品）：顶部应用栏 + 商品卡片网格 + 右下悬浮按钮（FAB）
- Screen `Calculator`（计算器）：顶部应用栏 + 两个数字输入框 + 通栏按钮 + 结果展示区
- 桌面形态使用侧边导航栏（Navigation Rail，左侧竖向，图标在上文字在下）
- 移动形态使用底部导航栏（Navigation Bar，横向 3 项）

## 2. 组件树

### Overview 屏
- 上部放置标题为「概览」的顶部应用栏，左侧为菜单图标按钮，右侧为搜索图标按钮
- 内容区纵向排列 3 张 Elevated Card，横向三等分，每张包含：小标签（总商品数 / 库存总值 / 今日新增）、大号数值、一行次要说明
- 下部放置 3 个 List Item 组成的列表，每项左侧为圆角图标容器，中间为主标题与副标题，右侧为箭头图标

### Items 屏
- 上部放置标题为「商品」的顶部应用栏
- 内容区为自适应网格，每列最小 240px，卡片包含：商品名（主标题）、分类（次级标签片）、价格（大号数值）、库存（次要说明）
- 右下角放置一个 Filled FAB，图标为加号，容器使用 primaryContainer 色
- 新增商品对话框（Dialog）：标题「新增商品」、两个文本输入框（名称、价格）、底部两个按钮（取消为 Text Button，确认为 Filled Button）

### Calculator 屏
- 上部放置标题为「计算器」的顶部应用栏
- 两个 Outlined Text Field 纵向排列，标签分别为「数字 A」「数字 B」，输入类型为数字
- 下方一个通栏 Filled Button，文字「计算」
- 底部一个 Filled Card 展示结果，无结果时显示占位符「—」

## 3. 颜色角色（浅色主题，共 12 个关键角色）

| 角色 | 十六进制值 |
|---|---|
| primary | #00696E |
| onPrimary | #FFFFFF |
| primaryContainer | #9CF1F6 |
| onPrimaryContainer | #002022 |
| secondaryContainer | #CCE8E9 |
| surface | #F4FBFB |
| surfaceContainer | #E8EFF0 |
| onSurface | #161D1D |
| onSurfaceVariant | #3F4949 |
| outline | #6F7979 |
| surfaceTint | #00696E |
| error | #BA1A1A |

所有颜色必须通过角色名引用，不得在组件里硬编码十六进制值。

## 4. 形状与字体

- 卡片圆角 16dp，对话框圆角 28dp，按钮与标签片为全圆角（999dp）
- 字体使用系统字体栈，字阶：大号数值 28sp/700、标题 16sp/600、正文 14sp/400、次要说明 12sp/400

## 5. 动效

- 视图切换使用标准缓动（cubic-bezier(0.2, 0, 0, 1)），时长 200ms
- FAB 与对话框入场使用 Expressive 回弹（轻微过冲），时长 300ms

## 6. 交互路由契约

| 源屏 | 触发组件 | 动作 | 目标屏 | 参数 |
|---|---|---|---|---|
| Overview | 导航项「概览」 | onClick | Overview（自身） | 无 |
| Overview | 商品 List Item | onClick | 底部提示条 | `item_name: string` |
| Items | FAB | onClick | 新增商品对话框 | 无 |
| Items | 对话框「确认」 | onClick | 关闭对话框并插入列表首位 | `name: string, price: number` |
| Calculator | 「计算」按钮 | onClick | 同屏结果区 | `a: number, b: number` |

## 7. 数据说明

**全部为假数据**，写死在页面脚本里，不请求任何后端接口。页面顶部必须有「演示原型 · 数据为虚构」的常驻提示，
避免客户误认为是已上线系统。