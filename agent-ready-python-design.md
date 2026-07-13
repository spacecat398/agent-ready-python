# Agent-ready Python：AI 应用脚手架设计说明

> 一个极简、默认安全、支持 OpenAI-compatible API 的 Python AI 应用起始模板。

> 模块化架构升级方案见 [`modular-architecture-design.md`](modular-architecture-design.md)。原文继续保留为最小文本生成项目的第一版基线。
> 实施状态和带时间戳的更新见 [`PROGRESS.md`](PROGRESS.md)。

## 1. 项目定位

这个项目不是一个具体的 AI 应用，也不是 LangChain、LangGraph 的替代品，而是一套用于快速创建 AI 小工具的基础模板。

它把每个 AI 项目都会重复搭建的基础部分整理好：

- `uv` 项目与依赖管理
- `src/` 项目结构
- `.env` 配置读取
- Pydantic 配置校验
- OpenAI-compatible API 客户端
- 超时、错误和有限重试
- CLI 命令行入口
- 不依赖真实 API 的测试
- GitHub Actions CI
- 默认安全与隐私边界
- 面向 Agent 的安装、验证和排错说明

以后制作网页总结器、本地知识库工具、Brain Hacker 分析器、RikkaHub 辅助工具或小型 Agent 时，可以从此模板开始，而不是从空目录重复搭建基础设施。

核心定位：

> 一个安全、轻量、可测试、Agent-friendly 的 Python AI 项目起点。

## 2. 为什么值得做

AI 项目经常重复遇到这些问题：

- API Key 放在哪里？
- 如何切换 OpenAI、DeepSeek、OpenRouter 或其他兼容服务？
- 请求超时、429 限流和 5xx 错误怎么处理？
- 测试时如何避免真实调用模型、消耗额度？
- 如何避免密钥和私人数据进入 Git？
- 如何让 GitHub Actions 在没有 API Key 的情况下通过？
- 如何让另一个 Agent 自动安装、配置和验证项目？

这些问题通常与具体业务无关，适合固化在模板中。

TinyRAG 已经验证了一些值得复用的工程习惯：

- 使用 `uv`
- 配置显式化
- 默认安全，远程服务必须有明确配置
- 测试和 CI 独立运行
- 运行前先检查环境
- 失败时返回可靠的退出码
- 不把敏感信息写入日志
- README 面向 Agent 编写

这个脚手架就是把这些经验提炼出来。

## 3. 与普通 Python 模板的区别

普通模板通常只提供目录和 `pyproject.toml`。本项目额外关注 AI 应用的实际运行边界：

1. 统一模型、端点和 Key 配置；
2. 通过 OpenAI-compatible API 支持多个服务商；
3. 测试不依赖真实模型服务；
4. 对认证失败、限流、超时和非法响应提供清晰错误；
5. README 能被 Agent 直接执行；
6. 默认不因为宿主机存在某个通用 Key 就自动上传数据。

它更像：

> Python AI 项目模板 + 最小运行时规范 + Agent 安装协议。

## 4. 推荐项目结构

第一版建议保持简单：

```text
agent-ready-python/
├── src/
│   └── ai_app/
│       ├── __init__.py
│       ├── __main__.py
│       ├── config.py
│       ├── client.py
│       ├── errors.py
│       ├── logging_config.py
│       └── cli.py
│
├── tests/
│   ├── test_config.py
│   ├── test_client.py
│   └── test_cli.py
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── .env.example
├── .gitignore
├── pyproject.toml
├── uv.lock
├── README.md
├── AGENTS.md
└── LICENSE
```

以后有实际业务逻辑时再扩展：

```text
src/ai_app/
├── config.py
├── client.py
├── prompts.py
├── services/
│   └── summarizer.py
└── cli.py
```

第一版不要拆出过多模块。脚手架的目标是降低启动成本，而不是制造架构负担。

## 5. 核心模块设计

### 5.1 `config.py`：集中读取配置

