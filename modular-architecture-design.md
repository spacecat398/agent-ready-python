# Agent-ready Python 模块化架构设计 v0.1

> 从 TinyRAG、Visual Layer、Emovoice 和 AnythingQuiz 中提炼可组合、可替换、可裁剪的 Python AI 应用骨架。

> 实施状态和带时间戳的更新见 [`PROGRESS.md`](PROGRESS.md)。

## 1. 设计目标

本设计不是创建覆盖所有 AI 场景的框架，而是建立稳定的模块边界，使新项目可以选择需要的能力，并在不需要时完整删除。

必须实现：

1. 最小项目只保留基础层也能运行和测试；
2. Feature 可以按目录添加或删除；
3. Provider、数据库和交付入口可以替换；
4. 业务模块不依赖供应商 SDK；
5. 所有具体实现只在一个组装根中连接；
6. 测试不需要真实 API Key，也不默认访问网络；
7. 外发数据必须有显式配置或产品授权；
8. 删除模块后的残留引用可以被自动检查发现。

明确不做：

- 不构建运行时插件市场；
- 不使用自动扫描和隐式依赖注入；
- 不要求所有应用采用 Artifact 或 Pipeline；
- 不创建统一表示音频、图像、文档和对话的万能模型；
- 不把所有 Provider 差异塞进一个无限扩张的接口；
- 不为了未来可能性提前拆成独立服务；
- 不要求业务项目继承大型基类。

## 2. 从真实项目提炼出的共性

四个样本分别代表：

- TinyRAG：文档、切块、检索、Embedding、缓存和 MCP；
- Visual Layer：屏幕采集、变化检测、路由、视觉模型和状态发布；
- Emovoice：ASR、LLM、TTS 和音频输入输出；
- AnythingQuiz：Artifact、Processor、Validator、持久化和 CLI。

共同的数据流是：

```text
输入
-> 确定性预处理
-> AI 能力调用
-> 结果验证
-> 状态、缓存或持久化
-> 输出接口
```

共同的工程能力包括配置、密钥、日志、错误、Provider 切换、结构化契约、Fake、运行检查、隐私边界和离线测试。

## 3. 架构总览

```text
interfaces
    |
    v
application / features
    |
    v
contracts <----- adapters
    |
    v
foundation

bootstrap 负责创建并连接所有具体对象
```

推荐目录：

```text
src/<app_name>/
├── foundation/
│   ├── config.py
│   ├── errors.py
│   ├── logging.py
│   ├── secrets.py
│   └── lifecycle.py
├── contracts/
│   ├── llm.py
│   ├── events.py
│   └── storage.py
├── features/
│   ├── llm/
│   ├── documents/
│   ├── retrieval/
│   ├── vision/
│   ├── asr/
│   ├── tts/
│   ├── artifacts/
│   └── pipeline/
├── adapters/
│   ├── openai_compatible/
│   ├── ollama/
│   ├── sqlite/
│   ├── filesystem/
│   └── mcp/
├── interfaces/
│   ├── cli/
│   ├── web/
│   └── mcp/
├── application.py
└── bootstrap.py
```

目录是逻辑分类，不要求每个项目创建全部目录。没有对应能力时，目录本身也不应存在。

## 4. 模块职责

### 4.1 Foundation

Foundation 只包含几乎所有项目都需要、且不带具体 AI 业务语义的能力：

- 配置加载和校验；
- 项目级错误基类；
- 安全日志初始化；
- Secret 引用和脱敏；
- 资源关闭和应用生命周期。

Foundation 不包含 OpenAI 请求格式、Prompt、对话历史、RAG、音频、视觉、SQLite 数据模型或 CLI 命令。HTTP 重试、缓存、Artifact 和 Pipeline 都是可选模块。

### 4.2 Contracts

Contracts 保存项目拥有的稳定协议和跨模块数据类型：

```python
from typing import Protocol


class TextGenerator(Protocol):
    def generate(self, request: "TextGenerationRequest") -> "TextGenerationResult": ...
```

规则：

1. Contract 由能力使用方定义，不由 Provider SDK 定义；
2. Contract 不暴露 HTTP 响应、SDK 对象或数据库行；
3. 文本、Embedding、视觉、ASR 和 TTS 使用独立协议；
4. 只有多个模块共享的类型才进入顶层 `contracts/`；
5. 仅供单个 Feature 使用的 Port 放在该 Feature 内部。

### 4.3 Features

Feature 是主要积木单位，包含一项能力的业务代码、内部 Port、模型和错误：

