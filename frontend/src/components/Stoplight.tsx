import React from 'react';

export const Stoplight: React.FC = () => {
  const handle = (action: 'close' | 'minimize' | 'maximize') => (e: React.MouseEvent) => {
    e.stopPropagation();
    window.electron?.window[action]();
  };

  return (
    <div className="stoplight no-drag">
      <button onClick={handle('close')} className="control close" title="Close" />
      <button onClick={handle('minimize')} className="control minimize" title="Minimize" />
      <button onClick={handle('maximize')} className="control maximize" title="Maximize" />
    </div>
  );
};
