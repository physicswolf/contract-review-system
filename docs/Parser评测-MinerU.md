# Parser 评测报告 — MinerU

| 项目 | 内容 |
|------|------|
| 文档主题 | 文档解析器调研与评测方案：MinerU |
| 评测对象 | MinerU（OpenDataLab 开源文档解析工具） |
| 应用场景 | 合同 AI 分析系统（PDF / Word 合同解析 + 章节结构化 + RAG/Agent 数据准备） |
| 调研日期 | 2026-06-20 |
| 版本 | v1.0 |
| 关联项目 | 北航课题 · 合同 AI 分析系统 |

---

## 一、调研背景与目标

当前 demo 已实现基于 LiteParse 的合同解析能力，并完成了《Parser 评测报告 — LiteParse》。实测结果表明，LiteParse 对电子版 PDF 的纯文本解析速度非常快、乱码率低，但在 PDF 章节结构化方面存在明显短板：目录行、细粒度编号、字号差异等会导致章节过度切分。

MinerU 是 OpenDataLab 开源的高精度文档解析工具，面向 LLM、RAG、Agent 工作流，主打复杂版面解析、OCR、表格、公式、阅读顺序恢复与 Markdown/JSON 结构化输出。因此，本次调研目标是：

1. 评估 MinerU 是否适合补强当前 demo 的 PDF 结构化能力；
2. 对比 MinerU 与 LiteParse 在合同解析场景中的定位差异；
3. 设计一套可复用的评测方案，用于后续本机或云端实测；
4. 给出是否引入 MinerU 的建议与集成路线。

> 说明：当前本机 Python 虚拟环境未安装 MinerU，且 MinerU 涉及模型下载与较重推理依赖。因此本文为“调研评估版”，结合官方能力、当前 demo 代码和已有 LiteParse 实测数据进行分析；正式性能数据需在安装 MinerU 后补充。

---

## 二、MinerU 能力概览

MinerU 是面向复杂文档解析的开源工具，可将 PDF、图片、DOCX、PPTX、XLSX 等输入转换为 Markdown、JSON 及中间结构化结果，供大模型、RAG、知识库和 Agent 工作流使用。

### 2.1 核心能力

| 能力 | 说明 | 对合同分析的价值 |
|------|------|------------------|
| 多格式输入 | 支持 PDF、图片、DOCX、PPTX、XLSX 等 | 可覆盖合同正文、扫描件、附件材料 |
| 版面分析 | 支持单栏、多栏、复杂版面阅读顺序恢复 | 降低 PDF 文本乱序风险 |
| 标题/段落/列表保留 | 输出结构化 Markdown / JSON | 有利于章节切分与 RAG 分块 |
| 页眉页脚/页码清理 | 自动移除页眉、页脚、脚注、页码等干扰项 | 可缓解当前 demo 的目录/页码误判问题 |
| 表格识别 | 表格可转为 HTML | 有利于采购清单、付款表、验收表解析 |
| 公式识别 | 公式可转 LaTeX | 合同场景价值较低，但科研文档有价值 |
| OCR | 自动检测扫描 PDF、乱码 PDF 并启用 OCR，支持多语言 | 可处理扫描版合同 |
| 可视化结果 | 支持 layout / span 可视化 | 便于人工检查解析质量 |
| 部署方式 | CLI、Python、FastAPI、Gradio WebUI | 可独立部署成解析服务 |

### 2.2 与 LiteParse 的定位差异

| 维度 | LiteParse | MinerU |
|------|-----------|--------|
| 定位 | 轻量本地解析，文本与坐标抽取 | 重型结构化解析，面向 LLM/RAG/Agent |
| PDF 速度 | 极快，电子版 PDF 亚秒级 | 预计明显更慢，取决于 CPU/GPU 与模型模式 |
| 输出 | text、page、text_items、坐标、字号 | Markdown、JSON、版面元素、表格 HTML、公式 LaTeX |
| OCR | 可选但当前 demo 关闭 | 自动检测扫描/乱码 PDF 并启用 OCR |
| 表格 | 主要为文本抽取 | 可保留表格结构 |
| 章节结构 | 需自行基于正则/字号切分 | 更可能保留标题、列表和阅读顺序 |
| 部署成本 | 低，Docker 镜像相对轻 | 高，模型与依赖较重 |
| 适合场景 | 电子版合同、快速解析、轻量部署 | 复杂版面、扫描件、结构化 Markdown/RAG |