建议使用 Pydantic Settings：

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_key: str | None = None
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    timeout_seconds: float = 60
    max_retries: int = 2

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AI_",
        extra="ignore",
    )
```

推荐配置：

```env
AI_API_KEY=
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini
AI_TIMEOUT_SECONDS=60
AI_MAX_RETRIES=2
AI_LOG_LEVEL=INFO
```

设计原则：

- 所有配置集中管理；
- 环境变量命名统一；
- 默认值明确；
- 配置错误尽早暴露；
- 业务代码不直接到处读取 `os.environ`；
- 只读取项目明确声明的 `AI_API_KEY`，不自动继承其他工具的通用 Key。

### 5.2 `client.py`：统一 API 客户端

业务代码不应散落 HTTP 请求或 SDK 调用，而应使用统一接口：

```python
from ai_app.client import LLMClient

client = LLMClient(settings)
answer = client.complete("请解释什么是 RAG")
```

第一版可保持简单：

```python
class LLMClient:
    def complete(self, prompt: str) -> str:
        ...
```

以后需要时再扩展 `system`、`temperature`、结构化输出和流式输出。

客户端负责：

- 构造认证头；
- 发送 Chat Completions 请求；
- 设置 timeout；
- 处理有限重试；
- 解析响应；
- 将供应商错误转换为项目自己的错误类型；
- 拒绝空响应和明显非法响应。

推荐第一版使用 `httpx` 自己实现一个薄客户端，而不是一开始依赖复杂框架。这样依赖少，也能真正掌握 HTTP/API 基础。

### 5.3 `errors.py`：明确错误类型

```python
class AIAppError(Exception):
    """所有项目级错误的基类。"""


class ConfigurationError(AIAppError):
    """配置无效或缺失。"""


class AuthenticationError(AIAppError):
    """API Key 无效或权限不足。"""


class RateLimitError(AIAppError):
    """服务端限流。"""


class ProviderError(AIAppError):
    """模型服务端返回错误。"""


class ResponseFormatError(AIAppError):
    """模型响应格式不符合预期。"""
