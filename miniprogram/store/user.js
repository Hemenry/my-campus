/**
 * 用户状态：登录资料与登录标记，落本地持久化。
 * persist / restore 可注入，便于测试。
 */

const { createStore } = require('../utils/store');
const storage = require('../utils/storage');

function createUserStore(deps) {
  const options = deps || {};
  const persist = options.persist || ((profile) => storage.set('profile', profile));
  const readProfile = options.restore || (() => storage.get('profile', null));

  const store = createStore({
    profile: null,
    isLogin: false
  });

  function login(profile) {
    persist(profile);
    store.setState({ profile, isLogin: true });
  }

  function logout() {
    persist(null);
    store.setState({ profile: null, isLogin: false });
  }

  function restore() {
    const profile = readProfile();
    if (profile) store.setState({ profile, isLogin: true });
  }

  function patchProfile(patch) {
    const next = Object.assign({}, store.getState().profile, patch);
    persist(next);
    store.setState({ profile: next });
  }

  return Object.assign({}, store, { login, logout, restore, patchProfile });
}

const userStore = createUserStore();

module.exports = { createUserStore, userStore };
