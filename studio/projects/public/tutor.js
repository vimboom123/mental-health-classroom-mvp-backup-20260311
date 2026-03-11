const bootstrap = window.__TUTOR_BOOTSTRAP__ || {};
const REQUEST_TIMEOUT_MS = Number(bootstrap.requestTimeoutMs || 12000);

const stateCopy = {
  welcome: {
    title: '准备就绪',
    copy: '你好。我是你的课程助教。比起漫无目的地聊天，我更想先帮你理清此时此刻最耗能的那件事。',
    pill: '在线就绪',
    caption: '当前模式：陪伴引导'
  },
  thinking: {
    title: '正在理解',
    copy: '我正在研判你刚才提到的场景，尝试为你匹配最合适的模块、练习和下一步动作。',
    pill: '理解中...',
    caption: '当前模式：正在提炼核心'
  },
  speaking: {
    title: '行动引导',
    copy: '我会尽量先把问题压缩成一个动作，再带你去相应的模块、练习或现实支持。',
    pill: '建议已出',
    caption: '当前模式：动作联动'
  },
  'risk-alert-soft': {
    title: '支持入口前置',
    copy: '目前我建议先关注现实支持资源。这些支持能比站内内容更直接地帮助你。',
    pill: '安全导向',
    caption: '当前模式：风险联动中'
  },
  'risk-alert': {
    title: '安全出口',
    copy: '我们先暂停学习对话。请优先查看下方的现实支持和紧急联系方式。',
    pill: '安全优先',
    caption: '当前模式：强制安全出口'
  }
};

const riskBannerCopy = {
  subtle: {
    title: '如果你现在压力极大',
    copy: '请记得这里始终有一个全站兜底的安全出口，提供校内外支持。'
  },
  emphasized: {
    title: '请优先查看现实支持',
    copy: '联动已开启。在处理具体学习任务前，请先确保你的现实状态是安全的。'
  },
  critical: {
    title: '请立刻寻求现实帮助',
    copy: '如果你已经感到无法保证安全，请立即联系紧急支持或身边的人。不要一个人硬撑。'
  }
};

const chatLog = document.getElementById('chat-log');
const avatarPanel = document.getElementById('avatar-panel');
const avatarTitle = document.getElementById('avatar-state-title');
const avatarCopy = document.getElementById('avatar-state-copy');
const avatarLivePill = document.getElementById('avatar-live-pill');
const avatarStatusCaption = document.getElementById('avatar-status-caption');
const actionsPanel = document.getElementById('recommended-actions-panel');
const actionsEmpty = document.getElementById('recommended-actions-empty');
const promptPanel = document.getElementById('quick-prompts-panel');
const promptRoot = document.getElementById('quick-prompts');
const actionsRoot = document.getElementById('recommended-actions');
const riskBanner = document.getElementById('risk-banner');
const riskBannerTitle = document.getElementById('risk-banner-title');
const riskBannerCopyEl = document.getElementById('risk-banner-copy');
const riskBannerLink = document.getElementById('risk-banner-link');
const supportCard = document.getElementById('real-support-card');
const emergencyNotice = document.getElementById('emergency-notice');
const form = document.getElementById('tutor-form');
const input = document.getElementById('tutor-input');
const inputCount = document.getElementById('input-count');
const sendButton = document.getElementById('send-button');

const messages = [];
let hasAutoSent = false;
let isBusy = false;
let currentUiState = bootstrap.initialUiState || {};

function scrollChatToBottom() {
  setTimeout(() => {
    chatLog.scrollTo({
      top: chatLog.scrollHeight,
      behavior: 'smooth'
    });
  }, 50);
}

function renderMessages() {
  chatLog.innerHTML = messages
    .map(
      (message) => `
        <article class="message ${message.role}" aria-label="${message.role === 'user' ? '我的提问' : '助教回复'}">
          <header class="message-meta">${message.meta}</header>
          <div class="message-body"><p>${message.content}</p></div>
        </article>
      `
    )
    .join('');

  scrollChatToBottom();
}

function addMessage(role, meta, content) {
  messages.push({ role, meta, content });
  renderMessages();
}

function showTyping() {
  const typingId = 'typing-indicator';
  if (document.getElementById(typingId)) return;

  const indicator = document.createElement('article');
  indicator.id = typingId;
  indicator.className = 'message assistant';
  indicator.innerHTML = '<div class="message-body"><p>正在思考...</p></div>';
  chatLog.appendChild(indicator);
  scrollChatToBottom();
}

function hideTyping() {
  document.getElementById('typing-indicator')?.remove();
}

function setAvatarState(stateKey) {
  const copy = stateCopy[stateKey] || stateCopy.speaking;

  avatarPanel.dataset.state = stateKey;
  avatarTitle.textContent = copy.title;
  avatarCopy.textContent = copy.copy;
  avatarLivePill.textContent = copy.pill;
  avatarStatusCaption.querySelector('p').textContent = copy.caption;
}

function applyActionVisibility(uiState = {}) {
  const cards = Array.from(actionsRoot.querySelectorAll('.action-card'));
  let visibleCount = 0;

  cards.forEach((card) => {
    const type = card.dataset.type;
    const hidden =
      ((type === 'module' || type === 'resource') && uiState.showModuleRecommendations === false) ||
      (type === 'practice' && uiState.showPracticeRecommendations === false);

    card.classList.toggle('hidden', hidden);
    if (!hidden) visibleCount += 1;
  });

  actionsRoot.classList.toggle('hidden', visibleCount === 0);
  actionsEmpty.classList.toggle('hidden', visibleCount > 0);
}

