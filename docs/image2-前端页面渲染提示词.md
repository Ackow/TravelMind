# TravelMind 前端页面参考渲染图提示词

> 用途：将下列提示词逐条复制到 Image 2，以生成 TravelMind 桌面端高保真 UI 参考图。  
> 生成策略：每个页面单独生成一张图，不要在一张图中拼接多个屏幕。  
> 建议画幅：`16:10` 横向，优先 1536×1024；需要更宽的地图工作台时可用 `16:9`。  
> 注意：AI 图像模型容易拼错小字。首轮重点参考布局、层级、配色和组件密度；真正实现时以产品文案为准。

## 1. 全局视觉基线

所有页面提示词都重复包含以下设计语言，确保每张图可以独立生成且风格一致：

- 产品：TravelMind，动态旅行规划 Agent Web 应用。
- 定位：可信赖、清晰、聪明但不过度科幻的旅行规划工作台。
- 风格：高保真、可真实开发落地的现代 SaaS UI，不是概念艺术。
- 画布：桌面浏览器，1440px 宽设计基准，16:10 横向。
- 顶部导航：白色 72px 顶栏，左侧 TravelMind 字标与简洁罗盘/路线图标，中间“我的旅行、探索、帮助”，右侧通知与圆形头像。
- 页面背景：很浅的暖灰 `#F7F8F6`。
- 主色：深蓝绿 `#123F3A`；强调色：珊瑚橙 `#FF735D`；辅助色：鼠尾草绿 `#DDEBE5`；信息蓝 `#DCEAF7`。
- 卡片：白色，16～20px 圆角，1px 浅灰边框，克制的柔和阴影。
- 排版：清晰现代的中文无衬线字体，大标题深墨色，正文高可读，数字略紧凑。
- 图标：简洁圆角线性图标，统一 2px 描边。
- 数据视觉：小型天气图标、预算进度条、时间轴、路线节点；不要炫技式 3D。
- 密度：专业产品级中等信息密度，充足留白，网格对齐准确。
- 品牌细节：可少量使用抽象路线曲线与地图等高线纹理，不使用真实公司商标。

## 2. 通用负面约束

可追加在每条提示词末尾：

```text
Avoid: dark cyberpunk dashboard, neon gradients, glassmorphism overload, giant decorative illustration, mobile layout, landing-page marketing hero, excessive rounded pills, excessive shadows, cramped cards, random charts, illegible tiny text, garbled Chinese, mixed languages, duplicated navigation, floating windows, perspective device mockup, browser chrome, watermark, unrelated logos, stock photography, fantasy map, 3D globe.
```

如果生成器频繁拼错中文，可把 `Text` 部分替换为“use short clean Chinese placeholder labels with correct hierarchy”，先取得构图，再在 Figma 或实现代码中补准确文案。

---

## 3. 页面一：我的旅行 / 空状态

### 设计重点

这是用户进入产品后的首页。它需要回答三件事：当前有没有旅行、如何创建、系统会怎样帮助规划。空状态不能像营销落地页，而应像成熟应用的任务入口。

### Image 2 提示词

