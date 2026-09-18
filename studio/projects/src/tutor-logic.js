import { getModule, getPractice, modules } from './content.js';

const moduleKeywordMap = {
  interpersonal: ['室友', '人际', '边界', '沟通', '拒绝', '朋友', '同学', '关系', '冷战', '宿舍'],
  'study-mindset': ['学习', '拖延', '考试', '作业', '绩点', '保研', '考研', '考公', '任务', '复习'],
  'emotion-regulation': ['情绪', '焦虑', '烦', '崩溃', '难受', '内耗', '压力', '失眠', '想哭', '委屈']
};

const highRiskPatterns = [
  /自杀/u,
  /想死/u,
  /不想活/u,
  /轻生/u,
  /结束生命/u,
  /活不下去/u,
  /伤害自己/u,
  /自残/u,
  /割腕/u,
  /跳楼/u,
  /伤害他人/u,
  /杀了(我自己|自己|他|她|所有人)/u,
  /无法保证(自身|自己)安全/u
];

const mediumRiskPatterns = [
  /撑不住/u,
  /快崩了/u,
  /崩溃/u,
  /没法继续/u,
  /睡不着/u,
  /失眠/u,
  /很绝望/u,
  /活着没意思/u,
  /一点希望都没有/u,
  /控制不住情绪/u,
  /一直想哭/u,
  /喘不过气/u
];

function countKeywordHits(message, keywords) {
  return keywords.reduce((count, keyword) => count + (message.includes(keyword) ? 1 : 0), 0);
}

function getModuleScores(message) {
  const scores = Object.entries(moduleKeywordMap).map(([moduleId, keywords]) => ({
    moduleId,
    score: countKeywordHits(message, keywords)
  }));

  scores.sort((left, right) => right.score - left.score);
  return scores;
}

function buildUiState(riskLevel) {
  if (riskLevel === 'high') {
    return {
      avatarState: 'risk-alert',
      showQuickPrompts: false,
      quickPromptsMode: 'hidden',
      showModuleRecommendations: false,
      moduleRecommendationsPriority: 'hidden',
      showPracticeRecommendations: false,
      practiceRecommendationsPriority: 'hidden',
      showRiskHelpBanner: true,
      riskHelpBannerMode: 'critical',
      showRealSupportCard: true,
      showEmergencyNotice: true
    };
  }

  if (riskLevel === 'medium') {
    return {
      avatarState: 'risk-alert-soft',
      showQuickPrompts: true,
      quickPromptsMode: 'collapsed',
      showModuleRecommendations: true,
      moduleRecommendationsPriority: 'secondary',
      showPracticeRecommendations: true,
      practiceRecommendationsPriority: 'secondary',
      showRiskHelpBanner: true,
      riskHelpBannerMode: 'emphasized',
      showRealSupportCard: true,
      showEmergencyNotice: false
    };
  }

  return {
    avatarState: 'speaking',
    showQuickPrompts: true,
    quickPromptsMode: 'normal',
    showModuleRecommendations: true,
    moduleRecommendationsPriority: 'primary',
    showPracticeRecommendations: true,
    practiceRecommendationsPriority: 'primary',
    showRiskHelpBanner: true,
    riskHelpBannerMode: 'subtle',
    showRealSupportCard: false,
    showEmergencyNotice: false
  };
}

export function classifyRisk(message) {
  for (const pattern of highRiskPatterns) {
    if (pattern.test(message)) {
      return 'high';
    }
  }

  for (const pattern of mediumRiskPatterns) {
    if (pattern.test(message)) {
      return 'medium';
    }
  }

  return 'low';
}

export function inferModuleId(message) {
  const scores = getModuleScores(message);

  if (scores[0].score === 0) {
    if (message.includes('压力')) {
      return 'study-mindset';
    }

    return 'emotion-regulation';
  }

  return scores[0].moduleId;
}

function resolveModuleId(message, contextModuleId = '') {
  const scores = getModuleScores(message);

  if (contextModuleId && scores[0].score === 0 && !message.includes('压力')) {
    return contextModuleId;
  }

  return inferModuleId(message);
}

function inferPracticeId(message, moduleId) {
  if (moduleId === 'interpersonal' && /室友|宿舍|作息/u.test(message)) {
    return 'roommate-talk';
  }

  if (moduleId === 'study-mindset' && /考试|考前|复习|任务/u.test(message)) {
    return 'exam-reset';
  }

  if (moduleId === 'emotion-regulation' && /情绪|崩|爆|烦|乱|委屈|想哭/u.test(message)) {
    return 'emotion-cooldown';
  }

  return null;
}

function buildAction(type, label, description, target, priority = 'secondary') {
  return { type, label, description, target, priority };
}

