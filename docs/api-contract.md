# TravelMind API 与对象契约

> 版本：MVP v1 草案  
> 面向：前端、FastAPI 后端、Agent、工具适配器与 MCP Server 的实现者  
> 基础路径：`/api/v1`  
> 规范目标：本文中的字段可直接映射为 Pydantic Model、TypeScript Type 和 OpenAPI Schema。

## 1. 契约原则

### 1.1 通用格式

- HTTP 请求和响应使用 `application/json; charset=utf-8`。
- JSON 字段统一使用 `snake_case`；TypeScript 也保持相同名字，避免转换层。
- ID 均为 UUID v4 字符串，例如 `9c135ef7-e038-4d17-9412-0812fdb3cf05`。
- 时间戳使用 RFC 3339 UTC，例如 `2026-08-13T10:30:00Z`。
- 旅行当地日期使用 `YYYY-MM-DD`，当地时间使用 `HH:mm`。
- 每个旅行必须保存 IANA 时区，如 `Asia/Tokyo`，禁止只保存 `UTC+9`。
- 金额使用最小货币单位整数。例如 CNY `10000` 表示 100.00 元，JPY `10000` 表示 10000 日元。
- 距离使用整数米，耗时使用整数分钟，概率使用 `[0, 1]` 小数。
- 可选字段省略表示“未提供”；显式 `null` 表示“已知为空/要求清除”。每个 Patch 接口会单独说明是否允许 `null`。
- 列表默认为空数组 `[]`，不返回 `null`。
- 未知事实使用 `null` 加 `data_quality`，不得由 LLM 猜测。
- 所有枚举值在 API 中使用小写 `snake_case`。

### 1.2 并发、幂等与版本

- 创建旅行、启动规划、提交反馈和导出接口支持 `Idempotency-Key` 请求头。
- 同一个调用方在 24 小时内使用相同 Key 和相同请求体，应得到相同业务结果。
- 修改旅行和接受计划使用 `If-Match: "<revision>"` 做乐观锁。
- `Trip.revision` 每次可变状态更新后加一。
- 行程内容不原地覆盖；每次规划生成新的 `PlanVersion.version`。
- 客户端基于旧版本反馈时返回 `409 VERSION_CONFLICT`。

### 1.3 鉴权边界

MVP 本地版不实现账号系统。接口仍预留 `user_id` 的服务端上下文，但客户端不得在请求体中伪造它。部署为多人服务前，应增加身份认证并对每个 `trip_id` 做资源归属校验。

## 2. 通用对象

### 2.1 `Money`

| 属性 | 类型 | 必填 | 约束 | 说明 |
|---|---|---:|---|---|
| `amount` | integer | 是 | `>= 0` | 最小货币单位整数 |
| `currency` | string | 是 | ISO 4217，3 个大写字母 | 如 `CNY`、`JPY` |

```json
{"amount": 1000000, "currency": "CNY"}
```

### 2.2 `GeoPoint`

| 属性 | 类型 | 必填 | 约束 |
|---|---|---:|---|
| `latitude` | number | 是 | `-90 <= x <= 90` |
| `longitude` | number | 是 | `-180 <= x <= 180` |

### 2.3 `DateRange`

| 属性 | 类型 | 必填 | 约束 |
|---|---|---:|---|
| `start_date` | date | 是 | 当地日期 |
| `end_date` | date | 是 | `>= start_date`；MVP 相差 2～6 天 |

旅行天数按首尾日期都包含计算。

### 2.4 `TimeWindow`

| 属性 | 类型 | 必填 | 约束 | 默认值 |
|---|---|---:|---|---|
| `start_time` | string | 是 | `HH:mm` | — |
| `end_time` | string | 是 | 晚于 `start_time` | — |

### 2.5 `SourceRef`

用于追踪事实来源。

| 属性 | 类型 | 必填 | 约束/说明 |
|---|---|---:|---|
| `provider` | string | 是 | `mock`、`open_meteo`、具体地图服务等 |
| `source_id` | string/null | 是 | Provider 内部资源 ID；没有则为 `null` |
| `source_url` | string/null | 是 | 可核验 URL；没有则为 `null` |
| `fetched_at` | datetime | 是 | UTC |
| `expires_at` | datetime/null | 是 | 缓存失效时间 |
| `data_quality` | enum | 是 | `verified`、`estimated`、`incomplete`、`stale`、`mock` |

### 2.6 `PageMeta`

| 属性 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `next_cursor` | string/null | 是 | 下一页游标 |
| `has_more` | boolean | 是 | 是否还有数据 |
| `limit` | integer | 是 | 本页大小 |

分页响应统一为：

```json
{"items": [], "page": {"next_cursor": null, "has_more": false, "limit": 20}}
```

