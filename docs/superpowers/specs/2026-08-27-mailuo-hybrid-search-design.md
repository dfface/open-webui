# 脉络混合搜索设计

日期：2026-08-27
状态：设计已口头确认，待文档复核

## 1. 背景

脉络把 Outline 正文、Outline 评论以及后续的 Memos、Kaneo 等数据统一写入 PostgreSQL `mailuo` 数据库的 `public.chunks` 表，并使用同一个 embedding 模型生成向量。Open WebUI 已能通过外部 pgvector Knowledge 访问这些数据，但它当前更偏向 RAG 问答，不能独立提供完整的关键词、语义和混合搜索体验。

本设计在 Open WebUI fork 中增加独立的“脉络”搜索页面。页面不依赖聊天大模型，复用 Open WebUI 的登录、Knowledge 权限和外部 pgvector 连接，通过 PostgreSQL 完成关键词检索、语义检索和混合排序，并让每条结果能够直接打开原文。

## 2. 目标

- 在 Open WebUI 内提供独立的 `/mailuo` 搜索页面，产品名称和现有 Logo 保持不变。
- 支持混合搜索、关键词搜索、语义搜索三种模式。
- 搜索结果按原始对象聚合，而不是把多个 chunk 当成多篇结果。
- 每条结果可以直接打开 `source_url` 指向的原文或评论。
- 复用 Open WebUI Knowledge 的读取权限，不建立第二套权限系统。
- 复用外部 pgvector Knowledge 已配置的数据库连接与 embedding 配置。
- 对 embedding 服务的单请求容量进行串行保护，并定义清晰的降级行为。
- 新增 Memos、Kaneo 或其他 source 时，无需修改 Open WebUI 或搜索 SQL 的代码。
- 将对 Open WebUI 上游源码的修改压缩到少量、容易 rebase 和丢弃的接入点。

## 3. 非目标

- 本阶段不提供聊天问答，不调用聊天大模型。
- 本阶段不迁移到尚未投入使用的 `mailuo.object_chunks` 等规范化表。
- 本阶段不在 Open WebUI 中承担数据采集、切块、向量生成和删除同步；这些仍由 n8n 工作流负责。
- 本阶段不实现按 source 定制的结果卡片、图标或业务筛选器。
- 本阶段不修改 Open WebUI 原有 RAG 检索行为。

## 4. 核心原则：source 零代码接入

`outline`、`outline_comments`、`memos`、`kaneo` 不是程序枚举，也不会出现在前后端条件分支中。`source` 是数据字段，新 source 只需满足统一写入契约即可参与检索。

统一写入契约至少包含：

| 字段                | 语义                                                          |
| ------------------- | ------------------------------------------------------------- |
| `source`            | 稳定的数据源标识，例如 `memos`                                |
| `source_object_id`  | 该 source 内稳定的原始对象 ID                                 |
| `chunk_no`          | 同一对象内从 0 开始的 chunk 序号                              |
| `title`             | 对象标题；没有自然标题时由采集流程生成可读标题                |
| `content`           | 当前 chunk 的可检索正文，不重复拼接标题                       |
| `source_url`        | 可直接打开原对象的绝对地址，评论应包含 `commentId` 等定位参数 |
| `source_updated_at` | 原对象最后更新时间，用于增量同步和结果展示                    |
| `content_hash`      | 判断内容是否变化的开放长度哈希或版本标识                      |
| `metadata`          | JSONB 扩展字段，用于保存作者、项目、状态等非通用信息          |
| `embedding`         | 与 Open WebUI 配置使用相同模型生成的 pgvector 向量            |

数据库使用 `(source, source_object_id, chunk_no)` 作为 chunk 的业务唯一键。采集流程负责把不同系统映射到这些通用字段：例如 Outline 评论的深链接规则属于 n8n 连接器，不属于搜索页面。

搜索页面通过数据库动态发现当前存在的 source，前端不维护 source 列表。未知 source 使用通用 badge，显示原始 `source` 名称，仍能正常搜索和打开原文。可选的 `public.mailuo_sources` 配置表只负责显示名称、排序和颜色；未登记的 source 自动回退到默认显示，因此登记不是接入前置条件。

## 5. 总体架构