```text
features/retrieval/
├── __init__.py
├── models.py
├── ports.py
├── service.py
└── errors.py
```

Feature 可以依赖 Foundation、共享 Contract，或另一个 Feature 的公开 API，但不能导入另一个 Feature 的内部文件。`__init__.py` 是公开边界，未导出的对象视为内部实现。

### 4.4 Adapters

Adapter 实现 Contract 或 Feature Port，连接 OpenAI-compatible API、Ollama、本地模型、SQLite、文件系统、麦克风、屏幕和 MCP SDK。

第三方类型不能穿过 Adapter 边界。Provider 差异较大时创建不同 Adapter，不在一个类中持续增加条件分支。

### 4.5 Interfaces

Interface 把外部输入转换为 Application 调用，并渲染结果，包括 CLI、HTTP、MCP、后台任务和设备事件。

Interface 不能拥有核心业务规则。例如 CLI 可以解析 `--top-k`，但合法范围仍由应用服务或领域模型校验。

### 4.6 Bootstrap

`bootstrap.py` 是唯一允许同时知道具体 Adapter 和业务服务的地方：

```python
def build_application(settings: Settings) -> Application:
    generator = OpenAICompatibleTextGenerator(settings.llm)
    repository = SQLiteRepository(settings.database)
    return Application(generator=generator, repository=repository)
```

使用显式构造函数注入；不使用全局 Service Locator；不在导入时创建网络 Client、模型或数据库连接；不通过扫描目录自动注册实现。

## 5. 依赖规则

允许的依赖方向：

```text
foundation <- contracts <- features <- application <- interfaces
                    ^          ^
                    |          |
                  adapters ----+

bootstrap 可以引用以上所有层
```

| 来源 | 可以依赖 | 不可以依赖 |
|---|---|---|
| foundation | 标准库、基础配置库 | Feature、Adapter、Interface |
| contracts | foundation、纯数据模型 | Provider SDK、Interface |
| features | foundation、contracts、其他 Feature 的公开 API | Adapter、CLI、Web、SDK |
| adapters | foundation、contracts、对应 Feature Port | Interface、其他 Adapter 内部实现 |
| application | foundation、contracts、Feature 公开 API | CLI/Web 细节、SDK 类型 |
| interfaces | application、公开结果模型 | Adapter 内部实现、数据库细节 |
| bootstrap | 所有需要组装的公开对象 | 其他模块的私有实现 |

### 5.1 禁止循环依赖

如果 `retrieval` 依赖 `documents`，则 `documents` 不能反向依赖 `retrieval`。双向协作应提取共享 Contract、由 Application Service 协调，或在确实需要解耦生命周期时使用事件。不要用延迟导入掩盖架构循环。

### 5.2 Feature 默认不直接编排其他 Feature

ASR、LLM 和 TTS 各自提供能力，但 ASR 不直接调用 LLM。Emovoice 的顺序由应用服务表达：

```python
class VoiceConversationService:
    def __init__(
        self,
        asr: SpeechRecognizer,
        llm: TextGenerator,
        tts: SpeechSynthesizer,
    ) -> None:
        self._asr = asr
        self._llm = llm
        self._tts = tts
```

这样删除 TTS、替换 LLM 或增加纯文本模式时，不需要修改 ASR。

## 6. 模块胶囊规范

一个可选模块要被视为可删除积木，必须具备自己的描述、源码、测试和简短说明：

```text
src/agent_ready_python/catalog/modules/<module_name>/
├── module.toml
├── src/
├── tests/
└── README.md
```

`module.toml` 用于模板装配和静态检查，不参与运行时插件发现：

```toml
id = "retrieval"
kind = "feature"
description = "Document chunk retrieval"
requires = ["documents"]
optional = ["embeddings"]
conflicts = []
python_dependencies = []
exports = ["Retriever", "RetrievalQuery", "RetrievalResult"]
```

模块 README 只需回答：

1. 提供什么；
2. 依赖什么；
3. 外发或持久化什么数据；
4. 如何使用 Fake 测试；
5. 删除时要移除哪些组装和配置项。

第一版可以手工维护描述文件。后续初始化器再读取它们生成项目，不需要现在实现动态插件系统。

## 7. 删除和裁剪规则

删除一个 Feature 的过程必须机械且可验证：

1. 删除 Feature 目录；
2. 删除只服务于该 Feature 的 Adapter；
3. 从 `bootstrap.py` 删除组装代码；
4. 从 Settings 删除对应配置段；
5. 从 `pyproject.toml` 删除对应可选依赖；
6. 删除该 Feature 的入口命令；
7. 运行导入边界检查、类型检查和测试。

