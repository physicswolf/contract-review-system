# Agent 框架调研报告 — LlamaIndex

| 项目 | 内容 |
|------|------|
| 文档主题 | Agent 框架调研：LlamaIndex |
| 应用场景 | 合同 AI 分析系统（文档解析 + 结构化分析） |
| 调研日期 | 2026-06-16 |
| 版本 | v1.0 |
| 关联项目 | 北航课题 · 合同 AI 分析系统 |

---

## 一、调研背景与目标

### 1.1 背景

本课题正在建设「合同 AI 分析系统」，当前已实现的处理链路为：

```
上传文档 → LiteParse 解析 → 规则化章节切分 → 整篇 LLM 分析 → 前端展示
```

其中文档解析已采用 LlamaIndex 生态的开源本地解析库 **LiteParse**。随着需求向「多步骤、可分支、可并行、可人工复核」的自动化分析演进，需要评估引入 **Agent 编排框架** 的可行性。

### 1.2 调研目标

1. 厘清 LlamaIndex 在 Agent 领域的能力边界与架构模型；
2. 评估其与现有项目（LiteParse + FastAPI + 自部署 27B 模型）的契合度；
3. 与主流框架（LangChain / LangGraph）横向对比；
4. 给出是否引入、如何引入的落地建议与演进路线。

---

## 二、LlamaIndex 总览与定位

LlamaIndex 最初以 **RAG / 数据索引** 见长，近年将能力扩展到 **Agent 编排**。其 Agent 相关能力可分为三层：

| 层级 | 组件 | 作用 |
|------|------|------|
| 数据层 | LiteParse、LlamaParse、VectorStore、QueryEngine | 文档解析、索引、检索 |
| Agent 层 | `FunctionAgent`、`ReActAgent`、`CodeActAgent` | 单 Agent 推理 + 工具调用 |
| 编排层 | **Workflow**、**AgentWorkflow** | 多步骤、多 Agent、事件驱动流程 |

**与本项目的关系**：已使用 LiteParse，技术栈一致；若要做「解析 → 分章 → 检索 → 分析 → 复核」的自动化流水线，Workflow / AgentWorkflow 是自然延伸，可复用现有服务代码。

---

## 三、核心架构：Workflow（事件驱动）

Workflow 是 LlamaIndex Agent 的底层编排模型（2025 年发布 1.0），使用 **事件（Event）+ 步骤（Step）** 取代传统的有向无环图（DAG）。

### 3.1 流程示意

```
用户输入 (StartEvent)
    ↓
@step 解析文档 → ParseDoneEvent
    ↓
@step 章节切分 → ChaptersReadyEvent
    ↓
@step LLM 分析（可并行多章）→ AnalysisEvent
    ↓
@step 汇总输出 (StopEvent)
```

### 3.2 核心特点

- **纯 Python**：用 `@step` 装饰器，按函数入参/返回类型自动推断事件流，并在启动前做合法性校验；
- **原生 async**：天然适配 FastAPI 集成，便于并发；
- **控制流完整**：支持循环、分支、并行、人工介入（Human-in-the-loop）；
- **状态共享**：`Context` 对象提供共享状态、流式输出、断点续跑（Checkpoint）。

### 3.3 最小示例（贴合本项目）

```python
from workflows import Workflow, step
from workflows.events import StartEvent, StopEvent, Event

class ParseDoneEvent(Event):
    text: str

class ContractFlow(Workflow):
    @step
    async def parse(self, ev: StartEvent) -> ParseDoneEvent:
        text = parse_document(ev.file_path).text
        return ParseDoneEvent(text=text)

    @step
    async def analyze(self, ev: ParseDoneEvent) -> StopEvent:
        result = await analyze_contract(ev.text)
        return StopEvent(result=result)
```

> 相比 LangGraph 的「显式画边」，Workflow 更偏「事件驱动、代码即流程」，适合文档类、步骤可变的业务。