```text
Use case: ui-mockup
Asset type: high-fidelity desktop web application screen
Primary request: Design the “My Trips” empty-state page for TravelMind, a dynamic AI travel planning agent. Make it look like a shippable SaaS product screen, not a marketing landing page.
Scene/backdrop: desktop application canvas, 1440px design width, very light warm-gray background #F7F8F6, white 72px top navigation.
Brand system: TravelMind wordmark with a minimal compass-route icon; deep teal #123F3A as primary, coral #FF735D as CTA, sage #DDEBE5 and pale blue #DCEAF7 as supporting colors; modern Chinese sans-serif typography; white cards with 18px radius, thin borders and restrained shadows; consistent rounded outline icons.
Layout: top navigation with “我的旅行” active, then “探索” and “帮助”; right side notification icon and avatar. Main content uses a centered max-width 1180px grid. At top-left show page title “我的旅行” and subtitle “规划、调整并保存你的每一次旅程”. Top-right has coral primary button “创建新旅行” with plus icon.
Subject: a large central empty-state card occupying roughly two thirds of content width. Inside it, a restrained flat illustration of a folded city map with a curved route, three location pins, a small weather cloud and a budget coin—simple vector-like UI illustration, no people. Headline “还没有旅行计划”, supporting copy “从目的地、日期和偏好开始，让 TravelMind 为你构建可调整的行程”, and a coral button “创建第一段旅行”.
Secondary content: on the right or beneath, three compact capability cards titled “实时信息”, “约束检查”, “动态调整”, each with one simple icon and one short sentence. Add a subtle “规划流程” strip showing four steps: 填写需求 → 查询信息 → 检查冲突 → 审阅调整.
Composition/framing: straight-on full-page screenshot, landscape 16:10, practical spacing and accurate grid alignment, medium information density, generous whitespace.
Text (verbatim): “TravelMind”, “我的旅行”, “探索”, “帮助”, “创建新旅行”, “我的旅行”, “规划、调整并保存你的每一次旅程”, “还没有旅行计划”, “创建第一段旅行”, “实时信息”, “约束检查”, “动态调整”, “规划流程”, “填写需求”, “查询信息”, “检查冲突”, “审阅调整”.
Constraints: realistic implementable UI; clear Chinese typography; no real map provider branding; no photos; no browser chrome; no watermark; no extra navigation items.
Avoid: dark cyberpunk dashboard, neon gradients, glassmorphism overload, landing-page hero, giant globe, mobile layout, illegible tiny text, garbled Chinese, duplicated navigation, perspective mockup, unrelated logos.
```

---

## 4. 页面二：创建旅行

### 设计重点

表单字段很多，参考图必须体现分组与渐进披露，不能把所有控件堆成一张密集问卷。右侧摘要帮助用户随时理解“当前约束”。

### Image 2 提示词

```text
Use case: ui-mockup
Asset type: high-fidelity desktop web application form screen
Primary request: Design the “Create Trip” page for TravelMind, a dynamic travel planning agent. The page should make a complex trip request feel calm, guided and easy to complete.
Scene/backdrop: desktop SaaS UI at 1440px width, light warm-gray #F7F8F6 background, white 72px top nav.
Brand system: TravelMind compass-route icon; primary deep teal #123F3A, coral #FF735D for the final CTA, sage and pale-blue status accents; modern Chinese sans-serif; white cards, 18px rounded corners, thin gray border, restrained shadow; outline icons.
Layout: top nav consistent with the product. Below it, a narrow step indicator with “1 基本信息”, “2 偏好与约束”, “3 确认”, where step 2 is active in deep teal. Main area is a two-column grid: left form column about 760px, right sticky trip-summary card about 340px.
Left form: page title “创建旅行”, subtitle “告诉我们你想怎样旅行，之后随时可以调整”. Use three stacked white cards. Card one “去哪儿” contains two destination inputs with pin icons: 出发地 “南京”, 目的地 “东京”; below is a date-range selector “2026/10/01 — 2026/10/05” and traveler stepper showing “2 人”. Card two “你喜欢什么” contains selectable interest chips, with “动漫”, “美食”, “城市漫步” selected, while “博物馆”, “自然风景”, “夜生活” are unselected; below show “不希望出现” with a selected chip “购物”, plus a compact dietary preference selector. Card three “行程约束” contains total budget input “¥ 10,000”, transport segmented control with “公共交通” selected, pace selector with “均衡” selected, a walking-limit slider labeled “每天最多步行 12 km”, and latest end-time selector “21:00”.
Right summary: card titled “旅行摘要”, showing 南京 → 东京, 5 天 4 晚, 2 位旅行者, ¥10,000 总预算; a compact budget allocation preview; selected preferences as small chips; a pale-blue information callout “硬性约束会由系统自动检查”. At card bottom, a wide coral CTA “开始规划”, and a secondary text action “保存草稿”.
Composition/framing: straight-on full-page app screenshot, landscape 16:10, practical and implementable form controls, clear grouping, medium density, accurate spacing.
Text (verbatim): “TravelMind”, “创建旅行”, “告诉我们你想怎样旅行，之后随时可以调整”, “1 基本信息”, “2 偏好与约束”, “3 确认”, “去哪儿”, “出发地”, “南京”, “目的地”, “东京”, “你喜欢什么”, “动漫”, “美食”, “城市漫步”, “博物馆”, “自然风景”, “夜生活”, “不希望出现”, “购物”, “行程约束”, “总预算”, “公共交通”, “均衡”, “每天最多步行 12 km”, “旅行摘要”, “5 天 4 晚”, “2 位旅行者”, “¥10,000 总预算”, “开始规划”, “保存草稿”.
Constraints: shippable product UI, accessible contrast, visible input labels, no placeholder-only form, no provider logos, no map, no photos, no watermark.
Avoid: dense spreadsheet form, giant text, wizard modal, dark dashboard, neon, glassmorphism, mobile layout, illegible labels, garbled Chinese, random fields, perspective device frame.
```

