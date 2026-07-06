import { execSync } from 'child_process';
import { readdirSync, statSync, writeFileSync, readFileSync } from 'fs';
import { createHash } from 'crypto';
import { join } from 'path';
import { fileURLToPath } from 'url';

const ROOT = join(fileURLToPath(import.meta.url), '..', '..');
const DIST = join(ROOT, 'dist');

function getAllHtmlFiles(dir) {
  const files = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) files.push(...getAllHtmlFiles(full));
    else if (entry.name.endsWith('.html')) files.push(full);
  }
  return files;
}

function getCommitHash() {
  try {
    return execSync('git rev-parse --short HEAD', { cwd: ROOT, encoding: 'utf-8' }).trim();
  } catch {
    return 'unknown';
  }
}

const htmlFiles = getAllHtmlFiles(DIST);
const pages = htmlFiles.map(f => {
  const rel = f.replace(DIST, '').replace(/\\/g, '/').replace(/\/index\.html$/, '') || '/';
  const stat = statSync(f);
  const hash = createHash('sha256').update(readFileSync(f)).digest('hex').slice(0, 12);
  return { path: rel, size: stat.size, hash, mtime: stat.mtime.toISOString() };
});

const manifest = {
  generated: new Date().toISOString(),
  commit: getCommitHash(),
  total_pages: pages.length,
  pages: pages.sort((a, b) => a.path.localeCompare(b.path)),
};

writeFileSync(join(DIST, 'site-manifest.json'), JSON.stringify(manifest, null, 2));
console.log(`[site-manifest] Generated: ${pages.length} pages, commit ${manifest.commit}`);
