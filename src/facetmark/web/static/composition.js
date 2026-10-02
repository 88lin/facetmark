// IME candidate text is not yet a query. Share that state with the page's
// keyboard shortcuts so they also leave candidate navigation alone.
const composing = new WeakSet();

export function isComposing(event) {
  // Some engines report the confirming key as 229 after isComposing clears.
  return event.isComposing || event.keyCode === 229 || composing.has(event.target);
}

export function onCommittedInput(input, change, start) {
  input.addEventListener("compositionstart", () => {
    composing.add(input);
    start();
  });
  input.addEventListener("compositionend", () => {
    composing.delete(input);
    change();
  });
  input.addEventListener("input", (event) => {
    if (!isComposing(event)) change();
  });
  // The final input event may follow compositionend. Callers debounce their
  // work, so both event orders settle on one committed query.
  return () => composing.has(input);
}
