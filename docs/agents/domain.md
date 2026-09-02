# 领域文档

本文件规定工程技能在探索代码库时如何读取领域术语与架构决策。

## 探索前读取

- 根目录 `CONTEXT.md`：当前项目的领域词汇表。
- 根目录 `CONTEXT-MAP.md`：仅在项目未来拆成多个上下文时使用。
- `docs/adr/`：与当前改动相关的架构决策记录。

文件不存在时直接继续，不把缺失本身视为问题。`domain-modeling`、`grill-with-docs` 或 `improve-codebase-architecture` 会在真正形成术语或决策时按需创建。

## 当前布局

本项目采用 single-context：

```text
/
├── CONTEXT.md
├── docs/adr/
└── app/
```

## 术语规则

- Issue 标题、规格、测试名称与代码命名使用 `CONTEXT.md` 中确定的术语。
- 已定义概念不随意更换同义词。
- 遇到尚未定义的重要概念时，交给 `domain-modeling` 澄清并记录。

## ADR 冲突

当新方案与现有 ADR 冲突时，明确指出冲突及重新讨论的理由，不静默覆盖既有决策。