```text
n8n connectors
  ├─ Outline documents
  ├─ Outline comments
  ├─ Memos
  └─ Kaneo / future sources
          │ 统一写入契约
          ▼
mailuo PostgreSQL
  ├─ public.chunks
  ├─ search_tsv + GIN/trigram/vector indexes
  ├─ public.mailuo_hybrid_search(...)
  └─ public.open_webui_chunks compatibility view
          │ 外部 pgvector Knowledge 连接
          ▼
Open WebUI fork
  ├─ Knowledge 权限校验
  ├─ Mailuo search API
  ├─ Redis embedding lock
  └─ /mailuo 搜索页面
```

数据库负责候选召回、RRF 排序和 chunk 级结果；Open WebUI 后端负责身份鉴权、Knowledge 授权、embedding 调用、跨 Knowledge 容错和对象聚合；前端只负责查询状态、筛选和结果展示。

## 6. 数据库设计

### 6.1 继续使用 `public.chunks`

第一版直接在实际使用的 `public.chunks` 上增加搜索能力，避免维护两套事实表。数据库变更属于 Mailuo 数据层，由 Mailuo 仓库的独立迁移管理，不加入 Open WebUI 自带 migration。

### 6.2 全文与模糊检索

- 增加生成列 `search_tsv`，将 `title` 设为权重 A，`content` 设为权重 B。
- 为 `search_tsv` 建立 GIN 索引。
- 启用 PostgreSQL `pg_trgm` 扩展，为标题和正文的模糊匹配建立合适的 GIN/GiST 索引。
- 继续使用现有 pgvector 索引完成向量候选召回。
- 不要求 `zhparser`。第一版使用 PostgreSQL 原生全文检索补充精确词匹配，并由 trigram 覆盖中文子串和模糊匹配。

### 6.3 动态 source

检索函数接受可为空的 `source_filter text[]`：

- 空值代表搜索所有 source。
- 非空值使用 `source = ANY(source_filter)` 过滤。
- 函数不校验固定枚举，也不按 source 分支。

source 列表从当前可访问的数据集动态聚合。可选配置表结构为：

```sql
CREATE TABLE public.mailuo_sources (
  source varchar(64) PRIMARY KEY,
  display_name text,
  color text,
  sort_order integer NOT NULL DEFAULT 0,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);
```

查询时以实际存在的 `chunks.source` 为主，左连接该表补充展示信息。没有配置行的 source 仍会返回。

### 6.4 数据库检索函数

提供稳定的数据库边界 `public.mailuo_hybrid_search(...)`。参数包括查询文本、可为空的查询向量、模式、source 过滤、候选数、返回数和 RRF 参数。返回 chunk 级结果以及各召回通道的排名信息。

候选召回规则：

- 全文检索候选 Top 50。
- trigram 候选 Top 50。
- 向量候选 Top 50。
- 所有业务过滤必须在候选排名之前执行。
- 混合模式使用三路候选；关键词模式只使用全文和 trigram；语义模式只使用向量。
- 使用 RRF 融合，默认 `k = 60`。
- RRF 分数只用于排序，不直接展示给用户。

兼容 View `public.open_webui_chunks` 继续服务 Open WebUI 原有外部 pgvector Knowledge，不承担脉络混合排序逻辑。

## 7. 排序与对象聚合

数据库先对 chunk 排名，后端再按 `(source, source_object_id)` 聚合为原始对象：

- 对象得分取其最佳 chunk 的得分，不累加所有 chunk，避免长文档因 chunk 数量多而天然占优。
- 最多返回 20 个对象。
- 每个对象最多保留 3 个匹配片段。
- 结果携带 `matched_by`，可包含 `fulltext`、`trigram`、`semantic`，用于解释命中方式。
- 同分时使用确定性次序，例如 `source_updated_at DESC`、`source`、`source_object_id`，保证翻页或重复查询稳定。

Outline 正文和评论是不同对象：正文使用 `source = 'outline'`，评论使用 `source = 'outline_comments'`。删除正文时由 n8n webhook 同时删除其正文和关联评论 chunk；搜索层不推断跨 source 删除关系。

## 8. Open WebUI 后端

### 8.1 目录与接入点

