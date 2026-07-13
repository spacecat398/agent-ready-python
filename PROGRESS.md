# Agent-ready Python 开发进度

> 最后更新：2026-07-13 23:24:23 +08:00

## 当前状态

| 项目 | 状态 |
|---|---|
| 当前阶段 | Phase 8：分发与发布验收 |
| 阶段状态 | `completed` |
| 总体方向 | 模块化单体、目录级 Feature、显式 Composition Root |
| 当前阻塞 | 正式发布前需确认 PyPI 名称、版本标签和 trusted publishing 配置 |
| 下一步 | 等待 GitHub Actions 验证 `main`，再完成 PyPI 发布决策和最终 clean-build |

## 状态定义

- `planned`：范围已确定，尚未开始实现；
- `in_progress`：正在设计、实现或验证；
- `blocked`：存在需要处理的明确阻塞；
- `completed`：实现和对应验证均已完成。

## 阶段进度

| 阶段 | 状态 | 完成度 | 说明 |
|---|---|---:|---|
| 样本调研 | `completed` | 100% | 已分析 TinyRAG、Visual Layer、Emovoice 和 AnythingQuiz |
| 模块边界设计 | `completed` | 100% | 已定义六类模块、依赖方向和删除规则 |
| Phase 1：边界验证 | `completed` | 100% | Foundation、LLM Contract、Fake、Adapter、CLI 和 Bootstrap 已验证 |
| Phase 2：第二业务形态 | `completed` | 100% | TinyRAG 路线的 documents、retrieval 和 optional embeddings 已验证 |
| Phase 3：Artifact/Pipeline | `completed` | 100% | Artifact、SQLite Store、Validator 和可恢复 Runner 已验证 |
| Phase 4：装配工具 | `completed` | 100% | 静态模块选择、依赖解析和显式项目生成已验证 |
| Phase 5：独立样本验收 | `completed` | 100% | 三个生成项目已在独立环境中完成离线验收 |
| Phase 6：显式 Adapter 选择 | `completed` | 100% | Adapter 选择、裁剪、显式装配和独立样本已验证 |
| Phase 7：声明式 preset | `completed` | 100% | 四个正式 preset、CLI、合并规则和独立样本已验证 |
| Phase 8：分发与发布验收 | `completed` | 100% | wheel/sdist、隔离安装、安装后生成和发布工程化已验证 |

## Phase 1 检查表

- [x] 创建 `uv` 项目和 `src/` layout；
- [x] 实现 Foundation 配置、错误、日志、密钥和生命周期；
- [x] 定义 `llm-text` Contract 和请求/响应模型；
- [x] 实现 Fake Text Generator；
- [x] 实现 OpenAI-compatible Adapter；
- [x] 实现显式 `bootstrap.py`；
- [x] 实现 CLI `check`、`version` 和 `ask`；
- [x] 增加测试网络封锁；
- [x] 增加 `module.toml` 和模块图检查；
- [x] 验证 Fake Adapter 不依赖 OpenAI Adapter；
- [x] 验证核心 CLI 不导入 `llm-text`，可独立运行 `check` 和 `version`。

## Phase 2 检查表

- [x] 实现保留原始来源 offset 的 Document 和 DocumentChunk；
- [x] 实现严格 UTF-8、扩展名和文件大小检查；
- [x] 实现确定性重叠文本切块；
- [x] 实现默认本地关键词检索；
- [x] 将 `top_k` 限制为 1 到 20；
- [x] 定义独立 Embedding Contract 和 Fake；
- [x] 实现 OpenAI-compatible Embedding Adapter；
- [x] 校验向量数量、索引、维度和有限数值；
- [x] 远程 Embedding 默认关闭且不继承 LLM Key；
- [x] 关键词 Retrieval 的公开入口不导入 Embedding 能力；
- [x] 实现显式 Retrieval Bootstrap 和 CLI；
- [x] 增加 documents、retrieval、embeddings 模块描述和依赖图检查。

## Phase 3 检查表

