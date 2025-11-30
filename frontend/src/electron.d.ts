export {};

declare global {
  interface Window {
    electronAPI?: {
      minimize: () => void;
      maximize: () => void;
      close: () => void;
      resize: (width: number, height: number) => void;
      onWindowShown: (callback: () => void) => void;
      removeAllWindowShownListeners: () => void;
    };
  }
}

