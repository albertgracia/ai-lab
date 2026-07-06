import { execSync } from 'child_process';
import { readFileSync, existsSync, rmSync, renameSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const ROOT = join(fileURLToPath(import.meta.url), '..', '..');
const SRC_CONTENT = join(ROOT, 'src', 'content');
const BAK_DIR = join(SRC_CONTENT, '.public-build-bak');

function loadManifest() {
  return JSON.parse(readFileSync(join(ROOT, 'scripts', 'private-content-filter.json'), 'utf-8'));
}

function backupAndRemove() {
  const manifest = loadManifest();
  if (existsSync(BAK_DIR)) {
    console.error('[build:public] ERROR: .public-build-bak already exists (previous build interrupted)');
    process.exit(1);
  }
  mkdirSync(BAK_DIR, { recursive: true });

  let removed = 0;
  for (const entry of manifest.content) {
    const absPath = join(SRC_CONTENT, entry.path);
    if (!existsSync(absPath)) continue;

    const bakPath = join(BAK_DIR, entry.path);
    const bakParent = dirname(bakPath);
    mkdirSync(bakParent, { recursive: true });
    renameSync(absPath, bakPath);
    removed++;
  }
  console.log(`[build:public] Backed up ${removed} private paths to .public-build-bak/`);
}

function restore() {
  if (!existsSync(BAK_DIR)) {
    console.log('[build:public] Nothing to restore');
    return;
  }
  const manifest = loadManifest();
  let restored = 0;
  for (const entry of manifest.content) {
    const bakPath = join(BAK_DIR, entry.path);
    if (!existsSync(bakPath)) continue;
    const targetPath = join(SRC_CONTENT, entry.path);
    const targetParent = dirname(targetPath);
    mkdirSync(targetParent, { recursive: true });
    renameSync(bakPath, targetPath);
    restored++;
  }
  rmSync(BAK_DIR, { recursive: true, force: true });
  console.log(`[build:public] Restored ${restored} private paths`);
}

backupAndRemove();
try {
  execSync('npx astro build', {
    stdio: 'inherit',
    env: { ...process.env, AILAB_PUBLIC_BUILD: 'true' },
    cwd: ROOT,
  });
  execSync('node scripts/generate-site-manifest.mjs', {
    stdio: 'inherit',
    cwd: ROOT,
  });
} finally {
  restore();
}