- [x] 实现冻结、泛型、带版本的 Artifact Envelope；
- [x] 记录创建者、父 Artifact、Schema 和结构化质量结果；
- [x] 实现 ArtifactStore 和 ArtifactActivationStore Port；
- [x] 实现 SQLite append-only Store；
- [x] 将历史版本保存与活动版本切换分离；
- [x] 定义 typed Processor 和 Validator Contract；
- [x] 每个通过验证的 Stage 输出在下一 Stage 前持久化；
- [x] Validator 失败时不持久化失败输出；
- [x] 支持关闭并重开数据库后从中间 Artifact 恢复；
- [x] 未知 Artifact 类型、Schema 或 Payload 在执行前失败；
- [x] 两个 Processor 实现可替换且下游 Stage 不变；
- [x] Pipeline Feature 不依赖 SQLite Adapter；
- [x] 实现 `pipeline-check` 和模块描述。

## Phase 4 检查表

- [x] 实现静态 `module.toml` 目录加载和校验；
- [x] 实现确定性的必需依赖闭包；
- [x] 检测未知模块、缺失依赖、循环依赖和模块冲突；
- [x] 实现 `minimal` preset 和重复 `--add` 模块选择；
- [x] 生成普通 `src/` layout、`pyproject.toml` 和显式 Composition Root；
- [x] 仅复制所选模块源码并替换目标 Python 包名；
- [x] 根据模块描述聚合 Python 依赖和 `.env.example`；
- [x] 非空目标目录安全失败且不创建或覆盖 `.env`；
- [x] 验证 minimal、retrieval、retrieval+embeddings、llm-text 和 pipeline 组合；
- [x] 验证生成项目无悬空内部导入和运行时模块发现。

## Phase 5 检查表

- [x] 生成 minimal、retrieval+embeddings 和 llm-text 三个独立样本；
- [x] 每个样本生成独立 `pyproject.toml`、`uv.lock` 和 `.venv`；
- [x] 每个样本包含 Ruff、pytest 配置和离线 smoke tests；
- [x] minimal 样本仅验证 Foundation 与核心 CLI；
- [x] retrieval 样本验证本地文档搜索且不调用远程 Embedding；
- [x] llm-text 样本验证 Fake Provider 文本生成；
- [x] 验证组合 Bootstrap 的 import 顺序、编译和命令注册；
- [x] 将生成项目质量要求固化到根装配器测试。

## Phase 6 检查表

- [x] 定义 AdapterSpec、AdapterSelection 和静态默认 Adapter；
- [x] 支持重复 `--adapter MODULE=ADAPTER`；
- [x] 未显式选择时使用模块声明的安全默认 Adapter；
- [x] 校验格式错误、重复赋值、未选择模块、无 Adapter 模块和未知 Adapter；
- [x] 只复制所选 Adapter 的源码、依赖和环境配置；
- [x] Fake LLM 和 Embedding 项目不安装 `httpx` 且不生成远程配置；
- [x] OpenAI-compatible Adapter 仅在显式选择时进入项目；
- [x] 支持 LLM 与 Embedding 选择不同 Adapter；
- [x] 生成匹配选择的显式 Bootstrap、Settings、CLI 和离线 smoke tests；
- [x] 为长项目名建立 31 字符包名边界并保证生成项目通过 Ruff；
- [x] 验证 minimal、Fake retrieval、Fake LLM 和 mixed Adapter 四个独立样本；
- [x] 保持 `.env` 不创建不覆盖，测试不调用远程 Provider。

## Phase 7 检查表

- [x] 定义不可变 PresetSpec 和静态 TOML 格式；
- [x] 严格校验 preset 字段、类型、重复 ID 和重复模块；
- [x] 复用模块依赖、循环、冲突和 Adapter 选择规则；
- [x] 实现确定性的 preset 加载、列表和按 ID 解析；
- [x] 支持 `--list-presets` 且无需 destination；
- [x] 支持 preset 模块与重复 `--add` 合并；
- [x] 支持显式 `--adapter` 覆盖 preset Adapter；
- [x] 在创建目标目录前完成所有 preset、模块、Adapter 和源文件校验；
- [x] 实现 minimal、text-cli、rag-local 和 artifact-pipeline 四个正式 preset；
- [x] 将旧 retrieval 组合保留为静态兼容 preset；
- [x] 为四个正式 preset 建立独立样本映射；
- [x] 新增 artifact-pipeline-app 并验证无 AI Provider 或远程依赖。