### 2.7 `ApiError`

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数不合法",
    "details": [
      {"field": "date_range.end_date", "reason": "must_be_after_start_date"}
    ],
    "request_id": "req_01J...",
    "retryable": false
  }
}
```

| 属性 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `error.code` | string | 是 | 稳定机器错误码 |
| `error.message` | string | 是 | 面向用户的简短说明 |
| `error.details` | array<object> | 是 | 可为空；字段错误或上下文 |
| `error.request_id` | string | 是 | 日志关联 ID |
| `error.retryable` | boolean | 是 | 客户端稍后重试是否可能成功 |

## 3. 旅行需求对象

### 3.1 枚举

`TripStatus`：

```text
draft | planning | needs_review | replanning | completed | failed | archived
```

`Pace`：`relaxed | balanced | packed`

`TransportMode`：

```text
walking | public_transit | taxi | driving | cycling | mixed
```

`PlaceCategory`：

```text
attraction | museum | park | anime | food | restaurant | cafe
shopping | neighborhood | temple | shrine | viewpoint | entertainment
```

`DietaryPreference`：

```text
none | vegetarian | vegan | halal | kosher | gluten_free
no_pork | no_beef | seafood_free | nut_free
```

### 3.2 `WeightedPreference`

| 属性 | 类型 | 必填 | 约束 |
|---|---|---:|---|
| `value` | string | 是 | 1～50 字符，归一化后的偏好标签 |
| `weight` | number | 是 | `0 < weight <= 1` |

### 3.3 `TripPreferences`

| 属性 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---:|---|---|
| `interests` | `WeightedPreference[]` | 是 | `[]` | 兴趣及权重 |
| `avoid` | string[] | 是 | `[]` | 不喜欢的活动或地点类别 |
| `dietary` | `DietaryPreference[]` | 是 | `[]` | 饮食限制 |
| `transport_modes` | `TransportMode[]` | 是 | `["public_transit","walking"]` | 按偏好顺序排列 |
| `accommodation_notes` | string/null | 是 | `null` | 住宿位置偏好；MVP 不预订 |
| `pace` | `Pace` | 是 | `balanced` | 行程节奏 |
| `must_visit_place_names` | string[] | 是 | `[]` | 必去地点，之后解析为 Place ID |

### 3.4 `TripConstraints`

| 属性 | 类型 | 必填 | 默认值 | 约束/说明 |
|---|---|---:|---|---|
| `total_budget` | `Money` | 是 | — | 整个旅行总预算 |
| `budget_is_hard_limit` | boolean | 是 | `true` | 超出是否判为 error |
| `daily_start_time` | string | 是 | `09:00` | `HH:mm` |
| `daily_end_time` | string | 是 | `21:00` | 晚于开始时间 |
| `max_walking_meters_per_day` | integer/null | 是 | `12000` | `1000～50000`；`null` 表示不限 |
| `max_activities_per_day` | integer | 是 | 按 pace 推导 | `1～10` |
| `minimum_transfer_buffer_minutes` | integer | 是 | `10` | `0～60` |
| `rest_minutes_per_day` | integer | 是 | `60` | `0～240` |
| `required_place_names` | string[] | 是 | `[]` | 硬性必去；无法满足则无解 |
| `excluded_place_names` | string[] | 是 | `[]` | 明确禁止出现 |
| `accessible_only` | boolean | 是 | `false` | 是否仅无障碍地点/路线 |

### 3.5 `TripCreateRequest`

| 属性 | 类型 | 必填 | 约束/说明 |
|---|---|---:|---|
| `origin` | string | 是 | 1～100 字符 |
| `destination` | string | 是 | 单城市，1～100 字符 |
| `destination_timezone` | string/null | 否 | IANA 时区；省略时后端解析，无法唯一确定则报错 |
| `date_range` | `DateRange` | 是 | 3～7 天 |
| `travelers` | integer | 是 | `1～6` |
| `preferences` | `TripPreferences` | 是 | — |
| `constraints` | `TripConstraints` | 是 | — |
| `locale` | string | 否 | BCP 47；默认 `zh-CN` |
| `display_currency` | string | 否 | ISO 4217；默认取预算币种 |
| `notes` | string/null | 否 | 最多 1000 字符 |

`total_budget` 表示整个团队整个行程的预算，不是人均预算。

### 3.6 `TripPatchRequest`

仅允许旅行尚未完成或归档时修改；已存在计划时，修改约束应走反馈接口以保留版本历史。

| 属性 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `origin` | string | 否 | 仅 `draft` 可改 |
| `destination` | string | 否 | 仅 `draft` 可改 |
| `destination_timezone` | string | 否 | 仅 `draft` 可改 |
| `date_range` | `DateRange` | 否 | 仅 `draft` 可改 |
| `travelers` | integer | 否 | 仅 `draft` 可改 |
| `preferences` | `TripPreferences` | 否 | 整体替换 |
| `constraints` | `TripConstraints` | 否 | 整体替换 |
| `notes` | string/null | 否 | `null` 清除 |

### 3.7 `Trip`

| 属性 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | UUID | 是 | 旅行 ID |
| `status` | `TripStatus` | 是 | 当前业务状态 |
| `revision` | integer | 是 | 乐观锁版本，从 1 开始 |
| `origin` | string | 是 | 出发地 |
| `destination` | string | 是 | 目的地城市 |
| `destination_timezone` | string | 是 | IANA 时区 |
| `date_range` | `DateRange` | 是 | 旅行日期 |
| `travelers` | integer | 是 | 人数 |
| `preferences` | `TripPreferences` | 是 | 当前偏好 |
| `constraints` | `TripConstraints` | 是 | 当前约束 |
| `locale` | string | 是 | 输出语言 |
| `display_currency` | string | 是 | 显示币种 |
| `notes` | string/null | 是 | 用户备注 |
| `current_plan_version` | integer/null | 是 | 尚未生成计划时为 `null` |
| `active_planning_run_id` | UUID/null | 是 | 当前运行中的任务 |
| `created_at` | datetime | 是 | UTC |
| `updated_at` | datetime | 是 | UTC |

### 3.8 `TripSummary`

列表页使用，属性为 `id`、`status`、`revision`、`origin`、`destination`、`date_range`、`travelers`、`current_plan_version`、`created_at`、`updated_at`。

## 4. 研究与事实对象

### 4.1 `WeatherDay`

| 属性 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `date` | date | 是 | 目的地当地日期 |
| `condition` | enum | 是 | `clear`、`partly_cloudy`、`cloudy`、`rain`、`storm`、`snow`、`fog`、`unknown` |
| `temperature_min_c` | number/null | 是 | 摄氏度 |
| `temperature_max_c` | number/null | 是 | 摄氏度 |
| `rain_probability` | number/null | 是 | `[0,1]` |
| `precipitation_mm` | number/null | 是 | `>= 0` |
| `sunrise_time` | string/null | 是 | 当地 `HH:mm` |
| `sunset_time` | string/null | 是 | 当地 `HH:mm` |
| `outdoor_suitability` | enum | 是 | `good`、`acceptable`、`poor`、`unknown` |
| `source` | `SourceRef` | 是 | 来源 |

### 4.2 `OpeningPeriod`

| 属性 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `day_of_week` | integer | 是 | ISO：1=周一，7=周日 |
| `open_time` | string/null | 是 | `HH:mm`；全天开放时 `00:00` |
| `close_time` | string/null | 是 | `HH:mm`；跨午夜需由 Provider 标准化 |
| `closed` | boolean | 是 | 当天是否关闭 |

特殊日期临时闭馆放在 `Place.special_opening_periods`，优先级高于周规则。

### 4.3 `SpecialOpeningPeriod`

| 属性 | 类型 | 必填 |
|---|---|---:|
| `date` | date | 是 |
| `open_time` | string/null | 是 |
| `close_time` | string/null | 是 |
| `closed` | boolean | 是 |
| `note` | string/null | 是 |

### 4.4 `Place`

| 属性 | 类型 | 必填 | 约束/说明 |
|---|---|---:|---|
| `id` | string | 是 | TravelMind 稳定 ID，不等同 Provider ID |
| `name` | string | 是 | 展示名 |
| `localized_name` | string/null | 是 | 当地语言名 |
| `categories` | `PlaceCategory[]` | 是 | 至少一项 |
| `address` | string/null | 是 | 完整地址 |
| `location` | `GeoPoint` | 是 | 必须有坐标才可参与路线规划 |
| `rating` | number/null | 是 | 通常 `[0,5]` |
| `rating_count` | integer/null | 是 | `>= 0` |
| `estimated_visit_minutes` | integer | 是 | `15～720` |
| `indoor_outdoor` | enum | 是 | `indoor`、`outdoor`、`mixed`、`unknown` |
| `opening_periods` | `OpeningPeriod[]` | 是 | 未知时为空数组 |
| `special_opening_periods` | `SpecialOpeningPeriod[]` | 是 | 可为空 |
| `admission` | `Money/null` | 是 | 免费为金额 0；未知为 `null` |
| `tags` | string[] | 是 | 用于偏好匹配 |
| `reservation_required` | boolean/null | 是 | 未知为 `null` |
| `accessible` | boolean/null | 是 | 无障碍信息 |
| `website_url` | string/null | 是 | 官方/详情页 |
| `source` | `SourceRef` | 是 | 来源 |

### 4.5 `RouteLeg`

| 属性 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | UUID | 是 | 路段 ID |
| `origin_place_id` | string | 是 | 起点 |
| `destination_place_id` | string | 是 | 终点 |
| `mode` | `TransportMode` | 是 | 交通方式 |
| `departure_time` | datetime/null | 是 | 带偏移量；规划后通常有值 |
| `arrival_time` | datetime/null | 是 | 带偏移量 |
| `duration_minutes` | integer | 是 | `>= 0` |
| `distance_meters` | integer | 是 | `>= 0` |
| `walking_meters` | integer | 是 | 路段中步行距离 |
| `cost` | `Money/null` | 是 | 未知时 `null` |
| `polyline` | string/null | 是 | 可选地图路线编码 |
| `instructions_summary` | string/null | 是 | 简短换乘说明 |
| `source` | `SourceRef` | 是 | 来源或估算方法 |

## 5. 行程与预算对象

### 5.1 `Activity`

| 属性 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | UUID | 是 | 跨重规划保持稳定，除非活动被删除 |
| `kind` | enum | 是 | `visit`、`meal`、`rest`、`transfer`、`free_time`、`check_in`、`check_out` |
| `title` | string | 是 | 展示标题 |
| `place_id` | string/null | 是 | 非地点活动可为 `null` |
| `start_at` | datetime | 是 | 含目的地 UTC 偏移量 |
| `end_at` | datetime | 是 | `> start_at` |
| `route_leg_id` | UUID/null | 是 | `transfer` 通常引用 RouteLeg |
| `estimated_cost` | `Money` | 是 | 免费为 0 |
| `priority` | integer | 是 | `1～100`，越高越应保留 |
| `locked` | boolean | 是 | 用户是否锁定 |
| `indoor_outdoor` | enum | 是 | 同 Place 枚举 |
| `reason` | string | 是 | 选择该活动的可公开理由 |
| `notes` | string[] | 是 | 预约、着装等提示 |
| `source_type` | enum | 是 | `planner`、`user`、`replacement`、`fixed_rule` |

### 5.2 `DayStatistics`

| 属性 | 类型 | 必填 |
|---|---|---:|
| `activity_count` | integer | 是 |
| `walking_meters` | integer | 是 |
| `transfer_minutes` | integer | 是 |
| `planned_minutes` | integer | 是 |
| `estimated_cost` | `Money` | 是 |

### 5.3 `DayPlan`

| 属性 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `date` | date | 是 | 当地日期 |
| `day_number` | integer | 是 | 从 1 开始 |
| `theme` | string | 是 | 如“浅草与秋叶原” |
| `weather` | `WeatherDay/null` | 是 | 无天气数据时为 `null` |
| `activities` | `Activity[]` | 是 | 按开始时间升序 |
| `route_legs` | `RouteLeg[]` | 是 | 行程涉及的路段 |
| `statistics` | `DayStatistics` | 是 | 程序计算 |
| `warnings` | string[] | 是 | 面向用户的提醒 |

### 5.4 `BudgetCategory`

```text
intercity_transport | accommodation | food | admission
local_transport | shopping | contingency | other
```

### 5.5 `BudgetItem`

| 属性 | 类型 | 必填 |
|---|---|---:|
| `id` | UUID | 是 |
| `category` | `BudgetCategory` | 是 |
| `label` | string | 是 |
| `date` | date/null | 是 |
| `activity_id` | UUID/null | 是 |
| `amount` | `Money` | 是 |
| `estimated` | boolean | 是 |
| `source` | `SourceRef/null` | 是 |

### 5.6 `BudgetSummary`

| 属性 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `limit` | `Money` | 是 | 用户总预算 |
| `items` | `BudgetItem[]` | 是 | 全部明细 |
| `totals_by_category` | object | 是 | key 为 `BudgetCategory`，value 为 `Money` |
| `planned_total` | `Money` | 是 | 明细求和，不由 LLM 填写 |
| `remaining_amount` | integer | 是 | 最小单位，可为负 |
| `currency` | string | 是 | 统一展示币种 |
| `within_budget` | boolean | 是 | 程序计算 |
| `exchange_rates` | object | 是 | 原币种到展示币种的汇率及时间；无换汇则 `{}` |

### 5.7 `Itinerary`

| 属性 | 类型 | 必填 |
|---|---|---:|
| `trip_id` | UUID | 是 |
| `title` | string | 是 |
| `destination` | string | 是 |
| `timezone` | string | 是 |
| `date_range` | `DateRange` | 是 |
| `days` | `DayPlan[]` | 是 |
| `budget` | `BudgetSummary` | 是 |
| `general_notes` | string[] | 是 |
| `generated_at` | datetime | 是 |

## 6. 约束与版本对象

### 6.1 `ConstraintViolation`

| 属性 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | UUID | 是 | 本次检查中的标识 |
| `code` | enum | 是 | 见下方规则码 |
| `severity` | enum | 是 | `error`、`warning`、`info` |
| `day` | date/null | 是 | 作用日期 |
| `activity_id` | UUID/null | 是 | 作用活动 |
| `message` | string | 是 | 面向用户说明 |
| `actual` | object/null | 是 | 机器可读实际值 |
| `expected` | object/null | 是 | 机器可读期望值 |
| `repair_hint` | string/null | 是 | 可公开修复建议 |
| `rule_version` | string | 是 | 规则实现版本 |

规则码：

```text
DATE_OUT_OF_RANGE
ACTIVITY_OVERLAP
PLACE_CLOSED
TRANSFER_TIME_INSUFFICIENT
DAILY_END_TIME_EXCEEDED
MAX_WALKING_EXCEEDED
BUDGET_EXCEEDED
WEATHER_MISMATCH
REQUIRED_PLACE_MISSING
EXCLUDED_PLACE_PRESENT
TOO_MANY_ACTIVITIES
DATA_INCOMPLETE
```

### 6.2 `ConstraintReport`

| 属性 | 类型 | 必填 |
|---|---|---:|
| `passed` | boolean | 是；仅在无 `error` 时为 true |
| `violations` | `ConstraintViolation[]` | 是 |
| `checked_rule_codes` | string[] | 是 |
| `checked_at` | datetime | 是 |
| `engine_version` | string | 是 |

### 6.3 `PlanVersion`

| 属性 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | UUID | 是 | 版本记录 ID |
| `trip_id` | UUID | 是 | 所属旅行 |
| `version` | integer | 是 | 从 1 开始递增 |
| `parent_version` | integer/null | 是 | 首版为 `null` |
| `status` | enum | 是 | `draft`、`valid`、`accepted`、`superseded` |
| `itinerary` | `Itinerary` | 是 | 不可变快照 |
| `constraint_report` | `ConstraintReport` | 是 | 对该快照的检查 |
| `change_summary` | string | 是 | 相对父版本的公开摘要 |
| `trigger` | enum | 是 | `initial`、`user_feedback`、`data_change`、`manual_validation` |
| `planning_run_id` | UUID | 是 | 生成该版本的运行 |
| `created_at` | datetime | 是 | UTC |
| `accepted_at` | datetime/null | 是 | 接受时间 |

### 6.4 `PlanDiff`

| 属性 | 类型 | 必填 |
|---|---|---:|
| `trip_id` | UUID | 是 |
| `from_version` | integer | 是 |
| `to_version` | integer | 是 |
| `added_activity_ids` | UUID[] | 是 |
| `removed_activity_ids` | UUID[] | 是 |
| `changed_activities` | `ActivityChange[]` | 是 |
| `unchanged_activity_count` | integer | 是 |
| `preservation_rate` | number | 是，`[0,1]` |
| `budget_delta_amount` | integer | 是，可为负 |
| `currency` | string | 是 |
| `summary` | string | 是 |

`ActivityChange` 包含 `activity_id`、`fields_changed: string[]`、`before: Activity`、`after: Activity`、`reason`。

## 7. 反馈与重规划对象

### 7.1 `FeedbackOperation`

采用判别联合类型，所有操作都必须包含 `op`：

| `op` | 额外必填属性 | 说明 |
|---|---|---|
| `add_preference` | `value: string`, `weight: number` | 添加/提高偏好 |
| `remove_preference` | `value: string` | 删除偏好 |
| `remove_place` | `place_id` 或 `place_name` | 删除地点 |
| `replace_place` | `old_place_id`, `new_place_id/name` | 指定替换 |
| `lock_activity` | `activity_id` | 锁定活动 |
| `unlock_activity` | `activity_id` | 解锁活动 |
| `move_activity` | `activity_id`, `target_date`, `preferred_time?` | 移动活动 |
| `set_budget` | `total_budget: Money`, `hard_limit: boolean` | 修改预算 |
| `set_max_walking` | `meters_per_day: integer` | 修改每日步行上限 |
| `set_daily_time_window` | `start_time`, `end_time`, `dates?` | 修改时间窗 |
| `set_late_start` | `date`, `start_time` | 某天晚出发 |
| `add_required_place` | `place_name` | 添加硬性必去 |
| `add_excluded_place` | `place_name` | 添加禁止地点 |
| `replace_outdoor_for_weather` | `date` | 根据天气替换户外项目 |

每个操作还可包含 `reason: string/null`，用于记录用户意图。

### 7.2 `FeedbackScope`

| 属性 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `dates` | date[] | 是 | 空数组表示由系统分析 |
| `activity_ids` | UUID[] | 是 | 可为空 |
| `global` | boolean | 是 | 是否影响全局约束 |

### 7.3 `FeedbackCreateRequest`

| 属性 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `base_plan_version` | integer | 是 | 用户看到的计划版本 |
| `message` | string | 是 | 1～2000 字符 |
| `client_operations` | `FeedbackOperation[]` | 否 | UI 已结构化操作时提供；服务端仍验证 |
| `auto_start_replanning` | boolean | 否 | 默认 `true` |

### 7.4 `FeedbackRecord`

| 属性 | 类型 | 必填 |
|---|---|---:|
| `id` | UUID | 是 |
| `trip_id` | UUID | 是 |
| `base_plan_version` | integer | 是 |
| `message` | string | 是 |
| `operations` | `FeedbackOperation[]` | 是 |
| `scope` | `FeedbackScope` | 是 |
| `requires_clarification` | boolean | 是 |
| `clarification_question` | string/null | 是 |
| `planning_run_id` | UUID/null | 是 |
| `created_at` | datetime | 是 |

## 8. 规划运行与事件对象

### 8.1 `PlanningRun`

`PlanningRunStatus`：

```text
queued | researching | planning | validating | repairing
waiting_for_review | completed | failed | cancelled
```

| 属性 | 类型 | 必填 |
|---|---|---:|
| `id` | UUID | 是 |
| `trip_id` | UUID | 是 |
| `trigger` | enum | 是：`initial`、`feedback`、`data_change` |
| `status` | `PlanningRunStatus` | 是 |
| `progress_percent` | integer | 是，`0～100`；仅展示，不作为流程依据 |
| `current_step` | string/null | 是 |
| `base_plan_version` | integer/null | 是 |
| `result_plan_version` | integer/null | 是 |
| `feedback_id` | UUID/null | 是 |
| `repair_attempts` | integer | 是 |
| `max_repair_attempts` | integer | 是 |
| `error` | `ApiError.error/null` | 是 |
| `created_at` | datetime | 是 |
| `started_at` | datetime/null | 是 |
| `finished_at` | datetime/null | 是 |

### 8.2 `PlanningEvent`

| 属性 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `id` | string | 是 | 单调递增事件 ID，可用于 SSE 恢复 |
| `run_id` | UUID | 是 | 运行 ID |
| `sequence` | integer | 是 | 从 1 递增 |
| `type` | enum | 是 | 见下方 |
| `step` | string/null | 是 | 节点名 |
| `message` | string | 是 | 可公开状态文案 |
| `payload` | object | 是 | 不含隐藏思维链和密钥 |
| `created_at` | datetime | 是 | UTC |

事件类型：

```text
run_started | step_started | step_completed | tool_started | tool_completed
constraint_found | repair_started | plan_created | review_required
run_completed | run_failed | run_cancelled | heartbeat
```

## 9. REST API 总览

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/health/live` | 进程存活检查 |
| GET | `/health/ready` | 依赖就绪检查 |
| GET | `/api/v1/meta/options` | 获取前端枚举与限制 |
| POST | `/api/v1/trips` | 创建旅行 |
| GET | `/api/v1/trips` | 分页获取旅行 |
| GET | `/api/v1/trips/{trip_id}` | 获取旅行详情 |
| PATCH | `/api/v1/trips/{trip_id}` | 修改草稿 |
| DELETE | `/api/v1/trips/{trip_id}` | 归档旅行 |
| POST | `/api/v1/trips/{trip_id}/planning-runs` | 启动初次规划 |
| GET | `/api/v1/trips/{trip_id}/planning-runs` | 获取运行历史 |
| GET | `/api/v1/trips/{trip_id}/planning-runs/{run_id}` | 获取运行状态 |
| POST | `/api/v1/trips/{trip_id}/planning-runs/{run_id}/cancel` | 取消运行 |
| GET | `/api/v1/trips/{trip_id}/planning-runs/{run_id}/events` | SSE 订阅事件 |
| GET | `/api/v1/trips/{trip_id}/plans` | 获取计划版本列表 |
| GET | `/api/v1/trips/{trip_id}/plans/{version}` | 获取完整计划版本 |
| GET | `/api/v1/trips/{trip_id}/plans/diff` | 比较两个版本 |
| POST | `/api/v1/trips/{trip_id}/plans/{version}/validate` | 重新运行约束检查 |
| POST | `/api/v1/trips/{trip_id}/plans/{version}/accept` | 接受计划 |
| POST | `/api/v1/trips/{trip_id}/feedback` | 提交反馈并重规划 |
| GET | `/api/v1/trips/{trip_id}/feedback` | 获取反馈历史 |
| POST | `/api/v1/trips/{trip_id}/exports` | 创建导出任务 |
| GET | `/api/v1/trips/{trip_id}/exports/{export_id}` | 获取导出状态 |
| GET | `/api/v1/trips/{trip_id}/exports/{export_id}/download` | 下载文件 |

