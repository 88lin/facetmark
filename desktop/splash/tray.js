// This bridge is available only to the packaged tray-menu window.
const bridge = window.__TAURI_INTERNALS__;
const english = !navigator.language.toLowerCase().startsWith('zh');
const items = [...document.querySelectorAll('[data-action]')];
const feedback = document.querySelector('#tray-feedback');
const shell = document.querySelector('.tray-shell');
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
let arrival;
reducedMotion.addEventListener('change', () => { if (reducedMotion.matches) arrival?.cancel(); });
let busy = false;
let generation = 0;
if (english) {
  document.documentElement.lang = 'en';
  document.querySelectorAll('[data-en]').forEach(label => { label.textContent = label.dataset.en; });
}
function focusItem(index) {
  items.forEach((item, i) => { item.tabIndex = i === index ? 0 : -1; });
  items[index]?.focus({ preventScroll: true });
}
function showError(error) {
  feedback.dataset.error = 'true';
  feedback.setAttribute('role', 'alert');
  feedback.textContent = (english ? 'Could not apply this change. Retry: ' : '未能应用此设置，可重试：') + String(error);
}
function paint(state) {
  document.querySelector('[data-action="startup"]').setAttribute('aria-checked', String(state.startup));
  document.querySelector('[data-action="shortcut"]').setAttribute('aria-checked', String(state.shortcut));
  document.querySelector('#tray-status').textContent = state.ready
    ? english ? 'Your collection is ready' : '收藏工作区已就绪'
    : english ? 'Service is starting' : '本地服务正在启动';
  feedback.dataset.error = 'false';
  feedback.setAttribute('role', 'status');
  feedback.textContent = state.shortcut ? 'Ctrl + Shift + Space'
    : english ? 'Global shortcut is off' : '全局快捷键已关闭';
}
async function openMenu() {
  const current = ++generation;
  document.body.dataset.phase = 'open';
  // The native window is reused. Each opening owns one fresh, interruptible
  // entrance, even when the previous CSS state was already "open".
  arrival?.cancel();
  if (!reducedMotion.matches) arrival = shell.animate([
    { transform: 'translateY(5px) scale(.985)', opacity: .5 },
    { transform: 'none', opacity: 1 },
  ], { duration: 180, easing: 'cubic-bezier(.22, 1, .36, 1)' });
  if (!busy) items.forEach(item => { item.disabled = false; });
  focusItem(0);
  try {
    const state = await bridge.invoke('tray_snapshot');
    if (current === generation && !busy) paint(state);
  } catch (error) { if (current === generation) showError(error); }
}
window.openFacetmarkTray = openMenu;
items.forEach((item, index) => {
  item.addEventListener('pointerenter', () => { if (!busy) items.forEach((entry, i) => { entry.tabIndex = i === index ? 0 : -1; }); });
  item.addEventListener('focus', () => { items.forEach((entry, i) => { entry.tabIndex = i === index ? 0 : -1; }); });
  item.addEventListener('click', async () => {
    if (busy) return;
    busy = true; generation++;
    items.forEach(entry => { entry.disabled = true; });
    try { paint(await bridge.invoke('tray_action', { action: item.dataset.action })); }
    catch (error) { showError(error); }
    finally {
      busy = false; items.forEach(entry => { entry.disabled = false; });
      if (['startup', 'shortcut'].includes(item.dataset.action) || feedback.dataset.error === 'true') focusItem(index);
    }
  });
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape') { event.preventDefault(); void bridge.invoke('tray_action', { action: 'dismiss' }).catch(showError); return; }
  if (busy || !['ArrowDown', 'ArrowUp', 'Home', 'End', 'Tab'].includes(event.key)) return;
  event.preventDefault();
  const current = Math.max(0, items.indexOf(document.activeElement));
  const next = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1
    : (current + (event.key === 'ArrowUp' || (event.key === 'Tab' && event.shiftKey) ? -1 : 1) + items.length) % items.length;
  focusItem(next);
});
document.addEventListener('contextmenu', event => event.preventDefault());
void openMenu();
