import { app, BrowserWindow, protocol, ipcMain } from 'electron';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// 处理 ESM 下的 __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ==========================================
// 🚀 WebTransport / QUIC 证书绕过终极配置
// ==========================================

// 1. 忽略所有证书错误 (全局开关)
// 这会让 Chromium 忽略大部分 TLS 错误，包括自签名证书
app.commandLine.appendSwitch('ignore-certificate-errors');

// 2. 允许不安全的 localhost (辅助)
app.commandLine.appendSwitch('allow-insecure-localhost');

// 3. 禁用 HTTP 缓存
app.commandLine.appendSwitch('disable-http-cache');

// 监听证书错误事件，强制信任
app.on('certificate-error', (event, webContents, url, error, certificate, callback) => {
  // 允许私有证书、自签名证书
  // 这是 Electron 提供的最强力的证书绕过方式
  event.preventDefault();
  callback(true);
});

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    frame: false, // 无边框窗口
    icon: path.join(__dirname, '../public/fox.ico'), // 应用图标
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true
    }
  });

  // 根据环境加载页面
  const isDev = !app.isPackaged;
  if (isDev) {
    // 开发环境加载 Vite 服务
    mainWindow.loadURL('http://localhost:5173');
    // 开发环境下自动打开开发者工具
    mainWindow.webContents.openDevTools();
  } else {
    // 生产环境加载构建后的 index.html
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
    
    // 生产环境默认不打开，但可以通过快捷键 (Ctrl+Shift+I) 手动打开
    // mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// IPC handlers for window controls
ipcMain.on('window-minimize', () => {
  if (mainWindow) mainWindow.minimize();
});

ipcMain.on('window-maximize', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  }
});

ipcMain.on('window-close', () => {
  if (mainWindow) mainWindow.close();
});

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
