/**
 * Type-safe IPC channel definitions
 * Shared between main, preload, and renderer processes
 */

// Channel names as const for type safety
export const IPC_CHANNELS = {
  // Window control channels (renderer -> main)
  WINDOW_MINIMIZE: 'window:minimize',
  WINDOW_MAXIMIZE: 'window:maximize',
  WINDOW_CLOSE: 'window:close',
  WINDOW_RESIZE: 'window:resize',

  // Events from main -> renderer
  WINDOW_SHOWN: 'window:shown',
  WINDOW_STATE_CHANGED: 'window:state-changed',
} as const;

// Derive types from the const object
export type IpcChannel = (typeof IPC_CHANNELS)[keyof typeof IPC_CHANNELS];

// Payload types for each channel
export interface IpcPayloads {
  [IPC_CHANNELS.WINDOW_MINIMIZE]: undefined;
  [IPC_CHANNELS.WINDOW_MAXIMIZE]: undefined;
  [IPC_CHANNELS.WINDOW_CLOSE]: undefined;
  [IPC_CHANNELS.WINDOW_RESIZE]: { width: number; height: number };
  [IPC_CHANNELS.WINDOW_SHOWN]: undefined;
  [IPC_CHANNELS.WINDOW_STATE_CHANGED]: { isMaximized: boolean; isMinimized: boolean };
}

// Type helper for invoke channels (request -> response)
// eslint-disable-next-line @typescript-eslint/no-empty-object-type
export interface IpcInvokeMap {
  // Add invoke channels here as needed
  // 'app:get-version': { request: undefined; response: string };
}

// Type-safe API exposed to renderer
export interface ElectronAPI {
  window: {
    minimize: () => void;
    maximize: () => void;
    close: () => void;
    resize: (width: number, height: number) => void;
    onShown: (callback: () => void) => () => void;
    onStateChanged: (
      callback: (state: { isMaximized: boolean; isMinimized: boolean }) => void
    ) => () => void;
  };
  platform: NodeJS.Platform;
}

declare global {
  interface Window {
    electron?: ElectronAPI;
  }
}
