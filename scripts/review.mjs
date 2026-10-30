import { spawn } from 'node:child_process';

const child = spawn(process.execPath, ['node_modules/astro/bin/astro.mjs', ...process.argv.slice(2)], {
  env: { ...process.env, REVIEW_CONTENT:'true' }, stdio:'inherit',
});
child.on('exit', code => { process.exitCode = code ?? 1; });