## 10. 系统接口

### 10.1 `GET /health/live`

不检查外部依赖。成功返回 `200`：

```json
{"status": "ok", "service": "travelmind-api", "version": "0.1.0"}
```

### 10.2 `GET /health/ready`

检查数据库、Checkpoint 存储和必要配置；不要求第三方旅行 API 永远在线。

```json
{
  "status": "ready",
  "checks": {"database": "ok", "checkpoint_store": "ok", "llm_config": "ok"}
}
```

未就绪返回 `503 SERVICE_NOT_READY`。

### 10.3 `GET /api/v1/meta/options`

返回前端表单所需枚举、限制、默认值和服务能力：

```json
{
  "supported_locales": ["zh-CN", "en-US"],
  "supported_currencies": ["CNY", "JPY", "USD"],
  "transport_modes": ["walking", "public_transit", "taxi", "mixed"],
  "dietary_preferences": ["vegetarian", "vegan", "halal", "no_pork"],
  "trip_limits": {"min_days": 3, "max_days": 7, "max_travelers": 6},
  "capabilities": {"pdf_export": true, "mcp_tools": false, "real_providers": false}
}
```

## 11. 旅行接口

### 11.1 `POST /api/v1/trips`

请求体：`TripCreateRequest`。建议携带 `Idempotency-Key`。