function buildQueryString(params) {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value) {
      searchParams.set(key, value);
    }
  });

  const query = searchParams.toString();
  return query ? `?${query}` : '';
}

export function buildRiskHelpUrl({ source = 'site', riskLevel = '', moduleId = '', practiceId = '', reason = '', hash = '' } = {}) {
  const query = buildQueryString({
    from: source,
    risk: riskLevel,
    module: moduleId,
    practice: practiceId,
    reason
  });

  return `/risk-help${query}${hash}`;
}

function buildRecommendedActions(riskLevel, moduleId, practiceId) {
  const module = getModule(moduleId);
  const practice = practiceId ? getPractice(practiceId) : null;
  const riskHelpUrl = buildRiskHelpUrl({
    source: 'tutor',
    riskLevel,
    moduleId,
    practiceId,
    reason:
      riskLevel === 'high'
        ? 'safety-first'
        : riskLevel === 'medium'
          ? 'support-first'
          : 'just-in-case'
  });
  const actions = [];

  if (riskLevel === 'high') {
    return [
      buildAction('risk-help', '立刻看风险帮助', '先看现在该做什么、联系谁和现实支持出口。', riskHelpUrl, 'primary'),
      buildAction(
        'support',
        '优先联系可信任的人',
        '辅导员、室友、朋友、家人都比一个人硬撑更重要。',
        buildRiskHelpUrl({ source: 'tutor', riskLevel, moduleId, practiceId, reason: 'contact-support', hash: '#contacts' }),
        'primary'
      ),
      buildAction(
        'support',
        '查看校内支持资源占位',
        '上线前要替换成真实学校资源，这里先保留结构入口。',
        buildRiskHelpUrl({ source: 'tutor', riskLevel, moduleId, practiceId, reason: 'campus-support', hash: '#campus-support' })
      ),
      buildAction(
        'support',
        '看紧急情况提醒',
        '如果已经有明显危险，请先用现实中的紧急支持。',
        buildRiskHelpUrl({ source: 'tutor', riskLevel, moduleId, practiceId, reason: 'emergency', hash: '#emergency' })
      )
    ];
  }

  if (riskLevel === 'medium') {
    actions.push(
      buildAction('risk-help', '先看风险帮助', '现在先做什么、联系谁、去哪里找现实支持，都在这里。', riskHelpUrl, 'primary'),
      buildAction(
        'support',
        '优先联系现实支持',
        '先告诉一个你信得过的人，你现在状态不太对。',
        buildRiskHelpUrl({ source: 'tutor', riskLevel, moduleId, practiceId, reason: 'contact-support', hash: '#contacts' }),
        'primary'
      ),
      buildAction(
        'support',
        '只处理眼前最急的一件事',
        '把动作缩小，先把当前最危险或最急的问题稳住。',
        buildRiskHelpUrl({ source: 'tutor', riskLevel, moduleId, practiceId, reason: 'immediate-actions', hash: '#immediate-actions' })
      )
    );

    if (module) {
      actions.push(buildAction('module', `再看 ${module.title} 模块`, module.shortDescription, module.route));
    }

    return actions;
  }

  if (module) {
    actions.push(buildAction('module', `去看 ${module.title} 模块`, module.shortDescription, module.route, 'primary'));
  }

  if (practice) {
    actions.push(buildAction('practice', `做练习：${practice.title}`, practice.summary, practice.route, 'primary'));
  }

  if (module?.relatedResources?.[0]) {
    const firstResource = module.relatedResources[0];
    actions.push(
      buildAction('resource', `看方法卡：${firstResource.title}`, firstResource.summary, `${module.route}#resources`)
    );
  }

  actions.push(
    buildAction('risk-help', '保留风险帮助入口', '如果你现在状态已经明显失控，可以先去看现实支持和风险帮助。', riskHelpUrl)
  );

  return actions;
}

