import { join } from 'path';
import { BrowserWindow, screen, shell } from 'electron';

let mainWindow: BrowserWindow | null = null;

const WINDOW_CONFIG = {
  width: 400,
  height: 600,
  minWidth: 320,
  minHeight: 400,
} as const;

export function createMainWindow(): BrowserWindow {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width } = primaryDisplay.workAreaSize;

  mainWindow = new BrowserWindow({
    width: WINDOW_CONFIG.width,
    height: WINDOW_CONFIG.height,
    minWidth: WINDOW_CONFIG.minWidth,
    minHeight: WINDOW_CONFIG.minHeight,
    x: width - WINDOW_CONFIG.width - 20,
    y: 20,
    show: false,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: true,
    hasShadow: true,
    skipTaskbar: true,
    webPreferences: {
      preload: join(__dirname, '../preload/index.mjs'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false,
    },
  });

  // Handle external links
  mainWindow.webContents.setWindowOpenHandler(({ url }: { url: string }) => {
    void shell.openExternal(url);
    return { action: 'deny' };
  });

  // Load the app
  const rendererUrl = process.env['ELECTRON_RENDERER_URL'];
  if (rendererUrl) {
    void mainWindow.loadURL(rendererUrl);
  } else {
    void mainWindow.loadFile(join(__dirname, '../../dist/index.html'));
  }

  // Show when ready
  mainWindow.once('ready-to-show', () => {
    // Start hidden for tray app
  });

  // Hide on blur
  mainWindow.on('blur', () => {
    if (!mainWindow?.webContents.isDevToolsOpened()) {
      mainWindow?.hide();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  return mainWindow;
}

export function getMainWindow(): BrowserWindow | null {
  return mainWindow;
}

export function resizeWindow(width: number, height: number): void {
  if (!mainWindow) return;

  // Keep right edge anchored - expand/contract to the left
  const bounds = mainWindow.getBounds();
  const newX = bounds.x + (bounds.width - width);

  mainWindow.setBounds({ x: newX, y: bounds.y, width, height }, true);
}