---

## 5. 页面三：Agent 规划中

### 设计重点

这里不是展示模型的隐藏思维链，而是展示可公开、可验证的执行事件：调用了什么工具、取得多少数据、发现什么约束、当前进度和可取消操作。

### Image 2 提示词

```text
Use case: ui-mockup
Asset type: high-fidelity desktop AI agent progress screen
Primary request: Design the TravelMind “Planning in Progress” page. It should communicate trustworthy agent execution through public events and tool results, without exposing hidden chain-of-thought.
Scene/backdrop: desktop web app, 1440px width, warm light-gray background #F7F8F6, white top navigation.
Brand system: deep teal #123F3A, coral #FF735D, sage success #DDEBE5, pale blue information #DCEAF7, amber warning accent; modern Chinese sans-serif; white 18px cards; restrained shadows; rounded outline icons.
Header area: breadcrumb “我的旅行 / 东京 5 日游”, page title “正在规划你的东京之旅”, subtitle “TravelMind 正在查询事实、生成候选方案并检查约束”. On the right show circular 68% progress indicator and secondary button “取消规划”.
Main layout: two columns, left 65%, right 35%. Left has a large card titled “规划进度” with a vertical workflow timeline. Completed steps have sage check icons: “解析旅行需求”, “查询天气”, “搜索景点”; active step has a deep-teal animated-style ring “计算地点间路线”; upcoming muted steps are “生成候选行程”, “检查预算与时间”, “准备草案”. Each completed step shows a short factual detail, such as “已获得 5 天天气数据” and “筛选出 18 个候选地点”.
Below timeline: a compact “实时事件” feed with timestamped rows and small tool badges: Weather Tool, POI Tool, Route Tool. Show events like “10:32 已取得东京天气预报”, “10:33 排除 2 个临时闭馆地点”, “10:34 正在计算 18 个地点的交通矩阵”. Make it look like an audit trail, not terminal code and not model thoughts.
Right column: a trip-context card showing 东京, 2026/10/01—10/05, 2 人, budget ¥10,000, preference chips 动漫/美食/城市漫步. Beneath it, a “当前发现” card with a weather row showing Day 2 rain probability 75%, a warning “镰仓户外安排可能需要调整”, and a calm note “完成约束检查后会自动给出替代方案”. At bottom show small metrics: 工具调用 7, 候选地点 18, 已用时间 1m 42s.
Composition/framing: straight-on desktop product screenshot, landscape 16:10, strong visual hierarchy, calm trustworthy mood, medium information density.
Text (verbatim): “TravelMind”, “我的旅行 / 东京 5 日游”, “正在规划你的东京之旅”, “规划进度”, “解析旅行需求”, “查询天气”, “搜索景点”, “计算地点间路线”, “生成候选行程”, “检查预算与时间”, “准备草案”, “实时事件”, “当前发现”, “取消规划”, “68%”, “工具调用 7”, “候选地点 18”, “已用时间 1m 42s”.
Constraints: display only public execution summaries and tool facts; no hidden reasoning paragraphs; realistic progress UI; readable Chinese; no fake code console; no watermark; no provider logos.
Avoid: sci-fi AI brain, chain-of-thought text, terminal hacker screen, neon purple, dark mode, excessive animations, giant spinner, mobile layout, garbled Chinese, random charts, perspective mockup.
```

---

## 6. 页面四：旅行草案工作台

