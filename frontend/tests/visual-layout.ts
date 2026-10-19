import type { Page } from "@playwright/test";

// Screenshots must capture the finished layout, including JS-driven Motion and
// GSAP. Playwright's animations:disabled only finishes CSS/WAAPI animations.
export async function settleVisualLayout(page: Page) {
  await page.evaluate(async () => {
    await document.fonts.ready;
    const selectors = ".result-row, .preview-pane, .preview-drawer, .page-scroll, .workspace-toolbar";
    const deadline = performance.now() + 5000;
    let previous = "";
    let stableSince = performance.now();
    await new Promise<void>((resolve, reject) => {
      const frame = () => {
        const elements = [...document.querySelectorAll<HTMLElement>(selectors)];
        const snapshot = JSON.stringify(elements.map(element => {
          const rect = element.getBoundingClientRect();
          const style = getComputedStyle(element);
          return [...[rect.x, rect.y, rect.width, rect.height].map(n => Math.round(n * 10) / 10),
            style.opacity, style.transform, style.filter];
        }));
        const active = document.querySelector("[data-content-motion], .interaction-ink") ||
          elements.some(element => element.getAnimations().some(animation => animation.playState === "running"));
        if (snapshot !== previous || active) stableSince = performance.now();
        previous = snapshot;
        if (performance.now() - stableSince >= 250) return resolve();
        if (performance.now() >= deadline) return reject(new Error("Visual layout did not settle before capture"));
        requestAnimationFrame(frame);
      };
      requestAnimationFrame(frame);
    });
  });
}

