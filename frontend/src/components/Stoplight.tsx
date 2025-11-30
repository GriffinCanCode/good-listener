import React from 'react';

const ELECTRON = (window as any).require?.('electron');

export const Stoplight: React.FC = () => {
  const handle = (action: string) => (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent drag
    ELECTRON?.ipcRenderer.send(action);
  };

  return (
    <div className="stoplight no-drag">
      <button onClick={handle('window-close')} className="control close" title="Close" />
      <button onClick={handle('window-minimize')} className="control minimize" title="Minimize" />
      <button onClick={handle('window-maximize')} className="control maximize" title="Maximize" />
    </div>
  );
};