成功：`201 Created`，`Location: /api/v1/trips/{id}`，响应 `Trip`。

```json
{
  "origin": "南京",
  "destination": "东京",
  "destination_timezone": "Asia/Tokyo",
  "date_range": {"start_date": "2026-10-01", "end_date": "2026-10-05"},
  "travelers": 2,
  "preferences": {
    "interests": [{"value": "动漫", "weight": 1.0}, {"value": "美食", "weight": 0.8}],
    "avoid": ["购物"],
    "dietary": [],
    "transport_modes": ["public_transit", "walking"],
    "accommodation_notes": "靠近地铁",
    "pace": "balanced",
    "must_visit_place_names": []
  },
  "constraints": {
    "total_budget": {"amount": 1000000, "currency": "CNY"},
    "budget_is_hard_limit": true,
    "daily_start_time": "09:00",
    "daily_end_time": "21:00",
    "max_walking_meters_per_day": 12000,
    "max_activities_per_day": 5,
    "minimum_transfer_buffer_minutes": 10,
    "rest_minutes_per_day": 60,
    "required_place_names": [],
    "excluded_place_names": [],
    "accessible_only": false
  },
  "locale": "zh-CN",
  "display_currency": "CNY",
  "notes": null
}
```

错误：`400 TIMEZONE_AMBIGUOUS`、`422 VALIDATION_ERROR`、`409 IDEMPOTENCY_CONFLICT`。

