import {
  getModule,
  pathwayFlow,
  getPractice,
  homePage,
  modules,
  modulesIndexPage,
  notFoundPage,
  practicePage,
  riskReasonCopy,
  riskHelpPage,
  siteMeta,
  siteNavigation,
  tutorPage
} from './content.js';

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function serializeForScript(value) {
  return JSON.stringify(value).replaceAll('<', '\\u003c');
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

function buildTutorUrl(prompt, { moduleId = '', practiceId = '' } = {}) {
  return `/tutor${buildQueryString({
    prompt,
    module: moduleId,
    practice: practiceId
  })}`;
}

function buildRiskHelpPageUrl({ source = 'site', riskLevel = '', moduleId = '', practiceId = '', reason = '', hash = '' } = {}) {
  return `/risk-help${buildQueryString({
    from: source,
    risk: riskLevel,
    module: moduleId,
    practice: practiceId,
    reason
  })}${hash}`;
}

function resolveNavContext(currentPath, navContext = {}) {
  const sourceFromPath = currentPath === '/'
    ? 'home'
    : currentPath === '/modules'
      ? 'modules'
      : currentPath.startsWith('/modules/')
        ? 'module'
        : currentPath.startsWith('/practice/')
          ? 'practice'
          : currentPath.startsWith('/tutor')
            ? 'tutor'
            : 'site';

  return {
    source: navContext.source || sourceFromPath,
    moduleId: navContext.moduleId || '',
    practiceId: navContext.practiceId || '',
    riskLevel: navContext.riskLevel || '',
    reason: navContext.reason || ''
  };
}

function resolveNavHref(baseHref, navContext) {
  if (baseHref === '/tutor') {
    return buildTutorUrl('', {
      moduleId: navContext.moduleId,
      practiceId: navContext.practiceId
    });
  }

  if (baseHref === '/risk-help') {
    return buildRiskHelpPageUrl({
      source: navContext.source,
      riskLevel: navContext.riskLevel,
      moduleId: navContext.moduleId,
      practiceId: navContext.practiceId,
      reason: navContext.reason
    });
  }

  return baseHref;
}

function renderNav(currentPath, navContext = {}) {
  const resolvedNavContext = resolveNavContext(currentPath, navContext);

  let currentStageId = '';
  if (currentPath.startsWith('/risk-help')) currentStageId = 'safety';
  else if (currentPath.startsWith('/practice')) currentStageId = 'practice';
  else if (currentPath.startsWith('/tutor')) currentStageId = 'guide';
  else if (currentPath.startsWith('/modules') || currentPath === '/') currentStageId = 'identify';

  const currentStage = pathwayFlow.stages.find((stage) => stage.id === currentStageId);

  const stageIndex = currentStage ? pathwayFlow.stages.findIndex((stage) => stage.id === currentStage.id) : -1;
  const stageBadge = currentStage
    ? `
      <span class="nav-stage-badge" aria-label="当前主线路径阶段">
        <span class="nav-stage-kicker">Pathway</span>
        <span>Step ${String(stageIndex + 1)}/4 · ${escapeHtml(currentStage.title)}</span>
      </span>
    `
    : '';

  const navLinks = siteNavigation
    .map((item) => {
      const isActive =
        item.href === '/'
          ? currentPath === '/'
          : currentPath === item.href || currentPath.startsWith(`${item.href}/`);
      const linkHref = resolveNavHref(item.href, resolvedNavContext);

      return `<a class="nav-link${isActive ? ' is-active' : ''}" href="${linkHref}"${isActive ? ' aria-current="page"' : ''}>${escapeHtml(
        item.label
      )}</a>`;
    })
    .join('');

  return `
    <header class="topbar">
      <div class="topbar-inner">
        <div class="topbar-left">
          <a class="brand" href="/" aria-label="返回首页">
            <span class="brand-mark">示范课堂</span>
            <span class="brand-copy">${escapeHtml(siteMeta.title)}</span>
            <span class="brand-note">学 / 问 / 练 / 安全出口</span>
          </a>
          ${stageBadge}
        </div>
        <nav class="nav" aria-label="主导航">${navLinks}</nav>
      </div>
    </header>
  `;
}

function renderFooter() {
  const footer = siteMeta.footer || {};
  const footerLinks = (footer.quickLinks || [])
    .map((item) => `<a class="footer-link" href="${item.target}">${escapeHtml(item.label)}</a>`)
    .join('');
  const footerCommitments = (footer.commitments || [])
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join('');

  return `
    <footer class="footer">
      <div class="footer-inner">
        <div class="footer-brand">
          <p class="brand-copy">${escapeHtml(siteMeta.title)}</p>
          <p class="footer-stage">${escapeHtml(footer.stage || siteMeta.subtitle)}</p>
          <p>${escapeHtml(footer.description || siteMeta.description)}</p>
        </div>
        <div class="footer-meta-grid">
          <nav class="footer-links" aria-label="页脚快捷入口">${footerLinks}</nav>
          <ul class="bullet-list compact-list footer-list" aria-label="我们的承诺">${footerCommitments}</ul>
        </div>
      </div>
    </footer>
  `;
}

function renderLayout({ title, description, currentPath, navContext = {}, content, script = '' }) {
  return `<!DOCTYPE html>
  <html lang="zh-CN">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <meta name="description" content="${escapeHtml(description || siteMeta.description)}" />
      <title>${escapeHtml(title)} | ${escapeHtml(siteMeta.title)}</title>
      <link rel="stylesheet" href="/styles.css" />
    </head>
    <body>
      <a class="skip-link" href="#main-content">跳到主要内容</a>
      <div class="page-shell">
        ${renderNav(currentPath, navContext)}
        ${content}
        ${renderFooter()}
      </div>
      <button class="back-to-top" type="button" data-back-to-top aria-label="回到顶部" aria-hidden="true" tabindex="-1">↑ 回到顶部</button>
      <script>
        (() => {
          const navGroups = Array.from(document.querySelectorAll('.section-nav, .risk-anchor-list'));
          const anchorItems = navGroups
            .flatMap((group) => Array.from(group.querySelectorAll('a[href^="#"]')))
            .map((link) => {
              const id = link.getAttribute('href').slice(1);
              const target = document.getElementById(id);
              return id && target ? { link, id, target } : null;
            })
            .filter(Boolean);

          if (anchorItems.length) {
            const targetMap = new Map(anchorItems.map((item) => [item.id, item]));
            const uniqueTargets = Array.from(new Set(anchorItems.map((item) => item.target)));

            const setActive = (id) => {
              anchorItems.forEach((item) => {
                const active = item.id === id;
                item.link.classList.toggle('is-active', active);
                if (active) {
                  item.link.setAttribute('aria-current', 'location');
                } else {
                  item.link.removeAttribute('aria-current');
                }
              });
            };

            const getHashId = () => {
              const rawHash = window.location.hash.replace(/^#/, '');
              if (!rawHash) return '';
              try {
                return decodeURIComponent(rawHash);
              } catch {
                return rawHash;
              }
            };

            const resolveClosestVisibleId = () => {
              const threshold = window.scrollY + window.innerHeight * 0.32;
              let resolved = anchorItems[0].id;

              uniqueTargets.forEach((target) => {
                if (target.offsetTop <= threshold) {
                  resolved = target.id || resolved;
                }
              });

              return resolved;
            };

            const hashId = getHashId();
            if (hashId && targetMap.has(hashId)) {
              setActive(hashId);
            } else {
              setActive(anchorItems[0].id);
            }

            if ('IntersectionObserver' in window) {
              const observer = new IntersectionObserver(
                (entries) => {
                  const visible = entries
                    .filter((entry) => entry.isIntersecting)
                    .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
                  if (!visible.length) return;
                  const id = visible[0].target.id;
                  if (id && targetMap.has(id)) {
                    setActive(id);
                  }
                },
                {
                  rootMargin: '-28% 0px -56% 0px',
                  threshold: [0.15, 0.45, 0.75]
                }
              );

              uniqueTargets.forEach((target) => observer.observe(target));
            } else {
              const onScrollFallback = () => {
                setActive(resolveClosestVisibleId());
              };
              onScrollFallback();
              window.addEventListener('scroll', onScrollFallback, { passive: true });
            }

            anchorItems.forEach((item) => {
              item.link.addEventListener('click', () => setActive(item.id));
            });

            window.addEventListener('hashchange', () => {
              const currentHash = getHashId();
              if (currentHash && targetMap.has(currentHash)) {
                setActive(currentHash);
              }
            });
          }

          const backToTop = document.querySelector('[data-back-to-top]');
          if (!backToTop) return;

          const setBackToTopVisibility = (visible) => {
            backToTop.classList.toggle('is-visible', visible);
            backToTop.setAttribute('aria-hidden', visible ? 'false' : 'true');
            backToTop.tabIndex = visible ? 0 : -1;
          };

          const toggleBackToTop = () => {
            setBackToTopVisibility(window.scrollY > 360);
          };

          toggleBackToTop();
          window.addEventListener('scroll', toggleBackToTop, { passive: true });
          backToTop.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
          });
        })();
      </script>
      ${script}
    </body>
  </html>`;
}

function renderSectionHeader(title, description, kicker = 'MVP P0') {
  return `
    <header class="section-heading">
      <p class="eyebrow">${escapeHtml(kicker)}</p>
      <h2>${escapeHtml(title)}</h2>
      <p>${escapeHtml(description)}</p>
    </header>
  `;
}

function renderMetricStrip(items = [], className = '') {
  if (!items.length) {
    return '';
  }

  const classes = ['metric-strip', className].filter(Boolean).join(' ');

  return `
    <div class="${classes}">
      ${items
        .map(
          (item) => `
            <article class="metric-card">
              <strong>${escapeHtml(item.value)}</strong>
              <span>${escapeHtml(item.label)}</span>
            </article>
          `
        )
        .join('')}
    </div>
  `;
}

function renderTagRow(items = [], className = 'tag-row') {
  if (!items.length) {
    return '';
  }

  return `
    <div class="${className}">
      ${items.map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join('')}
    </div>
  `;
}

function renderTextList(items = [], { ordered = false, className = '' } = {}) {
  if (!items.length) {
    return '';
  }

  const tagName = ordered ? 'ol' : 'ul';
  const baseClass = ordered ? 'ordered-list' : 'bullet-list';
  const classes = [baseClass, className].filter(Boolean).join(' ');

  return `
    <${tagName} class="${classes}">
      ${items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}
    </${tagName}>
  `;
}

function renderPathwayRail(currentStageId, { title = pathwayFlow.title, description = pathwayFlow.description, className = '', compact = false } = {}) {
  const currentIndex = pathwayFlow.stages.findIndex((stage) => stage.id === currentStageId);
  const classes = ['card', 'pathway-shell', compact ? 'pathway-shell-compact' : '', className]
    .filter(Boolean)
    .join(' ');

  return `
    <article class="${classes}">
      ${
        title || description
          ? `
            <header class="section-heading pathway-heading">
              <div class="panel-header-row">
                <p class="eyebrow">主线路径</p>
                <span class="context-pill">全程导览</span>
              </div>
              ${title ? `<h2>${escapeHtml(title)}</h2>` : ''}
              ${description ? `<p class="pathway-desc">${escapeHtml(description)}</p>` : ''}
            </header>
          `
          : ''
      }
      <ol class="pathway-rail" aria-label="${escapeHtml(pathwayFlow.title)}">
        ${pathwayFlow.stages
          .map((stage, index) => {
            const state =
              index === currentIndex
                ? 'current'
                : currentIndex !== -1 && index < currentIndex
                  ? 'complete'
                  : 'upcoming';
            const stateLabel = state === 'current' ? '当前' : state === 'complete' ? '已完成' : '待解锁';

            return `
              <li class="pathway-step is-${state}"${state === 'current' ? ' aria-current="step"' : ''}>
                <div class="pathway-step-index" aria-hidden="true">${state === 'complete' ? '✓' : String(index + 1).padStart(2, '0')}</div>
                <div class="pathway-step-copy">
                  <div class="panel-header-row pathway-step-head">
                    <p class="card-kicker">${escapeHtml(stage.kicker || `Step ${index + 1}`)}</p>
                    <span class="status-chip is-${state}">${escapeHtml(stateLabel)}</span>
                  </div>
                  <h3>${escapeHtml(stage.title)}</h3>
                  <p>${escapeHtml(stage.description)}</p>
                  <a class="pathway-link" href="${stage.target}">${escapeHtml(stage.actionLabel)} →</a>
                </div>
              </li>
            `;
          })
          .join('')}
      </ol>
    </article>
  `;
}

function renderNumberedCardGrid(items = [], { gridClassName = '', cardClassName = '', renderContent } = {}) {
  if (!items.length) {
    return '';
  }

  const gridClasses = ['card-grid', gridClassName].filter(Boolean).join(' ');
  const cardClasses = ['card', 'numbered-card', cardClassName].filter(Boolean).join(' ');

  return `
    <div class="${gridClasses}">
      ${items
        .map(
          (item, index) => `
            <article class="${cardClasses}">
              <span class="step-badge" aria-hidden="true">${index + 1}</span>
              ${renderContent(item, index)}
            </article>
          `
        )
        .join('')}
    </div>
  `;
}

function renderModuleCard(module, ctaLabel = '看懂这个问题') {
  const practiceCount = module.practiceEntries.length;
  const promptCount = module.tutorPrompts.length;
  const firstPractice = module.practiceEntries[0]?.label || '先从模块内容开始';
  const hasPracticeBadge = practiceCount > 0 ? '<span class="live-pill">含情景练习</span>' : '';

  return `
    <article class="card module-card" data-module="${escapeHtml(module.id)}">
      <header>
        <div class="panel-header-row">
          <p class="card-kicker">课程模块</p>
          ${hasPracticeBadge}
        </div>
        <h3>${escapeHtml(module.title)}</h3>
        <p class="card-eyeline">${escapeHtml(module.subtitle)}</p>
      </header>
      <p>${escapeHtml(module.shortDescription)}</p>
      ${renderTagRow(module.tags)}
      ${renderMetricStrip(
        [
          { value: String(practiceCount), label: '练习入口' },
          { value: String(promptCount), label: '助教提问示例' }
        ],
        'metric-strip-compact'
      )}
      <footer class="card-footer">
        <p class="card-inline-note">建议开始：${escapeHtml(firstPractice)}</p>
        <a class="button button-secondary" href="${module.route}">${escapeHtml(ctaLabel)}</a>
      </footer>
    </article>
  `;
}

function renderPracticeCard(practice, ctaLabel = '先做这个练习') {
  const module = getModule(practice.moduleId);
  const stepCount = practice.steps.length;

  return `
    <article class="card practice-card" data-module="${escapeHtml(practice.moduleId)}">
      <header>
        <p class="card-kicker">情景模拟</p>
        <h3>${escapeHtml(practice.title)}</h3>
      </header>
      <p>${escapeHtml(practice.summary)}</p>
      ${renderMetricStrip(
        [
          { value: module?.title || '未分类', label: '所属模块' },
          { value: String(stepCount), label: '练习步骤' }
        ],
        'metric-strip-compact'
      )}
      <footer class="card-footer">
        <p class="card-inline-note">目标：${escapeHtml(practice.goal)}</p>
        <a class="button button-secondary" href="${practice.route}">${escapeHtml(ctaLabel)}</a>
      </footer>
    </article>
  `;
}

function renderRiskHelpBanner({ mode = 'subtle', source = 'site', moduleId = '', practiceId = '' } = {}) {
  return `
    <section class="risk-banner-block" data-mode="${mode}" aria-labelledby="risk-banner-title">
      <div class="risk-banner-content">
        <p class="eyebrow">风险帮助</p>
        <h3 id="risk-banner-title">${escapeHtml(homePage.riskHelp.title)}</h3>
        <p>${escapeHtml(homePage.riskHelp.description)}</p>
        ${renderTagRow(homePage.riskHelp.actionPoints || [])}
      </div>
      <a class="button button-ghost" href="${buildRiskHelpPageUrl({ source, moduleId, practiceId })}">先看风险帮助</a>
    </section>
  `;
}

function renderPromptLinks(prompts, context = {}, { id = '', className = '' } = {}) {
  const classes = ['chip-list', className].filter(Boolean).join(' ');
  const idAttribute = id ? ` id="${escapeHtml(id)}"` : '';

  return `
    <div class="${classes}"${idAttribute}>
      ${prompts
        .map(
          (prompt) =>
            `<a class="chip-link" href="${buildTutorUrl(prompt, context)}">${escapeHtml(prompt)}</a>`
        )
        .join('')}
    </div>
  `;
}

function renderModuleSwitchRail(currentModuleId) {
  return `
    <section class="section compact-section" id="module-switcher">
      <article class="card module-switcher">
        <header class="panel-header-row">
          <p class="card-kicker">模块切换</p>
          <span class="context-pill">统一模板</span>
        </header>
        <p class="module-switch-copy">保留当前阅读节奏，按你此刻的困扰快速切换到其他主题。</p>
        <div class="chip-list module-switch-list" aria-label="模块切换入口">
          ${modules
            .map((entry) => {
              if (entry.id === currentModuleId) {
                return `<span class="chip-link is-current" aria-current="true">${escapeHtml(entry.title)}（当前）</span>`;
              }
              return `<a class="chip-link" href="${entry.route}">${escapeHtml(entry.title)}</a>`;
            })
            .join('')}
        </div>
      </article>
    </section>
  `;
}

function getRouteTone(target) {
  if (target.startsWith('/modules')) return 'module';
  if (target.startsWith('/practice')) return 'practice';
  if (target.startsWith('/risk-help')) return 'risk';
  return 'tutor';
}

function getRiskLevelLabel(riskLevel) {
  if (riskLevel === 'high') return '高风险联动';
  if (riskLevel === 'medium') return '中风险联动';
  return '常驻安全出口';
}

function getSourceLabel(source) {
  const labelMap = {
    home: '首页',
    modules: '模块总览',
    module: '当前模块页',
    tutor: '智能助教',
    practice: '当前练习页',
    site: '站内入口'
  };
  return labelMap[source] || '站内入口';
}

function buildRiskReturnLinks(riskContext = {}) {
  const links = [];
  const addLink = (label, target) => {
    if (!label || !target || links.some((item) => item.target === target)) return;
    links.push({ label, target });
  };

  if (riskContext.practice?.route) addLink('回当前练习', riskContext.practice.route);
  if (riskContext.module?.route) addLink('回当前模块', riskContext.module.route);
  if (riskContext.source === 'tutor') {
    const tutorTarget = buildTutorUrl('', {
      moduleId: riskContext.module?.id || '',
      practiceId: riskContext.practice?.id || ''
    });
    addLink('回助教页', tutorTarget.replace(/\?$/u, '') || '/tutor');
  }
  addLink('回模块总览', '/modules');
  addLink('回首页', '/');
  return links.slice(0, 4);
}

function getRiskReasonText(reason = '') {
  if (!reason) {
    return '';
  }
  return riskReasonCopy[reason] || `触发标记：${reason}`;
}

function renderRiskContextCard(riskContext = {}) {
  if (!riskContext.source && !riskContext.riskLevel && !riskContext.module && !riskContext.practice) return '';

  const sourceLabel = getSourceLabel(riskContext.source || 'site');
  const reasonText = getRiskReasonText(riskContext.reason || '');

  const chips = [
    sourceLabel,
    getRiskLevelLabel(riskContext.riskLevel),
    riskContext.module?.title,
    riskContext.practice?.title,
    reasonText ? '触发原因已记录' : ''
  ]
    .filter(Boolean)
    .map((item) => `<span class="tag">${escapeHtml(item)}</span>`)
    .join('');

  const copy =
    riskContext.riskLevel === 'high'
      ? '由于识别到极高风险，全站入口已自动锁定至安全模式。请优先执行下方的直接救助动作。'
      : riskContext.riskLevel === 'medium'
        ? '根据当前对话反馈，我们建议您优先关注现实支持。以下联动信息已为您准备好。'
        : '此页作为常驻安全出口，在您感到不适时提供即时支持。';

  return `
    <section class="section compact-section">
      <article class="card risk-context-card is-${escapeHtml(riskContext.riskLevel || 'low')}" data-risk="${escapeHtml(riskContext.riskLevel || 'low')}">
        <header class="panel-header-row">
           <p class="card-kicker">全站联动上下文</p>
           <span class="live-pill">实时状态同步</span>
        </header>
        <h2>你是从 ${escapeHtml(sourceLabel)} 进入的</h2>
        <p class="context-copy">${escapeHtml(copy)}</p>
        ${reasonText ? `<p class="risk-reason-note">${escapeHtml(reasonText)}</p>` : ''}
        <div class="tag-row">${chips}</div>
      </article>
    </section>
  `;
}

function renderRiskActionDeck(riskContext = {}) {
  const returnLinks = buildRiskReturnLinks(riskContext);
  const fallbackLink = returnLinks.find((item) => item.target !== '/');

  return `
    <section class="section compact-section" id="risk-actions">
      <article class="card split-card risk-action-deck">
        <div>
          <p class="card-kicker">先执行动作</p>
          <h2>先把自己放在更安全的位置</h2>
          <p>如果你已经明显顶不住，请先联系现实中的人或紧急热线，再考虑回到站内内容。</p>
        </div>
        <div class="button-stack">
          <a class="button button-danger" href="tel:110">立即拨打 110</a>
          <a class="button button-secondary" href="#contacts">查看可联系对象</a>
          ${fallbackLink ? `<a class="button button-ghost" href="${fallbackLink.target}">${escapeHtml(fallbackLink.label)}</a>` : ''}
        </div>
      </article>
    </section>
  `;
}

export function renderHomePage() {
  const featuredPractices = [getPractice('roommate-talk'), getPractice('exam-reset'), getPractice('emotion-cooldown')].filter(Boolean);

  const content = `
    <main class="page page-home" id="main-content" tabindex="-1">
      <section class="hero hero-home">
        <div class="hero-copy">
          <header class="hero-lead-row">
            <p class="eyebrow">${escapeHtml(homePage.hero.kicker || 'Round 1')}</p>
            <div class="live-indicator">
              <span class="live-dot"></span>
              <span class="live-pill">助教在线 · 24h 响应</span>
            </div>
          </header>
          <h1>${escapeHtml(homePage.hero.title)}</h1>
          <p class="hero-text">${escapeHtml(homePage.hero.subtitle)}</p>
          <div class="hero-intro-box">
             <p>${escapeHtml(homePage.hero.intro)}</p>
          </div>
          <div class="button-row">
            <a class="button button-primary" href="${homePage.hero.primaryCta.target}">${escapeHtml(homePage.hero.primaryCta.label)}</a>
            <a class="button button-secondary" href="${homePage.hero.secondaryCta.target}">${escapeHtml(homePage.hero.secondaryCta.label)}</a>
          </div>
          ${renderTagRow(homePage.hero.supportChips || [], 'tag-row hero-chip-row')}
          ${renderMetricStrip(homePage.hero.metrics, 'hero-metrics')}
        </div>
        <aside class="hero-side">
          <article class="card hero-visual-card">
            <div class="orb-container" aria-hidden="true">
               <div class="orb orb-1"></div>
               <div class="orb orb-2"></div>
            </div>
            <header class="panel-header-row">
              <p class="card-kicker">陪伴入口</p>
            </header>
            <h2>别把困扰想成一团</h2>
            <p>我们先做三件事：定位问题、找到动作、保留出口。</p>
            <nav class="hero-quicklist" aria-label="快速入口">
              <a class="signal-row" href="/tutor">向助教寻求引导</a>
              <a class="signal-row" href="/practice/exam-reset">5分钟快速练习</a>
              <a class="signal-row" href="/risk-help">查看安全支持</a>
            </nav>
          </article>
          <article class="card hero-status-card">
            <header class="panel-header-row">
               <p class="card-kicker">当前主链路</p>
               <span class="context-pill">已串通</span>
            </header>
            ${renderTextList(homePage.heroFlow || [], { ordered: true, className: 'hero-flow' })}
            <footer class="hero-status">
              <span class="status-dot"></span>
              <p>${escapeHtml(homePage.heroStatus || '内容、助教、练习与风险帮助已接通。')}</p>
            </footer>
          </article>
        </aside>
      </section>

      <section class="section" id="home-routes">
        ${renderSectionHeader(homePage.routeSection.title, homePage.routeSection.description, '入口设计')}
        <div class="card-grid route-grid">
          ${homePage.routeCards
            .map(
              (item) => `
                <article class="card route-card" data-tone="${getRouteTone(item.target)}">
                  <header><p class="card-kicker">切入点</p></header>
                  <h3>${escapeHtml(item.title)}</h3>
                  <p>${escapeHtml(item.description)}</p>
                  <footer class="card-footer">
                    <a class="button button-secondary" href="${item.target}">${escapeHtml(item.label)}</a>
                  </footer>
                </article>
              `
            )
            .join('')}
        </div>
      </section>

      <section class="section" id="home-modules">
        ${renderSectionHeader(homePage.moduleSection.title, homePage.moduleSection.description, '核心内容')}
        <div class="card-grid module-grid">
          ${modules.map((module) => renderModuleCard(module)).join('')}
        </div>
      </section>

      <section class="section" id="home-journey">
        ${renderPathwayRail('identify', {
          title: homePage.journeySection.title,
          description: homePage.journeySection.description,
          className: 'pathway-shell-home'
        })}
      </section>

      <section class="section" id="home-practice">
        ${renderSectionHeader(homePage.practiceSection.title, homePage.practiceSection.description, '情景模拟')}
        <div class="card-grid practice-grid">
          ${featuredPractices.map((practice) => renderPracticeCard(practice)).join('')}
        </div>
      </section>

      <section class="section tutor-entry" id="home-tutor">
        <article class="card split-card tutor-entry-card">
          <div class="tutor-entry-main">
            <header class="section-heading">
              <p class="eyebrow">智能对话</p>
              <h2>${escapeHtml(homePage.tutorEntry.title)}</h2>
              <p>${escapeHtml(homePage.tutorEntry.description)}</p>
            </header>
            ${renderPromptLinks(homePage.tutorEntry.quickPrompts)}
            <footer class="card-footer">
              <a class="button button-primary" href="/tutor">开始对话</a>
            </footer>
          </div>
          <aside class="tutor-entry-side">
            <p class="card-kicker">助教功能点</p>
            ${renderTextList(homePage.tutorEntry.highlights || [], { className: 'compact-list' })}
          </aside>
        </article>
      </section>

      <section class="section" id="home-safety">
        ${renderRiskHelpBanner({ source: 'home' })}
      </section>
    </main>
  `;

  return renderLayout({
    title: '首页',
    currentPath: '/',
    content
  });
}

export function renderModulesIndexPage() {
  const modulesTutorUrl = buildTutorUrl('');
  const modulesRiskHelpUrl = buildRiskHelpPageUrl({ source: 'modules' });

  const content = `
    <main class="page page-modules" id="main-content" tabindex="-1">
      <header class="page-header modules-header">
        <div class="header-main">
          <p class="eyebrow">${escapeHtml(modulesIndexPage.kicker || 'Overview')}</p>
          <h1>课程模块</h1>
          <p class="hero-text">选择最符合你当前状态的主题。这一轮我们聚焦于最常见的校园卡点。</p>
          ${renderMetricStrip(
            [
              { value: String(modules.length), label: '优先模块' },
              { value: '上下文联动', label: '支持一带进入助教' },
              { value: '场景化练习', label: '保留专属入口' }
            ],
            'metric-strip-compact'
          )}
          <nav class="section-nav" aria-label="模块页导航">
            <a href="#module-pathway">主线位置</a>
            <a href="#module-grid">浏览主题</a>
            <a href="${modulesTutorUrl}">助教引导</a>
            <a href="${modulesRiskHelpUrl}">安全出口</a>
          </nav>
        </div>
        <aside class="card page-header-aside">
          <p class="card-kicker">如何选择</p>
          <ul class="bullet-list compact-list">
            ${(modulesIndexPage.decisionTips || []).map((item) => `<li>${escapeHtml(item)}</li>`).join('')}
          </ul>
        </aside>
      </header>

      <section class="section compact-section" id="module-pathway">
        ${renderPathwayRail('identify', {
          title: '你现在在第 1 步：先看清问题',
          description: '模块页负责把“我很难受”拆成更具体的校园场景，再决定下一跳是助教、练习还是安全出口。',
          className: 'pathway-shell-inline',
          compact: true
        })}
      </section>

      <section class="section" id="module-grid">
        <div class="card-grid module-grid">
          ${modules.map((module) => renderModuleCard(module)).join('')}
        </div>
      </section>

      <section class="section">
        <article class="card split-card">
          <div>
            <p class="card-kicker">仍不确定？</p>
            <h2>让助教帮你定位</h2>
            <p>直接告诉助教你最近遇到的难事，它会帮你匹配最合适的模块和练习。</p>
          </div>
          <div class="button-stack">
            <a class="button button-primary" href="${modulesTutorUrl}">进入助教页</a>
            <a class="button button-secondary" href="${modulesRiskHelpUrl}">了解风险支持</a>
          </div>
        </article>
      </section>
    </main>
  `;

  return renderLayout({
    title: '课程模块',
    currentPath: '/modules',
    content
  });
}

export function renderModulePage(module) {
  const practiceCards = module.practiceEntries
    .map((entry) => getPractice(entry.id))
    .filter(Boolean)
    .map((practice) => renderPracticeCard(practice, '开始练习'))
    .join('');

  const tutorContext = { moduleId: module.id };
  const moduleRiskHelpUrl = buildRiskHelpPageUrl({ source: 'module', moduleId: module.id });

  const content = `
    <main class="page page-module" id="main-content" tabindex="-1">
      <header class="page-header module-hero">
        <div data-module="${escapeHtml(module.id)}">
          <p class="eyebrow">模块详情</p>
          <h1>${escapeHtml(module.title)}</h1>
          <p class="hero-text">${escapeHtml(module.subtitle)}</p>
          <p>${escapeHtml(module.intro)}</p>
          ${renderMetricStrip(
            [
              { value: String(module.problemList.length), label: '典型困扰' },
              { value: String(module.methods.length), label: '核心动作' },
              { value: String(module.practiceEntries.length), label: '练习入口' }
            ],
            'metric-strip-compact'
          )}
          <nav class="section-nav" aria-label="模块内导航">
            <a href="#pathway">主线位置</a>
            <a href="#module-switcher">切换模块</a>
            <a href="#prompts">快捷发问</a>
            <a href="#problems">常见困扰</a>
            <a href="#insights">核心认识</a>
            <a href="#methods">试试看</a>
            <a href="#practice">去练习</a>
            <a href="${moduleRiskHelpUrl}">安全出口</a>
          </nav>
        </div>
        <aside class="card module-summary" data-module="${escapeHtml(module.id)}">
          <p class="card-kicker">适合你，如果</p>
          ${renderTagRow(module.tags)}
          ${renderTextList(module.problemList.slice(0, 3), { className: 'compact-list emphasis-list' })}
          <a class="button button-primary" href="${buildTutorUrl(module.tutorPrompts[0] || '', tutorContext)}">向助教提问</a>
        </aside>
      </header>

      ${renderModuleSwitchRail(module.id)}

      <section class="section compact-section" id="pathway">
        ${renderPathwayRail('identify', {
          title: '先在这个模块里把问题看清',
          description: '你仍处在主线的“识别”阶段。先定位触发场景，再去助教页拿动作或进入练习页试一次。',
          className: 'pathway-shell-inline',
          compact: true
        })}
      </section>

      <section class="section compact-section" id="prompts">
        <article class="card split-card">
          <div>
            <p class="card-kicker">别在脑子里空转</p>
            <h2>带着这个场景直接去问</h2>
            <p>如果你已经大致定位了问题，但还不知道第一句话怎么说，直接把场景丢给助教。</p>
            ${renderPromptLinks(module.tutorPrompts.slice(0, 3), tutorContext, { id: 'module-prompts', className: 'module-prompts' })}
          </div>
          <div class="button-stack">
            <p class="card-inline-note">建议直接点一条最贴近现状的话，再继续补充细节。</p>
            <a class="button button-primary" href="${buildTutorUrl(module.tutorPrompts[0] || '', tutorContext)}">开始对话</a>
          </div>
        </article>
      </section>

      <section class="section" id="problems">
        ${renderSectionHeader('你可能正面对的情况', '先确认你的感受，不必急于行动。', '问题定位')}
        <div class="section-split">
          <div class="card list-card">
            ${renderTextList(module.problemList)}
          </div>
          <aside class="card side-note-card">
            <p class="card-kicker">小提示</p>
            <p>先关注一个最让你耗能的问题。只要这个点有突破，其他部分往往会随之改善。</p>
            <a class="button button-ghost" href="#methods">直接看动作</a>
          </aside>
        </div>
      </section>

      <section class="section" id="insights">
        ${renderSectionHeader('核心认识', '关于这个问题，你可能需要先了解的几个点。', '认知重构')}
        ${renderNumberedCardGrid(module.insights, {
          gridClassName: 'insight-grid',
          cardClassName: 'detail-card',
          renderContent: (item) => `
            <h3>${escapeHtml(item.title)}</h3>
            <p>${escapeHtml(item.body)}</p>
          `
        })}
      </section>

      <section class="section">
        ${renderSectionHeader('常见误区', '这些想法可能会增加你的额外心理负担。', '避坑指南')}
        <div class="card-grid misconception-grid">
          ${module.misunderstandings
            .map(
              (item) => `
                <article class="card compact-card warning-card">
                  <p>${escapeHtml(item)}</p>
                </article>
              `
            )
            .join('')}
        </div>
      </section>

      <section class="section" id="methods">
        ${renderSectionHeader('试试这些动作', '所有建议都旨在帮助你迈出最小的一步。', '行动方案')}
        ${renderNumberedCardGrid(module.methods, {
          gridClassName: 'method-grid',
          cardClassName: 'detail-card',
          renderContent: (item) => `
            <h3>${escapeHtml(item.title)}</h3>
            <p>${escapeHtml(item.body)}</p>
          `
        })}
      </section>

      <section class="section" id="practice">
        ${renderSectionHeader('进入场景练习', '在真实的情景中模拟，帮你的想法落地。', '技能内化')}
        <div class="section-split">
          <div class="card-grid practice-grid">
            ${practiceCards || '<article class="card"><p>该模块的练习正在完善中，请先使用助教引导。</p></article>'}
          </div>
          <aside class="card side-note-card">
            <p class="card-kicker">建议顺序</p>
            ${renderTextList(
              ['选一个贴近现状的练习。', '只关注一句话的表达。', '完成后如有余力再继续。'],
              { ordered: true, className: 'compact-list' }
            )}
          </aside>
        </div>
      </section>

      <section class="section" id="resources">
        ${renderSectionHeader('推荐资源', '进一步阅读或获取支持的入口。', '延伸学习')}
        <div class="card-grid resource-grid">
          ${module.relatedResources
            .map(
              (resource) => `
                <article class="card resource-card">
                  <h3>${escapeHtml(resource.title)}</h3>
                  <p>${escapeHtml(resource.summary)}</p>
                </article>
              `
            )
            .join('')}
        </div>
      </section>

      <footer class="section">
        ${renderRiskHelpBanner({ source: 'module', moduleId: module.id })}
      </footer>
    </main>
  `;

  return renderLayout({
    title: module.title,
    currentPath: module.route,
    navContext: { source: 'module', moduleId: module.id },
    content
  });
}

export function renderPracticePage(practice) {
  const module = getModule(practice.moduleId);
  const practiceTutorUrl = buildTutorUrl('在这个场景下，我该如何起头？', {
    moduleId: practice.moduleId,
    practiceId: practice.id
  });
  const practiceRiskHelpUrl = buildRiskHelpPageUrl({
    source: 'practice',
    moduleId: practice.moduleId,
    practiceId: practice.id
  });

  const content = `
    <main class="page page-practice" id="main-content" tabindex="-1">
      <header class="page-header practice-header">
        <div>
          <p class="eyebrow">${escapeHtml(practicePage.kicker || 'Scenario')}</p>
          <h1>${escapeHtml(practice.title)}</h1>
          <p class="hero-text">${escapeHtml(practice.summary)}</p>
          ${renderMetricStrip(
            [
              { value: module?.title || '未分类', label: '所属主题' },
              { value: String(practice.steps.length), label: '关键步骤' },
              { value: String(practice.feedbackFocus.length), label: '关注维度' }
            ],
            'metric-strip-compact'
          )}
          <nav class="section-nav" aria-label="练习页导航">
            <a href="#practice-pathway">主线位置</a>
            <a href="#practice-context">场景背景</a>
            <a href="#practice-sample">示范引导</a>
            <a href="#practice-reflection">反思小结</a>
            <a href="${practiceRiskHelpUrl}">安全出口</a>
          </nav>
        </div>
        <aside class="card page-header-aside">
          <p class="card-kicker">练习原则</p>
          <ul class="bullet-list compact-list">
            ${(practicePage.heroChecklist || []).map((item) => `<li>${escapeHtml(item)}</li>`).join('')}
          </ul>
          <div class="button-stack">
            <a class="button button-secondary" href="${module?.route || '/modules'}">查看模块方法</a>
            <a class="button button-ghost" href="${practiceTutorUrl}">问问助教</a>
          </div>
        </aside>
      </header>

      <section class="section compact-section" id="practice-pathway">
        ${renderPathwayRail('practice', {
          title: '你现在在第 3 步：把动作练顺',
          description: '练习页不是考试，而是先把一句话或一个动作练到足够能带回现实情境。',
          className: 'pathway-shell-inline',
          compact: true
        })}
      </section>

      <div class="practice-layout" id="practice-context">
        <article class="card">
          <header><p class="card-kicker">情景设定</p></header>
          <h2>你目前面对的情况</h2>
          <p>${escapeHtml(practice.context.situation)}</p>
          <dl class="meta-stack">
            <div><dt>你的角色</dt><dd>${escapeHtml(practice.context.userRole)}</dd></div>
            <div><dt>对方/环境</dt><dd>${escapeHtml(practice.context.otherRole)}</dd></div>
          </dl>
        </article>

        <article class="card">
          <header><p class="card-kicker">行动目标</p></header>
          <h2>尝试完成以下步骤</h2>
          <ol class="ordered-list">
            ${practice.steps.map((step) => `<li>${escapeHtml(step)}</li>`).join('')}
          </ol>
        </article>
      </div>

      <section class="section" id="practice-sample">
        ${renderSectionHeader('你可以尝试这样说', '这只是一个参考，重要的是表达出你的核心意思。', '示范引导')}
        <article class="card quote-card">
          <p>${escapeHtml(practice.sampleLine)}</p>
        </article>
      </section>

      <section class="section" id="practice-feedback">
        ${renderSectionHeader('你可以关注这些点', '在表达时，尝试观察这些维度的反馈。', '自测重点')}
        <div class="card-grid resource-grid">
          ${practice.feedbackFocus
            .map(
              (item) => `
                <article class="card compact-card">
                  <header><h3>${escapeHtml(item)}</h3></header>
                </article>
              `
            )
            .join('')}
        </div>
      </section>

      <section class="section" id="practice-reflection">
        ${renderSectionHeader('练习后小结', '记录你的感受，这能帮你更好地内化。', '反思复盘')}
        <div class="card list-card">
          <ul class="bullet-list">
            ${practice.reflectionQuestions.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}
          </ul>
        </div>
      </section>

      <section class="section">
        <article class="card split-card">
          <div>
            <p class="card-kicker">接下来</p>
            <h2>继续深入或尝试其他</h2>
            <p>你可以回到模块继续学习，或者带着刚练过的场景去问助教。</p>
          </div>
          <div class="button-stack">
            ${practice.nextActions
              .map((action) => `<a class="button button-secondary" href="${action.target}">${escapeHtml(action.label)}</a>`)
              .join('')}
          </div>
        </article>
      </section>

      <footer class="section" id="practice-safety">
        ${renderRiskHelpBanner({ source: 'practice', moduleId: practice.moduleId, practiceId: practice.id })}
      </footer>
    </main>
  `;

  return renderLayout({
    title: practice.title,
    currentPath: practice.route,
    navContext: {
      source: 'practice',
      moduleId: practice.moduleId,
      practiceId: practice.id
    },
    content
  });
}

export function renderTutorPage(bootstrapData) {
  const contextModuleId = bootstrapData.contextModuleId || '';
  const contextPracticeId = bootstrapData.contextPracticeId || '';
  const tutorRiskHelpUrl = buildRiskHelpPageUrl({
    source: 'tutor',
    moduleId: contextModuleId,
    practiceId: contextPracticeId
  });
  const tutorEmergencyUrl = buildRiskHelpPageUrl({
    source: 'tutor',
    moduleId: contextModuleId,
    practiceId: contextPracticeId,
    reason: 'emergency',
    hash: '#emergency'
  });
  const tutorSupportUrl = buildRiskHelpPageUrl({
    source: 'tutor',
    moduleId: contextModuleId,
    practiceId: contextPracticeId,
    reason: 'contact-support',
    hash: '#contacts'
  });

  const apiMeta = bootstrapData.apiMeta || {};
  const apiChecklist = tutorPage.apiPreparation?.checklist || [];
  const apiStatusRows = [
    { label: '密钥状态', status: apiMeta.envStatus?.DASHSCOPE_API_KEY || apiMeta.envStatus?.QWEN_API_KEY ? '已配置' : '待配置' },
    { label: '当前模型', status: apiMeta.modelLabel || bootstrapData.modelLabel || 'qwen-plus' },
    { label: '交互接口', status: apiMeta.endpoint || '/api/tutor' }
  ];

  const content = `
    <main class="page page-tutor" id="main-content" tabindex="-1">
      <header class="page-header tutor-header">
        <div class="header-main">
          <p class="eyebrow">${escapeHtml(tutorPage.kicker || 'Assistant')}</p>
          <h1>${escapeHtml(tutorPage.title)}</h1>
          <p class="hero-text">${escapeHtml(tutorPage.subtitle)}</p>
          <div class="card-inline-note risk-warning-pill">${escapeHtml(tutorPage.disclaimer)}</div>
          <p class="tutor-note">${escapeHtml(tutorPage.panelNote)}</p>
          ${renderMetricStrip(
            [
              { value: bootstrapData.modelConfigured ? '模型已就绪' : '本地兜底', label: '核心链路' },
              { value: bootstrapData.contextTitle || '全站通行', label: '当前上下文' }
            ],
            'metric-strip-compact'
          )}
          <nav class="section-nav" aria-label="助教页导航">
            <a href="#tutor-pathway">主线位置</a>
            <a href="#tutor-workbench">进入工作台</a>
            <a href="#tutor-flow">使用说明</a>
            <a href="#tutor-principles">工作方式</a>
            <a href="${tutorRiskHelpUrl}">安全出口</a>
          </nav>
        </div>
        <aside class="card api-card">
          <header><p class="card-kicker">系统状态</p></header>
          <p>${escapeHtml(tutorPage.apiPreparation?.description || tutorPage.panelNote)}</p>
          <div class="status-list">
            ${apiStatusRows
              .map(
                (item) => `
                  <div class="status-row">
                    <span>${escapeHtml(item.label)}</span>
                    <strong class="status-badge">${escapeHtml(item.status)}</strong>
                  </div>
                `
              )
              .join('')}
          </div>
          ${renderTextList(apiChecklist, { className: 'compact-list list-block-spaced' })}
        </aside>
      </header>

      <section class="section compact-section" id="tutor-pathway">
        ${renderPathwayRail('guide', {
          title: '你现在在第 2 步：先拿到下一步动作',
          description: '助教页的任务不是长谈，而是把你带到最相关的模块、练习或现实支持入口。',
          className: 'pathway-shell-inline',
          compact: true
        })}
      </section>

      <section class="section compact-section" id="tutor-flow">
        <div class="section-split tutor-flow-layout">
          <article class="card tutor-flow-card">
            <header class="section-heading">
              <p class="eyebrow">使用流程</p>
              <h2>${escapeHtml(tutorPage.flowTitle)}</h2>
            </header>
            ${renderNumberedCardGrid(tutorPage.usageSteps || [], {
              gridClassName: 'tutor-flow-grid',
              cardClassName: 'compact-card',
              renderContent: (item) => `
                <h3>${escapeHtml(item.title)}</h3>
                <p>${escapeHtml(item.body)}</p>
              `
            })}
          </article>

          <aside class="card tutor-principles-card">
            <p class="card-kicker">工作方式</p>
            <h2>${escapeHtml(tutorPage.roleName)}</h2>
            <p>${escapeHtml(tutorPage.roleDescription)}</p>
            ${renderTextList(tutorPage.responsePrinciples || [], { className: 'compact-list emphasis-list' })}
          </aside>
        </div>
      </section>

      <section class="tutor-workbench" id="tutor-workbench">
        <aside class="tutor-sidebar">
          <article class="card avatar-panel" id="avatar-panel" data-state="welcome">
            <header class="panel-header-row">
              <p class="card-kicker">课程助教</p>
              <span class="live-pill" id="avatar-live-pill">正常在线</span>
            </header>
            <div class="avatar-orb" aria-hidden="true"></div>
            <h2 id="avatar-state-title">你好</h2>
            <p id="avatar-state-copy">${escapeHtml(tutorPage.stateCopy.welcome)}</p>
            <p class="card-meta">${escapeHtml(tutorPage.roleDescription)}</p>
            <footer class="status-caption" id="avatar-status-caption">
              <p>模式：交互引导</p>
            </footer>
          </article>

          <article class="card" id="quick-prompts-panel">
            <header><p class="card-kicker">你可以这样问</p></header>
            <p>${escapeHtml(tutorPage.panelNote)}</p>
            <div class="chip-list prompt-chip-list" id="quick-prompts">
              ${tutorPage.quickPrompts
                .map((prompt) => `<button class="chip-button" type="button" data-prompt="${escapeHtml(prompt)}">${escapeHtml(prompt)}</button>`)
                .join('')}
            </div>
          </article>

          <article class="card" id="recommended-actions-panel">
            <header><p class="card-kicker">建议动作</p></header>
            <p class="panel-empty" id="recommended-actions-empty">对话开始后，这里会给你最贴近当前状态的下一步入口。</p>
            <div class="action-list" id="recommended-actions"></div>
          </article>
        </aside>

        <section class="card chat-panel">
          <header class="chat-toolbar">
            <div>
              <p class="card-kicker">对话窗口</p>
              <h3>尝试描述你的卡点</h3>
            </div>
            ${renderTagRow(tutorPage.surfaceTags || [])}
          </header>

          <div class="risk-banner-block is-inline inline-risk-banner" id="risk-banner" data-mode="subtle">
            <div class="risk-banner-content">
              <h3 id="risk-banner-title">风险帮助入口</h3>
              <p id="risk-banner-copy">如感状态极差，请优先使用此入口。</p>
            </div>
            <a class="button button-ghost" id="risk-banner-link" href="${tutorRiskHelpUrl}">查看支持</a>
          </div>

          <div class="chat-log" id="chat-log" aria-live="polite" role="log">
            <!-- 消息动态插入 -->
          </div>

          <form class="chat-form" id="tutor-form">
            <label class="sr-only" for="tutor-input">输入消息</label>
            <textarea id="tutor-input" name="message" rows="3" placeholder="${escapeHtml(tutorPage.composerHint)}"></textarea>
            <footer class="input-meta">
              <div class="input-meta-copy">
                <p class="card-meta">Enter 发送 / Shift+Enter 换行</p>
                <p class="input-count-wrap" aria-live="polite">已输入 <strong id="input-count">0</strong> 字</p>
              </div>
              <div class="button-row">
                <button class="button button-primary" type="submit" id="send-button">发送</button>
                <a class="button button-ghost" href="${tutorSupportUrl}">寻求现实支持</a>
              </div>
            </footer>
          </form>

          <article class="emergency-notice hidden" id="emergency-notice">
            <p class="card-kicker">紧急提示</p>
            <h3>如果你已经无法保证安全</h3>
            <p>先停止继续输入，直接联系身边的人或拨打紧急电话。风险帮助页里保留了现实支持入口。</p>
            <a class="button button-danger" href="${tutorEmergencyUrl}">立刻看紧急出口</a>
          </article>

          <article class="support-card hidden" id="real-support-card">
            <h3>建议先联系一个现实中的人</h3>
            <p>你可以联系辅导员、校心理中心或家人。不要一个人独自面对。</p>
            <a class="button button-secondary" href="${tutorSupportUrl}">看可以联系谁</a>
          </article>
        </section>
      </section>

      <section class="section" id="tutor-principles">
        ${renderSectionHeader('助教怎样帮助你推进', '这不是闲聊窗口，而是把问题、动作和出口串起来的工作台。', '工作方式')}
        ${renderNumberedCardGrid(tutorPage.responsePrinciples || [], {
          gridClassName: 'principle-grid',
          cardClassName: 'detail-card principle-card',
          renderContent: (item) => `<p>${escapeHtml(item)}</p>`
        })}
      </section>
    </main>
  `;

  const script = `
    <script>window.__TUTOR_BOOTSTRAP__ = ${serializeForScript(bootstrapData)};</script>
    <script type="module" src="/tutor.js"></script>
  `;

  return renderLayout({
    title: tutorPage.title,
    currentPath: '/tutor',
    navContext: {
      source: 'tutor',
      moduleId: contextModuleId,
      practiceId: contextPracticeId
    },
    content,
    script
  });
}

export function renderRiskHelpPage(riskContext = {}) {
  const returnLinks = buildRiskReturnLinks(riskContext);
  const returnCopy = riskContext.practice?.route ? '你可以随时回练习或模块。' : '你可以回模块或首页。';

  const content = `
    <main class="page page-risk-help" id="main-content" tabindex="-1">
      <header class="page-header risk-header">
        <div class="header-main">
          <p class="eyebrow">${escapeHtml(riskHelpPage.kicker || 'Safety')}</p>
          <h1>${escapeHtml(riskHelpPage.title)}</h1>
          <p class="hero-text">${escapeHtml(riskHelpPage.subtitle)}</p>
          <nav class="risk-anchor-list" aria-label="风险页内导航">
            <a href="#risk-pathway">主线位置</a>
            <a href="#support-principles">先稳住</a>
            <a href="#risk-actions">马上执行</a>
            <a href="#immediate-actions">即刻动作</a>
            <a href="#emergency">紧急提醒</a>
            <a href="#contacts">联系人</a>
            <a href="#support-resources">校内外支持</a>
            <a href="#aftercare">稳定之后</a>
          </nav>
        </div>
        <aside class="card risk-verify-card">
          <header><p class="card-kicker">核验提醒</p></header>
          <p>${escapeHtml(riskHelpPage.verificationNote)}</p>
          ${renderTextList(riskHelpPage.verificationChecklist || [], { className: 'compact-list' })}
        </aside>
      </header>

      ${renderRiskContextCard(riskContext)}
      ${renderRiskActionDeck(riskContext)}

      <section class="section compact-section" id="risk-pathway">
        ${renderPathwayRail('safety', {
          title: '你现在在第 4 步：先把安全放在最前面',
          description: '一旦状态已经明显过载，就允许直接跳出学习链路，优先处理现实支持与紧急联络。',
          className: 'pathway-shell-inline pathway-shell-risk',
          compact: true
        })}
      </section>

      <section class="section" id="support-principles">
        ${renderSectionHeader('先把自己放回更安全的位置', '这一页的优先级高于课程内容。先稳住，再考虑后续。', '优先原则')}
        ${renderNumberedCardGrid(riskHelpPage.supportPrinciples, {
          gridClassName: 'principle-grid',
          cardClassName: 'detail-card principle-card',
          renderContent: (item) => `
            <h3>${escapeHtml(item.title)}</h3>
            <p>${escapeHtml(item.body)}</p>
          `
        })}
      </section>

      <section class="section" id="immediate-actions">
        ${renderSectionHeader('先做这几步', '优先保障安全感，后续再处理其他。', '安全第一')}
        ${renderNumberedCardGrid(riskHelpPage.immediateActions, {
          gridClassName: 'urgent-grid',
          cardClassName: 'detail-card urgent-card',
          renderContent: (item) => `<p>${escapeHtml(item)}</p>`
        })}
      </section>

      <div class="risk-layout section-gap-top" id="contacts">
        <article class="card support-list-card">
          <header><p class="card-kicker">可以联系谁</p></header>
          ${renderTextList(riskHelpPage.contactPeople, { className: 'list-block' })}
        </article>

        <article class="card support-list-card" id="emergency">
          <header><p class="card-kicker">紧急提醒</p></header>
          <p class="helper-note">${escapeHtml(riskHelpPage.emergencyNote)}</p>
          <a class="button button-danger emergency-call-link" href="tel:110">拨打紧急电话 110</a>
        </article>
      </div>

      <section class="section" id="support-resources">
        ${renderSectionHeader('现实支持资源', '以下信息正式上线前需完成真实填入核验。', '支持体系')}
        <div class="card-grid route-grid">
          <article class="card" id="campus-support">
            <header><p class="card-kicker">校内渠道</p></header>
            ${renderTextList(riskHelpPage.campusSupport, { className: 'compact-list' })}
          </article>
          <article class="card" id="external-support">
            <header><p class="card-kicker">校外渠道</p></header>
            ${renderTextList(riskHelpPage.externalSupport, { className: 'compact-list' })}
          </article>
        </div>
      </section>

      <section class="section" id="aftercare">
        ${renderSectionHeader('稍微稳住之后', '等眼前最危险的阶段过去，再做这几步收口。', '后续安置')}
        ${renderNumberedCardGrid(riskHelpPage.aftercareSteps, {
          gridClassName: 'followup-grid',
          cardClassName: 'detail-card followup-card',
          renderContent: (item) => `<p>${escapeHtml(item)}</p>`
        })}
      </section>

      <section class="section">
        <article class="card split-card">
          <div>
            <p class="card-kicker">后续引导</p>
            <h2>稳定之后</h2>
            <p>${escapeHtml(returnCopy)}</p>
          </div>
          <div class="button-stack">
            ${returnLinks
              .map((item) => `<a class="button button-secondary" href="${item.target}">${escapeHtml(item.label)}</a>`)
              .join('')}
          </div>
        </article>
      </section>
    </main>
  `;

  return renderLayout({
    title: '风险帮助',
    currentPath: '/risk-help',
    navContext: {
      source: riskContext.source || 'site',
      moduleId: riskContext.module?.id || '',
      practiceId: riskContext.practice?.id || '',
      riskLevel: riskContext.riskLevel || '',
      reason: riskContext.reason || ''
    },
    content
  });
}

export function renderNotFoundPage() {
  const content = `
    <main class="page page-not-found" id="main-content" tabindex="-1">
      <header class="page-header not-found-shell">
        <div>
          <p class="eyebrow">${escapeHtml(notFoundPage.kicker || '404')}</p>
          <h1>${escapeHtml(notFoundPage.title)}</h1>
          <p class="hero-text">${escapeHtml(notFoundPage.description)}</p>
          <div class="button-row">
            <a class="button button-primary" href="/">回首页</a>
            <a class="button button-secondary" href="/modules">去模块页</a>
          </div>
        </div>
        <aside class="card page-header-aside">
          <p class="card-kicker">建议动作</p>
          <ul class="bullet-list compact-list">
            ${(notFoundPage.recoverySteps || []).map((item) => `<li>${escapeHtml(item)}</li>`).join('')}
          </ul>
        </aside>
      </header>
    </main>
  `;

  return renderLayout({
    title: notFoundPage.title,
    description: notFoundPage.description,
    currentPath: '',
    content
  });
}
