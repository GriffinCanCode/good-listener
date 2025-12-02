import { Tray, Menu, app, type BrowserWindow, nativeImage } from 'electron';
import { getMainWindow } from './window';

let tray: Tray | null = null;

export function createTray() {
  // Use a system icon for macOS to ensure visibility
  // NSActionTemplate is a standard system icon that adapts to theme
  const icon =
    process.platform === 'darwin'
      ? nativeImage.createFromNamedImage('NSActionTemplate')
      : nativeImage.createFromDataURL(
          'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5AwcBA4AA318+AAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAAAoSURBVDjLY2AYBaNgFqyh/k/o//+E0f8J/4lWMOo/4T/RCkb9J1rBKAQA80YM96z2/tIAAAAASUVORK5CYII='
        );

  const trayIcon = icon.resize({ width: 16, height: 16 });
  trayIcon.setTemplateImage(true);

  tray = new Tray(trayIcon);
  tray.setToolTip('Good Listener');

  console.log('Tray created successfully');

  tray.on('click', (_event, bounds) => {
    toggleWindow(bounds);
  });

  tray.on('right-click', () => {
    const contextMenu = Menu.buildFromTemplate([
      {
        label: 'Quit',
        click: () => {
          app.quit();
        },
      },
    ]);
    tray?.popUpContextMenu(contextMenu);
  });
}

function toggleWindow(trayBounds: Electron.Rectangle) {
  const mainWindow = getMainWindow();
  if (!mainWindow) return;

  if (mainWindow.isVisible()) {
    mainWindow.hide();
  } else {
    const { x, y } = getWindowPosition(mainWindow, trayBounds);
    mainWindow.setPosition(x, y, false);
    mainWindow.show();
    mainWindow.focus();
  }
}

function getWindowPosition(mainWindow: BrowserWindow, trayBounds: Electron.Rectangle) {
  const windowBounds = mainWindow.getBounds();

  // Center window horizontally below the tray icon
  const x = Math.round(trayBounds.x + trayBounds.width / 2 - windowBounds.width / 2);

  // Position vertically below the tray icon
  const y = Math.round(trayBounds.y + trayBounds.height);

  return { x, y };
}
