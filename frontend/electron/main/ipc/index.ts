import { registerWindowHandlers } from './handlers/window';
import { registerSettingsHandlers } from './settings';

/**
 * Register all IPC handlers
 * Add new handler registrations here as modules are added
 */
export function registerIpcHandlers(): void {
  registerWindowHandlers();
  registerSettingsHandlers();
}