### 11.2 `GET /api/v1/trips`

Query：

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `status` | `TripStatus` | 无 | 可重复传递 |
| `cursor` | string | 无 | 分页游标 |
| `limit` | integer | 20 | `1～100` |
| `sort` | enum | `updated_desc` | `created_desc`、`updated_desc` |

成功 `200`：`{items: TripSummary[], page: PageMeta}`。

### 11.3 `GET /api/v1/trips/{trip_id}`

成功 `200` 返回 `Trip`，并设置 `ETag: "<revision>"`。不存在或无权访问统一返回 `404 TRIP_NOT_FOUND`。

### 11.4 `PATCH /api/v1/trips/{trip_id}`

请求头必须带 `If-Match`。请求体为 `TripPatchRequest`。成功 `200` 返回更新后的 `Trip`。

错误：`409 VERSION_CONFLICT`、`409 TRIP_NOT_EDITABLE`、`422 VALIDATION_ERROR`。

### 11.5 `DELETE /api/v1/trips/{trip_id}`

MVP 是软删除：将状态改为 `archived`，不物理删除版本和审计记录。必须带 `If-Match`。成功返回 `204 No Content`。

## 12. 规划运行接口

### 12.1 `POST /api/v1/trips/{trip_id}/planning-runs`

只用于初次规划或手动重新从当前需求生成，不用于自然语言反馈。

