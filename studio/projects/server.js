import { existsSync, readFileSync } from 'node:fs';
import { createAppServer } from './src/server.js';

function loadDotEnv() {
  const envUrl = new URL('./.env', import.meta.url);

  if (!existsSync(envUrl)) {
    return;
  }

  const content = readFileSync(envUrl, 'utf8');

  for (const rawLine of content.split(/\r?\n/u)) {
    const line = rawLine.trim();

    if (!line || line.startsWith('#')) {
      continue;
    }

    const separatorIndex = line.indexOf('=');

    if (separatorIndex === -1) {
      continue;
    }

    const key = line.slice(0, separatorIndex).trim();
    const value = line.slice(separatorIndex + 1).trim().replace(/^['"]|['"]$/gu, '');

    if (key && process.env[key] === undefined) {
      process.env[key] = value;
    }
  }
}

loadDotEnv();

const port = Number(process.env.PORT || 3000);
const server = createAppServer();

server.listen(port, () => {
  console.log(`MVP site running at http://localhost:${port}`);
});
