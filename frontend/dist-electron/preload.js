"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
electron_1.contextBridge.exposeInMainWorld('electronAPI', {
    minimize: () => electron_1.ipcRenderer.send('window-minimize'),
    maximize: () => electron_1.ipcRenderer.send('window-maximize'),
    close: () => electron_1.ipcRenderer.send('window-close'),
    resize: (width, height) => electron_1.ipcRenderer.send('window-resize', width, height),
    onWindowShown: (callback) => electron_1.ipcRenderer.on('window-shown', () => callback()),
    removeAllWindowShownListeners: () => electron_1.ipcRenderer.removeAllListeners('window-shown')
});