---

## 三、当前 demo 的基线情况

当前后端解析链路如下：

```text
上传文档
  → parse_document（LiteParse）
  → split_into_chapters（Word 样式 / PDF 字号 / 正则）
  → analyze_contract（切片后调用 LLM）
  → 前端展示解析原文、章节结构、AI 分析结果
```

现有 LiteParse 实测基线取自 `backend/uploads/` 的 3 份真实样本：

| 样本 | 类型 | 页数 | 字符数 | LiteParse 耗时(中位) | 章节数 | 主要问题 |
|------|------|------|--------|----------------------|--------|----------|
| UICC 采购协议 | PDF | 24 | 13,880 | 0.05 s | 131 | `1.1` 等细粒度编号过度切分 |
| UICC 采购协议 | DOCX | 36 | 14,053 | 2.57 s | 28 | 相对合理 |
| 物资采购通用合同 | PDF | 35 | 28,521 | 0.09 s | 318 | 目录页与行尾页码误判严重 |

基线结论：

1. LiteParse 解析电子版 PDF 非常快，文本质量高；
2. DOCX 由于依赖 LibreOffice 转换，有固定耗时；
3. 主要瓶颈不是“文本抽取”，而是“PDF 结构化与章节识别”；
4. 若 MinerU 能输出更接近阅读顺序的 Markdown 与标题层级，将直接改善章节切分与 RAG 分块质量。

---

## 四、MinerU 评测方案设计

### 4.1 测试数据集

沿用 LiteParse 评测的 3 份真实合同样本，保证可比性：

| 编号 | 样本 | 类型 | 评测重点 |
|------|------|------|----------|
| S1 | 支出类合同-UICC 车载硬件采购协议 | PDF | 普通电子版 PDF 结构化质量 |
| S2 | 支出类合同-UICC 车载硬件采购协议 | DOCX | 与 PDF 同文档对比 |
| S3 | 物资采购通用合同 | PDF | 目录页、长文档、多标题层级 |

后续可补充扫描件合同样本，用于测试 OCR 能力。

### 4.2 评测维度

| 维度 | 指标 | 说明 |
|------|------|------|
| 解析性能 | 总耗时、页/秒、CPU/GPU 占用 | 判断是否适合在线上传即解析 |
| 文本完整度 | 字符数、中文字符数、乱码数 | 与 LiteParse 输出对齐比较 |
| 结构化能力 | Markdown 标题数、列表数、表格数 | 评估对下游章节切分的支持 |
| 阅读顺序 | 目录、正文、表格是否按人类阅读顺序输出 | 合同问答/RAG 的关键 |
| 噪声清理 | 页眉、页脚、页码、目录页页码是否保留 | 直接影响切分误判 |
| 表格还原 | 采购清单、付款节点、验收表是否保留表格结构 | 影响合同金额与付款条款抽取 |
| 章节切分 | 基于 MinerU Markdown 后的章节数、平均章节长度 | 对比 LiteParse 的 131/318 过度切分 |
| 部署成本 | 镜像体积、模型大小、安装复杂度 | 影响离线包分发与 ECS 部署 |

### 4.3 预期命令流程

安装方式需以 MinerU 官方文档为准，常见使用路径包括 CLI 与服务化调用。后续可采用如下评测流程：

```bash
# 示例：安装（具体 extras 以实际版本为准）
pip install -U "mineru[all]"

# 示例：解析单文件
mineru -p backend/uploads/946755b7-7f4f-4833-aca3-16dddc084655.pdf -o eval/mineru_out
```

输出目录重点检查：

