import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

type TrayTestWindow = typeof window & {
  __actions: string[]; __rejectNext: boolean; __holdNext: boolean; __release: () => void;
  openFacetmarkTray: () => Promise<void>;
  __TAURI_INTERNALS__: { invoke: (command: string, args?: { action: string }) => Promise<unknown> };
};

for (const locale of ["zh-CN", "en-US"]) test.describe(`packaged tray page ${locale}`, () => {
  test.use({ locale });
  test("keyboard navigation, native-state feedback and rapid clicks remain coherent across themes", async ({ page }) => {
    await mkdir("screenshots/collection-review", { recursive: true });
    await page.setViewportSize({ width: 312, height: 374 });
    await page.route("**/*", route => new URL(route.request().url()).protocol === "file:" ? route.continue() : route.abort());
    const errors: string[] = []; page.on("pageerror", error => errors.push(error.message));
    await page.addInitScript(() => {
      const target = window as TrayTestWindow;
      target.__actions = []; target.__rejectNext = false; target.__holdNext = false;
      const state = { startup: false, shortcut: true, ready: true };
      target.__TAURI_INTERNALS__ = { invoke: async (command, args) => {
        if (command === "tray_snapshot") return { ...state };
        if (command !== "tray_action" || !args) throw new Error("Unexpected synthetic tray command");
        target.__actions.push(args.action);
        if (target.__holdNext) { target.__holdNext = false; await new Promise<void>(resolve => { target.__release = resolve; }); }
        if (target.__rejectNext) { target.__rejectNext = false; throw new Error("Synthetic native registration failure; retry is available."); }
        if (args.action === "startup") state.startup = !state.startup;
        if (args.action === "shortcut") state.shortcut = !state.shortcut;
        return { ...state };
      } };
    });
    await page.goto(pathToFileURL(resolve("../desktop/splash/tray.html")).href);
    await page.evaluate(() => document.fonts.ready);
    const show = page.locator('[data-action="show"]'), startup = page.locator('[data-action="startup"]'), shortcut = page.locator('[data-action="shortcut"]');
    await expect(show).toBeFocused(); await expect(shortcut).toHaveAttribute("aria-checked", "true");
    for (let opening = 0; opening < 3; opening++) {
      const motion = await page.evaluate(async () => {
        await (window as TrayTestWindow).openFacetmarkTray();
        await new Promise(requestAnimationFrame);
        return document.querySelector('.tray-shell')!.getAnimations().filter(animation => animation.playState === "running").length;
      });
      expect(motion).toBe(1);
    }
    await page.keyboard.press("ArrowDown"); await expect(startup).toBeFocused();
    await page.keyboard.press("Space"); await expect(startup).toHaveAttribute("aria-checked", "true");
    await page.keyboard.press("ArrowDown"); await expect(shortcut).toBeFocused();
    await page.evaluate(() => { (window as TrayTestWindow).__rejectNext = true; });
    await shortcut.press("Enter");
    await expect(page.locator("#tray-feedback")).toContainText("Synthetic native registration failure");
    await expect(shortcut).toHaveAttribute("aria-checked", "true"); await expect(shortcut).toBeEnabled();
    await page.screenshot({ path: `screenshots/collection-review/polish-native-tray-error-${locale}.png`, animations: "disabled" });
    await shortcut.press("Enter"); await expect(shortcut).toHaveAttribute("aria-checked", "false");
    const before = await page.evaluate(() => (window as TrayTestWindow).__actions.length);
    await page.evaluate(() => { (window as TrayTestWindow).__holdNext = true; });
    await startup.click(); await expect(startup).toBeDisabled();
    await startup.evaluate(element => { (element as HTMLButtonElement).click(); (element as HTMLButtonElement).click(); });
    expect(await page.evaluate(() => (window as TrayTestWindow).__actions.length)).toBe(before + 1);
    await page.evaluate(() => (window as TrayTestWindow).__release());
    await expect(startup).toBeEnabled(); await expect(startup).toHaveAttribute("aria-checked", "false");
    for (const theme of ["light", "dark"] as const) {
      await page.emulateMedia({ colorScheme: theme });
      await page.keyboard.press("End"); await expect(page.locator('[data-action="exit"]')).toBeFocused();
      await expect(page.locator('[data-action="exit"]')).toBeInViewport({ ratio: 1 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await page.screenshot({ path: `screenshots/collection-review/polish-native-tray-${locale}-${theme}.png`, animations: "disabled" });
    }
    await page.emulateMedia({ reducedMotion: "reduce" });
    await expect(page.locator(".tray-shell")).toHaveCSS("animation-name", "none");
    expect(await page.locator(".tray-shell").evaluate(element => element.getAnimations().every(animation => animation.playState !== "running"))).toBe(true);
    await page.evaluate(() => (window as TrayTestWindow).openFacetmarkTray());
    expect(await page.locator(".tray-shell").evaluate(element => element.getAnimations().length)).toBe(0);
    await page.keyboard.press("Escape");
    await expect.poll(() => page.evaluate(() => (window as TrayTestWindow).__actions.at(-1))).toBe("dismiss");
    expect(errors).toEqual([]);
  });
});
