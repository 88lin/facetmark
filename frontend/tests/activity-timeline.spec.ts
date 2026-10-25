import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { settleVisualLayout } from "./visual-layout";

type Snapshot = { days: { key: string; from: number; to: number; count: number }[];
  months: { key: string; count: number }[]; older: number; oldest: number | null };
const timestamp = (value: string) => Date.parse(value) / 1000;
const snapshot = (today = "2026-10-25", months = ["2026-10", "2026-09"]): Snapshot => ({
  days: [2, 0, 1, 0, 0, 0, 3].map((count, index) => {
    const from = timestamp(today + "T00:00:00Z") - index * 86400;
    return { key: "day:" + new Date(from * 1000).toISOString().slice(0, 10), from, to: from + 86400, count };
  }),
  months: months.map((month, index) => ({ key: "month:" + month, count: index === 0 ? 4 : 2 })),
  older: 3, oldest: timestamp("2025-01-12T13:00:00Z"),
});
const records = [
  ["2026-10-25T01:00:00Z", "Today one"], ["2026-10-25T08:00:00Z", "Today two"],
  ["2026-10-23T11:00:00Z", "Recent Friday"], ["2026-10-19T00:00:00Z", "Recent boundary one"],
  ["2026-10-19T02:00:00Z", "Recent boundary two"], ["2026-10-19T03:00:00Z", "Recent boundary three"],
  ["2026-10-01T00:00:00Z", "Earlier October one"], ["2026-10-10T12:00:00Z", "Earlier October two"],
  ["2026-10-18T23:59:59Z", "Earlier October end"], ["2026-10-18T00:00:00Z", "Earlier October four"],
  ["2026-09-01T00:00:00Z", "September one"], ["2026-09-30T23:59:59Z", "September end"],
  ["2025-01-12T13:00:00Z", "Older January"], ["2025-06-01T12:00:00Z", "Older June"],
  ["2026-08-31T23:59:59Z", "Older boundary"],
].map(([date, title], index) => ({ bookmark_id: index + 1, title, ai_title: title,
  url: "https://synthetic.invalid/" + (index + 1), domain: "synthetic.invalid", folder: "",
  tags: [], summary: "Saved synthetic content.", summary_status: "done", date_added: timestamp(date) }));
const crossMonthDates = [
  "2026-08-04T01:00:00Z", "2026-08-04T08:00:00Z", "2026-08-02T11:00:00Z",
  "2026-07-29T00:00:00Z", "2026-07-29T02:00:00Z", "2026-07-29T03:00:00Z",
  "2026-07-01T00:00:00Z", "2026-07-10T12:00:00Z", "2026-07-28T23:59:59Z", "2026-07-28T00:00:00Z",
  "2026-06-01T00:00:00Z", "2026-06-30T23:59:59Z", "2025-01-12T13:00:00Z", "2025-06-01T12:00:00Z", "2026-05-31T23:59:59Z",
];
const crossMonthRecords = records.map((record, index) => ({ ...record, date_added: timestamp(crossMonthDates[index]),
  title: record.title.replace("October", "July").replace("September", "June"),
  ai_title: record.title.replace("October", "July").replace("September", "June"),
}));
const responses: Record<string, typeof records> = {
  "added:>=2026-10-01 added:<2026-10-19": records.slice(6, 10),
  "added:>=2026-10-25 added:<2026-10-26": records.slice(0, 2),
  "added:>=2026-10-19 added:<2026-10-20": records.slice(3, 6),
  "added:>=2026-09-01 added:<2026-10-01": records.slice(10, 12),
  "added:>=2025-01-12 added:<2026-09-01": records.slice(12),
  "added:>=2026-07-01 added:<2026-07-29": crossMonthRecords.slice(6, 10),
  "previous query": records.slice(14),
};

async function fixture(page: Page, initial = snapshot()) {
  const control = { value: initial, failed: false, pause: null as Promise<void> | null,
    records: initial.days[0]?.key === "day:2026-08-04" ? crossMonthRecords : records,
    responses: { ...responses },
    reads: [] as URL[], queries: [] as URL[] };
  await page.route("**/timeline?**", async route => {
    control.reads.push(new URL(route.request().url()));
    const value = control.value, failed = control.failed, pause = control.pause;
    if (pause) await pause;
    return route.fulfill(failed ? { status: 503, json: { detail: "Synthetic timeline unavailable" } } : { json: value });
  });
  await page.route("**/sessions?**", route => route.fulfill({ json: [{
    session_id: 9, label: "Existing saving context", started_at: timestamp("2026-10-25T00:00:00Z"), size: 2,
  }] }));
  await page.route("**/bookmarks?**", route => {
    const url = new URL(route.request().url()); control.queries.push(url);
    const query = url.searchParams.get("q") || "";
    const items = query ? control.responses[query] || [] : control.records;
    return route.fulfill({ json: { items, total: items.length, offset: 0, limit: 30, has_more: false,
      summary_counts: { total: items.length, pending: 0, done: items.length, failed: 0 } } });
  });
  return control;
}

