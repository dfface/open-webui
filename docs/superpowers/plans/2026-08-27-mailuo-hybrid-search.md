# 脉络混合搜索实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Open WebUI v0.11.1 fork 中交付可独立使用的“脉络”页面，对 Mailuo `public.chunks` 提供关键词、语义和 RRF 混合搜索，并可点击返回原文。

**Architecture:** PostgreSQL 负责三路候选召回和 RRF，Open WebUI 新增隔离的 `mailuo` 后端模块负责 Knowledge ACL、查询 embedding 串行化、容错和对象聚合，Svelte 页面负责可收藏的查询状态与通用结果卡。source 完全数据驱动，新增数据源只需由 n8n 写入统一 `chunks` 契约。

**Tech Stack:** PostgreSQL 16、pgvector、pg_trgm、Python 3.11/FastAPI/Pydantic/psycopg、Redis、Svelte 5/SvelteKit/TypeScript/Vitest、Docker/GitHub Actions。

**Spec:** `docs/superpowers/specs/2026-08-27-mailuo-hybrid-search-design.md`

## Global Constraints

- Open WebUI 基线版本固定为 v0.11.1；脉络代码集中在新目录，上游接入点只允许 router 注册和侧栏入口。
- 不修改 Open WebUI 原有 RAG 检索、聊天模型选择和产品名称/Logo。
- 实际索引表固定为 Mailuo 数据库 `public.chunks`，业务唯一键为 `(source, source_object_id, chunk_no)`。
- source 不是枚举；后端、SQL、前端均不得按 `outline`、`memos`、`kaneo` 写条件分支。
- 关键词模式不生成 embedding；混合与语义模式每个用户查询只生成一个 embedding。
- RRF 三路候选各 Top 50，默认 `k = 60`；对象得分取最佳 chunk，每对象最多 3 个片段。
- 所有数据库值使用绑定参数；任何数据库 DSN、Token、向量、SQL 和堆栈都不得返回浏览器或进入普通日志。
- 读取范围严格复用 Open WebUI Knowledge read grants；用户显式指定无权 Knowledge 返回 403。
- 开发遵循 TDD：每项行为先写测试并确认预期失败，再写最小实现。
- 不覆盖 `mailuo`、`doco-cd-macos` 仓库中的既有用户文件或无关改动。

---

### Task 1: 修复 Open WebUI 外部 pgvector 查询向量类型

**Files:**

- Modify: `backend/open_webui/retrieval/external.py`
- Create: `backend/tests/retrieval/test_external_pgvector.py`

**Interfaces:**

- Consumes: Open WebUI `_retrieve_pgvector(...)` 的 embedding `list[float]`。
- Produces: 传给 psycopg 的 `pgvector.Vector`，保证执行 `vector <=> vector`。

- [ ] **Step 1: 写失败测试，证明 list 会被转换为 Vector**

测试使用假的 psycopg connection/cursor，捕获 `cursor.execute()` 参数，并断言第一个参数为 `pgvector.Vector`，其值等于 `[0.1, 0.2, 0.3]`。生产代码保持未改时，测试应因收到普通 list 而失败。

```python
assert isinstance(executed_params[0], Vector)
assert executed_params[0].to_list() == pytest.approx([0.1, 0.2, 0.3])
```

- [ ] **Step 2: 运行测试并确认 RED**

Run: `PYTHONPATH=backend uv run pytest backend/tests/retrieval/test_external_pgvector.py -q`

Expected: FAIL，实际参数类型是 `list`。

- [ ] **Step 3: 最小修复**

在 `_retrieve_pgvector()` 的可选依赖块中导入 `Vector`，并把 SQL 参数从 `vector` 改为 `Vector(vector)`；不改变 SQL、字段映射或其他 provider。

```python
from pgvector import Vector

cur.execute(query, (Vector(vector), collection_name, count))
```

- [ ] **Step 4: 运行定向测试和格式检查**

Run:

```bash
PYTHONPATH=backend uv run pytest backend/tests/retrieval/test_external_pgvector.py -q
uv run ruff check backend/open_webui/retrieval/external.py backend/tests/retrieval/test_external_pgvector.py
```

Expected: 全部通过。

- [ ] **Step 5: 独立提交兼容补丁**

```bash
git add backend/open_webui/retrieval/external.py backend/tests/retrieval/test_external_pgvector.py
git commit -m "fix: adapt external pgvector query vectors"
```

### Task 2: 为 `public.chunks` 增加混合检索数据库能力

**Files:**

