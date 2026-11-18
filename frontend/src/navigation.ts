export type View = "library" | "sessions" | "tasks" | "settings" | "setup" | "import" | "chat";
export const settingsSections = ["models", "sync", "extension", "mcp", "desktop"] as const;
export type SettingsSection = typeof settingsSections[number];

const views: readonly View[] = ["library", "sessions", "tasks", "settings", "setup", "import", "chat"];

export function viewFromHash(hash: string): View {
  const name = hash.slice(1).split("/")[0];
  return views.includes(name as View) ? name as View : "library";
}

export function sectionFromHash(hash: string): SettingsSection {
  const section = hash.split("/")[1];
  return settingsSections.includes(section as SettingsSection) ? section as SettingsSection : "models";
}

// Only view and category names enter the address. Drafts and credentials stay
// owned by their forms, and library filters stay in the current workspace.
export function viewHash(view: View, section: SettingsSection): string {
  return view === "library" ? "" : view === "settings" ? `#settings/${section}` : `#${view}`;
}
