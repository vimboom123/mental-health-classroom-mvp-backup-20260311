# 助教风险前端配置字段表与状态配置 JSON 草案（V1）

项目名：数智赋能示范课堂｜大学生心理健康教育网站

## 一、这一轮目标
把上一轮的组件级状态表继续往前端实现层推进，转成更接近配置驱动的形式。

目标是让前端可以不靠大量 if/else 硬编码，而是基于一份配置表完成：
- 风险等级切换
- 组件显隐
- 推荐动作优先级调整
- 风险帮助页联动

---

## 二、建议的核心状态字段

### 1. 顶层状态字段
建议前端至少维护以下状态：

```json
{
  "riskLevel": "low",
  "uiMode": "learning",
  "tutorAvatarState": "idle",
  "showRiskHelpBanner": false,
  "riskHelpBannerMode": "subtle",
  "showQuickPrompts": true,
  "quickPromptsMode": "normal",
  "showModuleRecommendations": true,
  "moduleRecommendationPriority": "primary",
  "showPracticeRecommendations": true,
  "practiceRecommendationPriority": "primary",
  "showResourceRecommendations": true,
  "resourceRecommendationMode": "normal",
  "showRealSupportCard": false,
  "realSupportPriority": "hidden",
  "showEmergencyNotice": false,
  "chatMode": "normal"
}
```

---

### 2. 字段解释
- `riskLevel`：low / medium / high
- `uiMode`：learning / support / safety
- `tutorAvatarState`：idle / listening / speaking / risk-alert-soft / risk-alert
- `showRiskHelpBanner`：是否显示风险帮助条
- `riskHelpBannerMode`：subtle / emphasized / critical
- `showQuickPrompts`：是否显示快捷问题
- `quickPromptsMode`：normal / collapsed / hidden
- `moduleRecommendationPriority`：primary / secondary / hidden
- `practiceRecommendationPriority`：primary / secondary / hidden
- `resourceRecommendationMode`：normal / support-only / hidden
- `realSupportPriority`：hidden / secondary / primary
- `chatMode`：normal / guarded / safety-only

---

## 三、风险等级 → 状态配置 JSON 草案

### 1. low 配置
```json
{
  "riskLevel": "low",
  "uiMode": "learning",
  "tutorAvatarState": "speaking",
  "showRiskHelpBanner": true,
  "riskHelpBannerMode": "subtle",
  "showQuickPrompts": true,
  "quickPromptsMode": "normal",
  "showModuleRecommendations": true,
  "moduleRecommendationPriority": "primary",
  "showPracticeRecommendations": true,
  "practiceRecommendationPriority": "primary",
  "showResourceRecommendations": true,
  "resourceRecommendationMode": "normal",
  "showRealSupportCard": false,
  "realSupportPriority": "hidden",
  "showEmergencyNotice": false,
  "chatMode": "normal"
}
```

### 2. medium 配置
```json
{
  "riskLevel": "medium",
  "uiMode": "support",
  "tutorAvatarState": "risk-alert-soft",
  "showRiskHelpBanner": true,
  "riskHelpBannerMode": "emphasized",
  "showQuickPrompts": true,
  "quickPromptsMode": "collapsed",
  "showModuleRecommendations": true,
  "moduleRecommendationPriority": "secondary",
  "showPracticeRecommendations": true,
  "practiceRecommendationPriority": "secondary",
  "showResourceRecommendations": true,
  "resourceRecommendationMode": "support-only",
  "showRealSupportCard": true,
  "realSupportPriority": "primary",
  "showEmergencyNotice": false,
  "chatMode": "guarded"
}
```