```

CLI 可以据此输出可操作的错误，而不是暴露难懂的 traceback：

```text
配置错误：缺少 AI_API_KEY。
请复制 .env.example 为 .env，并填写 API Key。
```

### 5.4 `logging_config.py`：安全日志

日志原则：

- 正常业务输出走 stdout；
- 调试日志走 stderr；
- 不打印 API Key；
- 不打印完整 Prompt；
- 不默认打印私人文档全文；
- 日志等级可由配置控制。

允许：

```text
INFO  Starting AI application
INFO  Using model: gpt-4o-mini
ERROR Request failed: timeout
```

禁止：

```text
Using API key: sk-xxxxx
Full document content: ...
```

如果以后模板支持 MCP 或其他 stdio 协议，普通日志绝不能污染 stdout，因为 stdout 可能承载 JSON-RPC 数据。

### 5.5 `cli.py`：统一命令行入口

建议第一版支持三个动作：

```bash
uv run ai-app check
uv run ai-app ask "什么是向量数据库？"
uv run ai-app version
```

#### `check`

只检查运行环境和配置，不调用模型：

```text
Python: OK
Configuration file: OK
API base URL: OK
API key: configured
Model: gpt-4o-mini
```

不显示完整 Key。

#### `ask`

真正调用模型：

```bash
uv run ai-app ask "用一句话解释 RAG"
```

没有 Key 时应输出清晰的配置错误，不应产生无关 traceback。

#### `version`

```bash
uv run ai-app version
```

便于 Agent、脚本和 CI 检查版本。

## 6. API 客户端的范围

第一版只支持非流式 Chat Completions 即可。不要一开始实现所有模型能力。

建议支持：

```env
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=***
AI_MODEL=gpt-4o-mini
AI_TIMEOUT_SECONDS=60
AI_MAX_RETRIES=2
```

切换 DeepSeek 等兼容服务时，只改环境变量，不改业务代码：

```env
AI_BASE_URL=https://api.deepseek.com/v1
AI_MODEL=deepseek-chat
```

第一版暂不加入：

- 流式输出；
- 多轮会话状态；
- Responses API 专用抽象；
- 复杂结构化输出；
- 自动 provider 探测。

## 7. 错误处理要求

第一版不需要复杂的重试系统，但必须有可靠的基础行为。

### 缺少 API Key

立即失败，不发送网络请求：

```text
ConfigurationError: AI_API_KEY is not configured.
```

### 401 / 403

转换为认证错误，提示检查 Key 和权限。

### 超时

有限重试后失败，不能无限等待：

```text
Request timed out after 60 seconds.
```

### 429

在安全范围内重试一次或两次，必要时读取 `Retry-After`。

### 5xx

短暂重试，仍失败后给出服务端错误。

### 空响应或非法响应

不能把空字符串当成成功；不能让用户看到难懂的 `KeyError` 或原始 JSON 解析 traceback。

## 8. 测试策略

最重要的要求：

> 没有 API Key，也能完整跑完测试。

测试不连接真实模型服务，使用 Fake Transport 或 mock response。

### 配置测试

覆盖：

- 默认配置；
- 配置文件加载；
- 缺少 Key 的状态；
- timeout 和 retries 边界；
- 非法 URL 或空模型名。

### 客户端测试

覆盖：

- 成功响应返回文本；
- 空响应失败；
- 认证错误转换；
- 超时转换；
- 429 和 5xx 的有限重试；
- 异常信息不泄露完整 API Key。

### CLI 测试

覆盖：

```bash
uv run ai-app --help
uv run ai-app version
uv run ai-app check
```

在没有 Key 时：

- `version` 成功；
- `check` 提供明确状态；
- `ask` 清晰失败；
- 不输出无关 traceback。

### 安全测试

验证：

- `.env` 被 `.gitignore` 忽略；
- 日志不包含完整 Key；
- 错误消息不泄露敏感配置；
- 默认测试套件不进行网络请求。

## 9. 依赖建议

```toml
[project]
name = "agent-ready-python"
version = "0.1.0"
description = "A small, secure, agent-friendly Python starter for AI applications"
requires-python = ">=3.12"
dependencies = [
    "httpx>=0.27",
    "pydantic-settings>=2.0",
    "typer>=0.12",
]

[project.scripts]
ai-app = "ai_app.cli:main"

[dependency-groups]
dev = [
    "pytest>=8.0",
    "ruff>=0.6",
]
```

第一版应保持依赖少。暂不加入：

- LangChain；
- LangGraph；
- 向量数据库；
- MCP；
- Web UI；
- 复杂重试框架；
- 多 provider 插件系统。

## 10. Agent-native README

README 保留两层内容。

### 人类快速理解

```markdown
# Agent-ready Python

A small Python starter for building AI applications with uv,
Pydantic Settings, an OpenAI-compatible API client, CLI, tests,
and CI.
```

配一个最小运行示例：

```bash
uv sync
cp .env.example .env
uv run ai-app check
uv run ai-app ask "Hello"
```

### Agent 执行协议

README 应明确告诉 Agent：

```markdown
## Instructions for coding agents