请求：

```json
{
  "mode": "initial",
  "force_refresh_tools": false,
  "max_repair_attempts": 3
}
```

| 属性 | 类型 | 必填 | 默认/约束 |
|---|---|---:|---|
| `mode` | enum | 否 | `initial` 或 `regenerate`；默认 `initial` |
| `force_refresh_tools` | boolean | 否 | 默认 false |
| `max_repair_attempts` | integer | 否 | 默认 3，`1～5` |

成功 `202 Accepted`：

```json
{
  "planning_run": {"id": "...", "trip_id": "...", "status": "queued", "progress_percent": 0},
  "events_url": "/api/v1/trips/.../planning-runs/.../events"
}
```

完整的 `PlanningRun` 字段仍需返回，示例为简写。已有活动运行时返回 `409 PLANNING_ALREADY_RUNNING`。

### 12.2 `GET /api/v1/trips/{trip_id}/planning-runs`

Query：`cursor`、`limit`、可选 `status`。返回分页 `PlanningRun`。

### 12.3 `GET /api/v1/trips/{trip_id}/planning-runs/{run_id}`

返回 `PlanningRun`。适合 SSE 断开时轮询。

### 12.4 `POST /api/v1/trips/{trip_id}/planning-runs/{run_id}/cancel`

请求体：`{"reason": "user_requested"}`，reason 最多 200 字。成功 `202` 返回最新 `PlanningRun`。已进入终态时幂等返回当前对象。

### 12.5 `GET /api/v1/trips/{trip_id}/planning-runs/{run_id}/events`

响应类型 `text/event-stream`。可带 `Last-Event-ID` 请求头恢复：

```text
id: 12
event: tool_completed
data: {"id":"12","run_id":"...","sequence":12,"type":"tool_completed","step":"research_weather","message":"已取得 5 天天气数据","payload":{"tool":"get_weather","item_count":5},"created_at":"2026-08-13T10:30:00Z"}

```

每 15～30 秒发送 `heartbeat`。运行终态事件发出后服务端可关闭连接。若事件已过保留期，返回 `410 EVENT_CURSOR_EXPIRED`，客户端转为查询运行与计划。

## 13. 计划接口

### 13.1 `GET /api/v1/trips/{trip_id}/plans`

Query：`cursor`、`limit`、可选 `status`。列表项返回 `PlanVersion` 元数据，但不返回完整 `itinerary.days`，改为附带 `day_count`、`planned_total`、`violation_counts`。

### 13.2 `GET /api/v1/trips/{trip_id}/plans/{version}`

成功 `200` 返回完整 `PlanVersion`。`version` 也可用字符串 `current`。

### 13.3 `GET /api/v1/trips/{trip_id}/plans/diff`

Query 必填：`from_version`、`to_version`。成功返回 `PlanDiff`。

### 13.4 `POST /api/v1/trips/{trip_id}/plans/{version}/validate`

用于规则升级或人工排错。请求：

```json
{"rule_codes": [], "refresh_tool_data": false}
```

空 `rule_codes` 表示运行所有规则。默认不生成新计划版本，只返回最新 `ConstraintReport`。若事实已过期且未允许刷新，在报告中产生 `DATA_INCOMPLETE`。

### 13.5 `POST /api/v1/trips/{trip_id}/plans/{version}/accept`

请求头 `If-Match` 为 Trip revision。请求体：

```json
{"acknowledged_warning_ids": ["violation-uuid"]}
```

只有无 `error` 的计划可接受；warning 可以由用户确认。成功 `200` 返回更新后的 `PlanVersion` 和 `Trip`：

```json
{"trip": {}, "plan": {}}
```

错误：`409 PLAN_HAS_ERRORS`、`409 PLAN_VERSION_NOT_CURRENT`、`409 VERSION_CONFLICT`。

## 14. 反馈接口

### 14.1 `POST /api/v1/trips/{trip_id}/feedback`

请求为 `FeedbackCreateRequest`。成功情况分两种：

1. 意图明确且自动重规划：`202 Accepted`。

```json
{
  "feedback": {
    "id": "...",
    "trip_id": "...",
    "base_plan_version": 1,
    "message": "第二天 11:30 才能出发，但仍想看日落",
    "operations": [
      {"op": "set_late_start", "date": "2026-10-02", "start_time": "11:30", "reason": null}
    ],
    "scope": {"dates": ["2026-10-02"], "activity_ids": [], "global": false},
    "requires_clarification": false,
    "clarification_question": null,
    "planning_run_id": "...",
    "created_at": "2026-08-13T10:30:00Z"
  },
  "planning_run": {},
  "events_url": "/api/v1/trips/.../planning-runs/.../events"
}
```

2. 有歧义：`200 OK`，`requires_clarification=true`、`planning_run_id=null`。客户端显示 `clarification_question`，用户下一次反馈应明确回答，并仍引用同一 `base_plan_version`。

错误：`409 VERSION_CONFLICT`、`409 PLANNING_ALREADY_RUNNING`、`422 MODEL_OUTPUT_INVALID`。

### 14.2 `GET /api/v1/trips/{trip_id}/feedback`

Query：`cursor`、`limit`。返回分页 `FeedbackRecord`，按创建时间倒序。

## 15. 导出接口

### 15.1 `ExportJob`

| 属性 | 类型 | 必填 |
|---|---|---:|
| `id` | UUID | 是 |
| `trip_id` | UUID | 是 |
| `plan_version` | integer | 是 |
| `format` | enum | 是：`markdown`、`pdf` |
| `status` | enum | 是：`queued`、`processing`、`completed`、`failed` |
| `file_name` | string/null | 是 |
| `content_type` | string/null | 是 |
| `size_bytes` | integer/null | 是 |
| `download_expires_at` | datetime/null | 是 |
| `error` | `ApiError.error/null` | 是 |
| `created_at` | datetime | 是 |
| `completed_at` | datetime/null | 是 |

### 15.2 `POST /api/v1/trips/{trip_id}/exports`

请求：

```json
{"plan_version": 3, "format": "pdf", "locale": "zh-CN", "include_trace": false}
```

只有 `valid` 或 `accepted` 计划可导出。Markdown 可同步完成但仍统一返回 `202` 和 `ExportJob`，简化客户端。

### 15.3 `GET /api/v1/trips/{trip_id}/exports/{export_id}`

返回 `ExportJob`。完成后同时返回相对地址 `download_url`。