### 设计重点

这是核心页面。必须一眼看清“哪一天、几点、去哪里、怎么走、天气怎样、预算多少、是否有冲突”。布局采用左侧日程导航、中间时间轴、右侧地图与摘要。

### Image 2 提示词

```text
Use case: ui-mockup
Asset type: high-fidelity desktop travel itinerary workspace
Primary request: Design the core TravelMind itinerary draft workspace for a five-day Tokyo trip. It must look practical enough to implement and should clearly combine day navigation, timeline, map, weather, budget and constraint status.
Scene/backdrop: 1440px desktop app, light warm-gray #F7F8F6, fixed white top nav, no browser chrome.
Brand system: primary deep teal #123F3A, coral #FF735D, sage #DDEBE5, pale blue #DCEAF7, amber warnings; modern Chinese sans-serif; white cards with 16–18px radius, thin borders, subtle shadows; consistent outline icons.
Top content header: breadcrumb “我的旅行 / 东京 5 日游”, title “东京 5 日旅行草案”, status badge “等待审阅”, small line “版本 1 · 刚刚生成”. On the right, secondary button “导出”, coral button “调整行程”. Directly below show a pale amber alert banner: “10 月 2 日降雨概率较高，已将户外活动调整至其他日期” with action “查看调整”.
Main workspace: three-column layout. Left narrow column about 190px has vertical day cards: “Day 1 · 10/01 浅草与秋叶原”, “Day 2 · 10/02 博物馆与东京站” active in deep teal tint, then Day 3, Day 4, Day 5. Each day card has a tiny weather icon, temperature and daily cost. Add summary at bottom “总预算已使用 82%”.
Center column about 590px is a detailed timeline for Day 2. Header “Day 2 · 10 月 2 日 周五”, rain icon “18–22°C · 降雨 75%”, badges “室内为主” and “步行 6.2 km”. Vertical timeline with time labels and connected nodes: 09:00 早餐; 10:00 东京国立博物馆, category 博物馆, 2h, ticket ¥1,000; a compact transfer row with train icon “地铁 18 分钟 · 步行 420 m”; 13:00 上野午餐; 14:30 teamLab Borderless; 18:30 东京站晚餐. Each attraction card has priority icon, cost, duration, overflow menu and a subtle drag handle. Do not use photos; use small colored category icons.
Right column about 390px: upper card is a clean stylized Tokyo street map with pale neutral streets, teal route polyline, numbered coral pins 1–4, no real map provider branding. Under the map add tabs or cards “预算”, “天气”, “约束”. Show budget donut or progress bar with 已计划 ¥8,200 / ¥10,000; category rows 住宿, 餐饮, 交通, 门票. Constraint card shows green check “无硬性冲突” and one amber warning “teamLab 需提前预约”.
Bottom floating or sticky review bar: text “这份草案符合当前硬性约束”, buttons “提出修改” and deep-teal “接受计划”.
Composition/framing: straight-on full-page desktop screenshot, landscape 16:9 or 16:10, clear grid, high but comfortable information density, accurate product spacing.
Text (verbatim): “TravelMind”, “东京 5 日旅行草案”, “等待审阅”, “版本 1”, “导出”, “调整行程”, “10 月 2 日降雨概率较高，已将户外活动调整至其他日期”, “查看调整”, “Day 2 · 10 月 2 日 周五”, “18–22°C · 降雨 75%”, “室内为主”, “步行 6.2 km”, “东京国立博物馆”, “地铁 18 分钟 · 步行 420 m”, “上野午餐”, “teamLab Borderless”, “东京站晚餐”, “预算”, “天气”, “约束”, “已计划 ¥8,200 / ¥10,000”, “无硬性冲突”, “提出修改”, “接受计划”.
Constraints: realistic implementable product UI; all itinerary facts aligned to one selected day; no photos; no Google Maps or other trademarks; no hidden reasoning; no watermark.
Avoid: fantasy illustrated map, excessive gradients, neon, dark dashboard, giant cards, sparse landing page, illegible tiny text, garbled Chinese, overlapping panels, mobile layout, perspective mockup.
```

---

## 7. 页面五：修改行程 / 动态重规划

