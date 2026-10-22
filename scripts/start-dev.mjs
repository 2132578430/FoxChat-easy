#!/usr/bin/env node
/*
 * 开发环境启动器：Python → Java → Vue
 *
 *   node scripts/start-dev.mjs                  # Python + Java（同一终端）
 *   node scripts/start-dev.mjs --web            # Python + Java + Vue（同一终端）
 *   node scripts/start-dev.mjs --only=py        # 只启动 Python
 *   node scripts/start-dev.mjs --only=java      # 只启动 Java（先等 Python 的 8000+50051）
 *   node scripts/start-dev.mjs --only=web       # 只启动 Vue（先等 Java 的 12000+13000）
 *   node scripts/start-dev.mjs --stop           # 停止本脚本启动的服务（含残留）
 *   node scripts/start-dev.mjs --check --web    # 只检查路径、端口和 pid 记录
 *
 * 启动时若端口被占用（例如 VS Code 关闭后残留的服务），会自动终止占用进程后继续。
 *
 * 可用环境变量覆盖：FOXCHAT_PYTHON、FOXCHAT_JAVA_HOME
 */
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import net from 'node:net';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const CHECK_ONLY = process.argv.includes('--check');
const STOP_ONLY = process.argv.includes('--stop');
const WITH_WEB = process.argv.includes('--web');
const ONLY = (process.argv.find((arg) => arg.startsWith('--only=')) ?? '').slice('--only='.length).trim();

const PYTHON = process.env.FOXCHAT_PYTHON || 'D:\\Environment\\venvs\\foxchat-py312\\Scripts\\python.exe';
// 固定用 JDK 17，避免 VS Code 侧 Gradle 用 JDK 25 时的 Lombok 兼容问题
const JAVA_HOME = process.env.FOXCHAT_JAVA_HOME || 'D:\\Environment\\jdk-17';

const RUN_DIR = path.join(ROOT, 'scripts', '.run');
const LOG_DIR = path.join(RUN_DIR, 'logs');
const STOP_MARKER = path.join(RUN_DIR, '.stopping');

const RESET = '\x1b[0m';
const COLORS = {
  py: '\x1b[36m',
  java: '\x1b[32m',
  web: '\x1b[35m',
  info: '\x1b[33m',
  error: '\x1b[31m',
};

const ALL_SERVICES = [
  {
    key: 'py',
    tag: 'PY',
    color: COLORS.py,
    cwd: path.join(ROOT, 'FoxChatRAG-python'),
    command: PYTHON,
    args: ['main.py'],
    shell: false,
    ports: [8000, 50051],
    url: 'http://127.0.0.1:8000/health',
    timeoutMs: 180_000,
    dependencies: [],
    recent: [],
    env: {
      PYTHONUNBUFFERED: '1',
      PYTHONIOENCODING: 'utf-8',
    },
  },
  {
    key: 'java',
    tag: 'JAVA',
    color: COLORS.java,
    cwd: path.join(ROOT, 'FoxChat-java'),
    command: process.platform === 'win32' ? 'gradlew.bat' : './gradlew',
    args: ['--console=plain', ':foxChat-web:bootRun'],
    shell: true,
    ports: [12000, 13000],
    url: null,
    timeoutMs: 240_000,
    dependencies: ['py'],
    recent: [],
    env: {
      JAVA_HOME,
      GRADLE_OPTS: [
        process.env.GRADLE_OPTS,
        '-Dfile.encoding=UTF-8',
        '-Dsun.stdout.encoding=UTF-8',
        '-Dsun.stderr.encoding=UTF-8',
      ].filter(Boolean).join(' '),
    },
  },
  {
    key: 'web',
    tag: 'WEB',
    color: COLORS.web,
    cwd: path.join(ROOT, 'FoxChat-vue'),
    command: 'npm',
    args: ['run', 'dev'],
    shell: true,
    ports: [5173],
    url: null,
    timeoutMs: 60_000,
    dependencies: ['java'],
    recent: [],
  },
];

