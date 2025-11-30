/// <reference types="vite/client" />

import type { ElectronAPI } from '@electron/shared/ipc';

// Re-export electron types for renderer
export type { ElectronAPI };

// Augment global Window interface
declare global {
  interface Window {
    electron?: ElectronAPI;
  }
}
