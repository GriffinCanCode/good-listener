export {};

declare global {
  interface Window {
    electronAPI?: {
      minimize: () => void;
      maximize: () => void;
      close: () => void;
      onWindowShown: (callback: () => void) => void;
      removeAllWindowShownListeners: () => void;
    };
  }
}

