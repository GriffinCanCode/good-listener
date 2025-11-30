import { registerWindowHandlers } from './handlers/window';

/**
 * Register all IPC handlers
 * Add new handler registrations here as modules are added
 */
export function registerIpcHandlers(): void {
  registerWindowHandlers();
}