### 设计重点

这一页要直观表达 Human-in-the-loop：用户提出自然语言修改，系统解析成结构化变更，展示影响范围，重规划后提供版本差异，而不是直接悄悄覆盖旧计划。

### Image 2 提示词

```text
Use case: ui-mockup
Asset type: high-fidelity desktop human-in-the-loop replanning screen
Primary request: Design the TravelMind dynamic replanning page where a user modifies an existing Tokyo itinerary through natural language, reviews the interpreted constraints, and sees a clear before/after diff.
Scene/backdrop: 1440px desktop SaaS application, very light warm-gray background, fixed white top nav.
Brand system: deep teal #123F3A, coral #FF735D, sage success, pale blue information, amber warning; modern Chinese sans-serif; white 18px cards, thin borders and restrained shadows; outline icons.
Header: breadcrumb “东京 5 日游 / 调整行程”, title “根据你的反馈重新规划”, version badges “版本 1 → 版本 2”. Right side has secondary action “返回草案”.
Main layout: left column 40%, right column 60%. Left is a conversation and feedback panel. At top show prior user message in a soft-gray bubble: “第二天我 11:30 才能出发，但仍想看日落。” Under it show an Agent response card, not a chat bubble, titled “已理解你的调整”, with three structured chips: “10/02 11:30 后出发”, “保留日落活动”, “只调整 Day 2”. Include confidence status with green check “无需澄清”. Then a multiline input placeholder “继续告诉我你想怎样调整…” and coral button “重新规划”. Add quick suggestion chips “少走一点”, “降低预算”, “替换雨天活动”.
Right side: large diff card titled “本次变更”. A horizontal summary strip shows “保留 8 项”, “调整 3 项”, “移除 1 项”, “新增 1 项”, and “计划保留率 78%”. Beneath, a Day 2 timeline comparison with two aligned columns “调整前” and “调整后”. Use subtle red strikethrough treatment for removed “09:00 浅草寺”, amber moved indicator for “上野午餐 12:30 → 13:00”, green added card “16:40 江之岛海岸”, and a locked pin icon on “17:20 日落观景”. Connect the changes with slim arrows. Avoid showing every unchanged activity in full; collapse them into “其余 8 项保持不变”.
Lower right: “约束检查” section with green checks “结束时间 20:30，符合要求”, “预计步行 7.4 km”, “预算增加 ¥260，仍在范围内”; one pale-blue note “仅重新计算了 Day 2 的路线”. Bottom sticky actions: outlined “放弃修改” and deep-teal primary “应用版本 2”.
Composition/framing: straight-on full-page screenshot, landscape 16:10, practical comparison UI, clear hierarchy, medium-high information density.
Text (verbatim): “TravelMind”, “东京 5 日游 / 调整行程”, “根据你的反馈重新规划”, “版本 1 → 版本 2”, “返回草案”, “第二天我 11:30 才能出发，但仍想看日落。”, “已理解你的调整”, “10/02 11:30 后出发”, “保留日落活动”, “只调整 Day 2”, “无需澄清”, “重新规划”, “本次变更”, “保留 8 项”, “调整 3 项”, “移除 1 项”, “新增 1 项”, “计划保留率 78%”, “调整前”, “调整后”, “其余 8 项保持不变”, “约束检查”, “放弃修改”, “应用版本 2”.
Constraints: show structured interpretation and explicit version diff; no hidden chain-of-thought; realistic implementable UI; changes must be color-coded but accessible with icons and labels; no map provider logos; no watermark.
Avoid: generic chatbot-only screen, terminal logs, huge chat bubbles, invisible before/after distinction, dark AI dashboard, neon, glassmorphism, mobile layout, illegible tiny text, garbled Chinese, perspective mockup.
```

---

## 8. 页面六：最终行程

### 设计重点

最终页面应该比编辑工作台更安静，适合浏览、分享、打印和导出。仍需保留天气、预算和重要提醒，但弱化编辑控件。

### Image 2 提示词