### 15.4 `GET /api/v1/trips/{trip_id}/exports/{export_id}/download`

返回文件流，并设置安全的 `Content-Disposition`。任务未完成返回 `409 EXPORT_NOT_READY`；过期返回 `410 EXPORT_EXPIRED`。

## 16. HTTP 状态码与错误码

| HTTP | 错误码 | 场景 | 可重试 |
|---:|---|---|---:|
| 400 | `TIMEZONE_AMBIGUOUS` | 目的地无法唯一解析时区 | 否 |
| 400 | `INVALID_CURSOR` | 分页/事件游标无效 | 否 |
| 404 | `TRIP_NOT_FOUND` | 旅行不存在或不可访问 | 否 |
| 404 | `PLAN_NOT_FOUND` | 计划版本不存在 | 否 |
| 404 | `RUN_NOT_FOUND` | 运行不存在 | 否 |
| 409 | `VERSION_CONFLICT` | revision 或 base version 过期 | 否 |
| 409 | `PLANNING_ALREADY_RUNNING` | 已有活动任务 | 稍后 |
| 409 | `TRIP_NOT_EDITABLE` | 当前状态不允许 Patch | 否 |
| 409 | `PLAN_HAS_ERRORS` | 有硬约束错误，不能接受 | 否 |
| 409 | `NO_FEASIBLE_PLAN` | 当前约束组合无解 | 否 |
| 409 | `EXPORT_NOT_READY` | 导出未完成 | 是 |
| 410 | `EVENT_CURSOR_EXPIRED` | SSE 历史已清理 | 否 |
| 410 | `EXPORT_EXPIRED` | 下载文件过期 | 否 |
| 422 | `VALIDATION_ERROR` | Schema/业务字段校验失败 | 否 |
| 422 | `CLARIFICATION_REQUIRED` | 不用于正常反馈响应，仅特殊同步接口 | 否 |
| 422 | `MODEL_OUTPUT_INVALID` | 模型输出多次未通过 Schema | 是 |
| 429 | `RATE_LIMITED` | 服务限流 | 是 |
| 502 | `TOOL_DATA_INCOMPLETE` | 外部事实不足且不能降级 | 是 |
| 503 | `TOOL_TEMPORARILY_UNAVAILABLE` | 外部服务不可用 | 是 |
| 503 | `SERVICE_NOT_READY` | 本服务依赖未就绪 | 是 |
| 500 | `PLANNING_LIMIT_REACHED` | 修正循环上限/无进展 | 否 |
| 500 | `INTERNAL_ERROR` | 未分类错误 | 视情况 |

错误响应可通过 `Retry-After` 指示建议重试时间。

## 17. 后端内部工具协议

领域和 Agent 只依赖这些接口，不直接依赖 Provider SDK。

### 17.1 `WeatherTool.get_forecast`

输入 `WeatherQuery`：

| 属性 | 类型 | 必填 |
|---|---|---:|
| `city` | string | 是 |
| `location` | `GeoPoint/null` | 是 |
| `date_range` | `DateRange` | 是 |
| `timezone` | string | 是 |
| `locale` | string | 是 |

输出 `WeatherResult`：

| 属性 | 类型 | 必填 |
|---|---|---:|
| `days` | `WeatherDay[]` | 是 |
| `missing_dates` | date[] | 是 |
| `source` | `SourceRef` | 是 |

### 17.2 `PoiTool.search`

输入 `PoiSearchQuery`：

| 属性 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `city` | string | 是 | 城市 |
| `center` | `GeoPoint/null` | 是 | 可选搜索中心 |
| `categories` | `PlaceCategory[]` | 是 | 空表示不限 |
| `keywords` | string[] | 是 | 偏好关键词 |
| `exclude_keywords` | string[] | 是 | 排除词 |
| `date_range` | `DateRange` | 是 | 用于营业信息 |
| `limit` | integer | 是 | `1～50` |
| `locale` | string | 是 | 结果语言 |

输出 `PoiSearchResult`：`places: Place[]`、`next_cursor: string/null`、`source: SourceRef`。

### 17.3 `PoiTool.get_detail`

输入：`place_id: string`、`date_range: DateRange`、`locale: string`。输出：完整 `Place`。找不到应抛出稳定 `ToolError(code="PLACE_NOT_FOUND")`。

### 17.4 `RouteTool.get_matrix`

输入 `RouteMatrixQuery`：

| 属性 | 类型 | 必填 | 约束 |
|---|---|---:|---|
| `origins` | `RoutePoint[]` | 是 | `1～25` |
| `destinations` | `RoutePoint[]` | 是 | `1～25` |
| `mode` | `TransportMode` | 是 | Provider 必须支持或显式拒绝 |
| `departure_at` | datetime/null | 是 | 公交建议提供 |
| `timezone` | string | 是 | — |

`RoutePoint` 包含 `place_id`、`location: GeoPoint`。

输出 `RouteMatrixResult`：

```text
cells: RouteMatrixCell[]
source: SourceRef
```

`RouteMatrixCell` 包含 `origin_place_id`、`destination_place_id`、`status: ok|unreachable|unknown`、`duration_minutes`、`distance_meters`、`walking_meters`、`cost`；后三项在非 ok 时可为 null。

### 17.5 `RouteTool.get_route`

输入：`origin: RoutePoint`、`destination: RoutePoint`、`mode`、`departure_at`、`timezone`。输出完整 `RouteLeg`。

### 17.6 `ToolError`

| 属性 | 类型 | 必填 |
|---|---|---:|
| `code` | string | 是 |
| `message` | string | 是 |
| `provider` | string | 是 |
| `retryable` | boolean | 是 |
| `retry_after_seconds` | integer/null | 是 |
| `details` | object | 是 |

所有 Adapter 必须把第三方异常映射为 `ToolError`，不得把 SDK 异常泄漏进领域层。

## 18. MCP 工具契约

MCP 工具名称和输入输出语义与内部协议保持一致。MCP 层只做协议传输、鉴权、Schema 校验和错误映射。

### 18.1 `get_weather`

输入与 `WeatherQuery` 相同；输出与 `WeatherResult` 相同。

### 18.2 `search_poi`

输入与 `PoiSearchQuery` 相同；输出与 `PoiSearchResult` 相同。

### 18.3 `get_place_detail`

输入：

```json
{"place_id": "tm_place_123", "start_date": "2026-10-01", "end_date": "2026-10-05", "locale": "zh-CN"}
```

输出：`Place`。

### 18.4 `get_route_matrix`

