import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('electronAPI', {
  minimize: () => ipcRenderer.send('window-minimize'),
  maximize: () => ipcRenderer.send('window-maximize'),
  close: () => ipcRenderer.send('window-close'),
  onWindowShown: (callback: () => void) => ipcRenderer.on('window-shown', () => callback()),
  removeAllWindowShownListeners: () => ipcRenderer.removeAllListeners('window-shown')
});