大部分新增后端代码放在：

```text
backend/open_webui/mailuo/
```

上游文件仅在 `backend/open_webui/main.py` 增加 Mailuo router 的导入和注册。现有外部 pgvector 查询向量类型补丁保持独立、最小化提交；上游修复后可以整项删除。

### 8.2 搜索 API

接口：

```http
POST /api/v1/mailuo/search
```

请求示例：

```json
{
	"query": "统一搜索",
	"mode": "hybrid",
	"knowledge_ids": ["knowledge-id"],
	"sources": ["outline", "memos"],
	"limit": 20
}
```

响应示例：

```json
{
	"requested_mode": "hybrid",
	"executed_mode": "hybrid",
	"degraded": false,
	"warnings": [],
	"results": [
		{
			"source": "outline",
			"source_object_id": "object-id",
			"title": "统一搜索设计",
			"source_url": "https://example.com/doc/id",
			"source_updated_at": "2026-08-27T00:00:00Z",
			"matched_by": ["fulltext", "semantic"],
			"matches": [{ "chunk_no": 2, "content": "匹配片段……" }]
		}
	]
}
```

模式只允许 `hybrid`、`keyword`、`semantic`。非法输入返回 400。用户显式指定无权访问的 Knowledge 时返回 403，而不是悄悄忽略。

### 8.3 source 发现 API

提供一个只读 facets 接口，根据当前用户可访问且已选择的 Mailuo-compatible Knowledge 返回实际存在的 source 及可选显示配置。接口不返回数据库凭据或内部表结构。页面加载与 Knowledge 选择变化时调用该接口，因此后续写入 `memos`、`kaneo` 后会自动出现在筛选项中。

### 8.4 Knowledge 与权限

- 仅允许搜索当前用户具有读取权限的外部 pgvector Knowledge。
- 后端在每次请求中重新校验权限，不相信前端传入的 ID。
- Knowledge 必须满足 Mailuo 兼容契约；不兼容项不出现在脉络选择器中。
- 数据库连接、字段映射和 embedding 模型沿用 Knowledge 配置，不向浏览器暴露 DSN。
- 第一版允许选择全部可访问 Knowledge 或单个 Knowledge。

### 8.5 embedding 串行化

embedding 服务一次只能可靠处理一个请求，因此：

- 只有用户按 Enter 或点击搜索按钮时才发起搜索，不做输入联想和逐字 embedding。
- 每次查询只生成一个查询向量，并在同一请求涉及的所有 Knowledge 间复用。
- 使用 Redis 分布式锁串行化脉络页面的 embedding 请求；锁设置等待超时和自动过期，避免进程异常后永久占用。
- 关键词模式不调用 embedding，也不获取该锁。
- 混合模式发生 embedding 超时或失败时，自动执行关键词搜索，并返回 `degraded = true`、`executed_mode = 'keyword'` 和可读警告。
- 用户明确选择语义模式时，embedding 失败直接返回错误，不静默改变搜索语义。

### 8.6 局部失败与日志

- 一个 Knowledge 失败时返回其他 Knowledge 的结果，同时附带 warning。
- 所有 Knowledge 都失败时返回错误。
- 前端错误信息不包含 DSN、SQL、向量内容或堆栈。
- 后端记录结构化诊断信息，包括请求 ID、模式、耗时、候选数、降级原因和失败 Knowledge ID。
- 日志不记录完整查询文本、密码、Token 或数据库连接串。

## 9. 前端设计

新增路由：

```text
src/routes/(app)/mailuo/+page.svelte
```

可复用组件和请求逻辑集中在：

```text
src/lib/mailuo/
```

或 `src/lib/components/mailuo/`。上游公共组件只在 `src/lib/components/layout/Sidebar/UserMenu.svelte` 增加“脉络”入口。SvelteKit 自动发现页面，不引入中央路由表。

页面采用单列结果布局：

- 顶部为搜索框和明确的搜索按钮。
- 提供混合、关键词、语义三个模式 chip。
- 提供 Knowledge 和 source 筛选器；source 选项来自 facets API，不写死名称。
- 结果卡显示标题、通用 source badge、命中通道、更新时间、最佳片段和“打开原文”按钮。
- 每个对象默认显示一个片段，可展开另外两个片段。
- 未登记的 source 以原始字段值显示，不影响搜索能力。
- 原文链接在新标签页打开，并设置 `noopener noreferrer`。
- 不显示原始 RRF 分数，只显示 `matched_by` 解释标签。