- Create in Mailuo repo: `/Users/handy/Documents/projects/mailuo/migrations/0002_public_chunks_hybrid_search.sql`
- Create in Mailuo repo: `/Users/handy/Documents/projects/mailuo/tests/sql/public_chunks_hybrid_search.sql`
- Modify in Mailuo repo: `/Users/handy/Documents/projects/mailuo/migrations/README.md`

**Interfaces:**

- Consumes: `public.chunks(source, source_object_id, chunk_no, title, content, source_url, source_updated_at, metadata, embedding)`。
- Produces: `public.mailuo_hybrid_search(text, vector, text, text[], integer, integer)` 和 `public.mailuo_source_facets()`。

- [ ] **Step 1: 先写数据库行为测试**

测试在事务中创建 fixture chunks：标题精确命中、正文模糊命中、仅语义命中、同对象多 chunk、以及未知 source `test_future_source`。断言：

```sql
-- keyword 不返回纯语义 fixture
-- semantic 不返回纯关键词 fixture
-- hybrid 的 matched_by 能同时包含 lexical/semantic 通道
-- source_filter 只返回指定 source
-- facets 自动返回 test_future_source
-- 函数结果保留 source_url 和 source_updated_at
```

测试末尾 `ROLLBACK`，不污染数据库。

- [ ] **Step 2: 在隔离 PostgreSQL fixture 上确认 RED**

Run: `psql "$MAILUO_TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/public_chunks_hybrid_search.sql`

Expected: FAIL，提示 `public.mailuo_hybrid_search` 不存在。

- [ ] **Step 3: 实现幂等迁移**

迁移必须：

1. `CREATE EXTENSION IF NOT EXISTS pg_trgm/vector`；
2. 增加生成列 `search_tsv`，title 权重 A、content 权重 B；
3. 为 `search_tsv`、title/content trigram 建索引；
4. 建可选 `public.mailuo_sources` 展示配置表，不含 source 枚举；
5. 建 `public.mailuo_source_facets()`，以实际 chunks source 为主、左连接展示配置；
6. 建 `public.mailuo_hybrid_search()`，参数绑定，模式只允许 `hybrid/keyword/semantic`；
7. FTS、trigram、vector 分别先过滤 source 再取 Top 50；
8. 使用 `1.0 / (60 + rank)` 融合，并返回 `matched_by text[]`；
9. 返回 chunk 级字段，不在数据库累加同对象得分。

函数返回类型固定为：

```sql
TABLE (
  source text,
  source_object_id text,
  chunk_no integer,
  title text,
  content text,
  source_url text,
  source_updated_at timestamptz,
  metadata jsonb,
  score double precision,
  matched_by text[]
)
```

- [ ] **Step 4: 运行迁移和 SQL 行为测试**

Run:

```bash
psql "$MAILUO_TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/0002_public_chunks_hybrid_search.sql
psql "$MAILUO_TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/public_chunks_hybrid_search.sql
```

Expected: 两条命令 exit 0，测试事务回滚。

- [ ] **Step 5: 在实际 Mailuo 数据库只做 schema/EXPLAIN 验证**

先备份 schema，再应用迁移；用 `EXPLAIN (ANALYZE, BUFFERS)` 验证三路查询能使用 GIN/向量索引。不得修改已有 chunk 内容。

- [ ] **Step 6: 提交 Mailuo 数据库变更**

只暂存本任务新增/修改的三个文件，不包含该仓库其他未跟踪文件。

### Task 3: 定义 Mailuo 后端契约与对象聚合

**Files:**

- Create: `backend/open_webui/mailuo/__init__.py`
- Create: `backend/open_webui/mailuo/schemas.py`
- Create: `backend/open_webui/mailuo/ranking.py`
- Create: `backend/tests/mailuo/test_ranking.py`
- Create: `backend/tests/mailuo/test_schemas.py`

**Interfaces:**

- Produces: `SearchMode`、`MailuoSearchRequest`、`MailuoSearchResponse`、`MailuoChunkMatch`、`MailuoObjectResult`、`SourceFacet`、`aggregate_chunk_matches(rows, limit, snippets_per_object)`。
- Consumes: 数据库函数返回的 chunk rows。

- [ ] **Step 1: 写 schema 失败测试**

覆盖空查询、非法 mode、`limit` 小于 1/大于 50、sources 去重和默认 hybrid。生产模块不存在时确认 RED。

- [ ] **Step 2: 写聚合失败测试**

用手工 rows 验证：

