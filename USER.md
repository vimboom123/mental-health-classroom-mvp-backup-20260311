# USER.md - About Your Human

_Learn about the person you're helping. Update this as you go._

- **Name:**
- **What to call them:**
- **Pronouns:** _(optional)_
- **Timezone:**
- **Notes:**
  - 用户偏好：当他询问“我的手机地址/位置/当前位置”时，默认直接调用现成的 Find My skill / 已有会话查询设备 **leeee（iPhone 15 Pro）**；不要重复索要 Apple ID 或让用户重走配置流程。默认返回尽量具体的位置描述（优先到街道/小区/地标），并附坐标。
  - 门店/附近推荐默认主数据源使用高德（AMAP）；不再使用大众点评抓取链路。
  - 当能力缺少时，先主动提议可用 skill；仅在用户明确同意后再安装（不自动安装）。
  - 以后不再把该机制称作“多 AI 协同”，统一称为“工作室”。按正规工作室 / 小公司的标准运行，不能敷衍。
  - 工作室当前固定分工为：Codex=后端开发，Gemini=前端/表达层开发，Claude Code=代码审核，Oracle=全局复盘，Qwen（qwen-plus）=中文文档/中文润色/总结归纳/本土化判断第二意见；主智能体兼任工作室负责人（PM）+ 测试验收 + 产品文档 + 最终汇报。
  - 只要启用工作室模式，默认必须先发一条开工状态：说明已启动、参与模型/分工、任务目标、交付标准、预计下一次汇报时间；不能闷头跑不报备。
  - 工作室模式下默认需要更正规：有任务拆解、角色分工、阶段汇报、风险提示、审核把关、验收结论，不按“临时串几个模型”那种方式糊弄。
  - Gemini / Oracle 在本机调用时需走 wrapper：`scripts/gemini22.sh`、`scripts/oracle22.sh`（或 `scripts/oracle-browser-auto.sh`）；不要直接裸调 CLI，避免 PATH 缺少 `/usr/sbin` 导致 `sysctl ENOENT`。
  - 如果用户临时插入新任务，而旧任务未完成：默认不断开旧任务；主智能体应将旧任务转为后台持续跟踪，并先响应新任务，随后在定时汇报中同步两者进展；若存在资源冲突或优先级冲突，应主动提醒用户拍板。
  - 多智能体协同默认尽量按 Notion 策略执行，但保持动态灵活：代码类默认 Codex=实现、Gemini=前端/表达层、Claude Code=审核、Oracle=全局复盘、主智能体=PM/验收/汇报；文档类按任务主要矛盾动态分工（结构/论证偏 Codex 或 Claude，表达/润色偏 Gemini，全局第二视角偏 Oracle），若临时偏离默认分工，需在汇报中说明原因与补位情况。
  - Oracle reviewer 默认走 `scripts/oracle-browser-auto.sh`；首轮等待可放宽到 2 分钟，超时不阻塞主流程，晚到结果仍需纳入参考。
  - 已接入千问（阿里云 DashScope 兼容接口），当前确认可用默认模型为 `qwen-plus`；优先用于中文文档、中文润色、总结归纳，以及作为中文任务的额外第二意见 reviewer。
  - 涉及中国本土化判断的任务（如吃喝玩乐、本地平台语境、中文网络梗、本土表达习惯、国内生活方式/消费决策）时，默认把千问作为参考意见源之一，再与其他模型或数据源交叉判断。

## Context

_(What do they care about? What projects are they working on? What annoys them? What makes them laugh? Build this over time.)_

---

The more you know, the better you can help. But remember — you're learning about a person, not building a dossier. Respect the difference.
