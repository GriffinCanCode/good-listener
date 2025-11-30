/// <reference types="vite/client" />

// Re-export electron types for renderer
export type { ElectronAPI } from '@electron/shared/ipc';

// Augment global Window interface
declare global {
  interface Window {
    electron: import('@electron/shared/ipc').ElectronAPI;
  }
}

