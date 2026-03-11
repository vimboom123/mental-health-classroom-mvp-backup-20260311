import { readFile } from 'node:fs/promises';
import http from 'node:http';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { getModule, getPractice } from './content.js';
import { buildRiskHelpUrl, generateTutorResponse, getTutorApiMeta, getTutorBootstrapData } from './tutor-logic.js';
import {
  renderHomePage,
  renderModulePage,
  renderModulesIndexPage,
  renderNotFoundPage,
  renderPracticePage,
  renderRiskHelpPage,
  renderTutorPage
} from './templates.js';

const publicDir = fileURLToPath(new URL('../public/', import.meta.url));

const staticFiles = new Map([
  ['/styles.css', { filename: 'styles.css', contentType: 'text/css; charset=utf-8' }],
  ['/tutor.js', { filename: 'tutor.js', contentType: 'text/javascript; charset=utf-8' }]
]);

function htmlResponse(body, statusCode = 200) {
  return {
    statusCode,
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'no-store'
    },
    body
  };
}

function jsonResponse(payload, statusCode = 200) {
  return {
    statusCode,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store'
    },
    body: JSON.stringify(payload)
  };
}

async function staticResponse(pathname) {
  const file = staticFiles.get(pathname);

  if (!file) {
    return null;
  }

  const filePath = path.join(publicDir, file.filename);
  const buffer = await readFile(filePath);

  return {
    statusCode: 200,
    headers: {
      'Content-Type': file.contentType,
      'Cache-Control': 'no-store'
    },
    body: buffer
  };
}

function getTutorContextTitle(url) {
  const moduleId = url.searchParams.get('module');
  const practiceId = url.searchParams.get('practice');
  const module = moduleId ? getModule(moduleId) : null;
  const practice = practiceId ? getPractice(practiceId) : null;

  if (practice) {
    return `来自练习：${practice.title}`;
  }

  if (module) {
    return `来自模块：${module.title}`;
  }

  return '';
}

function getTutorContext(url) {
  const practiceId = url.searchParams.get('practice') || '';
  const practice = practiceId ? getPractice(practiceId) : null;

  return {
    moduleId: url.searchParams.get('module') || practice?.moduleId || '',
    practiceId
  };
}

function getRiskHelpContext(url) {
  const source = url.searchParams.get('from') || 'site';
  const riskLevel = url.searchParams.get('risk');
  const practiceId = url.searchParams.get('practice') || '';
  const moduleId = url.searchParams.get('module') || '';
  const practice = practiceId ? getPractice(practiceId) : null;
  const module = getModule(moduleId || practice?.moduleId || '');

  return {
    source,
    riskLevel: ['low', 'medium', 'high'].includes(riskLevel) ? riskLevel : '',
    reason: url.searchParams.get('reason') || '',
    module,
    practice
  };
}

function buildTutorErrorResponse() {
  return jsonResponse(
    {
      reply: '助教接口刚刚没有正常返回。你可以先刷新页面，或者直接打开风险帮助页。',
      riskLevel: 'medium',
      recommendedActions: [
        {
          type: 'risk-help',
          label: '先看风险帮助',
          description: '如果当前状态已经明显顶不住，先看现实支持入口。',
          target: '/risk-help',
          priority: 'primary'
        }
      ],
      uiState: {
        avatarState: 'risk-alert-soft',
        showQuickPrompts: true,
        quickPromptsMode: 'collapsed',
        showModuleRecommendations: true,
        moduleRecommendationsPriority: 'secondary',
        showPracticeRecommendations: false,
        practiceRecommendationsPriority: 'hidden',
        showRiskHelpBanner: true,
        riskHelpBannerMode: 'emphasized',
        showRealSupportCard: true,
        showEmergencyNotice: false
      },
      source: 'error-fallback',
      riskHelpUrl: buildRiskHelpUrl({
        source: 'tutor',
        riskLevel: 'medium',
        reason: 'api-error'
      })
    },
    500
  );
}

export async function handleAppRequest({ method = 'GET', url: requestUrl = '/', body = '' } = {}) {
  const url = new URL(requestUrl, 'http://localhost');
  const { pathname } = url;

  try {
    if (method === 'GET') {
      const asset = await staticResponse(pathname);

      if (asset) {
        return asset;
      }
    }

    if (method === 'GET' && pathname === '/') {
      return htmlResponse(renderHomePage());
    }

    if (method === 'GET' && pathname === '/modules') {
      return htmlResponse(renderModulesIndexPage());
    }

    if (method === 'GET' && pathname.startsWith('/modules/')) {
      const moduleId = pathname.split('/')[2];
      const module = getModule(moduleId);

      return module ? htmlResponse(renderModulePage(module)) : htmlResponse(renderNotFoundPage(), 404);
    }

    if (method === 'GET' && pathname === '/tutor') {
      const prompt = url.searchParams.get('prompt') || '';
      const tutorContext = getTutorContext(url);
      const bootstrapData = getTutorBootstrapData(prompt, getTutorContextTitle(url), tutorContext);
      return htmlResponse(renderTutorPage(bootstrapData));
    }

    if (method === 'GET' && pathname === '/risk-help') {
      return htmlResponse(renderRiskHelpPage(getRiskHelpContext(url)));
    }

    if (method === 'GET' && pathname.startsWith('/practice/')) {
      const practiceId = pathname.split('/')[2];
      const practice = getPractice(practiceId);

      return practice ? htmlResponse(renderPracticePage(practice)) : htmlResponse(renderNotFoundPage(), 404);
    }

    if (method === 'GET' && pathname === '/api/health') {
      return jsonResponse({ ok: true });
    }

    if (method === 'GET' && pathname === '/api/tutor/meta') {
      return jsonResponse(getTutorApiMeta());
    }

    if (method === 'POST' && pathname === '/api/tutor') {
      const payload = body ? JSON.parse(String(body)) : {};
      const result = await generateTutorResponse(payload.message, {
        moduleId: payload.moduleId,
        practiceId: payload.practiceId
      });
      return jsonResponse(result);
    }

    return htmlResponse(renderNotFoundPage(), 404);
  } catch {
    if (method === 'POST' && pathname === '/api/tutor') {
      return buildTutorErrorResponse();
    }

    return htmlResponse(renderNotFoundPage(), 500);
  }
}

export function createAppServer() {
  return http.createServer(async (request, response) => {
    const requestBody =
      request.method === 'POST'
        ? await (async () => {
            const chunks = [];

            for await (const chunk of request) {
              chunks.push(chunk);
            }

            return Buffer.concat(chunks).toString('utf8');
          })()
        : '';

    const result = await handleAppRequest({
      method: request.method || 'GET',
      url: request.url || '/',
      body: requestBody
    });

    response.writeHead(result.statusCode, result.headers);
    response.end(result.body);
  });
}