```text
Use case: ui-mockup
Asset type: high-fidelity desktop final itinerary screen
Primary request: Design the final accepted itinerary page for TravelMind. It should feel calm, polished, printable and easy to share, while preserving practical trip details.
Scene/backdrop: desktop web app at 1440px, light warm-gray #F7F8F6 background, white top navigation.
Brand system: deep teal #123F3A, coral #FF735D, sage success and pale blue support; modern Chinese sans-serif; clean white cards with 16–18px corners, thin borders and subtle shadows; outline icons.
Hero header within the application: small green status pill “已确认”, title “东京 · 5 日旅行计划”, subtitle “2026 年 10 月 1 日—10 月 5 日 · 2 位旅行者”, a compact route line “南京 → 东京”. Right side buttons: outlined “分享链接”, outlined “导出 PDF”, deep-teal “查看版本”. Under title show preference chips 动漫, 美食, 城市漫步 and a small label “版本 2”.
Summary band: four clean statistic cards showing “5 天 4 晚”, “18 个活动”, “预计 ¥8,460”, “步行 38.6 km”; add a green validation statement “所有硬性约束已通过”.
Main layout: left content about 72%, right sticky summary about 28%. Left contains an accordion or stacked list for Day 1 through Day 5. Day 1 is expanded with title “Day 1 · 浅草与秋叶原”, small clear-weather icon, temperature, daily cost and walking distance. Inside is a clean vertical timeline: arrival/check-in, 浅草寺, 午餐, 上野, 秋叶原, dinner; each row shows time, place name, duration, transport transition and cost in a print-friendly style. Other days are collapsed but show theme, weather, total cost and an expand chevron.
Right column: “旅行总览” card with a miniature route-map thumbnail, budget progress “¥8,460 / ¥10,000”, category breakdown, and “预留 ¥1,540”. Under it a card “出发前提醒” with checklist items: “预约 teamLab”, “准备雨具”, “确认交通卡”. Add a subtle info block “天气与开放时间获取于 8 月 13 日，出发前请再次确认”.
Composition/framing: straight-on desktop product screenshot, landscape 16:10, polished but not decorative, print-friendly whitespace, readable hierarchy.
Text (verbatim): “TravelMind”, “已确认”, “东京 · 5 日旅行计划”, “2026 年 10 月 1 日—10 月 5 日 · 2 位旅行者”, “南京 → 东京”, “分享链接”, “导出 PDF”, “查看版本”, “版本 2”, “5 天 4 晚”, “18 个活动”, “预计 ¥8,460”, “步行 38.6 km”, “所有硬性约束已通过”, “Day 1 · 浅草与秋叶原”, “旅行总览”, “¥8,460 / ¥10,000”, “预留 ¥1,540”, “出发前提醒”, “预约 teamLab”, “准备雨具”, “确认交通卡”.
Constraints: final read-only presentation, printable layout, no heavy editing controls, no real provider logos, no photos, no watermark, no hidden reasoning.
Avoid: marketing landing page, giant scenic photo, boarding-pass gimmick, dark mode, neon, glassmorphism, dense editor controls, mobile layout, garbled Chinese, illegible text, perspective mockup.
```

---

## 9. 页面七：计划版本历史

### 设计重点

版本历史虽然不是原说明中的独立页面，却是动态重规划可信度的重要载体。它让用户知道计划为什么变化，也利于你演示状态持久化与审计能力。

### Image 2 提示词