删除 Feature 不应要求修改其他 Feature 的内部实现。

一个模块只有满足以下条件才算真正可删除：

- 没有其他模块导入其内部路径；
- 没有模块导入时副作用；
- 没有隐式注册表残留；
- 配置缺失不会被其他模块无条件访问；
- 数据库迁移和持久化兼容需求已明确处理；
- 删除后基础测试仍可运行。

对于已经产生持久化数据的应用，删除代码和删除历史数据必须分开。移除 Feature 不得自动删除用户数据。

## 8. 依赖安装策略

基础依赖保持最小，重量级能力使用 optional dependencies：

```toml
[project]
dependencies = [
    "pydantic-settings>=2.0",
]

[project.optional-dependencies]
openai = ["httpx>=0.27"]
rag = []
voice = ["openai-whisper", "pydub"]
vision = ["mss", "pillow"]
```

最终 extras 应由真实实现验证后确定。不能因为模板仓库包含某个目录，就让所有项目默认安装 Torch、Whisper 或视觉依赖。

## 9. 能力分类

### 9.1 默认保留

- typed settings；
- project errors；
- safe logging；
- secret references；
- lifecycle；
- test network guard；
- 如果选择 CLI，则包含 `check` 和 `version`。

### 9.2 通用可选 Feature

- `llm-text`：文本生成；
- `llm-vision`：图像和多模态分析；
- `embeddings`：向量生成；
- `documents`：文档块和来源引用；
- `retrieval`：关键词或语义检索；
- `artifacts`：版本化不可变中间产物；
- `pipeline`：阶段执行、校验、恢复；
- `events`：进程内发布订阅；
- `cache`：显式版本和输入指纹缓存；
- `persistence`：Repository 和 Unit of Work；
- `conversation`：消息、上下文预算和压缩；
- `evaluation`：离线样本和质量门禁。

### 9.3 领域 Feature

- `asr`；
- `tts`；
- `screen-capture`；
- `change-detection`；
- `ocr`；
- `quiz`；
- `learning-route`。

领域 Feature 至少在两个项目中复用，或边界被一个真实替换场景验证后，才提升为模板公共模块。

## 10. 四个项目的组合验证

### 10.1 TinyRAG

```text
foundation
+ documents
+ retrieval
+ cache
+ optional embeddings
+ filesystem adapter
+ optional OpenAI-compatible embedding adapter
+ CLI interface
+ MCP interface
```

远程 Embedding 必须显式启用；检索 Feature 不知道 MCP；缓存键包含输入、模型和配置版本。

### 10.2 Visual Layer

```text
foundation
+ screen-capture
+ change-detection
+ llm-vision
+ events
+ optional cache
+ provider adapters
+ terminal or JSONL interface
```

捕获不能被模型调用阻塞。有界队列和 latest-wins 属于该应用的运行编排，不应强塞进所有 Pipeline。

### 10.3 Emovoice

```text
foundation
+ asr
+ llm-text
+ tts
+ conversation
+ audio device adapters
+ local/cloud provider adapters
+ CLI or desktop interface
```

ASR、LLM 和 TTS 彼此独立，由 `VoiceConversationService` 编排。本地模型和远程 API 是 Adapter 选择。

### 10.4 AnythingQuiz

```text
foundation
+ documents
+ llm-text
+ artifacts
+ pipeline
+ persistence
+ conversation
+ evaluation
+ parser/provider/sqlite adapters
+ CLI interface
```

Artifact 和 Pipeline 在这里是核心能力，但仍然是模板中的可选模块，不能成为所有 AI 应用的强制抽象。

## 11. 横切策略

### 11.1 配置

- 每个模块拥有自己的 Settings 子模型；
- 应用 Settings 只组合已选择模块；
- 密钥保存为 Secret 或凭据引用；
- 配置文件路径显式解析，不依赖不可预测的当前工作目录；
- 本地无认证 Provider 使用明确认证模式，不能伪造 API Key。

### 11.2 错误

公共错误只定义稳定类别：configuration、validation、authentication、rate limit、timeout、provider、persistence 和 unavailable。

Feature 可以定义更具体的错误。Interface 负责把错误映射为退出码、HTTP 状态或 MCP 错误，不在底层直接打印。

### 11.3 重试

- 连接失败、429 和部分 5xx 可以有限重试；
- 读取超时后的生成请求可能已产生费用，不能盲目重放；
- `Retry-After` 必须设置上限；
- 重试次数、延迟和最终失败必须可观察；
- 确定性 Stage 和付费 AI Stage 使用不同策略。