- 相同 `(source, source_object_id)` 合并；
- 对象 score 使用最大 chunk score；
- 片段按 chunk score 排序且最多 3 个；
- 对象最多 20 个；
- 同分时按更新时间、source、object ID 稳定排序；
- 相同 object ID 但 source 不同不得合并；
- `matched_by` 合并去重。

- [ ] **Step 3: 运行测试并确认 RED**

Run: `PYTHONPATH=backend uv run pytest backend/tests/mailuo/test_schemas.py backend/tests/mailuo/test_ranking.py -q`

Expected: import 失败或目标类型不存在。

- [ ] **Step 4: 实现最小 Pydantic 模型与纯聚合函数**

聚合函数不得访问数据库、Redis 或 Request；保持可独立测试。snippet 内容直接来自排名 chunk，第一版不做 HTML 高亮。

- [ ] **Step 5: 运行测试与 ruff**

Run:

```bash
PYTHONPATH=backend uv run pytest backend/tests/mailuo/test_schemas.py backend/tests/mailuo/test_ranking.py -q
uv run ruff check backend/open_webui/mailuo backend/tests/mailuo
```

- [ ] **Step 6: 提交后端契约**

```bash
git add backend/open_webui/mailuo backend/tests/mailuo
git commit -m "feat: define Mailuo search contracts"
```

### Task 4: 实现 Knowledge 授权和 PostgreSQL gateway

**Files:**

- Create: `backend/open_webui/mailuo/knowledge.py`
- Create: `backend/open_webui/mailuo/postgres.py`
- Create: `backend/tests/mailuo/test_knowledge.py`
- Create: `backend/tests/mailuo/test_postgres.py`

**Interfaces:**

- Produces: `list_accessible_mailuo_knowledges(user, db)`、`resolve_mailuo_knowledges(ids, user, db)`、`MailuoPostgresGateway.search(...)`、`MailuoPostgresGateway.facets()`。
- Consumes: Open WebUI `Knowledges`、`Groups`、`Config` 和外部 connection 配置。

- [ ] **Step 1: 写授权失败测试**

测试 owner、admin、直接 read grant、group read grant、无权限和不存在 Knowledge。显式选择中只要包含一个无权限 ID，`resolve_mailuo_knowledges` 必须抛出安全的 forbidden 异常；列表接口只返回 provider 为 pgvector、已启用并包含 Mailuo 数据库函数的 Knowledge。

- [ ] **Step 2: 写 gateway 失败测试**

假的 psycopg cursor 捕获调用，断言：

```python
assert sql_text.startswith('SELECT * FROM public.mailuo_hybrid_search(')
assert params == (query, Vector(query_embedding), mode, sources, 150, 60)
```

并验证 facets 只调用固定 `public.mailuo_source_facets()`，异常信息经 `MailuoDatabaseError` 脱敏。

- [ ] **Step 3: 运行测试确认 RED**

Run: `PYTHONPATH=backend uv run pytest backend/tests/mailuo/test_knowledge.py backend/tests/mailuo/test_postgres.py -q`

- [ ] **Step 4: 实现授权 resolver**

复用 `Knowledges.check_access_by_user_id(..., permission='read')` 和 admin/owner 规则；从 `external_knowledge.connections` 解析连接，但只向 gateway 传内部 endpoint、timeout 和 Knowledge ID。不得把 DSN 放入模型或响应。

- [ ] **Step 5: 实现固定 SQL gateway**

使用 `asyncio.to_thread` 包装同步 psycopg，`register_vector(conn)`，查询向量使用 `Vector(query_embedding)`。多 Knowledge 返回时在上层按 connection 独立调用。

- [ ] **Step 6: 运行定向测试与 ruff**

Run:

```bash
PYTHONPATH=backend uv run pytest backend/tests/mailuo/test_knowledge.py backend/tests/mailuo/test_postgres.py -q
uv run ruff check backend/open_webui/mailuo backend/tests/mailuo
```

- [ ] **Step 7: 提交 gateway**

```bash
git add backend/open_webui/mailuo backend/tests/mailuo
git commit -m "feat: connect Mailuo search to pgvector knowledge"
```

### Task 5: 实现 embedding 锁、搜索编排与降级

**Files:**

- Create: `backend/open_webui/mailuo/embedding.py`
- Create: `backend/open_webui/mailuo/service.py`
- Create: `backend/tests/mailuo/test_embedding.py`
- Create: `backend/tests/mailuo/test_service.py`

**Interfaces:**