if (ONLY && !ALL_SERVICES.some((svc) => svc.key === ONLY)) {
  console.error(`未知的 --only=${ONLY}，可选：${ALL_SERVICES.map((svc) => svc.key).join(', ')}`);
  process.exit(1);
}
if (ONLY && WITH_WEB) {
  console.error('--only 与 --web 不能同时使用');
  process.exit(1);
}
if (STOP_ONLY && (CHECK_ONLY || ONLY || WITH_WEB)) {
  console.error('--stop 不能与其他启动/检查参数一起使用');
  process.exit(1);
}

const SELECTED = ONLY
  ? ALL_SERVICES.filter((svc) => svc.key === ONLY)
  : WITH_WEB
    ? ALL_SERVICES
    : ALL_SERVICES.filter((svc) => svc.key !== 'web');

const started = [];
let shuttingDown = false;

function log(tag, message, color = COLORS.info) {
  console.log(`${color}[${tag}]${RESET} ${message}`);
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function connectOnce(host, port, timeoutMs = 500) {
  return new Promise((resolve) => {
    const socket = net.connect({ host, port });
    let settled = false;
    const finish = (value) => {
      if (settled) return;
      settled = true;
      socket.destroy();
      resolve(value);
    };
    socket.setTimeout(timeoutMs);
    socket.once('connect', () => finish(true));
    socket.once('timeout', () => finish(false));
    socket.once('error', () => finish(false));
  });
}

// Vite 等工具把 localhost 解析成 ::1，只探测 127.0.0.1 会误判“未就绪”
async function probePorts(port) {
  const [v4, v6] = await Promise.all([
    connectOnce('127.0.0.1', port),
    connectOnce('::1', port),
  ]);
  return { v4, v6 };
}

async function checkPort(port) {
  const { v4, v6 } = await probePorts(port);
  return v4 || v6;
}

async function checkHttp(url) {
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(1500) });
    return res.ok;
  } catch {
    return false;
  }
}

async function isServiceReady(svc) {
  if (svc.url && !(await checkHttp(svc.url))) return false;
  for (const port of svc.ports) {
    if (!(await checkPort(port))) return false;
  }
  return true;
}

function getPortOwners(port) {
  if (process.platform === 'win32') {
    const res = spawnSync('netstat', ['-ano'], { encoding: 'utf8', windowsHide: true });
    if (res.status !== 0 || !res.stdout) return [];
    const pids = new Set();
    for (const line of res.stdout.split(/\r?\n/)) {
      if (!/LISTENING/i.test(line)) continue;
      const parts = line.trim().split(/\s+/);
      if (parts.length < 5) continue;
      if (parts[1].endsWith(`:${port}`)) pids.add(parts[4]);
    }
    return [...pids];
  }
  const res = spawnSync('lsof', ['-ti', `tcp:${port}`, '-sTCP:LISTEN'], { encoding: 'utf8' });
  return res.stdout.split(/\s+/).filter(Boolean);
}

function listProcesses() {
  if (process.platform !== 'win32') return [];
  // 最后一个字段标记 Gradle daemon：它是常驻构建进程，不属于某个服务的运行实例
  const command = `Get-CimInstance Win32_Process | ForEach-Object { '{0}|{1}|{2}|{3}|{4}' -f $_.ProcessId, $_.ParentProcessId, $_.CreationDate.ToString('o'), [int]($_.CommandLine -like '*GradleDaemon*'), $_.Name }`;
  const res = spawnSync('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', command], {
    encoding: 'utf8',
    windowsHide: true,
    maxBuffer: 4 * 1024 * 1024,
  });
  if (res.status !== 0 || !res.stdout) return [];
  return res.stdout
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [pid, ppid, startedAt, daemon, name] = line.split('|');
      return { pid: Number(pid), ppid: Number(ppid), startedAt, isGradleDaemon: daemon === '1', name };
    })
    .filter((proc) => Number.isInteger(proc.pid) && proc.pid > 0);
}

