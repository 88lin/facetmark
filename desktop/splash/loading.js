// Only the local splash has restart capability. Remote bookmark content has none.
const internals = window.__TAURI_INTERNALS__;
const english = !navigator.language.toLowerCase().startsWith('zh');
const status = document.querySelector('#status');
const hint = document.querySelector('#hint');
const retry = document.querySelector('#retry');
const track = document.querySelector('#track');
const idleStatus = english ? 'Opening your collection workspace…' : '正在打开你的收藏工作区…';
if (english) {
  document.documentElement.lang = 'en';
  status.textContent = idleStatus;
  hint.textContent = 'The first launch may take a moment';
  retry.textContent = 'Restart service';
}

function showError(message) {
  document.body.dataset.phase = 'error';
  status.textContent = english ? 'The local service could not start.' : '本地服务未能启动。';
  hint.textContent = message;
  track.hidden = true;
  retry.hidden = false;
  retry.focus({ preventScroll: true });
}

window.showStartupError = showError;

// The shell may have reported an error before this script parsed; the native
// side parks the message on the window rather than racing a timer.
if (window.__facetmarkStartupError) showError(window.__facetmarkStartupError);

retry.onclick = async () => {
  if (retry.disabled) return;
  retry.disabled = true;
  // Set waiting before the invocation. Native errors received during the
  // promise must stay visible after the restart command resolves.
  document.body.dataset.phase = 'connecting';
  retry.hidden = true;
  track.hidden = false;
  status.textContent = idleStatus;
  hint.textContent = english ? 'The first launch may take a moment' : '首次启动可能需要一点时间';
  try {
    await internals.invoke('restart_backend');
  } catch (error) {
    showError(String(error));
  } finally {
    retry.disabled = false;
    if (document.body.dataset.phase === 'error') retry.focus({ preventScroll: true });
  }
};
