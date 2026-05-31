#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const appRoot = process.cwd();
const rel = (...parts) => path.join(appRoot, ...parts);
let ok = true;

const fail = (msg) => {
  ok = false;
  console.error(msg);
};

const distHtmlPath = rel('dist', 'ai-infrastructure', 'index.html');
const pagePath = rel('src', 'pages', 'ai-infrastructure', 'index.astro');
const cssPath = rel('src', 'styles', 'global.css');
const visualFiles = [
  rel('src', 'components', 'visual', 'VisualSection.astro'),
  rel('src', 'components', 'visual', 'VisualCard.astro'),
  rel('src', 'components', 'visual', 'MetricBadge.astro'),
  rel('src', 'components', 'visual', 'RoadmapBlock.astro'),
];

if (!fs.existsSync(distHtmlPath)) {
  fail('FAIL: falta dist/ai-infrastructure/index.html');
}

const html = fs.existsSync(distHtmlPath) ? fs.readFileSync(distHtmlPath, 'utf8') : '';
const source = fs.existsSync(pagePath) ? fs.readFileSync(pagePath, 'utf8') : '';
const css = fs.existsSync(cssPath) ? fs.readFileSync(cssPath, 'utf8') : '';

for (const file of visualFiles) {
  if (!fs.existsSync(file)) {
    fail(`FAIL: falta componente visual requerido: ${path.relative(appRoot, file)}`);
  }
}

const requiredCss = [
  '.ai-visual-section',
  '.ai-visual-grid',
  '.ai-visual-card',
  '.ai-visual-card-title',
  '.ai-visual-card-kicker',
  '.ai-visual-metric',
  '.ai-visual-code-badge',
  '.ai-visual-callout',
  '.ai-visual-roadmap',
  '.ai-visual-safe-text',
];
for (const cls of requiredCss) {
  if (!css.includes(cls)) {
    fail(`FAIL: falta clase de sistema visual en CSS: ${cls}`);
  }
}

const technicalStrings = [
  'ailab_cognitive_health_score',
  'ai_lab:runtime_health_score',
  'no_nodes_online',
  'google/gemma-4-e4b',
  'qwen/qwen2.5-coder-14b-instruct',
];

const allowAnchors = ['<code', '<kbd', '<pre', 'ai-visual-code-badge', 'ai-visual-metric', 'ai-visual-safe-text'];
const headingBlocks = [...html.matchAll(/<h[1-6][^>]*>[\s\S]*?<\/h[1-6]>/gi)].map((match) => match[0]);

for (const needle of technicalStrings) {
  if (!html.includes(needle)) continue;
  const index = html.indexOf(needle);
  const window = html.slice(Math.max(0, index - 220), Math.min(html.length, index + needle.length + 220));
  const allowed = allowAnchors.some((anchor) => window.includes(anchor));
  const inHeading = headingBlocks.some((block) => block.includes(needle));
  if (inHeading) {
    fail(`FAIL: metrica larga detectada en heading: ${needle}`);
  } else if (!allowed) {
    fail(`FAIL: metrica larga detectada fuera de badge/code: ${needle}`);
  }
}

const visibleText = html
  .replace(/<script[\s\S]*?<\/script>/gi, ' ')
  .replace(/<style[\s\S]*?<\/style>/gi, ' ')
  .replace(/<[^>]+>/g, ' ')
  .replace(/\s+/g, ' ')
  .trim();

const englishPhrases = [
  'Working tree clean',
  'No tag',
  'Published',
  'Closing report',
  'Key findings',
  'Recommendation',
  'Next phase recommended',
];
for (const phrase of englishPhrases) {
  if (visibleText.includes(phrase)) {
    fail(`FAIL: resumen operativo en ingles detectado: ${phrase}`);
  }
}

const unsafeCards = [...source.matchAll(/<[^>]+class=['"][^'"]*rounded-(?:xl|2xl)[^'"]*['"][^>]*>/g)];
for (const match of unsafeCards) {
  const chunk = match[0];
  const safe = chunk.includes('min-w-0') || chunk.includes('ai-visual-');
  if (!safe) {
    fail('FAIL: card ad hoc sin min-width:0 o clases visuales oficiales');
    break;
  }
}

if (ok) {
  console.log('PASS: validacion visual basica superada');
} else {
  process.exitCode = 1;
}
