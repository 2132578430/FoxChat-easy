// 预加载脚本 (Preload Script)
// 用于在渲染进程和主进程之间建立安全的通信桥梁
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // 暴露一些基础信息，例如版本
  versions: process.versions,

  // 示例 IPC 通信
  sendMessage: (message) => ipcRenderer.send('message', message),
  onMessage: (callback) => ipcRenderer.on('message', (_event, value) => callback(value)),

  // Window controls
  minimizeWindow: () => ipcRenderer.send('window-minimize'),
  maximizeWindow: () => ipcRenderer.send('window-maximize'),
  closeWindow: () => ipcRenderer.send('window-close')
});
