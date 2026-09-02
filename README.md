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

后续 Ticket 会在该离线入口上加入说明书入库能力，并把 SSE 骨架接入真实问答链路。