输入与 `RouteMatrixQuery` 相同；输出与 `RouteMatrixResult` 相同。

### 18.5 `get_route`

输入与内部 `get_route` 相同；输出 `RouteLeg`。

### 18.6 可选 `search_local_event`

不属于首版 MVP。若实现，输入包含 `city`、`date_range`、`categories`、`locale`、`limit`；输出 `LocalEvent[]`。

`LocalEvent` 必须包含：`id`、`name`、`start_at`、`end_at`、`venue_name`、`location`、`price: Money/null`、`booking_url`、`categories`、`source`。没有可靠来源的活动不得返回。

### 18.7 MCP 错误

工具失败返回机器可识别的错误数据：

```json
{
  "code": "PROVIDER_RATE_LIMITED",
  "message": "天气服务暂时限流",
  "retryable": true,
  "retry_after_seconds": 30,
  "provider": "example_weather"
}
```

不要把失败包装成“成功但内容是一段错误文字”，否则 Agent 无法可靠路由。

## 19. LangGraph `TripAgentState`

此对象不直接暴露给前端，但需要明确属性：

| 属性 | 类型 | 必填 | Reducer/说明 |
|---|---|---:|---|
| `trip_id` | UUID | 是 | 覆盖 |
| `run_id` | UUID | 是 | 覆盖 |
| `trigger` | enum | 是 | 覆盖 |
| `request` | `Trip` | 是 | 最新权威需求快照 |
| `weather_data` | `WeatherDay[]` | 是 | 按日期 upsert |
| `poi_candidates` | `Place[]` | 是 | 按 Place ID upsert |
| `route_cache` | `RouteLeg[]` | 是 | 按起终点/方式/时间键 upsert |
| `current_itinerary` | `Itinerary/null` | 是 | 覆盖 |
| `constraint_report` | `ConstraintReport/null` | 是 | 覆盖 |
| `feedback` | `FeedbackRecord/null` | 是 | 覆盖 |
| `affected_dates` | date[] | 是 | 集合合并 |
| `locked_activity_ids` | UUID[] | 是 | 集合合并 |
| `repair_attempts` | integer | 是 | 累加 |
| `max_repair_attempts` | integer | 是 | 覆盖 |
| `last_plan_fingerprint` | string/null | 是 | 无进展检测 |
| `events` | `PlanningEvent[]` | 是 | 追加；持久化后可只留游标 |
| `status` | `PlanningRunStatus` | 是 | 覆盖 |
| `last_error` | `ToolError/ApiError.error/null` | 是 | 覆盖 |
| `result_plan_version` | integer/null | 是 | 覆盖 |

State 只保存工作流需要的数据；大量第三方原始响应应存工具调用记录或对象存储，不进入 checkpoint。

## 20. LLM 结构化对象

### 20.1 `ParsedFeedback`

| 属性 | 类型 | 必填 |
|---|---|---:|
| `operations` | `FeedbackOperation[]` | 是 |
| `scope` | `FeedbackScope` | 是 |
| `requires_clarification` | boolean | 是 |
| `clarification_question` | string/null | 是 |
| `confidence` | number | 是，`[0,1]` |

当 `requires_clarification=true` 时，`operations` 可以为空；当为 false 时至少有一个操作。服务端必须再次验证引用的日期、活动与地点是否存在。

### 20.2 `CandidateRanking`

| 属性 | 类型 | 必填 |
|---|---|---:|
| `ranked_place_ids` | string[] | 是 |
| `reasons` | object | 是；key 为 place ID，value 为短理由 |
| `rejected_place_ids` | string[] | 是 |

只允许返回输入候选集中的 ID。

### 20.3 `RepairProposal`

| 属性 | 类型 | 必填 |
|---|---|---:|
| `actions` | `RepairAction[]` | 是 |
| `summary` | string | 是 |
| `expected_resolved_violation_ids` | UUID[] | 是 |

`RepairAction.action` 可为 `shift_activity`、`remove_activity`、`replace_activity`、`change_transport_mode`、`swap_days`。每种 action 必须引用已存在 ID 或已验证候选 ID。程序执行后必须重新运行 Constraint Engine。

## 21. OpenAPI 与代码生成要求

实现时 FastAPI 应生成 `/openapi.json`，并满足：

1. 每个接口都有稳定 `operation_id`，如 `create_trip`、`start_planning_run`。
2. 每个请求/响应都引用命名 Schema，不使用匿名大对象。
3. 枚举有说明，错误响应引用统一 `ApiError`。
4. 给所有非 2xx 分支写 OpenAPI response。
5. 前端类型从 OpenAPI 自动生成，不手写第二套含义不同的类型。
6. CI 导出 OpenAPI 后检查 diff；破坏性变化必须升级 API 版本。

## 22. 实现顺序

不要一次实现本文全部接口。按依赖顺序落地：

1. `Money`、旅行需求对象、`Trip`、`ApiError`。
2. `/health/*`、`POST/GET/PATCH /trips`。
3. `Place`、`WeatherDay`、`RouteLeg`、`Activity`、`Itinerary`。
4. `ConstraintViolation`、`ConstraintReport`、规则引擎。
5. `PlanningRun` 和启动/查询接口，先同步内部执行，外部仍返回任务对象。
6. `PlanVersion`、计划查询、校验和接受接口。
7. `FeedbackOperation`、反馈接口和版本 diff。
8. SSE 事件。
9. 真实 Tool Adapter 和内部工具契约。
10. MCP 工具。
11. 导出接口。

每完成一个对象，至少测试：合法最小值、合法完整值、缺失必填字段、非法枚举、边界数值及 JSON 往返序列化。

## 23. 契约完整性检查表

- [ ] 请求对象与响应对象分开，服务端字段不能由客户端伪造。
- [ ] 金额包含币种，计算使用最小单位整数。
- [ ] 日期时间包含目的地时区语义。
- [ ] 未知、空值和零值没有混淆。
- [ ] 每个事实能追踪 `SourceRef`。
- [ ] 所有耗时操作都有 `PlanningRun` 或 `ExportJob`。
- [ ] 所有可变更新都有 revision/base version。
- [ ] 所有 Agent 输出都经过 Schema 和业务二次校验。
- [ ] 所有计划通过约束引擎后才能接受。
- [ ] 所有第三方异常映射成稳定 ToolError。
- [ ] SSE 可以断线恢复且不暴露隐藏推理。
- [ ] 计划版本不可变且可以比较差异。
- [ ] OpenAPI 是前后端共享契约的唯一权威来源。
