# 智药问点

面向现场展示的药品说明书智能问答 Demo。用户从首页自然提问，确认药品后即可获得 Grok 生成的中文答案和真实检索到的说明书原文证据。

## 本地配置

项目从根目录 `.env` 读取配置。该文件只保存在本机，不进入 Git。首次运行前填写以下四项：

- `BAILIAN_WORKSPACE_ID`
- `BAILIAN_API_KEY`
- `GROK_BASE_URL`
- `GROK_API_KEY`

其余 Demo 参数已经预填。

## 准备本地说明书

仓库保存候选来源和采集程序，说明书全文只写入 Git 忽略的本地 `data/` 目录：

```bash
python -m scripts.corpus.collect
```

已有本地说明书时无需重复采集。

## 一次性入库

使用最终应用镜像完成 TXT 解析、400 字符完整句子切片、`text-embedding-v4` Dense Embedding、Milvus Lite FLAT 写入和持久化：

```bash
docker compose run --build --rm app python -m medquery ingest
```

入库严格从 `data/processed/drugs.json` 读取药品注册表，只按 `drug_name` 过滤 Dense Top 10，再由 `qwen3-rerank` 返回 Top 3。

## 启动 Demo

```bash
docker compose up
```

打开 `http://localhost:8000`。页面只呈现问题、药品确认、流式答案和证据正文，不展示分数、章节、来源或内部 Agent 过程。

后端由 FastAPI、LangChain `create_agent` 和 Milvus Lite 组成。药名识别与问题改写分别调用 Grok；Agent 自主串行调用唯一说明书检索 Tool，并将实际 Tool 证据通过 SSE 交给前端。
