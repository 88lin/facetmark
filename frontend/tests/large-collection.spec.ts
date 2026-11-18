import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import { numberInputTextLayout, settleVisualLayout } from "./visual-layout";

test.skip(process.env.FACETMARK_LARGE_VALIDATION !== "1", "Runs in the separate 200k cloud matrix");

test("200k actual records stay paginated and all matching selection survives deep paging", async ({ page }) => {
  let started: Record<string, unknown> | null = null;
  await page.route("**/admin/jobs/start", route => {
    started = route.request().postDataJSON();
    return route.fulfill({ json: { id: "synthetic-summary", run_id: "synthetic-summary-run", state: "done", params: started } });
  });
  await page.goto("/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  const selectAll = page.getByRole("checkbox", { name: "全选当前结果", exact: true });
  await expect(selectAll).toBeVisible();
  await selectAll.check();
  await page.locator(".bookmark-check").first().uncheck();
  await page.locator(".bookmark-check").nth(1).uncheck();
  await expect(page.locator(".library-selection-count")).toHaveText("已选 199,998");
  await expect(selectAll).toHaveJSProperty("indeterminate", true);
  await expect(page.locator(".collection-selection")).toHaveCount(0);
  const jump = page.getByRole("spinbutton", { name: "跳转页码" });
  await jump.fill("6667");
  await jump.press("Enter");
  await expect(page.locator(".results-footer")).toContainText("199981–200000");
  await expect(page.locator(".result-row")).toHaveCount(20);
  await expect(page.locator(".bookmark-check:checked")).toHaveCount(20);
  await expect(page.locator(".library-selection-count")).toHaveText("已选 199,998");
  const request = page.waitForRequest(r => r.url().includes("/admin/jobs/preview"));
  await page.getByRole("button", { name: "生成摘要", exact: true }).click();
  const body = (await request).postDataJSON();
  expect(body.bookmark_ids).toBeUndefined();
  expect(body.scope.exclude_ids).toHaveLength(2);
  expect(body.force).toBe(true);
  expect(JSON.stringify(body).length).toBeLessThan(1000);
  await expect.poll(() => started).toEqual(expect.objectContaining({
    mode: "summarize", scope: body.scope, force: true, confirmed: true, summary_language: "zh",
  }));
  await expect(page.getByRole("dialog", { name: "生成 AI 摘要", exact: true })).toHaveCount(0);
  await expect(selectAll).not.toBeChecked();
  await page.getByRole("textbox", { name: "搜索书签", exact: true }).fill("needle");
  await expect(page.locator(".result-row")).toHaveCount(30);
  await expect(page.locator(".result-title").first()).toContainText("needle");
  expect(await page.locator(".result-row").count()).toBeLessThanOrEqual(30);
  await mkdir("screenshots", { recursive: true });
  await page.screenshot({ path: "screenshots/collection-200k.png", animations: "disabled" });
});

test("200k actual records keep full English counts and keyboard paging in narrow windows", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("fm-language", "en"); localStorage.setItem("fm-theme", "dark");
  });
  await page.setViewportSize({ width: 320, height: 640 });
  await page.goto("/app");
  await expect(page.locator(".result-row")).toHaveCount(30);
  const footer = page.locator(".results-footer");
  const jump = footer.getByRole("spinbutton", { name: "Page to jump to", exact: true });
  const captures: unknown[] = [];
  await mkdir("screenshots", { recursive: true });
  async function checkLayout(name: string) {
    await settleVisualLayout(page);
    const geometry = await footer.evaluate(element => {
      const box = (node: Element) => {
        const rect = node.getBoundingClientRect();
        return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom, width: rect.width, height: rect.height };
      };
      const textRects = (selector: string) => {
        const text = document.createRange(); text.selectNodeContents(element.querySelector(selector)!);
        return [...text.getClientRects()].filter(rect => rect.width > 0 && rect.height > 0)
          .map(rect => ({ left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom }));
      };
      return { viewport: innerWidth, footer: box(element), group: box(element.querySelector(".collection-subtitle")!),
        countRects: textRects(".result-count"), unitRects: textRects(".collection-count-label"),
        paging: box(element.lastElementChild!), controls: [...element.querySelectorAll("input, button")].map(node => {
          const style = getComputedStyle(node);
          return { ...box(node), focused: node.matches(":focus-visible") || node.getAttribute("data-focus-visible") === "true",
            outlineWidth: parseFloat(style.outlineWidth), outlineOffset: parseFloat(style.outlineOffset), outlineStyle: style.outlineStyle };
        }),
        pageCountRects: textRects(".page-jump > span"),
        scrollWidth: element.scrollWidth, clientWidth: element.clientWidth };
    });
    const textLayout = await numberInputTextLayout(page, ".page-jump input");
    captures.push({ name, ...geometry, textLayout });
    await writeFile("screenshots/collection-200k-narrow.json", JSON.stringify(captures, null, 2));
    await page.screenshot({ path: `screenshots/collection-200k-${name}.png` });
    expect(textLayout.text).toBe(await jump.inputValue()); expect(textLayout.width).toBeGreaterThan(0); expect(textLayout.fragments).not.toHaveLength(0);
    for (const fragment of textLayout.fragments) {
      expect(fragment.left).toBeGreaterThanOrEqual(textLayout.left - 1);
      expect(fragment.right).toBeLessThanOrEqual(textLayout.right + 1);
    }
    await expect(footer.locator(".result-count")).toHaveText("200000");
    await expect(footer.locator(".collection-count-label")).toHaveText("saved pages");
    expect(geometry.footer.height).toBeLessThanOrEqual(52);
    expect(geometry.scrollWidth).toBeLessThanOrEqual(geometry.clientWidth);
    for (const fragment of [...geometry.countRects, ...geometry.unitRects]) {
      expect(fragment.left).toBeGreaterThanOrEqual(geometry.group.left - 1);
      expect(fragment.right).toBeLessThanOrEqual(geometry.group.right + 1);
      expect(fragment.right).toBeLessThanOrEqual(geometry.paging.left - 1);
    }
    for (const control of geometry.controls) {
      expect(control.left).toBeGreaterThanOrEqual(0); expect(control.right).toBeLessThanOrEqual(geometry.viewport);
      expect(control.width).toBeGreaterThanOrEqual(44); expect(control.height).toBeGreaterThanOrEqual(44);
    }
    const focused = geometry.controls.find(control => control.focused)!;
    expect(focused).toBeDefined(); expect(focused.outlineStyle).toBe("solid"); expect(focused.outlineWidth).toBeGreaterThanOrEqual(2);
    const extra = Math.max(0, focused.outlineWidth + focused.outlineOffset);
    const paint = { left: focused.left - extra, right: focused.right + extra, top: focused.top - extra, bottom: focused.bottom + extra };
    expect(paint.left).toBeGreaterThanOrEqual(geometry.footer.left - 1); expect(paint.right).toBeLessThanOrEqual(geometry.footer.right + 1);
    expect(paint.top).toBeGreaterThanOrEqual(geometry.footer.top - 1); expect(paint.bottom).toBeLessThanOrEqual(geometry.footer.bottom + 1);
    for (const neighbor of [...geometry.countRects, ...geometry.unitRects, ...geometry.pageCountRects, ...geometry.controls.filter(control => control !== focused)]) {
      const overlapX = Math.min(paint.right, neighbor.right) - Math.max(paint.left, neighbor.left);
      const overlapY = Math.min(paint.bottom, neighbor.bottom) - Math.max(paint.top, neighbor.top);
      expect(overlapX <= 0 || overlapY <= 0).toBe(true);
    }
  }
  await expect(jump).toBeEnabled();
  await expect(jump).toHaveAttribute("max", "6667");
  await footer.getByRole("button", { name: "Next page", exact: true }).focus(); await page.keyboard.press("ArrowRight");
  await checkLayout("first-en-dark-320");
  const lastPage = page.waitForResponse(response => {
    const url = new URL(response.url());
    return url.pathname === "/bookmarks" && url.searchParams.get("offset") === "199980";
  });
  await jump.fill("6667"); await jump.press("Enter");
  const received = await (await lastPage).json();
  expect(received.total).toBe(200000); expect(received.offset).toBe(199980); expect(received.items).toHaveLength(20);
  await expect(page.locator(".result-row")).toHaveCount(20);
  await expect(jump).toHaveValue("6667"); await expect(jump).toBeEnabled();
  await expect(footer.getByRole("button", { name: "Next page", exact: true })).toBeDisabled();
  await jump.focus(); await jump.press("End");
  await checkLayout("last-en-dark-320");
  await page.setViewportSize({ width: 390, height: 640 });
  await footer.getByRole("button", { name: "Go", exact: true }).focus(); await page.keyboard.press("ArrowRight");
  await checkLayout("last-en-dark-390");
  await footer.getByRole("button", { name: "Previous page", exact: true }).press("Space");
  await expect(jump).toHaveValue("6666"); await expect(jump).toBeEnabled();
  await expect(page.locator(".result-row")).toHaveCount(30);
  await expect(footer.locator(".result-range")).toHaveText("199951–199980 / ");
});