## Phase 8 检查表

- [x] 将 modules 和 presets 迁入 Python 包内 catalog；
- [x] 删除仓库根重复描述，保持 catalog 为唯一事实源；
- [x] 生成器默认资源和源码根不再依赖仓库路径或当前工作目录；
- [x] 保留 modules_dir 和 presets_dir 显式覆盖；
- [x] 配置 Hatch wheel 和 sdist 包含 catalog、测试与发布文档；
- [x] 审计制品不包含 `.env`、虚拟环境、缓存、pyc、build 或 dist 残留；
- [x] 在隔离虚拟环境安装 wheel 并从源码仓库外列出 preset；
- [x] 使用安装后 wheel 生成并验收 rag-local 和 artifact-pipeline 项目；
- [x] 在第二隔离环境从 sdist 安装并生成 minimal 项目；
- [x] CI 新增本地 wheel 构建、隔离安装和生成项目 smoke；
- [x] 新增 CHANGELOG 和 RELEASE_CHECKLIST；
- [x] 增加安全的 keywords 和 PyPI classifiers；
- [x] 保留许可证、作者、项目 URL、PyPI 名称和 trusted publishing 为维护者确认项；
- [x] 不上传 PyPI，不调用远程 Provider。

## 时间线

### 2026-07-13 23:24:23 +08:00

状态：`completed`

- 初始化本地 Git 仓库，默认分支为 `main`，并配置 GitHub `origin`；
- 审查 263 个首次提交文件，确认未包含 `.env`、虚拟环境、缓存、构建制品或常见格式密钥；
- 使用维护者身份创建初始提交 `61028bd`（`Initial release candidate`）；
- 通过单次命令绕过未运行的本地代理，成功推送 `main` 到 GitHub；
- 远程 `refs/heads/main` 已核对为提交 `61028bd675e777116d316fadb230ecee7830f298`；
- 未修改用户或仓库 Git 配置，未上传 PyPI，未调用远程 Provider。

### 2026-07-13 23:22:17 +08:00

状态：`in_progress`

- 开始初始化本地 Git 仓库并准备首次推送到 `spacecat398/agent-ready-python`；
- 已确认 `.env`、虚拟环境、缓存和构建制品均未进入待提交范围；
- 已配置 `origin`，但当前 GitHub HTTPS 连接因 `127.0.0.1` 本地代理未运行而失败；
- 当前环境未安装 GitHub CLI，将使用标准 Git 完成提交和推送。

### 2026-07-13 23:20:13 +08:00

状态：`completed`

- 添加 MIT License，版权归属为 `spacecat398`；
- 在包元数据中确认作者、MIT 许可证及 Homepage、Documentation、Repository 和 Issues URL；
- 将 LICENSE 纳入 sdist，构建后的 wheel 也包含标准许可证文件；
- 更新 README、CHANGELOG、发布检查表和分发元数据测试；
- `uv sync --locked`、Ruff、187 项 pytest 和 `uv build` 全部通过；
- wheel 元数据确认 `License-Expression: MIT`、作者及四个 GitHub URL 正确；
- 未初始化或推送 Git，未上传 PyPI，未调用远程 Provider。

### 2026-07-13 23:14:31 +08:00

状态：`in_progress`

- 维护者已确认使用 MIT License，作者名称为 `spacecat398`；
- GitHub 仓库地址已确认为 `https://github.com/spacecat398/agent-ready-python`；
- 开始补齐许可证、作者、项目 URL 和分发制品元数据；
- 不初始化或推送 Git，不上传 PyPI，不调用远程 Provider。

### 2026-07-13 20:30:53 +08:00

状态：`completed`

