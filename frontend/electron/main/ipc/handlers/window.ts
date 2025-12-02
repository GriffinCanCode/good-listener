import { ipcMain } from 'electron';
import { IPC_CHANNELS } from '../../../shared/ipc';
import { getMainWindow, resizeWindow } from '../../window';

export function registerWindowHandlers(): void {
  ipcMain.on(IPC_CHANNELS.WINDOW_MINIMIZE, () => {
    getMainWindow()?.hide();
  });

  ipcMain.on(IPC_CHANNELS.WINDOW_MAXIMIZE, () => {
    const win = getMainWindow();
    if (!win) return;
    if (win.isMaximized()) win.unmaximize();
    else win.maximize();
  });

  ipcMain.on(IPC_CHANNELS.WINDOW_CLOSE, () => {
    getMainWindow()?.hide();
  });

  ipcMain.on(IPC_CHANNELS.WINDOW_RESIZE, (_, payload: { width: number; height: number }) => {
    resizeWindow(payload.width, payload.height);
  });
}
