import { ipcMain } from 'electron';
import { IPC_CHANNELS } from '../../../shared/ipc';
import { getMainWindow, resizeWindow } from '../../window';

export function registerWindowHandlers(): void {
  ipcMain.on(IPC_CHANNELS.WINDOW_MINIMIZE, () => {
    getMainWindow()?.minimize();
  });

  ipcMain.on(IPC_CHANNELS.WINDOW_MAXIMIZE, () => {
    const win = getMainWindow();
    if (!win) return;
    win.isMaximized() ? win.unmaximize() : win.maximize();
  });

  ipcMain.on(IPC_CHANNELS.WINDOW_CLOSE, () => {
    getMainWindow()?.close();
  });

  ipcMain.on(IPC_CHANNELS.WINDOW_RESIZE, (_, payload: { width: number; height: number }) => {
    resizeWindow(payload.width, payload.height);
  });
}

