# studio-orchestrator

通用“工作室模式持续推进”技能。

## 什么时候用

当任务不是一次性回答，而是需要在后台持续推进、分阶段执行、主动汇报时使用。

典型场景：
- 文档类：reviewer → 并单 → 改稿 → 复审 → 汇报
- 代码类：拆工 → 实现 → reviewer → 测试/回归 → 汇报
- 工程类：调查 → 执行 → 验证 → 下一步 → 汇报
- 用户明确说“启动工作室模式”“持续推进”“别等我催”“挂后台继续做”

## 核心原则

- 只要任务不处于“明确等待用户决策”，就继续推进。
- 主对话被新消息打断，不等于旧任务结束。
- 新任务插入时，旧任务进入后台跟踪，除非存在明确资源冲突或优先级冲突。
- 每个任务都必须可审计：当前阶段、下一步、最近推进时间、产物路径、日志路径。
- 只有在真正需要用户拍板时，才停下来问。

## 目录结构

- `state/tasks.json`：任务注册表
- `state/runner_state.json`：runner 心跳/轮次状态
- `scripts/studio_task.py`：任务注册/状态变更/查看 CLI
- `scripts/studio_runner.py`：最小持续推进 runner
- `scripts/studio_watch.py`：读取外部结果文件并映射回任务状态
- `scripts/studio_process_watch.py`：读取后台 session / process 输出并映射回任务状态
- `scripts/studio_decide.py`：根据真实日志信号决定下一步，而不是只按 phase 模板推进
- `scripts/studio_scheduler.py`：多任务调度，决定哪些任务本轮应活跃推进
- `scripts/studio_roles.py`：给文档/代码/工程任务自动分配工作室 AI 分工
- `scripts/studio_active_roles.py`：按当前 phase 切换当前活跃 AI
- `scripts/studio_feedback.py`：像 ROS2 action feedback 一样输出阶段性进度
- `scripts/studio_feedback_notify.py`：把阶段性进度主动发到消息层
- `scripts/studio_report.py`：筛出应该主动汇报的任务
- `scripts/studio_notify.py`：把可汇报任务真正发到消息层
- `scripts/studio_start.py`：统一入口，创建任务并交给 runner 首轮接管
- `examples/tasks.sample.json`：示例状态文件

## 最小工作流

1. 注册任务
2. 标注任务类型（doc/code/engineering/general）
3. 记录当前阶段、下一步、负责人、产物路径
4. 启动 runner，自动把任务往下一阶段推进
5. 每次推进后更新时间
6. 遇到阻塞时写明阻塞原因和所需决策

## 常用命令

注册任务：

```bash
python3 skills/studio-orchestrator/scripts/studio_task.py create \
  --title "Manuscript revision" \
  --type doc \
  --goal "合并 reviewer 意见并持续改稿直至可提交"
```

查看所有任务：

```bash
python3 skills/studio-orchestrator/scripts/studio_task.py list
```

推进任务状态：

```bash
python3 skills/studio-orchestrator/scripts/studio_task.py update <task_id> \
  --status in_progress \
  --phase revise \
  --next "继续修改 discussion section" \
  --owner main-agent
```

追加日志：

```bash
python3 skills/studio-orchestrator/scripts/studio_task.py log <task_id> "已取回 Qwen reviewer，开始并单"
```

执行一次 runner 推进：

```bash
python3 skills/studio-orchestrator/scripts/studio_runner.py tick --verbose
```

以 daemon 方式持续推进：

```bash
python3 skills/studio-orchestrator/scripts/studio_runner.py daemon --interval 60 --verbose
```

统一入口启动工作室任务：

```bash
python3 skills/studio-orchestrator/scripts/studio_start.py "Manuscript revision" doc "合并 reviewer 意见并持续改稿"
```

带 watch 文件 / process 日志 和主动汇报目标启动：

```bash
python3 skills/studio-orchestrator/scripts/studio_start.py "Manuscript revision" doc "合并 reviewer 意见并持续改稿" \
  --watch-file /tmp/reviewer_output.txt \
  --watch-process-log /tmp/reviewer_process.log \
  --notify-target 8783735951 --notify-channel telegram
```

读取外部结果并映射任务状态：

```bash
python3 skills/studio-orchestrator/scripts/studio_watch.py ingest <task_id> /path/to/reviewer_output.txt \
  --on-done-phase review_merge \
  --on-done-next "开始并单 reviewer 意见"
```

读取后台 session / process 导出的日志并映射任务状态：

```bash
python3 skills/studio-orchestrator/scripts/studio_process_watch.py <task_id> --log-file /tmp/reviewer.log --source-key reviewer-1 \
  --on-done-phase review_merge \
  --on-done-next "开始并单 reviewer 意见"
```

根据真实日志信号做决策：

```bash
python3 skills/studio-orchestrator/scripts/studio_decide.py <task_id>
```

筛出应该主动汇报的任务：

```bash
python3 skills/studio-orchestrator/scripts/studio_report.py
```

真正发出主动汇报：

```bash
python3 skills/studio-orchestrator/scripts/studio_notify.py --target 8783735951 --channel telegram
```

标记阻塞：

```bash
python3 skills/studio-orchestrator/scripts/studio_task.py update <task_id> \
  --status blocked \
  --blocker "需要用户决定是否保留激进结论表述"
```

## 状态约定

- `queued`：已登记，未开始
- `in_progress`：正在推进
- `waiting_reviewer`：等待 reviewer / 子代理结果
- `waiting_user`：等待用户决策
- `blocked`：外部阻塞
- `done`：已完成
- `cancelled`：已取消

## 阶段建议

### 文档类
- intake
- review_collect
- review_merge
- revise
- polish
- final_check
- report

### 代码类
- intake
- plan
- implement
- review
- test
- fixup
- report

### 工程类
- intake
- investigate
- execute
- verify
- iterate
- report

## 备注

这是第一版可运行 orchestrator。它现在已经能做这些事：
- 任务登记与状态追踪
- scheduler 选出本轮活跃任务
- runner 持续 tick
- watch 文件 / process 日志结果回流
- decide 按真实日志信号修正状态
- progress feedback 像 action feedback 一样阶段回报
- notify 把 report 发到消息层

后续还要继续接：
- 自动轮询真实 OpenClaw 子进程/后台 session
- reviewer / agent dispatch 适配器
- 更细的阶段模板与任务类型插件化
- 更强的资源冲突与依赖关系仲裁