---

## 四、Agent 类型

### 4.1 FunctionAgent（推荐，模型支持 Function Calling 时）

- 面向 GPT-4o、Qwen、Gemini 等具备原生工具调用能力的模型；
- 工具即普通 Python 函数，依赖类型注解与 docstring 描述能力；
- 适合直接对接现有的 `parse_document`、`split_into_chapters`、`analyze_contract`。

```python
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI

agent = FunctionAgent(
    tools=[parse_contract, split_chapters, analyze_risk],
    llm=OpenAI(model="qwen-plus", api_base="...", api_key="..."),
    system_prompt="你是合同分析助手，按需调用工具完成解析与分析。",
)
result = await agent.run("请分析这份合同的风险条款")
```

### 4.2 ReActAgent（通用兜底）

- 不依赖原生 Function Calling，采用 ReAct 提示词（Thought → Action → Observation）；
- 适合自部署 27B 等「OpenAI 兼容但工具调用不稳定」的模型；
- 延迟与 token 消耗通常高于 FunctionAgent。

### 4.3 CodeActAgent

- 让模型生成 Python 代码执行复杂逻辑；
- 适合数值计算、批量处理；合同场景一般不如显式工具稳妥。

---

## 五、多 Agent 编排：AgentWorkflow

在 Workflow 之上封装，用于 **多 Agent 协作、状态保持、Agent 间 handoff**。

### 5.1 三种典型模式

| 模式 | 说明 | 适用场景 | 代码量 | 灵活度 |
|------|------|----------|--------|--------|
| **AgentWorkflow** | 多 Agent 自动 handoff | 快速原型 | 最少 | ★★ |
| **Orchestrator Agent** | 主 Agent 把子 Agent 当工具调用 | 固定流程、可控顺序 | 中 | ★★★ |
| **Custom Workflow** | 手写 `@step` 编排 | 复杂分支、人工复核 | 多 | ★★★★★ |

### 5.2 合同分析示例（多 Agent）

```python
from llama_index.core.agent.workflow import AgentWorkflow, FunctionAgent

parse_agent = FunctionAgent(
    name="ParseAgent",
    description="解析 PDF/Word 并切分章节",
    tools=[parse_document, split_into_chapters],
    can_handoff_to=["RiskAgent"],
)

risk_agent = FunctionAgent(
    name="RiskAgent",
    description="识别违约、付款、保密等风险条款",
    tools=[analyze_risk_clauses],
    can_handoff_to=["SummaryAgent"],
)

summary_agent = FunctionAgent(
    name="SummaryAgent",
    description="汇总结构化分析报告",
    tools=[generate_report],
)

workflow = AgentWorkflow(agents=[parse_agent, risk_agent, summary_agent])
result = await workflow.run("分析 uploads/contract.docx")
```

> 选型建议：快速原型从 `AgentWorkflow` 起步；需要控制顺序时改用 Orchestrator Agent；只有前两者无法表达流程时再上 Custom Workflow。

---

## 六、与 LangChain / LangGraph 对比

| 维度 | LlamaIndex | LangChain / LangGraph |
|------|------------|------------------------|
| **强项** | 文档解析、RAG、索引与 Agent 一体 | 生态广、集成多、图编排成熟 |
| **编排模型** | 事件驱动 Workflow | 有向图 StateGraph |
| **学习曲线** | 文档/RAG 场景上手快 | 通用 Agent 资料多 |
| **与现有项目** | 已用 LiteParse，栈一致 | 需新引入整套抽象 |
| **部署** | 脚本/Notebook/FastAPI；LlamaCloud 可选 | LangSmith、LangGraph Platform 等 |
| **TypeScript** | Workflows TS 已弃用，主推 Python | TS 支持较好 |

**结论**：本场景是「文档解析 + 结构化分析」，LlamaIndex 与 LiteParse、章节切分、按章 RAG 天然契合；若未来主要做通用对话 Agent 或复杂状态机，LangGraph 也值得并行评估。

