"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
const path = __importStar(require("path"));
// Handle creating/removing shortcuts on Windows when installing/uninstalling.
if (require('electron-squirrel-startup')) {
    electron_1.app.quit();
}
let mainWindow = null;
function createWindow() {
    const primaryDisplay = electron_1.screen.getPrimaryDisplay();
    const { width } = primaryDisplay.workAreaSize;
    mainWindow = new electron_1.BrowserWindow({
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
    if (electron_1.app.isPackaged) {
        mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
    }
    else {
        mainWindow.loadURL(startUrl);
    }
    // IPC listeners for window controls
    electron_1.ipcMain.on('window-minimize', () => mainWindow === null || mainWindow === void 0 ? void 0 : mainWindow.minimize());
    electron_1.ipcMain.on('window-maximize', () => {
        if (mainWindow === null || mainWindow === void 0 ? void 0 : mainWindow.isMaximized())
            mainWindow.unmaximize();
        else
            mainWindow === null || mainWindow === void 0 ? void 0 : mainWindow.maximize();
    });
    electron_1.ipcMain.on('window-close', () => mainWindow === null || mainWindow === void 0 ? void 0 : mainWindow.close());
    electron_1.ipcMain.on('window-resize', (event, width, height) => {
        if (mainWindow) {
            mainWindow.setSize(width, height, true);
        }
    });
    mainWindow.on('closed', () => {
        mainWindow = null;
    });
    mainWindow.once('ready-to-show', () => {
        mainWindow === null || mainWindow === void 0 ? void 0 : mainWindow.show();
    });
}
electron_1.app.on('ready', () => {
    createWindow();
    electron_1.globalShortcut.register('CommandOrControl+H', () => {
        if (mainWindow) {
            if (mainWindow.isVisible()) {
                mainWindow.hide();
            }
            else {
                mainWindow.show();
                mainWindow.webContents.send('window-shown');
            }
        }
    });
});
electron_1.app.on('will-quit', () => {
    electron_1.globalShortcut.unregisterAll();
});
