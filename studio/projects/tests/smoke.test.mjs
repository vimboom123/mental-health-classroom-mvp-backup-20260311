import assert from 'node:assert/strict';
import { test } from 'node:test';
import { handleAppRequest } from '../src/server.js';

async function request(pathname, method = 'GET', body = '') {
  const response = await handleAppRequest({
    method,
    url: pathname,
    body
  });

  const isJson = response.headers['Content-Type'].includes('application/json');

  return {
    status: response.statusCode,
    data: isJson ? JSON.parse(String(response.body)) : String(response.body)
  };
}

test('core routes render successfully', async () => {
  const routes = [
    '/',
    '/modules',
    '/modules/interpersonal',
    '/modules/study-mindset',
    '/modules/emotion-regulation',
    '/tutor',
    '/risk-help',
    '/practice/roommate-talk',
    '/practice/exam-reset',
    '/practice/emotion-cooldown'
  ];

  for (const route of routes) {
    const response = await request(route);

    assert.equal(response.status, 200, `${route} should return 200`);
    assert.match(response.data, /数智赋能示范课堂|智能助教|风险帮助/u);
  }
});

test('low-risk tutor response returns structured UI state', async () => {
  const response = await request(
    '/api/tutor',
    'POST',
    JSON.stringify({ message: '我最近总拖延，考试前有点慌，应该先做什么？' })
  );

  assert.equal(response.status, 200);
  assert.equal(response.data.riskLevel, 'low');
  assert.equal(typeof response.data.reply, 'string');
  assert.equal(Array.isArray(response.data.recommendedActions), true);
  assert.equal(response.data.uiState.showQuickPrompts, true);
  assert.equal(response.data.uiState.showModuleRecommendations, true);
  assert.match(response.data.riskHelpUrl, /^\/risk-help\?/);
});

test('medium-risk tutor response fronts risk help', async () => {
  const response = await request(
    '/api/tutor',
    'POST',
    JSON.stringify({ message: '我这几天真的撑不住了，睡不着，也没法继续学。' })
  );

  assert.equal(response.status, 200);
  assert.equal(response.data.riskLevel, 'medium');
  assert.equal(response.data.uiState.riskHelpBannerMode, 'emphasized');
  assert.equal(response.data.uiState.showRealSupportCard, true);
  assert.equal(response.data.recommendedActions[0].type, 'risk-help');
});

test('high-risk tutor response switches to safety mode', async () => {
  const response = await request(
    '/api/tutor',
    'POST',
    JSON.stringify({ message: '我已经不想活了，也不能保证自己安全。' })
  );

  assert.equal(response.status, 200);
  assert.equal(response.data.riskLevel, 'high');
  assert.equal(response.data.uiState.showQuickPrompts, false);
  assert.equal(response.data.uiState.showModuleRecommendations, false);
  assert.equal(response.data.uiState.showEmergencyNotice, true);
  assert.equal(response.data.recommendedActions[0].type, 'risk-help');
  assert.match(response.data.riskHelpUrl, /risk=high/);
});

test('tutor meta endpoint exposes API readiness', async () => {
  const response = await request('/api/tutor/meta');

  assert.equal(response.status, 200);
  assert.equal(response.data.endpoint, '/api/tutor');
  assert.equal(response.data.metaEndpoint, '/api/tutor/meta');
  assert.equal(Array.isArray(response.data.supportedRiskLevels), true);
  assert.equal(Array.isArray(response.data.responseFields), true);
});

test('tutor request keeps module and practice context for ambiguous prompts', async () => {
  const response = await request(
    '/api/tutor',
    'POST',
    JSON.stringify({
      message: '这个场景里我第一句该怎么说？',
      moduleId: 'interpersonal',
      practiceId: 'roommate-talk'
    })
  );

  assert.equal(response.status, 200);
  assert.equal(response.data.moduleId, 'interpersonal');
  assert.equal(response.data.practiceId, 'roommate-talk');
});

test('risk help page shows source and return context when linked from tutor', async () => {
  const response = await request('/risk-help?from=tutor&risk=high&module=study-mindset&practice=exam-reset');

  assert.equal(response.status, 200);
  assert.match(response.data, /你是从 智能助教 进入的/u);
  assert.match(response.data, /高风险联动/u);
  assert.match(response.data, /回当前练习/u);
  assert.match(response.data, /回当前模块/u);
});

test('risk help page maps tutor reason code to readable helper copy', async () => {
  const response = await request('/risk-help?from=tutor&risk=medium&reason=support-first');

  assert.equal(response.status, 200);
  assert.match(response.data, /建议先联系现实支持后再继续学习/u);
});

test('tutor page exposes the full interaction shell expected by tutor.js', async () => {
  const response = await request(
    '/tutor?module=study-mindset&practice=exam-reset&prompt=' + encodeURIComponent('我最近压力很大，应该先做什么？')
  );

  assert.equal(response.status, 200);
  assert.match(response.data, /id="avatar-live-pill"/u);
  assert.match(response.data, /id="recommended-actions-empty"/u);
  assert.match(response.data, /id="input-count"/u);
  assert.match(response.data, /id="risk-banner"/u);
  assert.match(response.data, /href="\/risk-help\?from=tutor&module=study-mindset&practice=exam-reset"/u);
  assert.match(
    response.data,
    /href="\/risk-help\?from=tutor&module=study-mindset&practice=exam-reset&reason=contact-support#contacts"/u
  );
});

test('module page keeps section anchors and tutor prompt links for front-end navigation', async () => {
  const response = await request('/modules/interpersonal');

  assert.equal(response.status, 200);
  assert.match(response.data, /href="#methods"/u);
  assert.match(response.data, /id="prompts"/u);
  assert.match(response.data, /href="\/tutor\?prompt=/u);
  assert.match(response.data, /href="\/tutor\?module=interpersonal"/u);
  assert.match(response.data, /href="\/risk-help\?from=module&module=interpersonal"/u);
});

test('practice page keeps context-aware tutor and risk-help links', async () => {
  const response = await request('/practice/exam-reset');

  assert.equal(response.status, 200);
  assert.match(response.data, /href="\/tutor\?module=study-mindset&practice=exam-reset"/u);
  assert.match(response.data, /href="\/risk-help\?from=practice&module=study-mindset&practice=exam-reset"/u);
});

test('layout keeps back-to-top control hidden from tab order before scrolling', async () => {
  const response = await request('/modules');

  assert.equal(response.status, 200);
  assert.match(response.data, /data-back-to-top/u);
  assert.match(response.data, /aria-hidden="true"/u);
  assert.match(response.data, /tabindex="-1"/u);
});