- 完成 Phase 8 分发与首版发布技术验收；
- 将 7 个模块描述和 5 个 preset 迁入 `agent_ready_python.catalog` 并随制品分发；
- wheel 和 sdist 构建成功，制品内容完整且不包含本地环境、缓存或敏感配置；
- wheel 在隔离环境从源码仓库外成功列出 preset，并生成 rag-local 与 artifact-pipeline 项目；
- 两个 wheel 生成项目的 Ruff、pytest、CLI 和离线功能验收通过；
- sdist 在第二隔离环境安装成功，并可生成 minimal 项目；
- CI 增加 wheel 构建、隔离安装、preset 列表和生成项目 smoke；
- 新增 0.1.0 release candidate changelog、发布检查表和非法律包元数据；
- 根仓库 `uv sync --locked`、Ruff、pytest 和 build 通过，共 186 项测试；
- 正式发布仍需维护者确认许可证、作者、项目 URL、PyPI 名称和 trusted publishing；
- 未上传 PyPI，未创建 `.env`，未调用任何远程 Provider。

### 2026-07-13 15:13:08 +08:00

状态：`in_progress`

- 启动 Phase 8 分发与首版发布验收；
- 已确认当前生成器依赖仓库根 `modules/` 和 `presets/`，wheel 安装后存在资源定位风险；
- 计划将静态描述迁入 Python 包并随 wheel/sdist 分发；
- 将在隔离虚拟环境安装制品并脱离源码仓库执行生成、Ruff、pytest 和 CLI；
- 不上传 PyPI，不调用任何远程 Provider。

### 2026-07-13 15:11:03 +08:00

状态：`completed`

- 完成 Phase 7 声明式 preset；
- 将硬编码 preset 迁移为 `presets/*.toml` 静态描述；
- 新增 preset 加载、严格校验、确定性列表和按 ID 解析 API；
- CLI 新增 `--list-presets`，并支持 `preset + --add + --adapter override`；
- 实现 minimal、text-cli、rag-local 和 artifact-pipeline 四个正式 preset；
- 保留 retrieval 静态兼容 preset；
- 新增并独立验收 artifact-pipeline-app，Ruff、锁文件、CLI 和 2 项 smoke tests 通过；
- minimal、text-cli、rag-local 对应样本分别保持 2、3、3 项测试通过；
- 根仓库 `uv sync`、锁文件检查、Ruff 和 pytest 通过，共 174 项测试；
- 全工作区不存在 `.env`，未调用任何远程 Provider。

### 2026-07-13 13:25:12 +08:00

状态：`in_progress`

- 完成 PresetSpec、静态 TOML 加载、严格字段校验和确定性列表；
- 完成 preset 模块闭包与 Adapter 规则复用；
- 支持 `--list-presets`、`preset + --add` 和显式 Adapter 覆盖；
- minimal、text-cli、rag-local 和 artifact-pipeline 四个正式 preset 已通过生成与离线 smoke 测试；
- 根仓库 Ruff 通过，当前共 174 项测试通过；
- 下一步为同步独立样本并执行各自环境验收。

### 2026-07-13 13:00:08 +08:00

状态：`in_progress`

- 启动 Phase 7 声明式 preset；
- preset 将从静态 TOML 描述读取模块和 Adapter 选择，不参与运行时发现；
- 首批计划包含 minimal、text-cli、rag-local 和 artifact-pipeline；
- `--add` 扩展 preset，显式 `--adapter` 覆盖 preset Adapter，同时保持完整校验。

### 2026-07-13 12:57:16 +08:00

状态：`completed`

- 完成 Phase 6 显式 Adapter 选择；
- 新增 `--adapter MODULE=ADAPTER`，并以模块声明的 Fake 或本地 Adapter 作为安全默认；
- 生成项目只包含所选 Adapter 的源码、Python 依赖和环境配置模板；
- 实现 Fake/OpenAI-compatible LLM、Fake/OpenAI-compatible Embedding 及混合选择的显式装配；
- 修复源码缓存复制、组合 Bootstrap、长 CLI import 和包名长度边界问题；
- 将 `minimal-app`、`retrieval-app`、`llm-app` 更新到新装配规则，并新增 `mixed-adapters-app`；
- 四个样本的 Ruff 和 pytest 通过，测试数分别为 2、3、3、4；
- 根仓库 `uv sync`、锁文件检查、Ruff 和 pytest 通过，共 118 项测试；
- 全工作区不存在 `.env`，未调用任何远程 Provider。

