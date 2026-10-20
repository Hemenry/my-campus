/**
 * 轻量订阅式 store。
 * 只做三件事：持有状态、浅比较后通知、把状态绑定到页面。
 * 接口与 mobx-miniprogram 的常用部分保持等价，后续可平滑替换。
 */

function createStore(initialState) {
  let state = Object.assign({}, initialState);
  const listeners = new Set();

  function emit(delta, keys) {
    listeners.forEach((listener) => {
      try {
        listener(state, delta, keys);
      } catch (err) {
        console.warn('[store] listener 执行失败:', err);
      }
    });
  }

  function getState() {
    return state;
  }

  function setState(patch) {
    const incoming = typeof patch === 'function' ? patch(state) : patch;
    if (!incoming) return state;

    const delta = {};
    const keys = [];
    Object.keys(incoming).forEach((key) => {
      if (incoming[key] !== state[key]) {
        delta[key] = incoming[key];
        keys.push(key);
      }
    });

    if (keys.length === 0) return state;

    state = Object.assign({}, state, delta);
    emit(delta, keys);
    return state;
  }

  function subscribe(listener) {
    listeners.add(listener);
    return () => listeners.delete(listener);
  }

  /**
   * 把 store 状态同步到页面，返回取消订阅函数（页面 onUnload 调用）
   */
  function bind(page) {
    if (!page) return () => {};

    page.data = Object.assign({}, page.data, state);

    return subscribe((next) => {
      if (typeof page.setData === 'function') {
        page.setData(next);
      } else {
        page.data = Object.assign({}, page.data, next);
      }
    });
  }

  return { getState, setState, subscribe, bind };
}

module.exports = { createStore };