async function enterSessions(page: Page, language: "zh" | "en" = "zh") {
  const name = language === "zh" ? "浏览批次" : "Saving sessions";
  if (!(await page.getByRole("button", { name, exact: true }).isVisible()))
    await page.getByRole("button", { name: language === "zh" ? "打开导航" : "Open navigation", exact: true }).click();
  await page.getByRole("button", { name, exact: true }).click();
  await expect(page.locator(".activity-timeline")).toBeVisible();
}

test.use({ timezoneId: "Pacific/Honolulu" });
test.beforeEach(async ({ page }) => {
  await mkdir("screenshots/collection-review", { recursive: true });
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.addInitScript(() => { localStorage.setItem("fm-language", "zh"); localStorage.setItem("fm-theme", "light"); });
  await page.route("**/*", route => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
});

test("month navigation excludes the separately displayed week and clears the previous search scope", async ({ page }) => {
  const control = await fixture(page);
  await page.goto("/app");
  await expect(page.locator(".result-list")).toHaveAttribute("aria-busy", "false");
  expect(control.reads).toHaveLength(0);
  await page.locator(".workspace-search input").fill("previous query");
  await page.locator(".collection-status [data-status=failed]").click();
  await expect(page.locator(".collection-status [data-status=failed]")).toHaveAttribute("aria-pressed", "true");
  await enterSessions(page);
  const panel = page.locator(".activity-timeline"), month = panel.locator('[data-period="month:2026-10"]');
  await expect(panel.locator(".activity-day-strip button")).toHaveCount(7);
  await expect(panel.locator(".activity-period-heading").first()).toContainText("6 条收藏");
  await expect(month.locator(".activity-bucket-range")).toHaveText("2026-10-01–2026-10-18");
  await expect(month.locator(".activity-bucket-count")).toHaveText("4");
  await expect(month).toHaveAttribute("aria-label", /2026-10-01–2026-10-18 UTC/);
  await expect(page.locator(".session-row")).toContainText("Existing saving context");
  await month.click();
  await expect(page.locator(".workspace-search input")).toHaveValue("added:>=2026-10-01 added:<2026-10-19");
  await expect(page.locator(".result-count")).toHaveText("4");
  const request = control.queries[control.queries.length - 1];
  expect(request.searchParams.get("q")).toBe("added:>=2026-10-01 added:<2026-10-19");
  expect(request.searchParams.get("status")).toBe("all");
  expect(request.searchParams.get("offset")).toBe("0");
  for (const field of ["folder", "tag", "domain", "session"]) expect(request.searchParams.has(field)).toBe(false);
  await expect(page.locator(".activity-timeline")).toHaveCount(0);
  await expect(page.locator(".result-title").first()).toHaveText("Earlier October one");
});

test("UTC days keep their dates in another timezone, zero days stay disabled and keyboard activation selects a day", async ({ page }) => {
  const control = await fixture(page);
  await page.goto("/app"); await enterSessions(page);
  const panel = page.locator(".activity-timeline");
  await expect(panel.locator(".activity-period-heading").first()).toContainText("2026-10-19–2026-10-25 · UTC");
  const day = panel.locator('[data-period="day:2026-10-25"]');
  await expect(day.locator(".activity-bucket-date")).toHaveText("10/25");
  await expect(panel.locator('[data-period="day:2026-10-24"]')).toBeDisabled();
  await day.focus(); await day.press("Space");
  await expect(page.locator(".workspace-search input")).toHaveValue("added:>=2026-10-25 added:<2026-10-26");
  await expect(page.locator(".result-count")).toHaveText("2");
  expect(control.queries[control.queries.length - 1].searchParams.get("q")).toBe("added:>=2026-10-25 added:<2026-10-26");
});

test("a week crossing a month uses the service cutoff for the partial previous month", async ({ page }) => {
  const control = await fixture(page, snapshot("2026-08-04", ["2026-07", "2026-06"]));
  await page.goto("/app"); await enterSessions(page);
  const panel = page.locator(".activity-timeline"), month = panel.locator('[data-period="month:2026-07"]');
  await expect(panel.locator(".activity-period-heading").first()).toContainText("2026-07-29–2026-08-04 · UTC");
  await expect(month.locator(".activity-bucket-range")).toHaveText("2026-07-01–2026-07-28");
  await month.focus(); await month.press("Enter");
  await expect(page.locator(".workspace-search input")).toHaveValue("added:>=2026-07-01 added:<2026-07-29");
  await expect(page.locator(".result-count")).toHaveText("4");
  expect(control.queries[control.queries.length - 1].searchParams.get("q")).toBe("added:>=2026-07-01 added:<2026-07-29");
});

test("the older tail links only to dates before the displayed months", async ({ page }) => {
  const control = await fixture(page);
  await page.goto("/app"); await enterSessions(page);
  const older = page.locator('.activity-timeline [data-period="older"]');
  await expect(older).toContainText("3 条收藏");
  await expect(older).toContainText("2025-01-12–2026-08-31 · UTC");
  await older.click();
  await expect(page.locator(".workspace-search input")).toHaveValue("added:>=2025-01-12 added:<2026-09-01");
  await expect(page.locator(".result-count")).toHaveText("3");
  expect(control.queries[control.queries.length - 1].searchParams.get("q")).toBe("added:>=2025-01-12 added:<2026-09-01");
});

test("initial loading and refresh errors retain the last successful counts and allow a retry", async ({ page }) => {
  const control = await fixture(page);
  let release = () => {};
  control.pause = new Promise<void>(resolve => { release = resolve; });
  await page.goto("/app"); await enterSessions(page);
  const panel = page.locator(".activity-timeline");
  await expect(panel.getByRole("status")).toHaveText("正在读取收藏活动…");
  await expect(panel.getByRole("button", { name: "刷新收藏活动", exact: true })).toBeDisabled();
  expect(control.reads).toHaveLength(1);
  control.pause = null; release();
  await expect(panel.locator('[data-period="month:2026-10"] .activity-bucket-count')).toHaveText("4");
  control.failed = true;
  await panel.getByRole("button", { name: "刷新收藏活动", exact: true }).click();
  await expect(panel.getByRole("alert")).toContainText("上次读取的结果");
  await expect(panel.locator('[data-period="month:2026-10"] .activity-bucket-count')).toHaveText("4");
  control.failed = false; control.value = snapshot(); control.value.months[0].count = 6;
  const additions = [16, 17].map(bookmark_id => ({ ...records[6], bookmark_id,
    url: "https://synthetic.invalid/" + bookmark_id, date_added: timestamp("2026-10-03T12:00:00Z"),
    title: "Added October " + bookmark_id, ai_title: "Added October " + bookmark_id,
  }));
  control.records = [...records, ...additions];
  control.responses["added:>=2026-10-01 added:<2026-10-19"] = [...records.slice(6, 10), ...additions];
  await panel.getByRole("button", { name: "重试收藏活动", exact: true }).click();
  await expect(panel.locator('[data-period="month:2026-10"] .activity-bucket-count')).toHaveText("6");
  await expect(panel.getByRole("alert")).toHaveCount(0);
  expect(control.reads).toHaveLength(3);
  expect(control.reads.every(url => url.searchParams.get("months") === "12")).toBe(true);
});

test("empty activity stays distinct from a failed response and revisiting reads fresh activity", async ({ page }) => {
  const control = await fixture(page, { days: [], months: [], older: 0, oldest: null });
  await page.goto("/app"); await enterSessions(page);
  const panel = page.locator(".activity-timeline");
  await expect(panel.locator(".activity-empty")).toContainText("暂无收藏活动");
  await expect(panel.locator(".activity-bucket")).toHaveCount(0);
  await expect(panel.getByRole("alert")).toHaveCount(0);
  await page.getByRole("button", { name: "全部书签", exact: true }).click();
  control.value = snapshot();
  await enterSessions(page);
  await expect(panel.locator('[data-period="month:2026-10"]')).toBeEnabled();
  expect(control.reads).toHaveLength(2);
  control.value = { ...snapshot(), days: snapshot().days.slice(0, 2) };
  await panel.getByRole("button", { name: "刷新收藏活动", exact: true }).click();
  await expect(panel.getByRole("alert")).toContainText("未能刷新收藏活动");
  await expect(panel.locator('[data-period="month:2026-10"] .activity-bucket-count')).toHaveText("4");
});

test("Chinese and English activity stays compact at 320px and keyboard focus scrolls the strip", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await fixture(page);
  await page.goto("/app"); await enterSessions(page);
  const panel = page.locator(".activity-timeline");
  await expect(panel).toHaveAttribute("aria-busy", "false");
  expect((await panel.boundingBox())!.height).toBeLessThan(500);
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    if (width === 320) {
      await page.getByRole("button", { name: "打开导航", exact: true }).click();
      await page.getByRole("dialog", { name: "导航", exact: true })
        .getByRole("button", { name: "切换语言", exact: true }).click();
      await page.getByRole("dialog", { name: "Navigation", exact: true })
        .getByRole("button", { name: "Toggle theme", exact: true }).click();
      await page.keyboard.press("Escape");
      await expect(page.getByRole("dialog", { name: "Navigation", exact: true })).toHaveCount(0);
      await expect(panel.getByRole("heading", { name: "Saving activity", exact: true })).toBeVisible();
      await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    }
    const lastDay = panel.locator('[data-period="day:2026-10-19"]');
    await lastDay.focus();
    await expect(lastDay).toBeInViewport({ ratio: 1 });
    expect(await panel.locator(".activity-day-strip").evaluate(element => element.scrollLeft)).toBeGreaterThan(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await settleVisualLayout(page);
    await page.screenshot({ path: "screenshots/collection-review/activity-timeline-" + width + ".png", animations: "disabled" });
  }
  await panel.locator('[data-period="day:2026-10-19"]').press("Enter");
  await expect(page.locator(".workspace-search input")).toHaveValue("added:>=2026-10-19 added:<2026-10-20");
  await expect(page.locator(".result-count")).toHaveText("3");
  expect(errors).toHaveLength(0);
});
