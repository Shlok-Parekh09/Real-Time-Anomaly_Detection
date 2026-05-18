import { spawn } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const rootDir = dirname(dirname(fileURLToPath(import.meta.url)));
const backendDir = join(rootDir, 'fraud_detection_system', 'backend');
const viteBin = join(rootDir, 'node_modules', '.bin', process.platform === 'win32' ? 'vite.cmd' : 'vite');
const pythonBin = process.platform === 'win32' ? 'python' : 'python3';
const frontendCommand = process.platform === 'win32' ? 'cmd.exe' : viteBin;
const frontendArgs = process.platform === 'win32'
  ? ['/d', '/s', '/c', 'node_modules\\.bin\\vite.cmd --host 127.0.0.1 --port 5173 --strictPort']
  : ['--host', '127.0.0.1', '--port', '5173', '--strictPort'];
const children = [];
let stopping = false;

function run(name, command, args, cwd) {
  return new Promise((resolve, reject) => {
    console.log(`[${name}] running`);
    const child = spawn(command, args, {
      cwd,
      env: { ...process.env, PYTHONUNBUFFERED: '1' },
      stdio: 'inherit',
      windowsHide: true,
    });

    child.on('exit', (code) => {
      if (code === 0) {
        resolve();
        return;
      }
      reject(new Error(`${name} exited with code ${code}`));
    });
    child.on('error', reject);
  });
}

function checkBackendDependencies() {
  return new Promise((resolve) => {
    const child = spawn(
      pythonBin,
      ['-c', 'import fastapi, uvicorn, multipart, cv2, PIL, pydantic, pypdf, pytesseract'],
      {
        cwd: backendDir,
        stdio: 'ignore',
        windowsHide: true,
      }
    );
    child.on('exit', (code) => resolve(code === 0));
    child.on('error', () => resolve(false));
  });
}

async function ensureBackendDependencies() {
  if (await checkBackendDependencies()) {
    return;
  }

  console.log('[backend setup] installing Python dependencies from fraud_detection_system/backend/requirements.txt');
  await run(
    'backend setup',
    pythonBin,
    ['-m', 'pip', 'install', '-r', join(backendDir, 'requirements.txt')],
    rootDir
  );
}

function start(name, command, args, cwd) {
  console.log(`[${name}] starting`);
  const child = spawn(command, args, {
    cwd,
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
    stdio: 'inherit',
    windowsHide: true,
  });

  child.on('exit', (code, signal) => {
    if (stopping) return;
    const reason = signal ? `signal ${signal}` : `code ${code}`;
    console.error(`[${name}] exited with ${reason}`);
    stop(code ?? 1);
  });

  child.on('error', (error) => {
    if (stopping) return;
    console.error(`[${name}] failed to start: ${error.message}`);
    stop(1);
  });

  children.push(child);
  return child;
}

function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  for (const child of children) {
    if (!child.killed) {
      child.kill('SIGTERM');
    }
  }
  setTimeout(() => process.exit(code), 250).unref();
}

process.on('SIGINT', () => stop(0));
process.on('SIGTERM', () => stop(0));

console.log('Starting backend on http://127.0.0.1:8000');
console.log('Starting frontend on http://127.0.0.1:5173');

await ensureBackendDependencies().catch((error) => {
  console.error(`[backend setup] ${error.message}`);
  process.exit(1);
});

start('backend', pythonBin, ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000'], backendDir);
start('frontend', frontendCommand, frontendArgs, rootDir);