查询文本、模式、Knowledge 和 source 筛选状态写入 URL，支持刷新、浏览器前进后退和收藏。Enter 提交，`/` 聚焦搜索框，Esc 清空；所有控件支持键盘操作和可见焦点。

页面状态：

- 初始状态不自动搜索，提供简短使用提示。
- 加载状态保留上一轮结果，并显示进度，不清空页面造成闪烁。
- 空结果状态提示尝试切换模式或放宽 source 范围。
- 局部 Knowledge 失败显示非阻塞提示。
- 混合模式降级时在结果上方显示明确 banner。

## 10. 部署与上游同步

Open WebUI fork 使用仓库自带 GitHub Actions 构建多架构镜像，并发布：

```text
ghcr.io/dfface/open-webui:v0.11.1-mailuo.1-slim
```

`doco-cd-macos` 只引用经过验证的固定 tag，生产部署进一步固定到镜像 digest。部署机不再通过字符串替换给官方镜像打源码补丁。升级流程为：

1. fork 同步目标上游版本；
2. rebase 少量脉络接入提交；
3. 运行后端、前端和数据库兼容测试；
4. CI 构建新的不可变镜像；
5. `doco-cd-macos` 更新 tag/digest；
6. 部署并执行搜索冒烟测试。

源码提交保持可独立审查：数据库迁移、外部 pgvector `Vector(...)` 兼容补丁、Mailuo 后端模块、前端页面、两个上游接入点分别提交。上游一旦包含等价修复，兼容补丁可以单独删除。

## 11. 验证方案

### 11.1 数据库

- 验证 title 全文权重高于 content。
- 验证中文子串能由 trigram 召回。
- 验证三种模式只启用各自规定的召回通道。
- 验证 source 过滤在候选排序前执行。
- 验证 RRF `k = 60` 和 Top 50 候选规则。
- 验证长文档不会因 chunk 数量多而提高对象得分。
- 插入一个从未在代码出现过的 `source = 'test_future_source'`，确认无需改代码即可检索和展示。

### 11.2 后端

- 无权限 Knowledge 返回 403。
- 无效模式和参数返回 400。
- 同一查询只调用一次 embedding。
- 并发语义请求由 Redis 锁串行处理。
- 混合模式 embedding 失败时降级为关键词并返回 warning。
- 语义模式 embedding 失败时明确报错。
- 单 Knowledge 失败仍返回其他结果，全失败才报错。
- facets 能动态返回新 source，并为未配置 source 提供回退展示。

### 11.3 前端

- 搜索、模式和筛选状态可以通过 URL 恢复。
- 结果按对象展示，最多 3 个片段。
- 所有结果都能通过 `source_url` 打开原文。
- Outline 评论链接保留 `commentId`。
- 新 source 使用通用卡片正常展示。
- 键盘操作、加载、空结果、降级和局部失败状态均可用。

### 11.4 部署

- fork CI 能构建 `slim` 多架构镜像。
- 镜像启动后健康检查通过。
- 外部 pgvector Knowledge Test Query 通过。
- `/mailuo` 的关键词、语义、混合搜索各完成一次冒烟测试。

## 12. 已确认的关键决策

- 使用 Open WebUI 内嵌独立页面，而不是单独部署搜索服务。
- 不修改 Open WebUI 原有 RAG 流程。
- 使用 PostgreSQL 原生全文检索、pg_trgm 和 pgvector，不引入 zhparser。
- 使用 RRF 融合，三路候选各 Top 50，`k = 60`。
- 先排 chunk，再按对象聚合；对象分数取最佳 chunk。
- 新 source 通过统一数据契约和动态 facets 自动接入，不成为代码枚举。
- 数据库迁移归 Mailuo 管理，Open WebUI fork 只调用稳定数据库接口。
- 权限复用 Knowledge ACL，embedding 并发使用 Redis 锁保护。
- fork CI 发布固定版本镜像，部署仓库固定 tag/digest。
