# 网站项目文档整理地图（V1）

项目名：数智赋能示范课堂｜大学生心理健康教育网站

## 一、整理原则
这一版不是新增方案，而是把当前本地文档收口成两层：

### A. 主线文档（第一版必须围绕它推进）
这部分直接服务于：
- MVP 范围
- 页面与功能实现
- 助教与千问接入
- 风险帮助页
- 开发拆工与验收

### B. 优化方向（先保留，但不阻塞第一版）
这部分放入 `optimization/` 文件夹，并按不同优化方向分组。

原则：
- 第一版先做能用的
- 细化材料不删，但降级为后续参考
- 主线和优化方向物理分开，避免混在一起

---

## 二、主线文档（P0）

### 1. 产品与 MVP 主线
#### `website-product-plan-v1.md`
作用：项目总方案起点。

#### `website-mvp-implementation-checklist-v1.md`
作用：第一版最小可用实现清单。

#### `website-wireframe-flow-v1.md`
作用：关键页面低保真结构与 MVP 跳转主链。

---

### 2. 内容与页面主线
#### `website-module-content-and-tutor-boundary-v2.md`
作用：三大模块内容框架 + 助教边界规则。

#### `website-module-page-content-examples-v1.md`
作用：三大模块页面示例内容。

#### `website-risk-help-and-tutor-prompt-v1.md`
作用：风险帮助页草案 + 助教 prompt 初稿。

#### `website-data-structure-and-copy-v1.md`
作用：页面数据结构草案 + 首页 / 助教页用户可见文案。

---

### 3. 前端与实现主线
#### `website-frontend-component-breakdown-v1.md`
作用：前端组件拆分建议。

---

## 三、优化方向（`optimization/`）

### 1. 页面与结构优化类
#### `website-priority-wireframe-mvp-v1.md`
定位：可作为 MVP 背景参考，但不再作为主推进文档。

#### `website-flow-content-role-v1.md`
定位：早期结构与角色设定参考。

---

### 2. `optimization/risk-safety/`
更细的助教安全与风险边界增强材料：
- `tutor-risk-dialogue-examples-v1.md`
- `tutor-risk-edge-cases-v1.md`

---

### 3. `optimization/interaction-ui/`
更细的交互、组件状态、风险态 UI 与事件流材料：
- `tutor-risk-ui-mapping-v1.md`
- `tutor-risk-component-state-table-v1.md`
- `tutor-risk-ui-config-v1.md`
- `tutor-risk-state-wireframes-v1.md`
- `tutor-risk-event-flow-v1.md`

---

### 4. `optimization/testing-eval/`
更细的测试、Prompt 验收与风险样本库：
- `tutor-risk-test-cases-v1.md`
- `tutor-risk-prompt-eval-sheet-v1.md`
- `tutor-risk-test-library-v1.md`
- `tutor-risk-test-library-v1.json`

---

## 四、当前建议的阅读顺序（只看主线）

如果现在要真正进入实现准备，建议只按这个顺序看：

1. `website-mvp-implementation-checklist-v1.md`
2. `website-wireframe-flow-v1.md`
3. `website-module-content-and-tutor-boundary-v2.md`
4. `website-risk-help-and-tutor-prompt-v1.md`
5. `website-module-page-content-examples-v1.md`
6. `website-data-structure-and-copy-v1.md`
7. `website-frontend-component-breakdown-v1.md`

这样就不会被大量优化文档分散注意力。

---

## 五、当前结论
从现在开始，网站项目主线只围绕：
- MVP 页面
- MVP 功能
- 千问接入
- 风险帮助页
- 助教基础可用
- 1~2 个练习页

其他更精细的文档一律放到 `optimization/` 下，视为：
- 后续优化材料
- 增强方向
- 暂不阻塞第一版开发
