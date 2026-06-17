# Contract Review AI

> 基于 AI 的中文合同审查与知识库增强平台，支持合同风险分析、OnlyOffice 在线审阅、法律知识检索与智能问答。

## ✨ Features

* 📄 合同上传与 AI 预分析

  * 支持 DOCX / PDF 上传
  * 自动识别合同类型、主体信息与审查范围

* ⚖️ 合同风险审查

  * 输出风险点、修改建议、相关法条与审查理由
  * 支持关联裁判文书增强分析

* 📝 OnlyOffice 在线协同编辑

  * 文档内精准定位条款
  * 添加批注与修改建议
  * 一键采纳建议并高亮变更内容

* 📚 法律知识库

  * 支持法律法规、裁判文书、审查规则导入
  * 支持向量检索、删除与模板下载

* 🤖 智能问答

  * SSE 流式输出
  * 携带上下文会话历史
  * 支持知识库检索 + 受控联网搜索

* 🧠 向量检索与 AI 能力

  * Embedding / Rerank
  * Milvus 向量数据库
  * OpenAI Compatible API

* 🐳 Docker 一键部署

  * PostgreSQL
  * Milvus
  * MinIO
  * OnlyOffice

---

## 🖼️ Demo

| 首页             | 合同分析           |
| -------------- | -------------- |
| ![](img/1.png) | ![](img/2.png) |

| 风险审查           | 修改建议           |
| -------------- | -------------- |
| ![](img/3.png) | ![](img/4.png) |

| 知识库            | 智能问答           |
| -------------- | -------------- |
| ![](img/5.png) | ![](img/6.png) |

更多演示图：

![](img/7.png)

![](img/8.png)

![](img/9.png)

![](img/10.png)

![](img/11.png)

---

## 🏗️ Tech Stack

### Frontend

* Vue 3
* Vite
* Element Plus
* Tailwind CSS
* OnlyOffice Document Editor

### Backend

* Node.js
* Express
* Knex
* PostgreSQL
* Socket.IO

### AI / RAG

* OpenAI Compatible Chat API
* Embedding
* Rerank
* Milvus
* 法律 Markdown 解析
* 裁判文书 JSON 解析

### Infrastructure

* Docker Compose
* PostgreSQL
* Milvus
* MinIO
* etcd
* OnlyOffice

---

## 📁 Project Structure

```text
.
├── backend/
│   ├── data/              # 法律法规、裁判文书、模板
│   ├── routes/            # API 路由
│   ├── services/          # AI / 向量库 / 检索服务
│   └── uploads/           # 上传目录（已忽略）
│
├── frontend/
│   ├── src/               # Vue 源码
│   └── dist/              # 构建产物（已忽略）
│
├── data/
│   ├── postgres/          # PostgreSQL 数据目录
│   ├── milvus/            # Milvus / MinIO / etcd
│   └── onlyoffice/        # OnlyOffice 数据目录
│
├── docker-compose.yml
└── README.md
```

---

## 🚀 Quick Start

### 1. Clone Repository