```text
eval/mineru_out/
  ├─ *.md        # Markdown 结构化文本
  ├─ *.json      # 阅读顺序 JSON / 中间结构
  ├─ images/     # 提取图片
  └─ 可视化文件  # layout / span 检查
```

### 4.4 与当前 demo 的集成接口

可新增 `backend/app/services/mineru_parser.py`：

```python
@dataclass
class MinerUParseResult:
    markdown: str
    text: str
    page_count: int | None
    blocks: list[dict]
    tables: list[dict]


def parse_document_with_mineru(file_path: str) -> MinerUParseResult:
    \"\"\"调用 MinerU CLI 或独立解析服务，返回 Markdown/JSON 结构化结果。\"\"\"
    ...
```

再在现有 pipeline 中增加解析器选项：

```text
PARSER_ENGINE=liteparse | mineru | auto
```

推荐策略：

1. `liteparse`：默认，快，适合电子版合同；
2. `mineru`：复杂 PDF、扫描件、表格密集型合同；
3. `auto`：先用 LiteParse 快速解析，若章节过度切分、乱码、文本为空或检测为扫描件，则切换 MinerU。

---

## 五、对当前问题的预期改善

### 5.1 PDF 章节过度切分

LiteParse 路径的问题是只拿到纯文本、字号、坐标，下游需要自己推断标题层级。MinerU 若能输出 Markdown 标题和列表结构，可将切分逻辑从“正则猜测”改为“结构优先”：

```text
MinerU Markdown 标题
  → 一级/二级标题直接作为章节边界
  → 普通编号列表归并到上级章节
  → 目录页按结构过滤
```

预期对 S1 / S3 的改善：

| 样本 | LiteParse 当前章节数 | MinerU 预期目标 |
|------|---------------------|----------------|
| S1 PDF | 131 | 接近 DOCX 的 20~40 章 |
| S3 PDF | 318 | 目录不入正文，章节数显著下降 |

### 5.2 目录页与页码误判

MinerU 官方能力包含页眉、页脚、页码等干扰项清理，并强调阅读顺序输出。若对目录区域处理较好，可降低当前 `一、工程概况 1` 被误判为标题的问题。

需要注意：目录本身可能仍会作为 Markdown 内容输出，因此仍建议在 demo 中增加目录过滤策略：

```text
检测 “目录” 标志
  → 遇到连续行尾页码
  → 跳过直到正文页/第一部分/第一条
```

### 5.3 表格结构保留

采购合同中常见表格包括：

- 物资清单；
- 付款节点；
- 验收标准；
- 违约金计算规则；
- 联系人及账户信息。

LiteParse 主要抽文本，表格结构容易丢失；MinerU 可输出表格 HTML，理论上更利于后续 LLM 抽取结构化字段。

---

## 六、成本与风险

| 风险 | 说明 | 应对建议 |
|------|------|----------|
| 安装成本高 | MinerU 依赖模型、OCR、版面分析组件，安装远重于 LiteParse | 单独做解析服务，不直接打进轻量 demo 镜像 |
| 推理速度慢 | VLM/OCR 模式通常远慢于纯文本解析 | 默认 LiteParse，复杂文档再 fallback MinerU |
| 离线包变大 | 模型与依赖会显著增加 Docker 镜像体积 | 维护 `lite` 与 `full` 两套镜像 |
| ECS 资源依赖 | GPU/NPU 可加速，CPU 可跑但可能较慢 | 在 32vCPU/128GB ECS 上做 CPU 基准，必要时使用 GPU 机器 |
| 输出不稳定 | Markdown 标题层级可能仍需后处理 | 保留 `splitter.py` 规则作为兜底 |
| 许可与商用条件 | MinerU 基于 Apache 2.0 并带附加条件 | 内部研究可用；正式商用前需审查 license |

---

## 七、推荐集成路线

### 阶段一：离线评测，不改主流程

目标：验证 MinerU 是否真正改善 PDF 结构化。

工作内容：

