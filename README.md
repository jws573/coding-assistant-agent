# 🤖 智能编程助手 Agent

一个基于 LangChain 1.x + LangGraph + 阿里百炼 + Gradio 的智能编程助手，支持安全代码执行、本地知识库检索（RAG）、多轮对话与免费额度管理。

[![Hugging Face Space](https://img.shields.io/badge/HuggingFace-Space-yellow)](https://huggingface.co/spaces/jieweisun/coding-agent)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## ✨ 功能特性

- 🔒 **安全代码执行**：通过子进程+临时文件+超时机制隔离执行 Python 代码
- 📚 **本地知识库检索（RAG）**：基于 Chroma 向量库 + 阿里百炼 Embedding 检索私有文档
- 💬 **多轮对话记忆**：基于 LangGraph Checkpointer 自动维护会话上下文
- 🔁 **工具自动重试**：代码执行出错时，Agent 自动分析并重试（最多3次）
- 🎫 **免费额度管理**：基于 IP 的终身10次免费试用，超出后可填入自己的 API Key
- 🌐 **Web 界面**：Gradio 构建的聊天界面，支持公网访问（Hugging Face Spaces）

## 📸 效果演示

> 公网访问地址：https://jieweisun-coding-agent.hf.space  
> （如遇访问缓慢，可本地克隆运行）

## 🛠️ 技术栈

| 类别 | 技术 |
|------|------|
| Agent 框架 | LangChain 1.x + LangGraph |
| 大模型 | 阿里百炼 qwen-max |
| 向量数据库 | Chroma |
| Embedding | 阿里百炼 text-embedding-v3 |
| 前端界面 | Gradio 6.x |
| 部署平台 | Hugging Face Spaces |

## 📁 项目结构
├── app.py # 主程序（Gradio 界面 + Agent 逻辑）
├── requirements.txt # 依赖列表
├── knowledge/ # 知识库源文件（.txt）
├── chromadb/ # 向量库持久化目录（自动生成）
├── total_usage.json # 免费额度记录（自动生成）
└── README.md

## 📝 常见问题与解决方案

### 环境与依赖
- **pip 无法识别** → 使用 `python -m pip`
- **LangChain 导入错误** → 改用新版 API `create_agent`
- **langchain_classic 不存在** → 使用 `langchain`、`langchain_openai` 等官方包

### 工具开发
- **exec() 安全风险** → 改用 subprocess + 临时文件 + 超时
- **模型不调用工具** → 设置 `tool_choice="auto"` 并强化提示词
- **工具返回错误后不重试** → 强化系统提示词，明确要求重试3次

### RAG 与向量库
- **阿里百炼 Embedding 400** → 改用 `text-embedding-v3` 并确认 `base_url`

### Gradio 与部署
- **多轮对话丢失记忆** → 适配 Gradio 6.x 的 OpenAI 风格 `history`
- **Hugging Face 不识别入口** → 主程序必须命名为 `app.py`，放在根目录
- **API Key 未注入** → 在 Space 的 `Repository secrets` 中添加 `DASHSCOPE_API_KEY`
- **公网链接生成失败** → 部署到Huggingface space生成公网链接

## 🌐 部署到 Hugging Face Spaces

公网访问地址：https://jieweisun-coding-agent.hf.space

### 部署要点
1. 主文件必须命名为 `app.py`
2. 依赖写入 `requirements.txt`
3. API Key 通过 `Repository secrets` 配置
4. 端口强制设为 `7860`
5. 文件需放在根目录（不能有子文件夹）
