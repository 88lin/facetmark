// Only the local splash has restart capability. Remote bookmark content has none.
const internals = window.__TAURI_INTERNALS__;
const english = !navigator.language.toLowerCase().startsWith('zh');
const status = document.querySelector('#status');
const hint = document.querySelector('#hint');
const retry = document.querySelector('#retry');
const track = document.querySelector('#track');
const idleStatus = english ? 'Opening your bookmark workspace…' : '正在启动你的书签工作台…';
if (english) {
  status.textContent = idleStatus;
  hint.textContent = 'The first launch may take a moment';
  retry.textContent = 'Restart service';
}

function showError(message) {
  status.textContent = english ? 'The local service could not start.' : '本地服务未能启动。';
  hint.textContent = message;
  track.hidden = true;
  retry.hidden = false;
}

window.showStartupError = showError;

// The shell may have reported an error before this script parsed; the native
// side parks the message on the window rather than racing a timer.
if (window.__facetmarkStartupError) showError(window.__facetmarkStartupError);

retry.onclick = async () => {
  retry.disabled = true;
  try {
    await internals.invoke('restart_backend');
    retry.hidden = true;
    track.hidden = false;
    status.textContent = idleStatus;
    hint.textContent = english ? 'The first launch may take a moment' : '首次启动可能需要一点时间';
  } catch (error) {
    hint.textContent = String(error);
  } finally {
    retry.disabled = false;
  }
};