- Produces: `generate_query_embedding(request, query, user)`、`MailuoSearchService.search(...)`、`MailuoSearchService.facets(...)`。
- Consumes: `request.app.state.redis`、`request.app.state.EMBEDDING_FUNCTION`、Knowledge resolver、gateway、聚合函数。

- [ ] **Step 1: 写 Redis 串行锁失败测试**

并发启动两个 embedding 调用，fake Redis lock 记录临界区，断言最大并发为 1、锁 key 固定为 `mailuo:embedding`、具有 blocking timeout 和 expiry。Redis 不可用时只允许单进程 fallback lock，并记录一次 warning。

- [ ] **Step 2: 写三模式与降级失败测试**

覆盖：

- keyword 从不调用 embedding，传 `None` 给数据库；
- hybrid 只调用一次 embedding，多 Knowledge 复用同一向量；
- semantic 只调用一次 embedding；
- hybrid embedding 失败改为 keyword，`degraded=true`；
- semantic embedding 失败返回安全错误，不降级；
- 一个 Knowledge 失败返回其他结果和 warning；
- 全部 Knowledge 失败返回服务错误；
- 跨 Knowledge 按对象键去重和排序。

- [ ] **Step 3: 运行测试确认 RED**

Run: `PYTHONPATH=backend uv run pytest backend/tests/mailuo/test_embedding.py backend/tests/mailuo/test_service.py -q`

- [ ] **Step 4: 实现锁和编排**

embedding 调用：

```python
vector = await request.app.state.EMBEDDING_FUNCTION(
    query,
    prefix=RAG_EMBEDDING_QUERY_PREFIX,
    user=user,
)
```

服务记录 request ID、requested/executed mode、耗时、结果数和降级原因；不记录 query 内容。数据库可以并发查询，embedding 不能并发。

- [ ] **Step 5: 运行全部 Mailuo 后端测试**

Run:

```bash
PYTHONPATH=backend uv run pytest backend/tests/mailuo -q
uv run ruff check backend/open_webui/mailuo backend/tests/mailuo
```

- [ ] **Step 6: 提交搜索服务**

```bash
git add backend/open_webui/mailuo backend/tests/mailuo
git commit -m "feat: orchestrate Mailuo hybrid search"
```

### Task 6: 增加 Mailuo FastAPI router

**Files:**

- Create: `backend/open_webui/mailuo/router.py`
- Create: `backend/tests/mailuo/test_router.py`
- Modify: `backend/open_webui/main.py`

**Interfaces:**

- Produces:
  - `GET /api/v1/mailuo/knowledges`
  - `POST /api/v1/mailuo/facets`
  - `POST /api/v1/mailuo/search`
- Consumes: `get_verified_user`、async DB session、`MailuoSearchService`。

- [ ] **Step 1: 写路由失败测试**

用 FastAPI TestClient/依赖覆盖验证：未登录 401、非法请求 422/400、无权 Knowledge 403、搜索响应不含 DSN/stack、三条路由返回声明的 schema。

- [ ] **Step 2: 确认 RED**

Run: `PYTHONPATH=backend uv run pytest backend/tests/mailuo/test_router.py -q`

- [ ] **Step 3: 实现 router 和异常映射**

router prefix 固定 `/mailuo`；`main.py` 仅增加一条 import 和一条：

```python
app.include_router(mailuo.router, prefix='/api/v1')
```

内部 forbidden、validation、embedding、database 异常分别映射为 403、400、502/503，响应只含安全 detail 和 request ID。

- [ ] **Step 4: 运行后端测试与 import smoke**

Run:

```bash
PYTHONPATH=backend uv run pytest backend/tests/mailuo backend/tests/retrieval/test_external_pgvector.py -q
PYTHONPATH=backend uv run python -c "from open_webui.main import app; print(any(r.path == '/api/v1/mailuo/search' for r in app.routes))"
```

Expected: pytest 全绿，smoke 输出 `True`。

- [ ] **Step 5: 提交 API 接入点**

```bash
git add backend/open_webui/mailuo backend/open_webui/main.py backend/tests/mailuo
git commit -m "feat: expose Mailuo search API"
```

### Task 7: 增加前端 API、类型和 URL 状态

**Files:**

- Create: `src/lib/mailuo/types.ts`
- Create: `src/lib/mailuo/api.ts`
- Create: `src/lib/mailuo/query-state.ts`
- Create: `src/lib/mailuo/view-model.ts`
- Create: `src/lib/mailuo/query-state.test.ts`
- Create: `src/lib/mailuo/api.test.ts`
- Create: `src/lib/mailuo/view-model.test.ts`

