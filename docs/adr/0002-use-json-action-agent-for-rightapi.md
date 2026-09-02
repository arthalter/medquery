# 为 RightAPI 使用 JSON Action Agent

RightAPI 的 Grok 渠道支持普通 Chat Completions 与 JSON 输出，但真实请求会拒绝 OpenAI 标准 `tools` 字段。项目因此保留“模型自主选择、单工具、串行循环”的 Agent 语义，改用 `search`/`final` JSON Action 驱动检索，而不再通过 LangChain `create_agent` 发送原生 Tool Calling 请求。
