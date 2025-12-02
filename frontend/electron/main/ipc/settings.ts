import { ipcMain } from 'electron';
import Store from 'electron-store';
import { SETTINGS_CHANNELS, DEFAULT_SETTINGS, type Settings } from '../../shared/settings';

const store = new Store<Settings>({
  defaults: DEFAULT_SETTINGS,
});

export function registerSettingsHandlers() {
  ipcMain.handle(SETTINGS_CHANNELS.GET_SETTINGS, () => {
    return store.store;
  });

  ipcMain.handle(SETTINGS_CHANNELS.SET_SETTINGS, (_, settings: Settings) => {
    store.store = settings;
    return store.store;
  });
}
