# 助教风险组件级状态表（V1）

项目名：数智赋能示范课堂｜大学生心理健康教育网站

## 一、这一轮目标
把上一轮“风险等级 → 前端反馈样式与交互映射”继续往实现层推进一层：
直接拆到组件级，明确每个组件在 low / medium / high 风险等级下：
- 是否显示
- 是否弱化
- 是否置顶
- 是否禁用
- 文案是否切换

这份文档的目标是让前端和产品在实现时，不再只靠口头理解“高风险时要收住”，而是有一张可执行状态表。

---

## 二、状态等级说明

### low
普通学习型对话状态。

### medium
明显超出普通压力，进入风险帮助前置状态。

### high
安全优先状态，普通学习型体验退到次要位置或直接隐藏。

---

## 三、组件级状态表

## 1. `TutorAvatarPanel`

### low
- 显示：是
- 状态：`idle / listening / speaking`
- 视觉：正常
- 文案：学习型陪伴文案

### medium
- 显示：是
- 状态：`risk-alert-soft`
- 视觉：收敛，不夸张
- 文案：缩短，提醒现实支持优先

### high
- 显示：是
- 状态：`risk-alert`
- 视觉：明显进入安全模式
- 文案：安全优先，不再走普通学习型语气

---

## 2. `TutorChatPanel`

### low
- 显示：是
- 输入：可用
- 作用：正常学习型问答

### medium
- 显示：是
- 输入：可用
- 作用：保留，但引导风险帮助与现实支持优先

### high
- 显示：是
- 输入：可用，但不鼓励继续长对话
- 作用：用于最小安全引导，不再承载普通学习型问答

---

## 3. `QuickPromptChips`

### low
- 显示：是
- 状态：正常
- 内容：模块相关快捷问题

### medium
- 显示：是
- 状态：弱化 / 可折叠
- 内容：减少普通模块提问主导感

### high
- 显示：否
- 原因：高风险下不应继续鼓励普通问题入口

---

## 4. `RecommendedActionPanel`

### low
- 显示：是
- 排序：模块 > 练习 > 方法卡 > 风险帮助

### medium
- 显示：是
- 排序：风险帮助 > 现实支持 > 一个最小继续动作 > 模块/练习
- 普通模块：保留但降级

### high
- 显示：是
- 排序：风险帮助 > 现实支持 > 联系可信任的人
- 普通模块：隐藏
- 练习：隐藏
- 方法卡：隐藏

---

## 5. `RiskHelpBanner`

### low
- 显示：是
- 位置：页面中下部 / 弱提示
- 样式：轻提示

### medium
- 显示：是
- 位置：聊天区上方或推荐动作上方
- 样式：明显提示，但不过度惊吓

### high
- 显示：是
- 位置：页面顶部置顶
- 样式：强提示
- 行为：优先级高于普通内容块

---

## 6. `ModuleRecommendationCards`

### low
- 显示：是
- 作用：主推荐内容

### medium
- 显示：是
- 状态：降级
- 作用：不再占主位

### high
- 显示：否
- 原因：高风险时不能优先引导普通模块学习

---

## 7. `PracticeRecommendationCards`

### low
- 显示：是
- 作用：主推荐内容之一

### medium
- 显示：是
- 状态：弱化
- 作用：可留作次级入口

### high
- 显示：否
- 原因：高风险时不应继续主推练习和情景模拟

---

## 8. `ResourceRecommendationCards`

### low
- 显示：是
- 作用：正常补充资源

### medium
- 显示：是
- 作用：可保留，但优先级低于风险帮助与现实支持

### high
- 显示：部分保留
- 作用：只保留现实支持类资源
- 普通方法卡：隐藏

---

## 9. `RealSupportActionCard`

### low
- 显示：否或很弱

### medium
- 显示：是
- 位置：推荐动作前列
- 内容：联系朋友 / 辅导员 / 校心理中心

### high
- 显示：是
- 位置：页面顶部主区
- 内容：优先动作之一

---

## 10. `EmergencyNoticeCard`

### low
- 显示：否

### medium
- 显示：否或按需折叠

### high
- 显示：是
- 内容：如果存在明确危险，优先联系现实紧急支持

---

## 四、组件状态总表（简化版）

| 组件 | low | medium | high |
|---|---|---|---|
| TutorAvatarPanel | 正常 | soft risk | strong risk |
| TutorChatPanel | 正常 | 保留 | 保留但仅安全引导 |
| QuickPromptChips | 显示 | 弱化/折叠 | 隐藏 |
| RecommendedActionPanel | 模块/练习优先 | 风险帮助前置 | 仅安全相关动作 |
| RiskHelpBanner | 弱提示 | 明显提示 | 顶部强提示 |
| ModuleRecommendationCards | 主推荐 | 降级 | 隐藏 |
| PracticeRecommendationCards | 主推荐 | 弱化 | 隐藏 |
| ResourceRecommendationCards | 正常 | 降级 | 仅保留现实支持类 |
| RealSupportActionCard | 弱/无 | 前置 | 主位 |
| EmergencyNoticeCard | 无 | 无/折叠 | 显示 |

---

## 五、一个更可实现的前端状态对象

前端可以先按下面这类结构做：

```json
{
  "riskLevel": "medium",
  "uiState": {
    "avatarState": "risk-alert-soft",
    "showQuickPrompts": true,
    "quickPromptsMode": "collapsed",
    "showModuleRecommendations": true,
    "moduleRecommendationsPriority": "secondary",
    "showPracticeRecommendations": true,
    "practiceRecommendationsPriority": "secondary",
    "showRiskHelpBanner": true,
    "riskHelpBannerMode": "emphasized",
    "showRealSupportCard": true,
    "showEmergencyNotice": false
  }
}
```

这样前端拿到风险等级后，不必自己二次推理整套显隐逻辑。

---

## 六、验收要点

### 1. 不只测文本，要测组件显隐
如果 prompt 已经判成高风险，但页面还在主推模块卡片，那也算没通过。

### 2. 高风险下必须出现安全优先感
不是换一句更温柔的话就算切模式，页面结构本身也要收住。

### 3. 中风险不要“一刀切”成高风险页面
中风险仍保留一部分正常交互，但风险帮助和现实支持必须前置。

---

## 七、当前阶段结论
到这里，助教风险这条线已经从规则层一路推进到了组件层：
1. 风险规则
2. 风险示例对话
3. Prompt 验收表
4. 边缘样本库
5. 风险 UI 映射
6. 组件级状态表

下一轮如果继续推进，最自然的是：
- 把组件状态表转成前端配置字段表
- 设计高 / 中 / 低风险三种页面原型说明
- 把这套状态和助教页 / 风险帮助页联动到更细的交互稿里