function collectDescendants(rootPid) {
  const processes = listProcesses();
  if (processes.length === 0) return [];
  const byPid = new Map(processes.map((proc) => [proc.pid, proc]));
  const byParent = new Map();
  for (const proc of processes) {
    const children = byParent.get(proc.ppid) ?? [];
    children.push(proc.pid);
    byParent.set(proc.ppid, children);
  }
  const result = [];
  const seen = new Set();
  const stack = [Number(rootPid)];
  while (stack.length > 0) {
    const pid = stack.pop();
    if (seen.has(pid)) continue;
    seen.add(pid);
    const proc = byPid.get(pid);
    // daemon 不写入记录，但仍继续遍历它的子进程，避免漏掉真正的服务进程
    if (proc && !proc.isGradleDaemon) result.push(proc);
    for (const childPid of byParent.get(pid) ?? []) stack.push(childPid);
  }
  return result;
}

function isProcessAlive(pid) {
  const value = Number(pid);
  if (!Number.isInteger(value) || value <= 0) return false;
  try {
    process.kill(value, 0);
    return true;
  } catch (err) {
    return err.code === 'EPERM';
  }
}

function killPid(pid) {
  if (!isProcessAlive(pid)) return false;
  if (process.platform === 'win32') {
    spawnSync('taskkill', ['/PID', String(pid), '/T', '/F'], { stdio: 'ignore', windowsHide: true });
  } else {
    try {
      process.kill(Number(pid), 'SIGTERM');
    } catch {
      return false;
    }
  }
  return true;
}

function pidFile(svc) {
  return path.join(RUN_DIR, `${svc.key}.json`);
}

function ensureRunDir() {
  fs.mkdirSync(RUN_DIR, { recursive: true });
}

function openServiceLog(svc) {
  ensureRunDir();
  fs.mkdirSync(LOG_DIR, { recursive: true });
  const file = path.join(LOG_DIR, `${svc.key}.log`);
  try {
    if (fs.statSync(file).size > 10 * 1024 * 1024) {
      fs.rmSync(`${file}.1`, { force: true });
      fs.renameSync(file, `${file}.1`);
    }
  } catch {
    // 文件尚不存在
  }
  fs.appendFileSync(file, `\n===== ${new Date().toISOString()} [${svc.tag}] 启动 =====\n`);
  return file;
}

function readPidRecord(svc) {
  try {
    const rec = JSON.parse(fs.readFileSync(pidFile(svc), 'utf8'));
    if (!rec || rec.key !== svc.key || !rec.childPid) return null;
    return rec;
  } catch {
    return null;
  }
}

function writePidRecord(svc, child) {
  ensureRunDir();
  const rec = {
    key: svc.key,
    tag: svc.tag,
    childPid: child.pid,
    launcherPid: process.pid,
    startedAt: new Date().toISOString(),
    command: svc.command,
    args: svc.args,
    processes: [],
  };
  fs.writeFileSync(pidFile(svc), `${JSON.stringify(rec, null, 2)}\n`);
  return rec;
}

function refreshPidRecord(svc, child) {
  let rec;
  try {
    rec = JSON.parse(fs.readFileSync(pidFile(svc), 'utf8'));
  } catch {
    return;
  }
  if (!rec || Number(rec.childPid) !== Number(child.pid)) return;
  const tree = collectDescendants(child.pid);
  if (tree.length === 0) return;
  rec.processes = tree.map(({ pid, startedAt }) => ({ pid, startedAt }));
  fs.writeFileSync(pidFile(svc), `${JSON.stringify(rec, null, 2)}\n`);
}

function removePidRecord(svc, childPid) {
  const file = pidFile(svc);
  try {
    if (childPid !== undefined) {
      const rec = JSON.parse(fs.readFileSync(file, 'utf8'));
      if (rec && Number(rec.childPid) !== Number(childPid)) return;
    }
  } catch {
    // 文件不存在或已损坏，直接清理
  }
  fs.rmSync(file, { force: true });
}

function getProcessMap() {
  return new Map(listProcesses().map((proc) => [proc.pid, proc]));
}