### 3. high 配置
```json
{
  "riskLevel": "high",
  "uiMode": "safety",
  "tutorAvatarState": "risk-alert",
  "showRiskHelpBanner": true,
  "riskHelpBannerMode": "critical",
  "showQuickPrompts": false,
  "quickPromptsMode": "hidden",
  "showModuleRecommendations": false,
  "moduleRecommendationPriority": "hidden",
  "showPracticeRecommendations": false,
  "practiceRecommendationPriority": "hidden",
  "showResourceRecommendations": true,
  "resourceRecommendationMode": "support-only",
  "showRealSupportCard": true,
  "realSupportPriority": "primary",
  "showEmergencyNotice": true,
  "chatMode": "safety-only"
}
```

---

## 四、推荐动作配置字段建议

除了 UI 状态，推荐动作也建议走配置，而不是散落在页面逻辑里。

### 推荐动作结构建议
```json
{
  "recommendedActions": [
    {
      "id": "open-risk-help",
      "type": "risk_help",
      "label": "先看风险帮助",
      "priority": 1,
      "visible": true
    },
    {
      "id": "contact-real-support",
      "type": "real_support",
      "label": "联系现实里能接住你的人",
      "priority": 2,
      "visible": true
    },
    {
      "id": "go-study-module",
      "type": "module",
      "label": "进入学习心理模块",
      "priority": 9,
      "visible": false
    }
  ]
}
```

### 规则建议
- low：模块 / 练习动作放前
- medium：风险帮助与现实支持动作置前
- high：只保留安全相关动作

---

## 五、配置驱动渲染建议

前端渲染层可以先按这个思路：

```text
1. 根据助教输出判断 riskLevel
2. 从 riskConfigMap 里取对应配置
3. 把配置映射到页面组件
4. 再根据 recommendedActionsConfig 重新排序动作
```

这样有几个好处：
- 后续改风险策略，不用改大量页面逻辑
- 可以快速 A/B 调整
- 可以更方便接模型输出和前端状态

---

## 六、一个更完整的配置 map 示例

```json
{
  "riskConfigMap": {
    "low": {
      "uiMode": "learning",
      "tutorAvatarState": "speaking",
      "riskHelpBannerMode": "subtle",
      "quickPromptsMode": "normal",
      "moduleRecommendationPriority": "primary",
      "practiceRecommendationPriority": "primary",
      "resourceRecommendationMode": "normal",
      "realSupportPriority": "hidden",
      "chatMode": "normal"
    },
    "medium": {
      "uiMode": "support",
      "tutorAvatarState": "risk-alert-soft",
      "riskHelpBannerMode": "emphasized",
      "quickPromptsMode": "collapsed",
      "moduleRecommendationPriority": "secondary",
      "practiceRecommendationPriority": "secondary",
      "resourceRecommendationMode": "support-only",
      "realSupportPriority": "primary",
      "chatMode": "guarded"
    },
    "high": {
      "uiMode": "safety",
      "tutorAvatarState": "risk-alert",
      "riskHelpBannerMode": "critical",
      "quickPromptsMode": "hidden",
      "moduleRecommendationPriority": "hidden",
      "practiceRecommendationPriority": "hidden",
      "resourceRecommendationMode": "support-only",
      "realSupportPriority": "primary",
      "chatMode": "safety-only"
    }
  }
}
```

---

## 七、验收关注点

### 1. 配置不能只改视觉，不改动作顺序
如果 high 风险只是颜色变了，但推荐动作还是普通模块优先，那不算通过。

### 2. medium 和 high 不能混成一档
如果两个等级在页面上看起来几乎一样，说明策略不够清楚。

### 3. high 必须明显进入安全模式
不仅是文案更短，而是页面本身的内容优先级也要变。

---

## 八、当前阶段结论
到这里，助教风险这条线已经推进到配置驱动层：
1. 风险规则
2. 测试库
3. 对话样例
4. 验收表
5. UI 映射
6. 组件级状态表
7. 状态配置 JSON 草案

下一轮如果继续推进，最自然的是：
- 设计助教页三种风险态的原型说明
- 把配置字段进一步转成前端 TypeScript 类型草案
- 把风险帮助页 / 助教页联动整理成事件流说明