function buildLocalReply(message, riskLevel, moduleId, practiceId) {
  const module = getModule(moduleId);
  const practice = practiceId ? getPractice(practiceId) : null;

  if (riskLevel === 'high') {
    return '先把安全放在第一位。现在不要一个人硬扛，优先联系身边可信任的人、老师或家人，并尽快使用现实中的紧急支持。页面已经把风险帮助和现实支持放在最前面。';
  }

  if (riskLevel === 'medium') {
    const mediumLead =
      moduleId === 'study-mindset'
        ? '你现在更像是已经被压力压得很满了，不是简单的没状态。'
        : moduleId === 'interpersonal'
          ? '你现在遇到的已经不只是普通沟通卡壳，更像是状态被持续顶住了。'
          : '你现在更像是情绪和压力已经明显堆高了。';

    return `${mediumLead} 先别逼自己一次解决所有问题，先联系一个你信得过的人，把你现在最难受的一件事说出来。页面上方的风险帮助和现实支持可以先用起来。`;
  }

  const leadByModule = {
    interpersonal: '这更像是一个要把边界和需求说清的问题，不是你只能一直忍。',
    'study-mindset': '这更像是压力把启动难度抬高了，不是你单纯不够努力。',
    'emotion-regulation': '你现在更需要先把情绪降到能处理的强度，再谈怎么解决问题。'
  };

  const actionPart = practice
    ? `你可以先做“${practice.title}”这个练习，把最卡的那一步具体化。`
    : module
      ? `你可以先从“${module.title}”模块里挑一个最贴近的部分看。`
      : '你可以先把最近最卡的一件事拆成一句更具体的话。';

  const closing =
    moduleId === 'interpersonal'
      ? '如果你愿意，把你最难开口的那句话发过来，我可以帮你换一种更稳的说法。'
      : moduleId === 'study-mindset'
        ? '先别追求把整天安排满，先抓一个 10 到 20 分钟能开始的小步就够了。'
        : '先认一下你更接近愤怒、委屈、焦虑还是无力，后面才好选动作。';

  return `${leadByModule[moduleId] || '先别急着把问题一次讲完。'} ${actionPart} ${closing}`;
}

function getApiKey() {
  return process.env.DASHSCOPE_API_KEY || process.env.QWEN_API_KEY || '';
}

export function isQwenConfigured() {
  return Boolean(getApiKey());
}

function getModelLabel() {
  return process.env.DASHSCOPE_MODEL || 'qwen-plus';
}

function getBaseUrl() {
  return process.env.DASHSCOPE_BASE_URL || 'https://dashscope.aliyuncs.com/compatible-mode/v1';
}

function getModelTimeoutMs() {
  const raw = Number(process.env.TUTOR_MODEL_TIMEOUT_MS || process.env.DASHSCOPE_TIMEOUT_MS || 8000);
  if (!Number.isFinite(raw)) return 8000;
  return Math.min(Math.max(raw, 800), 15000);
}

export function getTutorApiMeta() {
  return {
    provider: 'dashscope-compatible',
    modelConfigured: isQwenConfigured(),
    modelLabel: getModelLabel(),
    modelTimeoutMs: getModelTimeoutMs(),
    baseUrl: getBaseUrl(),
    endpoint: '/api/tutor',
    metaEndpoint: '/api/tutor/meta',
    fallbackMode: 'local-rule-engine',
    envStatus: {
      DASHSCOPE_API_KEY: Boolean(process.env.DASHSCOPE_API_KEY),
      QWEN_API_KEY: Boolean(process.env.QWEN_API_KEY),
      DASHSCOPE_MODEL: Boolean(process.env.DASHSCOPE_MODEL || 'qwen-plus'),
      DASHSCOPE_BASE_URL: Boolean(process.env.DASHSCOPE_BASE_URL || 'https://dashscope.aliyuncs.com/compatible-mode/v1')
    },
    supportedRiskLevels: ['low', 'medium', 'high'],
    responseFields: ['reply', 'riskLevel', 'moduleId', 'practiceId', 'recommendedActions', 'uiState', 'source', 'riskHelpUrl']
  };
}

async function callQwenReply(message, riskLevel, moduleId, practiceId) {
  const apiKey = getApiKey();

  if (!apiKey) {
    return null;
  }

  const module = getModule(moduleId);
  const practice = practiceId ? getPractice(practiceId) : null;
  const baseUrl = getBaseUrl();
  const model = getModelLabel();
  const fallbackModel = process.env.DASHSCOPE_FALLBACK_MODEL || '';

  async function requestModel(modelName) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), getModelTimeoutMs());
    try {
      const response = await fetch(`${baseUrl}/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${apiKey}`
        },
        body: JSON.stringify({
          model: modelName,
          temperature: 0.5,
          max_tokens: Number(process.env.TUTOR_MAX_TOKENS || 900),
          messages: [
            {
              role: 'system',
              content:
                `你是大学生心理健康教育网站的课程内嵌智能助教。` +
                `不要诊断，不要提供药物建议，不要承诺替代专业咨询。` +
                `回复风格：自然中文、短句、稳定、可执行。` +
                `系统已预判风险等级：${riskLevel}。` +
                `相关模块：${module ? module.title : '未确定'}。` +
                `建议练习：${practice ? practice.title : '暂无'}。` +
                `如果风险等级是 medium 或 high，优先现实支持和风险帮助，不继续长篇教学。` +
                `只输出给用户的最终回复，不要标题，不要解释规则。`
            },
            {
              role: 'user',
              content: message
            }
          ]
        }),
        signal: controller.signal
      });

      if (!response.ok) {
        const errorPayload = await response.json().catch(() => null);
        const modelNotFound = errorPayload?.error?.code === 'model_not_found';
        return { content: null, modelNotFound };
      }

      const payload = await response.json();
      const content = payload?.choices?.[0]?.message?.content?.trim();
      return { content: content || null, modelNotFound: false };
    } catch (error) {
      // 之前这里是一个裸 catch，超时/鉴权/网络错误全部被静默吞掉，
      // 表现是「助教看起来正常但永远走本地规则」，线上无从排查。
      console.warn(
        `[tutor] model request failed (model=${modelName}):`,
        (error && (error.name || error.message)) || error
      );
      return { content: null, modelNotFound: false };
    } finally {
      clearTimeout(timeout);
    }
  }

  const primary = await requestModel(model);
  if (primary.content) {
    return primary.content;
  }
  if (primary.modelNotFound && fallbackModel && fallbackModel !== model) {
    const fallback = await requestModel(fallbackModel);
    if (fallback.content) {
      return fallback.content;
    }
  }
  return null;
}