**Interfaces:**

- Produces: `searchMailuo(token, request)`、`getMailuoKnowledges(token)`、`getMailuoFacets(token, knowledgeIds)`、`parseMailuoQueryState(url)`、`serializeMailuoQueryState(state)`。
- Consumes: `/api/v1/mailuo/*` JSON 契约。

- [ ] **Step 1: 写 URL 状态失败测试**

覆盖中文 query、mode、多个 knowledge/source、默认值、空字符串、重复参数和非法 mode。期望 URL 使用重复 query parameter 或稳定逗号编码，并能 round-trip。

- [ ] **Step 2: 写 API 失败测试**

stub `global.fetch`，断言 Bearer token、请求 body、非 2xx detail 传播、响应类型保持 `requested_mode/executed_mode/degraded/warnings/results`。

- [ ] **Step 3: 运行测试确认 RED**

Run: `npm run test:frontend -- src/lib/mailuo/query-state.test.ts src/lib/mailuo/api.test.ts`

- [ ] **Step 4: 实现纯函数和 API client**

不得把 localStorage 读取放进 API client；token 由页面传入。source 类型为 `string`，不定义联合枚举。

- [ ] **Step 5: 运行 Vitest 和类型检查**

Run:

```bash
npm run test:frontend -- src/lib/mailuo/query-state.test.ts src/lib/mailuo/api.test.ts
npm run check
```

- [ ] **Step 6: 提交前端基础层**

```bash
git add src/lib/mailuo
git commit -m "feat: add Mailuo frontend client"
```

### Task 8: 实现“脉络”搜索页面和入口

**Files:**

- Create: `src/lib/components/mailuo/SearchBar.svelte`
- Create: `src/lib/components/mailuo/SearchFilters.svelte`
- Create: `src/lib/components/mailuo/SearchResult.svelte`
- Create: `src/lib/components/mailuo/SearchStates.svelte`
- Create: `src/routes/(app)/mailuo/+page.svelte`
- Modify: `src/lib/components/layout/Sidebar/UserMenu.svelte`

**Interfaces:**

- Consumes: Task 7 client/types；Open WebUI `user`、`mobile`、`showSidebar` stores。
- Produces: `/mailuo` 可人工操作页面和用户菜单“脉络”入口。

- [ ] **Step 1: 先写页面状态/组件可观察行为测试**

对 `view-model.ts` 的纯函数补测试：loading 保留旧结果、每对象默认一个片段、展开最多三个、unknown source label 回退原始值，以及 `safeSourceUrl()` 只接受绝对 HTTP/HTTPS URL。Svelte 结构由 `npm run check` 和最终 Playwright/人工验收覆盖，不增加只检查源码字符串的测试。

- [ ] **Step 2: 运行测试确认 RED**

Run: `npm run test:frontend -- src/lib/mailuo`

- [ ] **Step 3: 实现页面布局和交互**

页面必须包含：

- 搜索框、按钮、hybrid/keyword/semantic chip；
- Knowledge selector 和动态 source selector；
- 单列对象结果卡、matched_by、更新时间、一个默认片段、展开两个片段；
- `target="_blank" rel="noopener noreferrer"` 原文链接；
- 初始、loading、empty、partial warning、degraded、fatal error 状态；
- Enter 搜索、`/` 聚焦、Esc 清空；
- 查询完成/筛选变化后同步 URL，浏览器 back/forward 恢复状态。

- [ ] **Step 4: 增加最小菜单入口**

在 UserMenu 添加一个与现有 Workspace/Notes 风格一致的 `<a href="/mailuo">脉络</a>`；移动端导航后关闭侧栏。不得改 Open WebUI 名称或 Logo。

- [ ] **Step 5: 运行前端验证**

Run:

```bash
npm run test:frontend -- src/lib/mailuo
npm run check
npm run build
```

Expected: tests、Svelte check 和 production build 全部 exit 0。

- [ ] **Step 6: 提交页面**

```bash
git add src/lib/components/mailuo 'src/routes/(app)/mailuo' src/lib/components/layout/Sidebar/UserMenu.svelte
git commit -m "feat: add Mailuo search page"
```

### Task 9: 构建镜像、调整部署并完成自动化冒烟

**Files:**

- Modify if required: `.github/workflows/docker.yaml`
- Modify in deployment repo: `/Users/handy/Documents/projects/doco-cd-macos/stacks/open-webui/compose.yml`
- Remove after custom image cutover: `/Users/handy/Documents/projects/doco-cd-macos/stacks/open-webui/Dockerfile`
- Modify: `docs/superpowers/specs/2026-08-27-mailuo-hybrid-search-design.md` status
- Create: `docs/mailuo-search-acceptance.md`