// 旧记录可能把 Gradle daemon 也写了进去；判定存活时忽略它，避免应用已退出却仍被当成在运行
function livePidsFromRecord(rec, current) {
  const pids = [...new Set(
    [rec.childPid, ...(rec.processes ?? []).map((proc) => proc.pid)]
      .map(Number)
      .filter((pid) => Number.isInteger(pid) && pid > 0),
  )];
  if (!current || current.size === 0) return pids.filter(isProcessAlive);
  return pids.filter((pid) => {
    const proc = current.get(pid);
    return Boolean(proc) && !proc.isGradleDaemon;
  });
}

function findRunningRecord(svc) {
  const rec = readPidRecord(svc);
  if (!rec) return null;
  const livePids = livePidsFromRecord(rec, getProcessMap());
  if (livePids.length > 0) {
    rec.livePids = livePids;
    return rec;
  }
  log('INFO', `${svc.tag} 清理已失效的 pid 记录 (${rec.childPid})`);
  removePidRecord(svc);
  return null;
}

function terminateRecorded(svc) {
  const rec = readPidRecord(svc);
  if (!rec) return 0;
  const pids = new Set([rec.childPid, ...(rec.processes ?? []).map((proc) => proc.pid)]);
  let killed = 0;
  for (const pid of pids) {
    if (Number(pid) === process.pid) continue;
    if (killPid(pid)) killed += 1;
  }
  return killed;
}

function prefixStream(stream, svc, logPath) {
  let buffer = '';
  stream.setEncoding('utf8');
  stream.on('data', (chunk) => {
    buffer += chunk;
    const lines = buffer.split(/\r?\n/);
    buffer = lines.pop() || '';
    for (const line of lines) {
      if (line.length > 0) {
        svc.recent.push(line);
        if (svc.recent.length > 20) svc.recent.shift();
        fs.appendFileSync(logPath, `${line}\n`);
        console.log(`${svc.color}[${svc.tag}]${RESET} ${line}`);
      }
    }
  });
  stream.on('end', () => {
    if (buffer.length > 0) {
      svc.recent.push(buffer);
      if (svc.recent.length > 20) svc.recent.shift();
      fs.appendFileSync(logPath, `${buffer}\n`);
      console.log(`${svc.color}[${svc.tag}]${RESET} ${buffer}`);
    }
  });
}

async function diagnose(svc, child) {
  const status = child
    ? child.exitCode === null
      ? `存活 (pid ${child.pid})`
      : `已退出 (code ${child.exitCode})`
    : '未知（不是本次启动的进程）';
  log('DIAG', `${svc.tag} 进程: ${status}`);
  for (const port of svc.ports) {
    const { v4, v6 } = await probePorts(port);
    log('DIAG', `${svc.tag} 端口 ${port}: 127.0.0.1=${v4 ? '可连接' : '不可连接'}，::1=${v6 ? '可连接' : '不可连接'}`);
    const owners = getPortOwners(port);
    if (owners.length > 0) log('DIAG', `${svc.tag} 端口 ${port} 占用 PID: ${owners.join(', ')}`);
  }
  if (svc.url) {
    log('DIAG', `${svc.tag} 健康检查 ${svc.url}: ${(await checkHttp(svc.url)) ? '通过' : '失败'}`);
  }
  const recent = svc.recent.slice(-10);
  if (recent.length > 0) {
    log('DIAG', `${svc.tag} 最近 ${recent.length} 行输出：`);
    for (const line of recent) console.log(`${svc.color}[${svc.tag}]${RESET} ${line}`);
  }
}

