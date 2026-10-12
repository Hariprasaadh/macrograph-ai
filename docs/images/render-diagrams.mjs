// Extracts every "<!-- fig: N slug -->" + mermaid block from ch*.md and renders PNG and SVG.
// Usage (from docs/images):  node render-diagrams.mjs [--only 6.1] [--no-svg]
// Requires: npm install   (installs @mermaid-js/mermaid-cli)
import { readdirSync, readFileSync, mkdirSync, writeFileSync, existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const only = args.includes('--only') ? args[args.indexOf('--only') + 1] : null;
const svg = !args.includes('--no-svg');
const mmdc = join(here, 'node_modules', '.bin', process.platform === 'win32' ? 'mmdc.cmd' : 'mmdc');
const srcDir = join(here, 'src');
const pngDir = join(here, 'png');
const svgDir = join(here, 'svg');
for (const d of [srcDir, pngDir, svgDir]) mkdirSync(d, { recursive: true });

const pattern = /<!--\s*fig:\s*([A-Za-z0-9.]+)\s+([a-z0-9-]+)\s*-->[\s\S]*?```mermaid\n([\s\S]*?)```/g;
let ok = 0, fail = 0;
for (const file of readdirSync(here).filter((f) => /^ch\d+.*\.md$/.test(f)).sort()) {
  const text = readFileSync(join(here, file), 'utf8').replaceAll('\r\n', '\n');
  for (const m of text.matchAll(pattern)) {
    const [, num, slug, code] = m;
    if (only && only !== num) continue;
    const base = `fig-${num.replace(/\./g, '-')}-${slug}`;
    const input = join(srcDir, `${base}.mmd`);
    writeFileSync(input, code, 'utf8');
    const formats = svg ? ['png', 'svg'] : ['png'];
    for (const fmt of formats) {
      const out = join(fmt === 'png' ? pngDir : svgDir, `${base}.${fmt}`);
      const cli = ['-i', input, '-o', out, '-c', join(here, 'mermaid-config.json'),
        '-p', join(here, 'puppeteer-config.json'), '-b', 'white', '-q'];
      if (fmt === 'png') cli.push('-s', '3');
      const r = spawnSync(mmdc, cli, { encoding: 'utf8', shell: process.platform === 'win32' });
      if (r.status === 0 && existsSync(out)) { ok++; } else { fail++; console.error(`FAIL ${base}.${fmt}\n${r.stderr || r.stdout}`); }
    }
    console.log(`rendered ${base}`);
  }
}
console.log(`done: ${ok} files ok, ${fail} failed`);
process.exit(fail ? 1 : 0);