---

## 七、对本课题的适用性分析

### 7.1 当前架构（已实现）

```
上传 → LiteParse 解析 → 规则章节切分 → 整篇 LLM 分析 → 前端展示
```

### 7.2 引入 LlamaIndex Agent 后的演进方向

1. **按章节并行分析**：Workflow 中对每章 `asyncio.gather` 后汇总，比手写 BackgroundTasks 更清晰；
2. **工具化 Agent**：把 `parse_document`、`split_into_chapters`、`search_clause` 封装为工具，由 Agent 决策调用顺序；
3. **多 Agent 分工**：ParseAgent（解析+切分）/ RiskAgent（违约·付款·保密）/ LegalAgent（合规性）/ SummaryAgent（报告）；
4. **RAG 增强**：合同入库 VectorStore，`QueryEngineTool` 支持「第几条关于违约金？」类问答；
5. **人工复核**：利用 Human-in-the-loop，高风险条款暂停等待用户确认再继续。

### 7.3 是否建议现在引入

| 阶段 | 建议 |
|------|------|
| **当前（课题验证）** | 保持现有 FastAPI 流水线，成本低、可控 |
| **下一阶段** | 引入 `FunctionAgent` + 工具封装，对接 27B 内网模型 |
| **规模化** | 上 `AgentWorkflow` 或多 Agent，加 RAG 与人工复核 |

---

## 八、落地建议与演进路线

```
阶段一（现状）   规则切分 + 整篇分析，跑通内网 27B 模型联调
      ↓
阶段二（试点）   现有 services 封装为工具，接入单个 FunctionAgent / ReActAgent
      ↓
阶段三（增强）   按章并行分析 + VectorStore + QueryEngineTool 问答
      ↓
阶段四（规模化） 多 Agent AgentWorkflow + 人工复核 + 流式可观测
```

**兼容性要点**：现有 `parser.py`、`splitter.py`、`analyzer.py` 可直接封装为 Agent 工具，无需重写；`liteparse` 与 `llama-index` 为独立包，可继续独立使用 LiteParse，仅在 Agent 层引入 `llama-index-core`。

---

## 九、依赖与安装

```bash
# 核心（含 Workflow）
pip install llama-index-core

# OpenAI 兼容 LLM（通义 / 自部署 27B）
pip install llama-index-llms-openai

# 可选：向量检索
pip install llama-index-vector-stores-chroma  # 或其他向量库
```

> 注意：`llama-index` 与 `liteparse` 是不同的包；项目可继续独立使用 `liteparse`，仅在 Agent 层按需引入 `llama-index-core`。

---

## 十、调研结论

1. **能力体系**：LlamaIndex Agent = Workflow（底层编排）+ FunctionAgent/ReActAgent（单 Agent）+ AgentWorkflow（多 Agent）；
2. **核心优势**：与文档解析、RAG、索引同属一套生态，对合同分析场景比纯对话型框架更贴合；
3. **编排适配**：Workflow 事件驱动模型适合「解析 → 切分 → 分析 → 复核」这类可分支、可并行的流程；
4. **兼容性好**：现有服务代码可直接封装为 Agent 工具，迁移成本低；
5. **建议路径**：先完成规则切分与内网模型联调 → 再试点 FunctionAgent 工具调用 → 有需要再上多 Agent Workflow。

---

## 附录：参考链接

- LlamaIndex Workflows 文档：https://developers.llamaindex.ai/python/llamaagents/workflows/
- Agents 模块指南：https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/
- 多 Agent 模式：https://developers.llamaindex.ai/python/framework/understanding/agent/multi_agent/
- AgentWorkflow 介绍：https://www.llamaindex.ai/blog/introducing-agentworkflow-a-powerful-system-for-building-ai-agent-systems
- Workflows 官网：https://www.llamaindex.ai/workflows