function renderActions(actions) {
  actionsRoot.innerHTML = (actions || [])
    .map(
      (action) => `
        <article class="action-card" data-type="${action.type}" data-priority="${action.priority}">
          <h3>${action.label}</h3>
          <p>${action.description}</p>
          <a class="button button-secondary" href="${action.target}">立即打开</a>
        </article>
      `
    )
    .join('');

  applyActionVisibility(currentUiState);
}

function applyUiState(uiState = {}) {
  currentUiState = { ...currentUiState, ...uiState };

  setAvatarState(currentUiState.avatarState || 'speaking');
  
  supportCard.classList.toggle('hidden', !currentUiState.showRealSupportCard);
  emergencyNotice.classList.toggle('hidden', !currentUiState.showEmergencyNotice);
  riskBanner.classList.toggle('hidden', currentUiState.showRiskHelpBanner === false);
  promptPanel.classList.toggle('hidden', currentUiState.showQuickPrompts === false);

  const bannerMode = currentUiState.riskHelpBannerMode || 'subtle';
  const bannerCopy = riskBannerCopy[bannerMode] || riskBannerCopy.subtle;
  const promptsCollapsed = currentUiState.quickPromptsMode === 'collapsed';

  riskBanner.dataset.mode = bannerMode;
  riskBannerTitle.textContent = bannerCopy.title;
  riskBannerCopyEl.textContent = bannerCopy.copy;
  promptRoot.querySelectorAll('.chip-button').forEach((button) => {
    button.classList.toggle('is-muted', promptsCollapsed);
  });

  applyActionVisibility(currentUiState);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function updateInputCount() {
  inputCount.textContent = String(input.value.trim().length);
  syncSendButtonState();
}

function syncSendButtonState() {
  const hasInput = input.value.trim().length > 0;
  const disabled = isBusy || !hasInput;
  sendButton.disabled = disabled;
  sendButton.setAttribute('aria-disabled', String(disabled));
}

function setPromptButtonsDisabled(disabled) {
  promptRoot.querySelectorAll('.chip-button').forEach((button) => {
    button.disabled = disabled;
    button.setAttribute('aria-disabled', String(disabled));
  });
}

function setBusy(busy) {
  isBusy = busy;
  input.disabled = busy;
  syncSendButtonState();
  setPromptButtonsDisabled(busy);
  sendButton.textContent = busy ? '等待回复' : '发送';
  if (busy) showTyping(); else hideTyping();
}

async function sendMessage(text) {
  const message = String(text || '').trim();
  if (!message || isBusy) return;

  addMessage('user', '你', escapeHtml(message));
  input.value = '';
  updateInputCount();
  setAvatarState('thinking');
  setBusy(true);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch('/api/tutor', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        moduleId: bootstrap.contextModuleId,
        practiceId: bootstrap.contextPracticeId
      }),
      signal: controller.signal
    });

    const payload = await response.json();
    if (!payload || typeof payload.reply !== 'string') {
      throw new Error('invalid-payload');
    }
    const sourceLabel = payload.source === 'local-offline'
      ? '助教 · 离线'
      : payload.source === 'local-fallback'
        ? '助教 · 兜底'
        : '助教';
    addMessage('assistant', sourceLabel, escapeHtml(payload.reply));
    if (riskBannerLink) riskBannerLink.href = payload.riskHelpUrl || '/risk-help';
    applyUiState(payload.uiState);
    renderActions(payload.recommendedActions);
  } catch (error) {
    const timedOut = error?.name === 'AbortError';
    addMessage(
      'assistant',
      '助教',
      timedOut
        ? '我这边连接有点慢，先给你一个兜底建议：先把最急的一件事说出来，我会先帮你定一个 10 分钟内能做的动作。'
        : '抱歉，我现在遇到了一点技术问题。如果你的状态很急，请直接打开风险帮助页。'
    );
    const reason = timedOut ? 'request-timeout' : 'api-error';
    if (riskBannerLink) riskBannerLink.href = `/risk-help?from=tutor&risk=medium&reason=${reason}`;
    applyUiState({ avatarState: 'risk-alert-soft', riskHelpBannerMode: 'emphasized' });
    renderActions([
      {
        type: 'risk-help',
        label: '先看风险帮助',
        description: '接口异常时，先按安全路径处理当前状态。',
        target: '/risk-help?from=tutor&risk=medium&reason=api-error',
        priority: 'primary'
      },
      {
        type: 'support',
        label: '查看可联系对象',
        description: '优先联系一个现实中的人，不要独自硬扛。',
        target: '/risk-help?from=tutor&risk=medium&reason=api-error#contacts',
        priority: 'primary'
      }
    ]);
  } finally {
    clearTimeout(timeout);
    setBusy(false);
  }
}

form.addEventListener('submit', (e) => { e.preventDefault(); sendMessage(input.value); });

promptRoot.addEventListener('click', (e) => {
  const btn = e.target.closest('.chip-button');
  if (btn) sendMessage(btn.dataset.prompt);
});

input.addEventListener('input', updateInputCount);
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage(input.value);
  }
});

function bootstrapPage() {
  const welcomeText = bootstrap.modelConfigured
    ? '你好。我是你的课程助教。你可以直接说出最近最耗能的一件事，我会尽量先帮你定位卡点，再给你一个可执行的下一步。'
    : '你好。助教已就绪。即使当前走本地兜底链路，我也会先帮你定位问题，再给你一个能立刻执行的动作。';
  
  addMessage('assistant', '助教', welcomeText);
  updateInputCount();
  setPromptButtonsDisabled(false);
  applyUiState(bootstrap.initialUiState);
  renderActions(bootstrap.initialActions || []);

  if (bootstrap.prefillPrompt && !hasAutoSent) {
    hasAutoSent = true;
    input.value = bootstrap.prefillPrompt;
    updateInputCount();
    sendMessage(bootstrap.prefillPrompt);
  }
}

bootstrapPage();