function buildInitialActions() {
  return [
    buildAction('module', `去看 ${modules[0].title} 模块`, modules[0].shortDescription, modules[0].route, 'primary'),
    buildAction('module', `去看 ${modules[1].title} 模块`, modules[1].shortDescription, modules[1].route, 'primary'),
    buildAction('practice', '先做一个情绪降强度练习', '如果你现在已经很满，先把强度降下来，再决定下一步。', '/practice/emotion-cooldown'),
    buildAction('practice', '先做一个考试前重启练习', '如果你不想先读内容，可以直接从一个具体场景开始。', '/practice/exam-reset'),
    buildAction('risk-help', '如果状态很糟，先看风险帮助', '风险帮助页会把现实支持入口放在前面。', buildRiskHelpUrl({ source: 'tutor' }))
  ];
}

export function getTutorBootstrapData(prefillPrompt = '', contextTitle = '', context = {}) {
  const apiMeta = getTutorApiMeta();

  return {
    initialUiState: buildUiState('low'),
    initialActions: buildInitialActions(),
    prefillPrompt,
    autoSendPrompt: Boolean(prefillPrompt),
    contextTitle,
    modelConfigured: apiMeta.modelConfigured,
    modelLabel: apiMeta.modelLabel,
    requestTimeoutMs: Number(process.env.TUTOR_FRONTEND_TIMEOUT_MS || 12000),
    apiMeta,
    riskHelpUrl: buildRiskHelpUrl({ source: 'tutor', moduleId: context.moduleId, practiceId: context.practiceId }),
    contextModuleId: context.moduleId || '',
    contextPracticeId: context.practiceId || ''
  };
}

export async function generateTutorResponse(rawMessage, context = {}) {
  const message = String(rawMessage || '').trim();

  if (!message) {
    return {
      reply: '你可以直接说最近最卡的一件事，比如拖延、室友沟通、考试焦虑，或者情绪乱得停不下来。',
      riskLevel: 'low',
      recommendedActions: buildInitialActions(),
      uiState: buildUiState('low'),
      source: 'bootstrap'
    };
  }

  const riskLevel = classifyRisk(message);
  const contextPractice = context.practiceId ? getPractice(context.practiceId) : null;
  const contextModuleId = context.moduleId || contextPractice?.moduleId || '';
  const moduleId = resolveModuleId(message, contextModuleId);
  const practiceId = inferPracticeId(message, moduleId) || (contextPractice?.moduleId === moduleId ? context.practiceId : null);
  const localReply = buildLocalReply(message, riskLevel, moduleId, practiceId);
  // Medium/High risk responses prioritize deterministic safety guidance and speed.
  const shouldCallModel = riskLevel === 'low';
  const modelReply = shouldCallModel ? await callQwenReply(message, riskLevel, moduleId, practiceId) : null;

  const source = riskLevel === 'low'
    ? (modelReply ? 'qwen' : (isQwenConfigured() ? 'local-fallback' : 'local-offline'))
    : 'safety-local';

  return {
    reply: modelReply || localReply,
    riskLevel,
    moduleId,
    practiceId,
    recommendedActions: buildRecommendedActions(riskLevel, moduleId, practiceId),
    uiState: buildUiState(riskLevel),
    source,
    riskHelpUrl: buildRiskHelpUrl({
      source: 'tutor',
      riskLevel,
      moduleId,
      practiceId,
      reason:
        riskLevel === 'high'
          ? 'safety-first'
          : riskLevel === 'medium'
            ? 'support-first'
            : 'just-in-case'
    })
  };
}