1. Check the Python version and available package manager.
2. Prefer uv if available.
3. Run `uv sync`.
4. Copy `.env.example` to `.env` only if `.env` does not exist.
5. Never overwrite an existing `.env`.
6. Never print or commit API keys.
7. Run the test suite before claiming success.
8. Run `ai-app check` after installation.
9. Do not call the provider API unless the user explicitly asks for a live request.
10. Report failed commands with their actual output.
```

安全部分应写清：

- 默认测试不访问网络；
- 只有 `ask` 等明确操作才联系 provider；
- 不要把私人文档放进仓库；
- 不要提交 `.env`；
- 不要把 Key 写入日志；
- 外部 provider 请求属于数据传输；
- 不要在测试通过前声称安装完成。

## 11. 第一版范围

### 必须有

- `uv` 项目结构；
- `src/` layout；
- Pydantic Settings；
- `.env.example`；
- `httpx` OpenAI-compatible 客户端；
- CLI；
- 明确错误类型；
- 不依赖真实 API 的测试；
- GitHub Actions；
- Agent-readable README；
- `check`、`version`、`ask` 命令。

### 可以有

- 简单有限重试；
- timeout；
- 日志等级；
- provider 信息展示；
- Fake Transport；
- ruff 检查。

### 暂时不要有

- 流式输出；
- 多轮对话状态；
- LangChain / LangGraph；
- 向量数据库；
- RAG；
- 多 Agent；
- Web UI；
- MCP；
- 插件系统；
- 自动 provider 探测；
- 自动读取宿主环境中的任意 API Key。

## 12. 分阶段路线

### Phase 1：最小可用脚手架

- 项目结构；
- 配置读取；
- API 客户端；
- CLI；
- 测试；
- README；
- CI。

验收：

```bash
uv sync
uv run pytest
uv run ai-app version
uv run ai-app check
```

### Phase 2：可靠性增强

- 重试退避；
- 429 处理；
- 更精细的错误映射；
- 结构化日志；
- 更完整的 CLI 测试。

### Phase 3：模板化初始化器

以后如果实际复制模板创建了多个项目，再考虑提供：

```bash
ai-app-starter init my-project
```

第一版建议先做纯模板，不要一开始就写初始化器。先确认哪些文件和约定真的值得固定下来。

### Phase 4：可选能力

未来可以增加可选模块：

```text
providers/
streaming/
structured_output/
embeddings/
tools/
```

但不应让这些能力拖累最小模板。

## 13. 项目名称候选

- `agent-ready-python`
- `python-ai-starter`
- `ai-app-starter`
- `ai-project-template`

推荐暂用：

```text
agent-ready-python
```

它表达了项目的两个重点：Python AI 应用，以及对 Agent 的友好性。

## 14. 与 TinyRAG 的关系

TinyRAG 是一个具体的 Agent 工具：

```text
文档 → 切块 → 检索 → MCP → Agent
```

这个脚手架是更底层的基础设施：

```text
配置 → API → CLI → 测试 → CI → Agent 安装协议
```

TinyRAG 解决：

> 如何给 Agent 提供本地知识库能力？

脚手架解决：

> 如何快速、可靠地写出下一个 AI 工具？

它们不是竞争关系。TinyRAG 中验证过的工程习惯，正好可以沉淀进这个模板。

## 15. 今晚的开发顺序

1. 创建项目：

   ```bash
   uv init --package agent-ready-python
   cd agent-ready-python
   uv sync
   ```

2. 搭建 `src/` 与 `tests/` 结构；
3. 实现配置读取和 `check` 命令；
4. 实现最小非流式 API 客户端；
5. 实现 `version` 与 `ask`；
6. 加入 Fake Transport 和 3～6 个核心测试；
7. 加入 GitHub Actions；
8. 写 README、AGENTS.md 和安全边界；
9. 跑完整验收命令；
10. 提交一个干净的初始版本。

## 16. 最终验收标准

以下命令应成立：

```bash
uv sync
uv run pytest
uv run ai-app version
uv run ai-app check
```

没有 API Key 时：

```bash
uv run ai-app ask "hello"
```

应得到清晰配置错误，而不是崩溃。

完整要求：

- 测试不自动调用网络；
- CI 不需要 API Key；
- `.env` 不会进入 Git；
- 日志不泄露 Key；
- 更换 API Base URL 不需要修改业务代码；
- Agent 读 README 后能完成安装和验证；
- 项目结构足够简单，可以直接复制；
- 不在第一版引入不必要的大型框架。

## 最终定位

> 一个极简的、默认安全的、支持 OpenAI-compatible API 的 Python AI 应用起始模板。它不试图替开发者解决所有 AI 问题，只负责把配置、API 调用、命令行、测试、CI 和 Agent 安装流程整理成一个可靠起点。

第一版不需要追求“框架感”。只要以后想写新的 AI 小工具时，可以从模板开始，十分钟内进入业务代码，就已经成功。