```text
Use case: ui-mockup
Asset type: high-fidelity desktop plan version history screen
Primary request: Design a TravelMind itinerary version history page that lets users understand how and why an AI travel plan changed over time.
Scene/backdrop: 1440px desktop SaaS app, warm off-white background #F7F8F6, white navigation bar.
Brand system: TravelMind deep teal #123F3A, coral #FF735D, sage green, pale blue and restrained amber; modern Chinese sans-serif; white rounded cards, thin borders, subtle shadows; outline icons.
Header: breadcrumb “东京 5 日游 / 版本历史”, title “计划版本”, subtitle “每次调整都会保存为一个不可变版本”. Right side button “返回当前计划”.
Main layout: left 38% version timeline, right 62% selected-version detail. Left card shows vertical timeline with four version entries. Version 3 at top has green badge “当前 · 已确认”, trigger “减少每日步行距离”, timestamp “今天 14:32”, and author label “根据用户反馈”. Version 2 says “Day 2 晚出发并保留日落”; Version 1 says “初次规划”; a small research refresh entry may say “天气数据更新”. Each entry shows validation status and compact metrics.
Right side selected Version 3: summary header “版本 3 相对版本 2”, pills “保留 15 项”, “调整 2 项”, “替换 1 项”, preservation bar 88%. A change list grouped by day: Day 2 green added/amber moved rows, Day 4 one route mode changed. Each row contains activity title, old value, arrow, new value, and concise reason. Under it a “验证结果” card with green checks for budget, opening hours, transfer time and walking limit. At bottom show actions “查看完整版本”, “与其他版本比较”, and a destructive-looking but disabled/secondary option “恢复为新版本” rather than overwriting history.
Composition/framing: straight-on desktop screenshot, landscape 16:10, audit-friendly product UI, clear chronology and comparison hierarchy.
Text (verbatim): “TravelMind”, “东京 5 日游 / 版本历史”, “计划版本”, “每次调整都会保存为一个不可变版本”, “返回当前计划”, “当前 · 已确认”, “版本 3”, “版本 2”, “版本 1”, “根据用户反馈”, “初次规划”, “版本 3 相对版本 2”, “保留 15 项”, “调整 2 项”, “替换 1 项”, “验证结果”, “查看完整版本”, “与其他版本比较”, “恢复为新版本”.
Constraints: clearly communicate immutable version history; do not imply old versions are overwritten; no hidden AI reasoning; realistic implementable UI; no watermark.
Avoid: source-code Git interface, terminal, spreadsheet, dark dashboard, neon, mobile layout, tiny unreadable diff, garbled Chinese, perspective mockup.
```

---

## 10. 页面八：规划失败 / 无可行方案

### 设计重点

Agent 产品不能只设计成功状态。无解页面要说明哪些约束冲突、用户能放宽什么，以及哪些要求不会被系统偷偷忽略。

### Image 2 提示词

```text
Use case: ui-mockup
Asset type: high-fidelity desktop no-feasible-plan error state
Primary request: Design a trustworthy TravelMind “No Feasible Plan” page. The application could not satisfy all hard constraints, and the UI must explain conflicts and offer safe recovery actions instead of showing a generic error.
Scene/backdrop: desktop web app, 1440px width, light warm-gray background, white top navigation.
Brand system: deep teal #123F3A, coral #FF735D, pale blue, sage, restrained amber and muted red only for hard conflicts; modern Chinese sans-serif; white cards with 18px radius, thin borders and subtle shadows.
Header: breadcrumb “东京 5 日游 / 规划结果”, title “当前条件下无法生成可行计划”, supporting text “我们没有忽略你的要求。以下硬性约束彼此冲突，请选择要调整的项目.” Use a restrained route-warning illustration: two route lines blocked by a small warning marker, no sad robot.
Main card titled “发现 3 个冲突”. Show three structured conflict rows with red outline icons: “总预算不足”, actual “预计最低 ¥11,200” versus limit “¥10,000”; “必去地点营业时间冲突”, showing two required places closed on the only available day; “每日步行上限过低”, expected route minimum 9.3 km versus limit 5 km. Each row has a short explanation and link “查看详情”.
Recovery area titled “你可以这样调整”. Present three selectable recommendation cards with checkboxes or radio controls: “将预算提高至 ¥11,500”, “允许其中一天步行最多 10 km”, “移除一个必去地点”. Label the least disruptive option with a small badge “推荐”. Provide a secondary free-text input “或者告诉我你愿意怎样调整…”. Bottom actions: outlined “返回修改条件” and coral “按所选条件重新规划”.
Right compact panel “我们仍然保留” lists user preferences 动漫、美食、少购物 and states that no requirement will be dropped without confirmation. Include request ID as subtle support metadata, not prominent.
Composition/framing: straight-on landscape 16:10 product screenshot, calm and constructive error recovery, clear visual hierarchy, accessible contrast.
Text (verbatim): “TravelMind”, “当前条件下无法生成可行计划”, “我们没有忽略你的要求”, “发现 3 个冲突”, “总预算不足”, “预计最低 ¥11,200”, “¥10,000”, “必去地点营业时间冲突”, “每日步行上限过低”, “查看详情”, “你可以这样调整”, “推荐”, “将预算提高至 ¥11,500”, “允许其中一天步行最多 10 km”, “移除一个必去地点”, “返回修改条件”, “按所选条件重新规划”, “我们仍然保留”.
Constraints: not a generic 500 page; show machine-readable-style actual vs expected values in friendly UI; do not silently relax constraints; no hidden reasoning; no watermark.
Avoid: sad robot illustration, giant red error icon, blameful tone, dark mode, neon, terminal trace, mobile layout, garbled Chinese, illegible text, perspective mockup.
```

