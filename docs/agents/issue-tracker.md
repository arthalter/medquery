# Issue Tracker：GitHub

本仓库的需求、规格与实施任务使用 GitHub Issues 管理，目标仓库为 `arthalter/medquery`。仓库创建并连接 remote 后，统一使用 `gh` CLI 操作。

## 常用操作

- 创建：`gh issue create --title "..." --body "..."`
- 查看：`gh issue view <number> --comments`
- 列表：`gh issue list --state open --json number,title,body,labels,comments`
- 评论：`gh issue comment <number> --body "..."`
- 添加标签：`gh issue edit <number> --add-label "..."`
- 移除标签：`gh issue edit <number> --remove-label "..."`
- 关闭：`gh issue close <number> --comment "..."`

多行正文使用 heredoc，读取 Issue 时同时获取评论与标签。

## Pull Request 边界

**PR 不作为需求分流入口。** 外部 PR 不进入 Issue 的 triage 状态机。

GitHub 的 Issue 与 PR 共用编号空间。遇到单独的 `#42` 时，先运行 `gh pr view 42`，失败后再运行 `gh issue view 42`。

## 技能用语

- “发布到 Issue Tracker”表示创建一个 GitHub Issue。
- “获取相关 Ticket”表示读取对应 Issue、评论与标签。

## Wayfinder 约定

- **Map**：一个带 `wayfinder:map` 标签的父 Issue，正文保存 Notes、Decisions-so-far 与 Fog。
- **子 Ticket**：优先使用 GitHub Sub-issues 关联；不可用时，在父 Issue 的任务列表中链接，并在子 Issue 顶部写明 `Part of #<map>`。
- **类型标签**：使用 `wayfinder:research`、`wayfinder:prototype`、`wayfinder:grilling` 或 `wayfinder:task`。
- **阻塞关系**：优先使用 GitHub 原生 Issue dependencies；不可用时，在正文顶部写 `Blocked by: #<n>`。
- **领取任务**：`gh issue edit <n> --add-assignee @me`。
- **完成任务**：先评论结论，再关闭 Issue，并把结论链接加入父 Map 的 Decisions-so-far。
