# 网站前端组件拆分建议（V1）

项目名：数智赋能示范课堂｜大学生心理健康教育网站

## 一、这一轮目标
基于现有页面结构、模块内容和助教逻辑，把网站第一版拆成前端更容易实现的组件层级。

目标不是写技术栈代码，而是先把：
- 页面由哪些区块组成
- 哪些区块可以复用
- 哪些组件要优先做
- 助教、模块、练习、风险帮助之间怎么连

讲清楚。

---

## 二、第一版页面级拆分

### 1. 首页
建议拆成：
- `TopNav`
- `HeroSection`
- `TutorAvatarHeroCard`
- `PriorityModuleGrid`
- `PracticeEntryGrid`
- `TutorEntrySection`
- `RiskHelpBanner`
- `Footer`

### 2. 模块总览页
建议拆成：
- `TopNav`
- `PageHeader`
- `ModuleCardGrid`
- `TutorRouteCard`
- `Footer`

### 3. 单模块详情页
建议拆成：
- `TopNav`
- `ModuleHero`
- `ProblemListSection`
- `KeyInsightCards`
- `MisunderstandingList`
- `ActionMethodCards`
- `PracticeEntrySection`
- `TutorPromptSection`
- `RelatedResourceSection`
- `RiskHelpBanner`
- `Footer`

### 4. 智能助教页
建议拆成：
- `TopNav`
- `TutorPageHeader`
- `TutorAvatarPanel`
- `TutorChatPanel`
- `QuickPromptChips`
- `RecommendedActionPanel`
- `RiskHelpBanner`
- `Footer`

### 5. 情景模拟页
建议拆成：
- `TopNav`
- `ScenarioHero`
- `ScenarioContextCard`
- `ScenarioGoalCard`
- `ScenarioInteractionPanel`
- `FeedbackPanel`
- `ReflectionQuestionPanel`
- `NextStepPanel`
- `RiskHelpBanner`

### 6. 风险帮助页
建议拆成：
- `TopNav`
- `RiskHeader`
- `ImmediateActionCard`
- `ContactPeopleCard`
- `CampusSupportCard`
- `ExternalSupportCard`
- `EmergencyNoticeCard`
- `BackRoutePanel`

---

## 三、优先做的通用组件

### P0：先做这些，网站骨架就能立起来
- `TopNav`
- `PageHeader`
- `SectionTitle`
- `PrimaryButton`
- `SecondaryButton`
- `Card`
- `Tag`
- `RiskHelpBanner`
- `Footer`

### P1：内容页核心组件
- `ModuleCard`
- `InsightCard`
- `MethodCard`
- `PracticeCard`
- `PromptChip`
- `ResourceCard`

### P2：助教与练习互动组件
- `TutorAvatarPanel`
- `TutorChatMessage`
- `TutorInputBox`
- `RecommendedActionPanel`
- `ScenarioInteractionPanel`
- `FeedbackPanel`

---

## 四、模块页组件与内容映射

### 1. `ModuleHero`
承载：
- 模块标题
- 模块副标题
- 模块简介
- 适用困扰标签

### 2. `ProblemListSection`
承载：
- 你可能正遇到这些问题

### 3. `KeyInsightCards`
承载：
- 核心认识 3~5 条

### 4. `MisunderstandingList`
承载：
- 常见误区

### 5. `ActionMethodCards`
承载：
- 试试这些小动作 / 方法

### 6. `PracticeEntrySection`
承载：
- 情景模拟
- 小练习
- 方法卡

### 7. `TutorPromptSection`
承载：
- 助教引导提问示例
- 一键带上下文进入助教页

### 8. `RelatedResourceSection`
承载：
- 后续扩展资源内容

---

## 五、助教页组件与状态拆分

### 1. `TutorAvatarPanel`
显示：
- 助教形象
- 当前状态
- 状态说明文案

建议状态：
- idle
- welcome
- listening
- thinking
- speaking
- risk-alert

### 2. `TutorChatPanel`
显示：
- 对话历史
- 输入框
- 发送按钮

### 3. `QuickPromptChips`
显示：
- 预设问题
- 一键发问入口

### 4. `RecommendedActionPanel`
显示：
- 推荐模块
- 推荐练习
- 推荐方法卡
- 风险帮助页入口

### 5. `RiskHelpBanner`
逻辑：
- 正常状态下弱提示
- 中高风险状态下强提示

---

## 六、组件复用关系

### 这些组件可跨页复用
- `TopNav`
- `PageHeader`
- `Card`
- `PromptChip`
- `RiskHelpBanner`
- `Footer`

### 这些组件模块页和助教页可共用数据
- 模块标题 / 模块简介
- 典型困扰列表
- 助教引导提问示例
- 练习入口数据

也就是说，后面内容结构如果设计得好，可以把：
- 模块详情页内容
- 助教推荐动作
- 情景模拟入口

建立在同一套内容数据源上。

---

## 七、第一版推荐实现顺序

### 第一步：页面骨架组件
先做：
- 导航
- 通用卡片
- 标题区
- 按钮
- 风险 banner

### 第二步：模块内容组件
再做：
- ModuleHero
- ProblemListSection
- KeyInsightCards
- ActionMethodCards
- TutorPromptSection

### 第三步：助教组件
再做：
- TutorAvatarPanel
- TutorChatPanel
- QuickPromptChips
- RecommendedActionPanel

### 第四步：情景模拟与风险帮助页
最后做：
- ScenarioInteractionPanel
- FeedbackPanel
- CampusSupportCard
- ExternalSupportCard

这个顺序更稳，因为先有内容页和助教骨架，网站就已经能跑起来。

---

## 八、这一轮结论
到这里，前端视角下的第一版网站已经具备：
1. 页面级拆分
2. 通用组件清单
3. 模块页内容映射
4. 助教页状态拆分
5. 推荐实现顺序

下一轮如果继续推进，最值得做的是：
- 首页 / 助教页用户可见文案第一版
- 页面数据结构草案（JSON / CMS 字段级）
- 助教页和模块页联动数据结构