---

## 11. 可选移动端参考：最终行程随身查看

桌面端是 MVP 主目标。若后续需要响应式参考图，可额外生成这一张，而不是让 Image 2 自行把桌面页面缩成手机。

```text
Use case: ui-mockup
Asset type: high-fidelity mobile responsive travel itinerary screen
Primary request: Design the mobile responsive version of TravelMind’s accepted Tokyo itinerary for on-trip viewing, focused on today’s route rather than editing.
Scene/backdrop: single portrait mobile app screen, clean off-white background, no device frame.
Brand system: deep teal #123F3A, coral #FF735D, sage and pale blue; modern Chinese sans-serif; white cards with 16px radius; simple outline icons.
Layout: compact top bar with TravelMind icon, title “Day 2 · 东京”, overflow menu. A weather-and-progress card shows “10 月 2 日 周五”, rain 75%, 18–22°C, daily budget ¥1,620 and walking 6.2 km. Main vertical timeline emphasizes the next activity with coral accent: current time 13:42, next “14:30 teamLab Borderless”, transport “地铁 18 分钟”, CTA “开始导航”. Earlier activity is muted, later activities are compact cards. Bottom navigation has “今天”, “全部行程”, “预算”, “提醒”. Add a small offline status “行程已保存到本机”.
Composition/framing: portrait mobile UI only, straight-on, realistic responsive product screen, touch-friendly controls and readable text.
Text (verbatim): “TravelMind”, “Day 2 · 东京”, “10 月 2 日 周五”, “降雨 75%”, “18–22°C”, “今日预算 ¥1,620”, “步行 6.2 km”, “14:30 teamLab Borderless”, “地铁 18 分钟”, “开始导航”, “今天”, “全部行程”, “预算”, “提醒”, “行程已保存到本机”.
Constraints: one mobile screen only; prioritize today’s next action; no full desktop sidebar; no map provider branding; no watermark.
Avoid: device mockup, hands holding phone, desktop layout squeezed into mobile, marketing screen, neon, dark cyberpunk, garbled Chinese, tiny text.
```

## 12. 生成与筛选建议

1. 先生成“创建旅行”“旅行草案”“动态重规划”三张，它们决定产品的大部分组件语言。
2. 每个页面首轮只生成一张；选定构图后，再用单一修改指令迭代，例如“保持布局不变，仅降低右栏信息密度”。
3. 如果同一页面需要多个版本，优先变化信息密度或导航结构，不要同时更换配色、字体和布局。
4. 评审参考图时只检查：信息层级、任务路径、组件关系、视觉密度、状态表达。不要照抄生成图中的错误文本或不合理数据。
5. 最终实现应以 `api-contract.md` 的字段与状态为准，参考图只负责视觉方向。

## 13. 通用迭代指令

当首图整体方向正确时，可以追加这些短指令进行定向修改：

```text
Keep the existing layout, palette and component hierarchy unchanged. Improve only Chinese text legibility and alignment. Remove any invented labels. Do not add new panels.
```

```text
Keep all content and layout unchanged. Reduce visual density by about 15%, add more whitespace between card groups, and preserve the desktop 1440px product screenshot framing.
```

```text
Keep the page structure unchanged. Make the UI more realistically implementable: flatten decorative effects, reduce shadows, remove glassmorphism, standardize radii and icon stroke width.
```

```text
Change only the map styling: use a neutral light street map with a deep-teal route and numbered coral pins; remove all provider branding and unrelated labels. Keep every other panel unchanged.
```
