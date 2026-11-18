import type { Page } from "@playwright/test";

// Screenshots must capture the finished layout, including JS-driven Motion and
// GSAP. Playwright's animations:disabled only finishes CSS/WAAPI animations.
export async function settleVisualLayout(page: Page) {
  await page.evaluate(async () => {
    await document.fonts.ready;
    const selectors = ".result-row, .preview-pane, .preview-drawer, .page-scroll, .workspace-toolbar, .sidebar, .facet-options, .facet-tree-children, .selection-pill, .setup-panel:not([hidden]), .settings-panel:not([hidden]), .fm-picker-popover:popover-open";
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
        const active = document.querySelector("[data-content-motion]") ||
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

// Chromium's number field scrolls an internal editor that ordinary input
// geometry cannot see. Read its actual text viewport so a correct value cannot
// pass while native stepper buttons hide some of its digits.
export async function numberInputTextLayout(page: Page, selector: string) {
  const cdp = await page.context().newCDPSession(page);
  try {
    const { root } = await cdp.send("DOM.getDocument", { depth: 0, pierce: true });
    const { nodeId } = await cdp.send("DOM.querySelector", { nodeId: root.nodeId, selector });
    const { node } = await cdp.send("DOM.describeNode", { nodeId, depth: -1, pierce: true });
    type NativeNode = { backendNodeId: number; nodeType?: number; nodeValue?: string; attributes?: string[]; children?: NativeNode[]; shadowRoots?: NativeNode[] };
    const findViewport = (current: NativeNode): NativeNode | undefined => {
      const attributes = current.attributes || [];
      if (attributes.some((name, index) => index % 2 === 0 && name === "id" && attributes[index + 1] === "editing-view-port")) return current;
      for (const child of [...current.children || [], ...current.shadowRoots || []]) {
        const found = findViewport(child); if (found) return found;
      }
    };
    const viewport = findViewport(node);
    if (!viewport) throw new Error("Number input's native text viewport was not found");
    const textNodes: NativeNode[] = [];
    const collectText = (current: NativeNode) => {
      if (current.nodeType === 3 && current.nodeValue) textNodes.push(current);
      for (const child of current.children || []) collectText(child);
    };
    collectText(viewport);
    if (!textNodes.length) throw new Error("Number input's native text was not found");
    const { model } = await cdp.send("DOM.getBoxModel", { backendNodeId: viewport.backendNodeId });
    const x = model.content.filter((_value: number, index: number) => index % 2 === 0);
    const left = Math.min(...x), right = Math.max(...x);
    const fragments: { left: number; right: number; width: number }[] = [];
    for (const text of textNodes) {
      const { quads } = await cdp.send("DOM.getContentQuads", { backendNodeId: text.backendNodeId });
      for (const quad of quads) {
        const points = quad.filter((_value: number, index: number) => index % 2 === 0);
        const start = Math.min(...points), end = Math.max(...points);
        if (end > start) fragments.push({ left: start, right: end, width: end - start });
      }
    }
    return { text: textNodes.map(text => text.nodeValue).join(""), left, right, width: right - left, fragments };
  } finally { await cdp.detach(); }
}

