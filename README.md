# 智药问点

药品说明书智能问答 Demo。当前仓库包含医疗科技风格前端，以及用于承载 FastAPI、SSE 与 Milvus Lite 的单容器应用骨架。

## 本地配置

项目从根目录 `.env` 读取配置。该文件只保存在本机，不会进入 Git；百炼与 Grok 的真实凭据由本地使用者填写。

## Docker 启动

```bash
docker compose up --build
```

启动后访问 `http://localhost:8000`。

同一镜像也提供离线 Milvus 初始化入口：

```bash
docker compose run --rm app python -m medquery init-db
```

采集完成且百炼配置已填入 `.env` 后，使用同一镜像执行一次完整入库：

```bash
docker compose run --rm app python -m medquery ingest
```

该命令严格从 `data/processed/drugs.json` 读取药品注册表，依次完成 TXT 解析、400 字符完整句子切片、`text-embedding-v4` Dense Embedding 和 Milvus Lite FLAT 写入。正常应用启动只加载已经存在的向量库，不重复入库。

在线检索能力由 `InstructionRetrievalService.search()` 提供：仅以确认后的 `drug_name` 过滤，执行 Dense Top 10，再交给 `qwen3-rerank` 返回 Top 3。`DrugInstructionSearchTool` 是后续 Agent 使用的唯一知识库 Tool 接口。
