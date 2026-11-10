# 04 · 代码现状与影响面（样例）

- 关联需求：`order-partial-refund`
- 代码基线：`order-service @ main`

## 1. 系统现状

- 技术栈：TypeScript / NestJS / PostgreSQL / Kafka。
- 相关模块：`services/order`、`services/inventory`、`services/finance`。

## 2. 与需求相关的现有实现

| # | 现状 | 证据 | 标注 |
| --- | --- | --- | --- |
| 1 | 现有整单退款入口 | `services/order/src/refund.controller.ts:31` | 事实 |
| 2 | 退款金额按整单计算 | `services/order/src/refund.calculator.ts:88` | 事实 |
| 3 | 订单状态含 PAID/REFUNDING/REFUNDED | `services/order/src/order.state.ts:12` | 事实 |
| 4 | 财务流水消费 refund.succeeded 事件 | `services/finance/src/ledger.consumer.ts:54` | 事实 |
| 5 | 审批中心 SDK 可直接复用 | `services/order/src/approval.client.ts:19` | 推断 |

## 3. 能力差距（Gap）

| Gap | 功能点 | 现状 | 差距 | 证据 |
| --- | --- | --- | --- | --- |
| G1 | F1/F2 | 仅整单退款 | 需支持按商品/金额 | `refund.calculator.ts:88` |
| G2 | F3 | 无审批接入 | 需接审批中心 | `approval.client.ts:19` |
| G3 | F5 | 库存仅整单回补 | 需按退款商品回补 | `services/inventory/src/restock.service.ts:40` |

## 4. 影响面 / 爆炸半径

| 层面 | 涉及对象 | 现状 | 预计改动 | 风险 | 证据 |
| --- | --- | --- | --- | --- | --- |
| 页面/路由 | 客服订单详情 | 整单退款按钮 | 增加部分退款入口 | 低 | `web/order/detail.tsx:120` |
| 接口/API | POST /orders/{id}/refund | 整单 | 增加 items/amount | 中 | `refund.controller.ts:31` |
| 数据/表 | order_refund | 无明细 | 新增 order_refund_item | 中 | `migrations/0007_refund.sql` |
| 任务/消息 | refund.succeeded | 已有 | 复用 | 低 | `ledger.consumer.ts:54` |
| 配置/开关 | 无 | — | 新增灰度开关 | 低 | — |
| 权限/安全 | 客服角色 | 已有 | 新增退款权限点 | 中 | `auth/roles.ts:22` |
| 测试 | order 单测 | 覆盖整单 | 补部分退款用例 | 中 | `test/refund.spec.ts` |
| 监控/告警 | 退款失败告警 | 已有 | 增加金额差错监控 | 低 | `ops/alerts/refund.yml` |

## 5. 技术约束与历史包袱

- 退款计算强依赖订单快照，历史订单需按创建时规则。

## 6. 可复用点

- 审批中心 SDK、`refund.succeeded` 事件、库存回补服务。

## 7. 待 PM / 研发确认

- 退款明细是否需要独立对账口径。
