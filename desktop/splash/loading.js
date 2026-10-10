// Only the local splash has restart capability. Remote bookmark content has none.
const internals = window.__TAURI_INTERNALS__;
const english = !navigator.language.toLowerCase().startsWith('zh');
if (english) {
  document.querySelector('#status').textContent = 'Opening your bookmark workspace…';
  document.querySelector('#hint').textContent = 'The first launch may take a moment';
  document.querySelector('#retry').textContent = 'Restart service';
}
document.querySelector('#retry').onclick = async () => {
  const button = document.querySelector('#retry');
  button.disabled = true;
  try {
    await internals.invoke('restart_backend');
    button.hidden = true;
    document.querySelector('#status').textContent = english ? 'Opening your bookmark workspace…' : '正在打开你的书签工作台…';
  } catch (error) {
    document.querySelector('#hint').textContent = String(error);
  } finally { button.disabled = false; }
};
window.showStartupError = (message) => {
  document.querySelector('#status').textContent = english ? 'The local service could not start.' : '本地服务未能启动。';
  document.querySelector('#hint').textContent = message;
  document.querySelector('#retry').hidden = false;
};
