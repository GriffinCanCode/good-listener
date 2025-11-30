import { app, globalShortcut } from 'electron';
import { createMainWindow, getMainWindow } from './window';
import { registerIpcHandlers } from './ipc';

// Ensure single instance
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    const win = getMainWindow();
    if (win) {
      if (win.isMinimized()) win.restore();
      win.focus();
    }
  });

  app.whenReady().then(() => {
    // Register all IPC handlers
    registerIpcHandlers();

    // Create the main window
    createMainWindow();

    // Global shortcut to toggle visibility
    globalShortcut.register('CommandOrControl+H', () => {
      const win = getMainWindow();
      if (!win) return;

      if (win.isVisible()) {
        win.hide();
      } else {
        win.show();
        win.webContents.send('window:shown');
      }
    });
  });

  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
  });

  app.on('activate', () => {
    const win = getMainWindow();
    if (win) {
      win.show();
    } else {
      createMainWindow();
    }
  });

  app.on('will-quit', () => {
    globalShortcut.unregisterAll();
  });
}

