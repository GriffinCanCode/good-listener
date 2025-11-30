import type { IpcRendererEvent } from 'electron';
import { contextBridge, ipcRenderer } from 'electron';
import type { ElectronAPI } from '../shared/ipc';
import { IPC_CHANNELS } from '../shared/ipc';

// Event handler creator for void callbacks
const createVoidEventHandler = (channel: string) => {
  return (callback: () => void): (() => void) => {
    const handler = () => {
      callback();
    };
    ipcRenderer.on(channel, handler);
    return () => {
      ipcRenderer.removeListener(channel, handler);
    };
  };
};

// Event handler creator for typed callbacks
// eslint-disable-next-line @typescript-eslint/no-unnecessary-type-parameters -- factory pattern requires this
const createTypedEventHandler = <T>(channel: string) => {
  return (callback: (data: T) => void): (() => void) => {
    const handler = (_: IpcRendererEvent, data: T) => {
      callback(data);
    };
    ipcRenderer.on(channel, handler);
    return () => {
      ipcRenderer.removeListener(channel, handler);
    };
  };
};

// Build the API object
const electronAPI: ElectronAPI = {
  window: {
    minimize: () => {
      ipcRenderer.send(IPC_CHANNELS.WINDOW_MINIMIZE);
    },
    maximize: () => {
      ipcRenderer.send(IPC_CHANNELS.WINDOW_MAXIMIZE);
    },
    close: () => {
      ipcRenderer.send(IPC_CHANNELS.WINDOW_CLOSE);
    },
    resize: (width, height) => {
      ipcRenderer.send(IPC_CHANNELS.WINDOW_RESIZE, { width, height });
    },
    onShown: createVoidEventHandler(IPC_CHANNELS.WINDOW_SHOWN),
    onStateChanged: createTypedEventHandler<{ isMaximized: boolean; isMinimized: boolean }>(
      IPC_CHANNELS.WINDOW_STATE_CHANGED
    ),
  },
  platform: process.platform,
};

// Expose to renderer
contextBridge.exposeInMainWorld('electron', electronAPI);
