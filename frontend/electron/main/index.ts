import { app, globalShortcut } from 'electron';
import { registerIpcHandlers } from './ipc';
import { createTray } from './tray';
import { createMainWindow, getMainWindow } from './window';

// Ensure single instance
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  app.quit();
} else {
  // Hide dock icon on macOS (makes it a tray-only app)
  if (process.platform === 'darwin') {
    app.dock.hide();
  }

  app.on('second-instance', () => {
    const win = getMainWindow();
    if (win) {
      if (win.isMinimized()) win.restore();
      win.focus();
    }
  });

  void app.whenReady().then(() => {
    // Register all IPC handlers
    registerIpcHandlers();

    // Create the main window
    createMainWindow();

    // Create the system tray
    createTray();

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