### 2026-07-13 11:45:40 +08:00

状态：`in_progress`

- 完成 AdapterSpec、AdapterSelection 和选择解析核心；
- 支持默认 Fake 以及按模块显式选择 Adapter；
- 实现非法格式、重复赋值、未选择模块、无 Adapter 模块和未知 Adapter 校验；
- 生成器已只复制所选 Adapter 文件，并只聚合对应依赖和环境配置；
- 当前根仓库 Ruff 和 89 项既有测试通过；
- 下一步为按 Adapter 生成显式 Bootstrap，并补充完整回归测试和独立样本。

### 2026-07-13 11:02:59 +08:00

状态：`in_progress`

- 启动 Phase 6 显式 Adapter 选择；
- 目标语法为 `--adapter module=adapter`，未指定时使用模块声明的安全默认 Adapter；
- 只复制被选择 Adapter 的源码、依赖和配置模板；
- 保持显式 Composition Root、离线默认和无运行时模块发现。

### 2026-07-13 10:19:25 +08:00

状态：`completed`

- 完成 Phase 5 独立样本验收；
- 在 `samples/generated/` 保存 minimal、retrieval-app 和 llm-app 三个生成项目；
- 修复生成项目缺少 Ruff、pytest、工具配置和离线 smoke tests 的问题；
- 修复组合 Bootstrap 的重复 docstring、E402 和 import 排序问题；
- 三个样本分别在自己的 `.venv` 中完成依赖同步、锁文件检查、Ruff、pytest 和 CLI 验收；
- minimal、retrieval 和 llm 样本测试分别为 2、3、3 项通过；
- 根仓库 `uv sync`、`uv run ruff check .` 和 `uv run pytest` 通过，共 89 项测试；
- 未创建或覆盖 `.env`，未调用任何远程 Provider。

### 2026-07-13 10:02:49 +08:00

状态：`in_progress`

- 启动 Phase 5 独立样本验收；
- 计划生成 minimal、retrieval+embeddings 和 llm-text 三个仓库内样本；
- 每个样本将独立执行依赖同步、编译、CLI 和离线能力检查；
- 不复制 `.env`、不读取或输出 API Key、不调用远程 Provider。

### 2026-07-13 10:00:00 +08:00

状态：`completed`

- 完成 Phase 4 最小模块装配工具；
- 新增 `create-ai-app`，支持 `minimal` preset 和重复 `--add` 模块选择；
- 实现必需依赖闭包、未知模块、缺失依赖、循环和冲突校验；
- 生成项目只包含所选源码、显式 Bootstrap/CLI、聚合依赖和模块配置模板；
- 验证非空目录拒绝、`.env` 不创建不覆盖、目标包名替换和生成项目导入闭包；
- 保持 Pipeline Feature 不依赖 SQLite Adapter，生成项目不使用运行时模块发现；
- `uv sync` 和 `uv run ruff check .` 通过；
- `uv run pytest` 通过，共 85 项测试；
- 未调用任何远程 Provider。

### 2026-07-13 09:42:35 +08:00

状态：`in_progress`

- 启动 Phase 4 模块装配工具实现；
- 首版范围限定为静态 `module.toml` 目录、模块选择、必需依赖闭包、冲突校验和生成普通显式 Python 项目；
- 不加入运行时插件发现、自动模块扫描组装、远程 Provider 调用或隐式依赖注入。

### 2026-07-12 23:58:24 +08:00

状态：`completed`

- 完成 Phase 3 Artifact/Pipeline 验证；
- 实现不可变版本化 Artifact、Processor、Validator 和 Pipeline Runner；
- 实现 SQLite append-only Artifact Store 和显式活动版本指针；
- 验证 Stage 输出逐步持久化、失败输出不落库、旧活动版本不被失败替换；
- 验证 SQLite 重开后从中间 Artifact 恢复；
- 使用两个可替换 Processor 证明下游 Contract 不变；
- `uv lock --check`、Ruff 和 Python 编译检查通过；
- `uv run pytest` 通过，共 65 项测试；
- `pipeline-check` 验收通过；
- 未调用任何远程 Provider。

