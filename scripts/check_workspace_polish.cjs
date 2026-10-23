// Small isolated source checks, without an application server or browser.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('../frontend/node_modules/typescript');
const { gsap } = require('../frontend/node_modules/gsap/dist/gsap.js');
const read = name => fs.readFileSync(path.resolve(__dirname, '..', name), 'utf8');

function selectionContextCheck(source, detachBeforeCleanup = false) {
  let current;
  const instances = new Map();
  const react = {
    useRef(initial) {
      const index = current.index++;
      if (!(index in current.refs)) current.refs[index] = { current: initial };
      return current.refs[index];
    },
    useEffect(callback, dependencies) {
      const instance = current;
      const index = instance.index++;
      const previous = instance.effects[index];
      if (!previous || dependencies.some((value, i) => value !== previous.dependencies[i])) {
        instance.pending.push({
          cleanup: () => previous?.cleanup?.(),
          setup: () => { instance.effects[index] = { dependencies, cleanup: callback() }; },
        });
      }
    },
  };
  react.useLayoutEffect = react.useEffect;
  const scope = {};
  const observers = [];
  class SyntheticObserver {
    constructor(callback) { this.callback = callback; observers.push(this); }
    observe() { this.observing = true; }
    disconnect() { this.observing = false; }
  }
  const hookModule = { exports: {} };
  vm.runInNewContext(read('frontend/node_modules/@gsap/react/dist/index.js'), {
    exports: hookModule.exports, module: hookModule,
    require: name => name === 'react' ? react : { default: gsap },
  });
  const scriptModule = { exports: {} };
  const compiled = ts.transpileModule(source, { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText;
  vm.runInNewContext(compiled, {
    exports: scriptModule.exports, module: scriptModule, ResizeObserver: SyntheticObserver,
    require: name => {
      if (name === 'react') return react;
      if (name === 'gsap') return { gsap };
      if (name === '@gsap/react') return hookModule.exports;
      if (name === './useReducedMotion') return { useReducedMotion: () => false };
      if (name === 'react/jsx-runtime') return { jsx: (_, props) => props };
      throw new Error(`Unexpected import: ${name}`);
    },
  });
  const marker = (left, width) => {
    const owner = { isConnected: true, clientWidth: width, clientHeight: 32,
      closest: () => scope, getBoundingClientRect: () => ({ left, top: 10, width, height: 32 }) };
    const item = { parentElement: owner, x: 0, y: 0, width: '100%', height: '100%', clearProps: '' };
    item.getBoundingClientRect = () => ({ left: left + Number(item.x), top: 10 + Number(item.y),
      width: item.width === '100%' ? width : Number(item.width),
      height: item.height === '100%' ? 32 : Number(item.height) });
    return item;
  };
  const render = (id, active, target) => {
    if (!instances.has(id)) instances.set(id, { refs: [], effects: [], pending: [], index: 0 });
    current = instances.get(id); current.index = 0;
    const host = scriptModule.exports.SelectionPill({ active, group: 'synthetic-capsule' });
    const effects = current.pending.splice(0);
    if (!detachBeforeCleanup) effects.forEach(effect => effect.cleanup());
    if (host) host.ref.current = target;
    else current.refs[0].current = null;
    if (detachBeforeCleanup) effects.forEach(effect => effect.cleanup());
    effects.forEach(effect => effect.setup());
  };
  const a = marker(10, 80), b = marker(100, 95), c = marker(205, 90);
  try {
    render('a', true, a);
    render('a', false, a);
    render('b', true, b);
    const tween = gsap.getTweensOf(b).find(animation => animation.duration() > 0);
    assert.ok(tween, 'second capsule should move from the previous painted bounds');
    tween.progress(.35);
    const interrupted = b.getBoundingClientRect();
    render('b', false, b);
    assert.equal(gsap.getTweensOf(b).length, 0, 'inactive capsule must own and dispose all of its tweens');
    assert.equal(observers.at(-1).observing, false, 'inactive capsule must disconnect its observer');
    render('c', true, c);
    gsap.getTweensOf(c).find(animation => animation.duration() > 0).render(0, false, true);
    assert.ok(Math.abs(c.getBoundingClientRect().left - interrupted.left) < .001,
      `next capsule should resume from the interrupted paint: ${c.getBoundingClientRect().left} / ${interrupted.left}`);
    assert.ok(Math.abs(c.getBoundingClientRect().height - interrupted.height) < .001,
      'next capsule must preserve height during context cleanup with an attached ref');
    assert.ok(Math.abs(c.getBoundingClientRect().width - interrupted.width) < .001,
      'next capsule must preserve width during context cleanup with an attached ref');
    render('c', false, c);
    for (let i = 0; i < 30; i++) {
      render('a', true, a); render('a', false, a);
      render('b', true, b); render('b', false, b);
    }
    assert.equal(gsap.getTweensOf([a, b, c]).length, 0, 'rapid switches must leave no departed-marker tween');
    assert.ok(observers.every(observer => !observer.observing));
  } finally {
    for (const instance of instances.values()) for (const effect of instance.effects) effect?.cleanup?.();
    gsap.killTweensOf([a, b, c]);
  }
}

async function nativeRestartCheck(language) {
  const elements = new Map(['#status', '#hint', '#retry', '#track'].map(id => [id, {
    textContent: '', hidden: id === '#retry', disabled: false,
    focus() { if (!this.hidden && !this.disabled) this.focused = true; },
  }]));
  const retry = elements.get('#retry');
  let release;
  let calls = 0;
  const body = { dataset: { phase: 'connecting' } };
  const state = { __facetmarkStartupError: 'synthetic pre-script failure',
    __TAURI_INTERNALS__: { invoke(command) {
      assert.equal(command, 'restart_backend'); calls++;
      return new Promise((resolve, reject) => { release = { resolve, reject }; });
    } },
  };
  vm.runInNewContext(read('desktop/splash/loading.js'), {
    window: state, document: { body, documentElement: {}, querySelector: id => elements.get(id) },
    navigator: { language },
  });
  assert.equal(body.dataset.phase, 'error');
  const first = retry.onclick();
  assert.equal(body.dataset.phase, 'connecting');
  await retry.onclick();
  assert.equal(calls, 1, 'a second immediate retry must not start another service');
  state.showStartupError('synthetic native failure before promise resolution');
  retry.focused = false;
  release.resolve(); await first;
  assert.equal(body.dataset.phase, 'error');
  assert.equal(elements.get('#hint').textContent, 'synthetic native failure before promise resolution');
  assert.ok(retry.focused, 'failure received during restart regains focus after re-enabling retry');
  const second = retry.onclick();
  retry.focused = false;
  release.reject(new Error('synthetic restart rejection')); await second;
  assert.equal(body.dataset.phase, 'error');
  assert.ok(retry.focused);
  assert.match(elements.get('#hint').textContent, /synthetic restart rejection/);
  const third = retry.onclick(); release.resolve(); await third;
  assert.equal(body.dataset.phase, 'connecting');
  assert.equal(retry.hidden, true);
  assert.equal(elements.get('#track').hidden, false);
  assert.equal(calls, 3);
  assert.equal(retry.disabled, false);
}

(async () => {
  const source = read('frontend/src/InteractionMotion.tsx');
  selectionContextCheck(source, true);
  selectionContextCheck(source, false);
  const noPaintGuard = source.replaceAll('if (!paintLive.current || ref.current !== marker) return;', '');
  assert.throws(() => selectionContextCheck(noPaintGuard), /next capsule should resume/);
  const refOnlyGuard = source.replaceAll('if (!paintLive.current || ref.current !== marker) return;', 'if (ref.current !== marker) return;');
  assert.throws(() => selectionContextCheck(refOnlyGuard, false), /next capsule should resume/);
  // Disabling dependency cleanup is a synthetic negative control.
  const noDependencyCleanup = source.replace('revertOnUpdate: true', 'revertOnUpdate: false');
  assert.throws(() => selectionContextCheck(noDependencyCleanup), /inactive capsule must own/);
  await nativeRestartCheck('zh-CN');
  await nativeRestartCheck('en-US');
  gsap.ticker.sleep();
  console.log(JSON.stringify({ selectionContextCleanup: 'passed', interruption: 'passed',
    cleanupBeforeRefDetach: 'passed', cleanupAfterRefDetach: 'passed',
    unguardedReversionNegativeControl: 'failed as expected',
    refOnlyGuardNegativeControl: 'failed as expected',
    disabledCleanupNegativeControl: 'failed as expected', rapidSwitches: 60,
    syntheticNativeRestart: ['zh-CN', 'en-US'], browserOrInstalledRuntime: false }));
})().catch(error => { gsap.ticker.sleep(); console.error(error); process.exitCode = 1; });
