# studio-orchestrator 最小验证计划

目标：先把产品线打稳，再回到真实生产任务。

## 三类最小测试任务

### 1. 文档类
- 输入：一份固定 markdown 文稿
- 目标：按 reviewer checklist 改指定 3 段
- 验证：
  - 文件 diff 存在
  - 产物路径记录
  - 最终修改摘要存在
  - completion_evidence 结构化字段完整

### 2. 代码类
- 输入：一个小 repo + 明确 bug
- 目标：修 bug 并通过测试
- 验证：
  - git diff 存在
  - 测试命令通过
  - review dispatch 完成
  - completion_evidence 结构化字段完整

### 3. 工程类
- 输入：一个配置/脚本化检查任务
- 目标：修配置并生成验证结果
- 验证：
  - 产物文件存在
  - verify 阶段有日志证据
  - orchestration done
  - completion_evidence 结构化字段完整

## 当前产品线原则
- 不把真实生产任务当唯一回归测试样本。
- 先用低歧义、可验证的小任务打磨执行链。
- 产物变化必须进入状态机；没有产物，不算推进。
- 流程完成不等于内容完成；必须通过 acceptance gate。