1. 单独安装 MinerU；
2. 跑 S1/S2/S3 三份样本；
3. 记录耗时、输出 Markdown、JSON、表格数量；
4. 用同一套章节统计脚本计算章节数；
5. 与 LiteParse 基线对比。

### 阶段二：新增可选解析器

目标：让后端支持 `PARSER_ENGINE=mineru`。

改造点：

- 新增 `mineru_parser.py`；
- 修改 `pipeline.py` 选择解析器；
- DB 增加 `parser_engine`、`structured_markdown` 字段；
- 前端结果页增加“结构化 Markdown”展示。

### 阶段三：自动降级与增强

目标：生产可用。

策略：

```text
电子版 PDF / DOCX：LiteParse 优先
扫描件 / 文本为空 / 章节过度切分：MinerU fallback
表格密集型合同：允许用户手动选择 MinerU
```

### 阶段四：RAG/Agent 数据准备

目标：将 MinerU 输出用于 LlamaIndex / RAG。

```text
MinerU Markdown / JSON
  → 按标题层级分块
  → 建立向量索引
  → 支持合同问答、条款定位、风险追溯
```

---

## 八、与 LiteParse 的组合建议

不建议简单用 MinerU 替换 LiteParse，而是采用“轻重结合”：

| 文档类型 | 推荐解析器 | 原因 |
|----------|------------|------|
| 普通电子版 PDF | LiteParse | 极快，文本质量已达标 |
| Word 合同 | python-docx + LiteParse | 标题样式更可靠，成本低 |
| 扫描件 PDF | MinerU | 需要 OCR |
| 表格密集型合同 | MinerU | 表格结构更重要 |
| 复杂版面 PDF | MinerU | 阅读顺序与结构化能力更强 |
| 批量快速预处理 | LiteParse | 吞吐高、部署轻 |

最终架构建议：

```text
上传合同
  → 文档类型/质量检测
  → LiteParse 快速解析
  → 若解析异常或结构化质量差，则调用 MinerU
  → 输出统一 ParseResult
  → 章节切分 / LLM 分析 / RAG 问答
```

---

## 九、后续实测记录模板

后续安装 MinerU 后，可补充如下实测表：

| 样本 | 类型 | 模式 | 耗时 | 字符数 | Markdown 标题数 | 表格数 | 章节数 | 乱码 | 备注 |
|------|------|------|------|--------|----------------|--------|--------|------|------|
| S1 | PDF | pipeline/vlm | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | UICC 采购协议 |
| S2 | DOCX | pipeline/vlm | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | Word 版 |
| S3 | PDF | pipeline/vlm | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 物资采购通用合同 |

建议同时保存 MinerU 输出文件：

```text
eval/mineru/
  ├─ s1_uicc_pdf.md
  ├─ s1_uicc_pdf.json
  ├─ s2_uicc_docx.md
  ├─ s3_purchase_pdf.md
  └─ metrics.json
```

---

## 十、结论

1. MinerU 更适合作为**结构化增强解析器**，不是 LiteParse 的轻量替代品；
2. 当前 demo 的主要痛点是 PDF 章节过度切分，MinerU 的 Markdown/JSON、阅读顺序恢复、页眉页脚清理能力可能有明显帮助；
3. 由于 MinerU 模型和依赖较重，不建议直接塞进当前轻量离线包；建议单独做增强版或解析服务；
4. 最优策略是 **LiteParse 默认 + MinerU fallback**：普通电子版合同走 LiteParse，复杂/扫描/表格密集文档走 MinerU；
5. 在正式引入前，应先用当前 3 份真实合同样本做 MinerU 实测，重点比较章节数、目录误判、表格保留和解析耗时。

---

## 附录：参考资料

- MinerU GitHub：https://github.com/opendatalab/MinerU
- MinerU 官方文档：https://opendatalab.github.io/MinerU/
- MinerU 能力说明：支持 PDF、图片、DOCX、PPTX、XLSX；输出 Markdown / JSON；支持 OCR、表格 HTML、公式 LaTeX、版面可视化
- 当前项目基线文档：`Parser评测-LiteParse.md`