async function waitFor(label, probe, timeoutMs, child, svc) {
  const startedAt = Date.now();
  let nextProgress = 10_000;
  console.log(`${COLORS.info}[WAIT]${RESET} ${label} ...`);
  while (Date.now() - startedAt < timeoutMs) {
    if (child && child.exitCode !== null) {
      console.log(`${COLORS.error}[WAIT]${RESET} ${label} 失败：进程已退出 (code ${child.exitCode})`);
      if (svc) await diagnose(svc, child);
      return false;
    }
    if (await probe()) {
      console.log(`${COLORS.info}[WAIT]${RESET} ${label} 就绪 (${((Date.now() - startedAt) / 1000).toFixed(1)}s)`);
      return true;
    }
    const elapsed = Date.now() - startedAt;
    if (elapsed >= nextProgress) {
      console.log(`${COLORS.info}[WAIT]${RESET} ${label} 等待中 ${Math.round(elapsed / 1000)}s ...`);
      nextProgress += 10_000;
    }
    await sleep(1000);
  }
  console.log(`${COLORS.error}[WAIT]${RESET} ${label} 超时 (${Math.round(timeoutMs / 1000)}s)`);
  if (svc) await diagnose(svc, child);
  return false;
}

function startService(svc) {
  const logPath = openServiceLog(svc);
  log('RUN', `启动 ${svc.tag}: ${svc.command} ${svc.args.join(' ')} (cwd: ${svc.cwd})`);
  log('LOG', `${svc.tag} 日志文件: ${logPath}`);
  const child = spawn(svc.command, svc.args, {
    cwd: svc.cwd,
    env: { ...process.env, ...svc.env },
    shell: svc.shell,
    windowsHide: true,
  });
  if (child.stdout) prefixStream(child.stdout, svc, logPath);
  if (child.stderr) prefixStream(child.stderr, svc, logPath);
  if (child.pid) {
    writePidRecord(svc, child);
    for (const delay of [1000, 5000]) {
      const timer = setTimeout(() => refreshPidRecord(svc, child), delay);
      timer.unref?.();
    }
  }
  child.on('error', (err) => {
    log('ERR', `${svc.tag} 启动失败: ${err.message}`, COLORS.error);
    if (!shuttingDown) shutdown(1);
  });
  child.on('exit', (code, signal) => {
    if (shuttingDown) return;
    const requested = fs.existsSync(STOP_MARKER);
    const reason = requested ? '收到停止请求' : signal ? `signal ${signal}` : `code ${code}`;
    log('EXIT', `${svc.tag} 已退出 (${reason})`, requested || code === 0 ? COLORS.info : COLORS.error);
    shutdown(requested ? 0 : (code ?? 1));
  });
  started.push({ svc, child });
  return child;
}

function shutdown(code = 0) {
  if (shuttingDown) return;
  shuttingDown = true;
  log('STOP', '正在停止由本脚本启动的服务...');
  for (const { svc, child } of started) {
    const killed = terminateRecorded(svc);
    if (child.exitCode === null) {
      if (process.platform === 'win32' && child.pid) {
        spawnSync('taskkill', ['/PID', String(child.pid), '/T', '/F'], { stdio: 'ignore', windowsHide: true });
      } else if (child.pid) {
        child.kill('SIGTERM');
      }
      log('STOP', `${svc.tag} (pid ${child.pid})`);
    } else if (killed > 0) {
      log('STOP', `${svc.tag} 已退出，清理 ${killed} 个残留进程`);
    }
    removePidRecord(svc, child.pid);
  }
  setTimeout(() => process.exit(code), 1000);
}

process.on('SIGINT', () => shutdown(0));
process.on('SIGTERM', () => shutdown(0));

function preflight(servicesToCheck) {
  let ok = true;
  const mustExist = (target, label) => {
    if (!fs.existsSync(target)) {
      log('ERR', `${label} 不存在: ${target}`, COLORS.error);
      ok = false;
    }
  };
  for (const svc of servicesToCheck) {
    mustExist(svc.cwd, `${svc.tag} 工作目录`);
    if (svc.key === 'py') {
      mustExist(PYTHON, 'Python 解释器');
      mustExist(path.join(svc.cwd, 'main.py'), 'Python 入口 main.py');
    }
    if (svc.key === 'java') {
      mustExist(JAVA_HOME, 'JAVA_HOME');
      mustExist(path.join(svc.cwd, process.platform === 'win32' ? 'gradlew.bat' : 'gradlew'), 'Gradle Wrapper');
    }
  }
  return ok;
}

async function findPortConflict(svc) {
  for (const port of svc.ports) {
    if (await checkPort(port)) return { port, owners: getPortOwners(port) };
  }
  return null;
}