### 11.4 隐私与数据外发

每个远程 Adapter 必须声明发送的数据类型、目标端点、是否包含用户数据、默认是否启用以及日志保留的元数据。

宿主环境中存在通用 API Key 不能自动视为用户同意发送文档、截图、音频或对话。

### 11.5 测试

每个 Contract 至少提供 Fake 或测试构造方式，例如 Fake Text Generator、Fake Embedding Provider、In-memory Repository、Fake Clock 和 Fake Event Publisher。

默认测试套件应封锁非本地网络，而不仅仅依赖开发者记得 mock。

## 12. 模板仓库与生成应用

长期形态应区分两个概念。

### 模块目录仓库

包内 `catalog/modules/` 保存所有可选模块的描述文件、依赖关系和组合信息，`catalog/presets/`
保存声明式组合。它可以包含完整模块集合，但不代表每个应用都安装全部依赖。

### 生成后的应用

只包含用户选择的模块和 Adapter：

```bash
create-ai-app voice-bot --cli --asr --llm-text --tts --ollama
```

第一阶段不立即实现生成器。先通过手工复制和删除验证模块边界。只有两到三个项目成功使用同一模块后，再固化初始化命令。

## 13. 静态检查要求

模块化不能只靠约定。后续实现至少需要：

1. import boundary：禁止内层依赖外层；
2. public API：禁止跨模块导入内部路径；
3. module graph：`module.toml` 不允许缺失依赖或循环依赖；
4. network guard：单元测试禁止意外外网请求；
5. secret scan：测试和日志 Fixture 不包含真实密钥；
6. minimal profile：最小模块组合可以安装、导入和测试；
7. sample profiles：TinyRAG、Emovoice 等组合可以通过契约测试。

第一版可用普通 Python 测试检查 import 和模块描述，不必立即引入复杂架构工具。

## 14. 实施阶段

### Phase 1：边界验证

实现：

- Foundation；
- `llm-text` Contract；
- OpenAI-compatible Adapter；
- Fake Text Generator；
- CLI `check`、`version`、`ask`；
- 显式 `bootstrap.py`；
- 网络封锁测试；
- 一个模块描述文件。

验收：

- 删除 OpenAI Adapter 后，Fake 模式测试仍通过；
- 删除整个 `llm-text` Feature 后，`check` 和 `version` 仍可运行；
- 无 Key 时不发送请求；
- 不通过自动扫描组装模块。

### Phase 2：第二种业务形态验证

从 TinyRAG 或 Emovoice 选择一个加入。验收重点不是功能数量，而是同一 Foundation 和 Contract 是否能复用，删除一个能力是否不修改其他能力内部代码。

### Phase 3：Artifact 和 Pipeline

使用 AnythingQuiz 验证版本化 Artifact、Processor、Validator、持久化 Stage、失败恢复和显式激活。只有验证后，Artifact 和 Pipeline 才进入正式公共模块目录。

### Phase 4：模块装配工具

当至少三个项目验证模块边界后，再实现：

```bash
create-ai-app new-project --preset minimal
create-ai-app new-project --add retrieval --add embeddings
create-ai-app new-project --remove web
```

工具根据 `module.toml` 处理目录、依赖、配置模板和组合根，但生成后的代码仍是普通、显式、可编辑的 Python 项目。

## 15. 第一轮架构决策

当前采用：

- 模块化单体；
- 目录级 Feature；
- Consumer-owned Contract；
- 显式构造函数注入；
- 单一 Composition Root；
- 可选依赖；
- 静态模块描述；
- Fake 优先测试；
- 生成器延后。

当前拒绝：

- 运行时插件发现；
- 全局容器和 Service Locator；
- 万能 Provider 接口；
- 所有场景强制 Artifact/Pipeline；
- 默认安装全部模型和媒体依赖；
- 为了删除方便而忽略持久化数据兼容。

## 16. 成功标准

1. 新应用可以从少量稳定模块开始；
2. 业务代码不再重复实现配置、日志、密钥和 Provider 错误映射；
3. 一个 Provider 可以替换而不影响业务；
4. 一个 Feature 可以删除而不修改无关 Feature；
5. 重量级依赖只随对应能力安装；
6. 不同入口复用同一 Application Service；
7. 模块边界由测试和静态检查保证；
8. 真实项目而不是想象中的需求决定哪些模块进入公共目录。

最终定位：

> Agent-ready Python 不是一个大而全的 AI 框架，而是一套经过真实项目验证的 Python AI 应用模块目录、依赖规则和显式装配方式。
