import { app, BrowserWindow, screen, globalShortcut, ipcMain } from 'electron';
import * as path from 'path';

// Handle creating/removing shortcuts on Windows when installing/uninstalling.
if (require('electron-squirrel-startup')) {
  app.quit();
}

let mainWindow: BrowserWindow | null = null;

function createWindow(): void {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width } = primaryDisplay.workAreaSize;
  
  mainWindow = new BrowserWindow({
    width: 400,
    height: 600,
    x: width - 420,
    y: 20,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: true,
    hasShadow: true,
    show: false 
  });

  // In dev, load Vite dev server. In prod, load index.html from dist.
  const startUrl = process.env.ELECTRON_START_URL || 'http://localhost:5173';
  
  // Check if we are in production (packaged) to load file instead
  if (app.isPackaged) {
      mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  } else {
      mainWindow.loadURL(startUrl);
  }

  // IPC listeners for window controls
  ipcMain.on('window-minimize', () => mainWindow?.minimize());
  ipcMain.on('window-maximize', () => {
    if (mainWindow?.isMaximized()) mainWindow.unmaximize();
    else mainWindow?.maximize();
  });
  ipcMain.on('window-close', () => mainWindow?.close());
  ipcMain.on('window-resize', (event, width, height) => {
    if (mainWindow) {
      mainWindow.setSize(width, height, true);
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
  
  mainWindow.once('ready-to-show', () => {
    mainWindow?.show();
  });
}

app.on('ready', () => {
  createWindow();

  globalShortcut.register('CommandOrControl+H', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.hide();
      } else {
        mainWindow.show();
        mainWindow.webContents.send('window-shown');
      }
    }
  });
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});