// 启动前释放所选服务的端口：VS Code 直接关闭时 child 进程可能残留，pid 记录也可能已丢失
async function reclaimServicePorts(svc) {
  const processes = getProcessMap();
  const targets = new Map();
  for (const port of svc.ports) {
    if (!(await checkPort(port))) continue;
    const owners = getPortOwners(port);
    if (owners.length === 0) {
      log('WARN', `${svc.tag} 端口 ${port} 被占用，但无法定位占用进程。`, COLORS.error);
      continue;
    }
    for (const owner of owners) {
      const pid = Number(owner);
      if (!Number.isInteger(pid) || pid <= 0 || pid === process.pid) continue;
      const target = targets.get(pid);
      if (target) {
        target.ports.push(port);
      } else {
        targets.set(pid, { pid, name: processes.get(pid)?.name ?? '未知进程', ports: [port] });
      }
    }
  }

  if (targets.size === 0) return !(await findPortConflict(svc));

  for (const target of targets.values()) {
    log('STOP', `${svc.tag} 端口 ${target.ports.join('/')} 被 ${target.name} (pid ${target.pid}) 占用，自动终止`);
    killPid(target.pid);
  }

  const deadline = Date.now() + 10_000;
  while (Date.now() < deadline) {
    if (!(await findPortConflict(svc))) {
      log('STOP', `${svc.tag} 端口已释放，继续启动。`);
      return true;
    }
    await sleep(250);
  }
  log('ERR', `${svc.tag} 端口 ${svc.ports.join(', ')} 仍未释放，请手动检查占用进程。`, COLORS.error);
  return false;
}

async function printCheck() {
  const current = getProcessMap();
  for (const svc of SELECTED) {
    const rec = readPidRecord(svc);
    const running = Boolean(rec) && livePidsFromRecord(rec, current).length > 0;
    const portStates = [];
    for (const port of svc.ports) {
      const busy = await checkPort(port);
      const owners = busy ? getPortOwners(port) : [];
      portStates.push(`${port}=${busy ? `占用(${owners.join(',') || '未知'})` : '空闲'}`);
    }
    const state = running ? `pid 记录存在 (${rec.childPid})` : rec ? 'pid 记录失效' : '未运行';
    log('CHECK', `${svc.tag.padEnd(4)} ${portStates.join(' ')} | ${state}`);
  }
  log('OK', '检查完成，未启动任何服务。');
}

async function stopAll() {
  ensureRunDir();
  const files = fs.existsSync(RUN_DIR)
    ? fs.readdirSync(RUN_DIR).filter((file) => file.endsWith('.json'))
    : [];
  if (files.length === 0) log('STOP', '没有找到本脚本的 pid 记录。');

  const current = new Map(listProcesses().map((proc) => [proc.pid, proc]));
  const canValidateStartTime = current.size > 0;
  let killed = 0;

  try {
    if (files.length > 0) fs.writeFileSync(STOP_MARKER, new Date().toISOString());

    for (const file of files) {
      const svc = ALL_SERVICES.find((item) => `${item.key}.json` === file);
      if (!svc) {
        fs.rmSync(path.join(RUN_DIR, file), { force: true });
        continue;
      }
      const rec = readPidRecord(svc);
      if (!rec) {
        fs.rmSync(path.join(RUN_DIR, file), { force: true });
        continue;
      }

      const candidates = new Map();
      if (rec.childPid) candidates.set(Number(rec.childPid), rec.startedAt);
      for (const proc of rec.processes ?? []) {
        if (proc?.pid) candidates.set(Number(proc.pid), proc.startedAt);
      }

      const targets = [];
      for (const [pid, startedAt] of candidates) {
        if (!canValidateStartTime) {
          if (isProcessAlive(pid)) targets.push(pid);
          continue;
        }
        const live = current.get(pid);
        if (!live) continue;
        const expected = Date.parse(startedAt ?? '');
        const actual = Date.parse(live.startedAt ?? '');
        if (!Number.isNaN(expected) && !Number.isNaN(actual) && Math.abs(actual - expected) > 5000) {
          log('WARN', `${svc.tag} pid ${pid} 已被其他进程复用，跳过。`);
          continue;
        }
        targets.push(pid);
      }

      if (targets.length === 0) {
        log('STOP', `${svc.tag} 已不在运行，清理记录。`);
        removePidRecord(svc);
        continue;
      }
      for (const pid of targets) {
        log('STOP', `${svc.tag} 终止 pid ${pid}`);
        killPid(pid);
      }
      killed += targets.length;
      removePidRecord(svc);
    }

    if (killed > 0) await sleep(1000);
  } finally {
    fs.rmSync(STOP_MARKER, { force: true });
  }

  for (const svc of ALL_SERVICES) {
    for (const port of svc.ports) {
      if (await checkPort(port)) {
        const owners = getPortOwners(port);
        log('WARN', `${svc.tag} 端口 ${port} 仍被占用: ${owners.length ? owners.join(', ') : '未知进程'}`, COLORS.error);
      }
    }
  }

  log('OK', killed > 0 ? `已停止 ${killed} 个进程。` : '没有需要停止的进程。');
}

