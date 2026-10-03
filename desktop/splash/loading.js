// Only the local splash has restart capability. Remote bookmark content has none.
const internals = window.__TAURI_INTERNALS__;
const english = !navigator.language.toLowerCase().startsWith('zh');
if (english) {
  document.querySelector('#status').textContent = 'Opening your bookmark workspace…';
  document.querySelector('#hint').textContent = 'The first launch may take a moment';
  document.querySelector('#retry').textContent = 'Restart service';
}
document.querySelector('#retry').onclick = () => internals.invoke('restart_backend');
window.showStartupError = (message) => {
  document.querySelector('#status').textContent = english ? 'The local service could not start.' : '本地服务未能启动。';
  document.querySelector('#hint').textContent = message;
  document.querySelector('#retry').hidden = false;
};
