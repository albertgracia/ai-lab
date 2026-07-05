import { existsSync, renameSync, readdirSync } from 'fs';
import { join } from 'path';

const srcDir = new URL('../src/content/', import.meta.url);
const privDir = join(srcDir.pathname, 'private');
const privBak = join(srcDir.pathname, 'private.buildbak');

// Save private/ before public build
if (existsSync(privDir)) {
  if (existsSync(privBak)) {
    console.error('ERROR: private.buildbak already exists from a previous interrupted build');
    process.exit(1);
  }
  renameSync(privDir, privBak);
  const items = readdirSync(privBak).join(', ');
  console.log(`[build:public] Moved private/ to private.buildbak (${items})`);
} else {
  console.log('[build:public] No private/ directory found, nothing to filter');
}
