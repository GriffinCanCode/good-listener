import { contextBridge, ipcRenderer, IpcRendererEvent } from 'electron';
import { IPC_CHANNELS, ElectronAPI } from '../shared/ipc';

// Type-safe event handler creator
const createEventHandler = <T = void>(channel: string) => {
  return (callback: (data: T) => void): (() => void) => {
    const handler = (_: IpcRendererEvent, data: T) => callback(data);
    ipcRenderer.on(channel, handler);
    return () => ipcRenderer.removeListener(channel, handler);
  };
};

// Build the API object
const electronAPI: ElectronAPI = {
  window: {
    minimize: () => ipcRenderer.send(IPC_CHANNELS.WINDOW_MINIMIZE),
    maximize: () => ipcRenderer.send(IPC_CHANNELS.WINDOW_MAXIMIZE),
    close: () => ipcRenderer.send(IPC_CHANNELS.WINDOW_CLOSE),
    resize: (width, height) => ipcRenderer.send(IPC_CHANNELS.WINDOW_RESIZE, { width, height }),
    onShown: createEventHandler(IPC_CHANNELS.WINDOW_SHOWN),
    onStateChanged: createEventHandler(IPC_CHANNELS.WINDOW_STATE_CHANGED),
  },
  platform: process.platform,
};

// Expose to renderer
contextBridge.exposeInMainWorld('electron', electronAPI);