**Interfaces:**

- Produces: 可部署的 `ghcr.io/dfface/open-webui:v0.11.1-mailuo.1-slim` 或同 commit SHA 镜像；人工验收清单。
- Consumes: 通过全部验证的 Open WebUI branch 和已迁移 Mailuo 数据库。

- [ ] **Step 1: 运行完整本地验证**

Run:

```bash
PYTHONPATH=backend uv run pytest backend/tests -q
uv run ruff check backend/open_webui/mailuo backend/tests
npm run test:frontend
npm run check
npm run build
docker build -t open-webui:mailuo-acceptance .
```

- [ ] **Step 2: 启动本地容器做 API smoke**

在不覆盖生产数据的测试配置启动镜像，检查 `/health`、登录后 `/api/v1/mailuo/knowledges`、facets 和三种 search。保存命令与结果，不保存 Token/DSN。

- [ ] **Step 3: 生成并发布不可变镜像**

优先由 fork GitHub Actions 构建 `slim` 多架构镜像；部署引用具体版本并记录 digest。若 CI 发布前需要人工确认外部 push，则先用本地构建镜像在验收主机部署，不阻塞功能验收。

- [ ] **Step 4: 更新 `doco-cd-macos`**

把 compose 从部署机字符串补丁 build 切换到固定自有镜像：

```yaml
services:
  web:
    image: ${OPEN_WEBUI_IMAGE:?set an immutable ghcr.io/dfface/open-webui image digest}
```

保留既有 volume、端口和 secrets；仅在新镜像已验证后移除旧 Dockerfile。

- [ ] **Step 5: 在 192.168.31.147 部署并检查**

通过 SSH 运行 compose pull/up，检查容器 health、日志中无迁移/权限/向量类型错误，并从浏览器访问部署 URL。不得在命令输出中打印 secrets.env。

- [ ] **Step 6: 执行可复现的人工验收前置检查**

验收清单至少包括：

1. 菜单可进入“脉络”；
2. 页面不要求配置聊天模型；
3. 关键词搜索能命中精确中文/标识符；
4. 语义搜索能命中概念相关内容；
5. 混合搜索显示命中通道；
6. Outline 正文和评论都能出现；
7. 评论链接包含 `commentId`；
8. 原文按钮打开新标签；
9. unknown/new source 自动出现在筛选项；
10. 刷新和 back/forward 保留查询状态；
11. embedding 故障时 hybrid 显示降级，semantic 明确失败；
12. 无权 Knowledge 不可搜索。

- [ ] **Step 7: 更新文档状态并提交**

只有完整自动化验证和部署 smoke 均通过后，将 spec 状态改为“已实现，待人工验收”，写入实际镜像 digest、部署 URL 和验收步骤，并提交。

### Task 10: 完成前复核和人工验收交接

**Files:**

- Review all files changed since `05b291270`。

**Interfaces:**

- Produces: 一份包含证据、已知限制、部署入口和逐项验收动作的交接。

- [ ] **Step 1: 按 spec 逐条核对覆盖率**

把 spec 第 2、4、6、7、8、9、10、11 节逐项映射到实现、自动测试或人工验收项；任何缺口在交接前补齐。

- [ ] **Step 2: 检查侵入性**

Run: `git diff 05b291270...HEAD --stat` 和 `git diff 05b291270...HEAD -- backend/open_webui/main.py src/lib/components/layout/Sidebar/UserMenu.svelte backend/open_webui/retrieval/external.py`。

Expected: 上游文件只有预期的 router、菜单和独立 Vector 修复。

- [ ] **Step 3: 新鲜运行最终验证**

重新运行以下命令，不得引用旧运行结果：

```bash
PYTHONPATH=backend uv run pytest backend/tests -q
uv run ruff check backend/open_webui/mailuo backend/tests
npm run test:frontend
npm run check
npm run build
docker build -t open-webui:mailuo-final .
```

随后重新检查本地容器 `/health`、登录态 Mailuo 三个 API，以及验收主机上的 `/health` 和三种搜索。

- [ ] **Step 4: 使用 finishing-a-development-branch 完成交接**

保留 feature branch/worktree，向用户提供部署 URL、测试计数、commit 列表、验收清单和集成选项；未获得用户选择前不合并 main、不删除 worktree。