async function main() {
  if (STOP_ONLY) {
    await stopAll();
    return;
  }

  if (!preflight(SELECTED)) {
    process.exitCode = 1;
    return;
  }

  log('INFO', `项目根目录: ${ROOT}`);
  log('INFO', `启动顺序: ${SELECTED.map((svc) => svc.tag).join(' → ')}`);

  if (CHECK_ONLY) {
    await printCheck();
    return;
  }

  fs.rmSync(STOP_MARKER, { force: true });

  for (const svc of SELECTED) {
    const missingDeps = (svc.dependencies ?? []).filter(
      (key) => !SELECTED.some((item) => item.key === key),
    );
    for (const depKey of missingDeps) {
      const dep = ALL_SERVICES.find((item) => item.key === depKey);
      const ready = await waitFor(`${dep.tag} 依赖`, () => isServiceReady(dep), dep.timeoutMs, undefined, dep);
      if (!ready) {
        log('ERR', `${dep.tag} 未就绪，${svc.tag} 不启动。请先在另一个终端启动 ${dep.tag}。`, COLORS.error);
        shutdown(1);
        return;
      }
    }

    const existing = findRunningRecord(svc);
    if (existing) {
      const pidText = (existing.livePids ?? [existing.childPid]).join(', ');
      const managed = isProcessAlive(existing.launcherPid);
      if (managed && (await isServiceReady(svc))) {
        log('SKIP', `${svc.tag} 已在运行 (pid ${pidText})，跳过启动。`);
        if (ONLY) return;
        continue;
      }
      log('STOP', `${svc.tag} 发现残留服务 (pid ${pidText})，清理后重新启动。`);
      const killed = terminateRecorded(svc);
      if (killed > 0) log('STOP', `${svc.tag} 已终止 ${killed} 个残留进程。`);
      removePidRecord(svc);
    }

    const freed = await reclaimServicePorts(svc);
    if (!freed) {
      shutdown(1);
      return;
    }

    const child = startService(svc);
    const ready = await waitFor(`${svc.tag} 就绪`, () => isServiceReady(svc), svc.timeoutMs, child, svc);
    if (!ready) {
      log('ERR', `${svc.tag} 未在 ${Math.round(svc.timeoutMs / 1000)}s 内就绪，停止本次启动的服务。`, COLORS.error);
      shutdown(1);
      return;
    }
    refreshPidRecord(svc, child);
  }

  if (started.length === 0) {
    log('OK', '所选服务均已在运行，无需重复启动。');
    return;
  }

  log('OK', ONLY ? `${SELECTED[0].tag} 已就绪。按 Ctrl+C 停止。` : '全部服务已就绪。按 Ctrl+C 停止本次启动的服务。');
  await new Promise(() => {});
}

main().catch((err) => {
  log('ERR', err?.stack || String(err), COLORS.error);
  shutdown(1);
});
