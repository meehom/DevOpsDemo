# UI Specification: 上海市初中目标院校筛选高保真

> 本文件是设计的可版本化源文件。编辑器（m3e-canvas）的数据只存在浏览器 localStorage，
> 换浏览器或清缓存就会丢失，所以**提示词原文必须存在这里**，画布只是编辑态。
>
> 说明：本文件当前是按 m3e-canvas 的输出格式手工整理的稿子（画布导出后请整段替换，保留本说明区块）。
> 视觉令牌沿用 DS-001，见 `designs/DS-001-演示应用高保真/prompt.md` 第 3 节。

## 1. 页面结构

- Screen `SchoolFilter`（目标院校筛选，桌面 1280×800 / 移动 412×892）：
  顶部应用栏 + 常驻演示提示条 + 结果计数 + 筛选区 + 结果卡片列表 + 空态区域
- 单屏页面，无第二屏，筛选条件变化时原地重渲染列表

## 2. 组件树

### SchoolFilter 屏

- 最顶部放一条常驻 Top App Bar，标题「目标院校筛选」，左侧菜单图标按钮，右侧搜索图标按钮
- 紧贴应用栏下方放一条提示条，文字「演示原型 · 数据均为虚构，不代表真实招生信息」，
  底色 secondaryContainer，高度 32dp，通栏
- 内容区第一行放结果计数，文字「共 N 所」，14sp/400，色 onSurfaceVariant
- 筛选区纵向三块，桌面端（≥900px）三块横排、块间距 16dp；移动端（<900px）纵向堆叠：
  1. 行政区 Filter Chip 多选组，16 枚，标签分别为徐汇、黄浦、浦东、静安、杨浦、闵行、普陀、虹口、
     长宁、宝山、嘉定、松江、青浦、奉贤、金山、崇明；选中态底色 primaryContainer、文字 onPrimaryContainer、
     无描边；未选中态底色 transparent、1dp outline 描边、文字 onSurfaceVariant
  2. 办学性质 Filter Chip 单选组，3 枚，标签为全部、公办、民办，样式同上，互斥选中
  3. 「只看目标清单」Switch 组件，左侧文字标签，开启时轨道为 primary
- 筛选区右侧（移动端为筛选区下方右侧）放一个 Text Button「重置」，文字色 primary
- 结果列表纵向排列 Elevated Card，卡片间距 12dp，每张卡片横向三段：
  1. 左侧圆形头像容器，直径 40dp，底色 primaryContainer，居中放校名首字，色 onPrimaryContainer
  2. 中部两行：主标题校名 16sp/600 色 onSurface；副标题「行政区 · 办学性质」12sp/400 色 onSurfaceVariant
  3. 右侧 Icon Button，未加入目标清单时为描边星形图标、色 onSurfaceVariant；
     已加入时为实心星形图标、色 onPrimaryContainer、容器底色 primaryContainer
- 列表为空时不渲染任何卡片，改为居中显示一个搜索无结果图标与两行文字：
  主文案「没有符合条件的院校」16sp/600 色 onSurface，副文案「可以试试减少筛选条件，或点「重置」」12sp/400 色 onSurfaceVariant

## 3. 颜色角色

完全沿用 DS-001 的 12 个角色，不新增、不改值：

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

- 卡片圆角 16dp，Filter Chip 全圆角（999dp），头像容器与图标按钮为圆形
- 字体使用系统字体栈，字阶：标题 16sp/600、正文 14sp/400、次要说明 12sp/400

## 5. 动效

- 筛选结果列表重渲染使用标准缓动（cubic-bezier(0.2, 0, 0, 1)），时长 200ms
- 星形按钮切换目标状态时做一次轻微缩放回弹，时长 300ms
- Filter Chip 选中态切换时长 150ms

## 6. 交互路由契约

| 源屏 | 触发组件 | 动作 | 目标 | 参数 |
|---|---|---|---|---|
| SchoolFilter | 行政区 Chip | onClick | 原地刷新结果列表 | `district: string[]` |
| SchoolFilter | 办学性质 Chip | onClick | 原地刷新结果列表 | `school_type: "全部" \| "公办" \| "民办"` |
| SchoolFilter | 只看目标清单 Switch | onChange | 原地刷新结果列表 | `target_only: boolean` |
| SchoolFilter | 「重置」Text Button | onClick | 清空三条件并刷新 | 无 |
| SchoolFilter | 卡片星形按钮 | onClick | 切换该院校目标状态 | `school_id: number` |

## 7. 数据说明

mockup.html 内全部为虚构数据，写死在页面脚本里，不请求任何后端接口。

正式实现时由 `GET /schools` 提供数据，支持 `district`（可重复传参）、`school_type`、
`target_only` 三个查询参数，筛选在服务端完成；`GET /schools/options` 提供筛选器候选值；
`POST` / `DELETE /schools/{id}/target` 切换目标清单状态。院校名仍为演示用虚构数据。