### 2026-07-12 23:52:29 +08:00

状态：`in_progress`

- 启动 Phase 3 Artifact/Pipeline 验证；
- 范围限定为不可变版本化 Artifact、Processor、Validator、SQLite append-only Store 和从中间 Artifact 恢复；
- 不加入分布式任务、自动模块发现、消息队列或后台调度。

### 2026-07-12 23:47:04 +08:00

状态：`completed`

- 完成 Phase 2 TinyRAG 业务形态验证；
- 实现 documents、filesystem、keyword retrieval 和 optional embeddings；
- 修复 Adapter 聚合导出造成的跨能力删除耦合；
- 保留原始文本空白，使 chunk offset 对应真实来源；
- `uv lock --check`、Ruff 和 Python 编译检查通过；
- `uv run pytest` 通过，共 50 项测试；
- `retrieval-check` 和 README 本地搜索验收通过；
- 远程 Embedding 仅通过 MockTransport 验证，未发送真实文档或请求。

### 2026-07-12 23:39:27 +08:00

状态：`in_progress`

- 启动 Phase 2 第二业务形态验证；
- 选择 TinyRAG 路线；
- 范围限定为 documents、默认关键词 retrieval、optional embeddings、文件 Adapter 和 CLI；
- 远程 Embedding 默认关闭，本阶段不进行真实 Provider 请求。

### 2026-07-12 23:38:07 +08:00

状态：`completed`

- 完成 Phase 1 最小模块化项目骨架；
- 实现 Foundation、文本生成 Contract、Fake 和 OpenAI-compatible Adapter；
- 实现显式 `bootstrap.py` 以及独立核心 CLI 和可选 LLM 命令注册；
- 增加模块描述、导入边界检查、网络封锁和 GitHub Actions；
- `uv lock --check` 通过；
- `uv run ruff check .` 通过；
- `uv run pytest` 通过，共 22 项测试；
- Python 编译检查通过；
- `version`、`check`、`llm-check` 和 Fake `ask` 验收通过；
- 未发起任何真实模型请求。

### 2026-07-12 23:31:00 +08:00

状态：`in_progress`

- 首次 `uv sync` 在下载 Ruff 时达到命令时限；
- 用户开启代理后同步成功，无需修改项目永久镜像配置；
- 开始执行 lint、测试和 CLI 验收。

### 2026-07-12 23:27:06 +08:00

状态：`in_progress`

- 启动 Phase 1 边界验证；
- 确认 `uv 0.11.12` 和 Python `3.12.13` 可用；
- 开始实现最小 Foundation、LLM Contract、Adapter、Bootstrap、CLI 和离线测试。

### 2026-07-12 23:25:43 +08:00

状态：`completed`

- 创建本进度文档；
- 确认模块化架构设计已完成；
- 将 Phase 1 标记为下一阶段，尚未开始实现；
- 当前没有技术阻塞。

### 2026-07-12 23:18:00 +08:00

状态：`completed`

- 完成 `modular-architecture-design.md`；
- 定义 Foundation、Contracts、Features、Adapters、Interfaces 和 Bootstrap；
- 定义 Feature 删除规则、模块描述和四阶段实施路线。

### 2026-07-12 22:50:00 +08:00

状态：`completed`

- 阅读四个真实项目的 Markdown 资料；
- 提炼 Provider、流水线、结构化契约、状态、入口和安全边界等共性；
- 确认采用模块化单体，而不是运行时插件框架。

## 更新规则

后续工作按以下规则维护本文件：

1. 开始一项实质工作时，将对应阶段改为 `in_progress` 并追加时间线；
2. 发现阻塞时立即记录原因和解除条件；
3. 只有实现及验证都完成后才标记 `completed`；
4. 每次更新同步修改顶部“最后更新”时间；
5. 时间使用本机本地时间和 UTC 偏移；
6. 时间线只追加，不改写历史结论；如结论变化，新增更正记录。
