# USER.md - About Your Human

_Learn about the person you're helping. Update this as you go._

- **Name:**
- **What to call them:**
- **Pronouns:** _(optional)_
- **Timezone:**
- **Notes:**
  - 用户偏好：当他询问“我的手机地址/位置”时，默认返回尽量具体的位置描述（优先到街道/小区/地标），并附坐标。
  - 门店/附近推荐默认主数据源使用高德（AMAP）；不再使用大众点评抓取链路。
  - 当能力缺少时，先主动提议可用 skill；仅在用户明确同意后再安装（不自动安装）。
  - 多智能体组织当前固定为：Codex=后端开发，Gemini=前端/表达层开发，Claude Code=代码审核，Oracle=全局复盘；主智能体兼任 PM + 测试验收 + 产品文档 + 最终汇报。
  - Gemini / Oracle 在本机调用时需走 wrapper：`scripts/gemini22.sh`、`scripts/oracle22.sh`（或 `scripts/oracle-browser-auto.sh`）；不要直接裸调 CLI，避免 PATH 缺少 `/usr/sbin` 导致 `sysctl ENOENT`。
  - 如果用户临时插入新任务，而旧任务未完成：默认不断开旧任务；主智能体应将旧任务转为后台持续跟踪，并先响应新任务，随后在定时汇报中同步两者进展；若存在资源冲突或优先级冲突，应主动提醒用户拍板。

## Context

_(What do they care about? What projects are they working on? What annoys them? What makes them laugh? Build this over time.)_

---

The more you know, the better you can help. But remember — you're learning about a person, not building a dossier. Respect the difference.
