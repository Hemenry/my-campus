const test = require('node:test');
const assert = require('node:assert');

const { createStore } = require('../miniprogram/utils/store');
const { createPlazaStore } = require('../miniprogram/store/plaza');
const { createUserStore } = require('../miniprogram/store/user');

const fakeFeed = (list) => async () => ({ list, hasMore: false });

test('setState 只通知发生变化的键', () => {
  const store = createStore({ a: 1, b: 2 });
  const keysSeen = [];
  store.subscribe((state, delta, keys) => keysSeen.push(keys));

  store.setState({ a: 3 });

  assert.deepStrictEqual(keysSeen, [['a']]);
});

test('值未变化时不触发通知', () => {
  const store = createStore({ a: 1 });
  let calls = 0;
  store.subscribe(() => {
    calls += 1;
  });

  store.setState({ a: 1 });

  assert.strictEqual(calls, 0);
});

test('unsubscribe 之后不再收到通知', () => {
  const store = createStore({ a: 1 });
  let calls = 0;
  const unsubscribe = store.subscribe(() => {
    calls += 1;
  });

  store.setState({ a: 2 });
  unsubscribe();
  store.setState({ a: 3 });

  assert.strictEqual(calls, 1);
});

test('bind 在无 setData 环境下不抛错', () => {
  const store = createStore({ a: 1 });
  const fakePage = { data: {} };
  assert.doesNotThrow(() => store.bind(fakePage));
  assert.strictEqual(fakePage.data.a, 1);
});

test('toggleLike 同一 id 连点两次回到初始', async () => {
  const store = createPlazaStore({
    fetchFeed: fakeFeed([{ id: 'p1', liked: false, collected: false, likes: 3, collects: 0 }])
  });
  await store.loadFeed({ reset: true });

  store.toggleLike('p1');
  store.toggleLike('p1');

  const post = store.getState().feed[0];
  assert.strictEqual(post.liked, false);
  assert.strictEqual(post.likes, 3);
});

test('toggleCollect 连点两次回到初始', async () => {
  const store = createPlazaStore({
    fetchFeed: fakeFeed([{ id: 'p1', liked: false, collected: false, likes: 0, collects: 0 }])
  });
  await store.loadFeed({ reset: true });

  store.toggleCollect('p1');
  store.toggleCollect('p1');

  const post = store.getState().feed[0];
  assert.strictEqual(post.collected, false);
  assert.strictEqual(post.collects, 0);
});

test('toggleLike 只影响目标条目', async () => {
  const store = createPlazaStore({
    fetchFeed: fakeFeed([
      { id: 'p1', liked: false, likes: 0 },
      { id: 'p2', liked: false, likes: 0 }
    ])
  });
  await store.loadFeed({ reset: true });

  store.toggleLike('p1');

  assert.strictEqual(store.getState().feed[1].liked, false);
});

test('setCategory 切换分类后页码归 1 且清空列表', async () => {
  const store = createPlazaStore({
    fetchFeed: async ({ page }) => ({
      list: [{ id: 'p' + page, liked: false, likes: 0 }],
      hasMore: page < 3
    })
  });
  await store.loadFeed({ reset: true });
  await store.loadFeed({});
  assert.strictEqual(store.getState().page, 2);
  assert.strictEqual(store.getState().feed.length, 2);

  await store.setCategory('求助');

  assert.strictEqual(store.getState().category, '求助');
  assert.strictEqual(store.getState().page, 1);
  assert.strictEqual(store.getState().feed.length, 1);
});

test('setCategory 同一分类不重复加载', async () => {
  let calls = 0;
  const store = createPlazaStore({
    fetchFeed: async () => {
      calls += 1;
      return { list: [], hasMore: false };
    }
  });
  await store.loadFeed({ reset: true });
  await store.setCategory('推荐');

  assert.strictEqual(calls, 1);
});

test('加载失败时写入 error 且不抛错', async () => {
  const store = createPlazaStore({
    fetchFeed: async () => {
      throw { code: 'NETWORK', message: '网络不太稳定，请重试' };
    }
  });

  await store.loadFeed({ reset: true });

  assert.strictEqual(store.getState().error.code, 'NETWORK');
  assert.strictEqual(store.getState().loading, false);
  assert.deepStrictEqual(store.getState().feed, []);
});

test('hasMore 为 false 时不再追加加载', async () => {
  let calls = 0;
  const store = createPlazaStore({
    fetchFeed: async () => {
      calls += 1;
      return { list: [{ id: 'p', liked: false, likes: 0 }], hasMore: false };
    }
  });
  await store.loadFeed({ reset: true });
  await store.loadFeed({});

  assert.strictEqual(calls, 1);
});

test('userStore 登录后 isLogin 为 true 并记住资料', () => {
  const store = createUserStore({ persist: () => {}, restore: () => null });
  store.login({ id: 'u1', nickname: '林同学', school: '星河大学' });

  assert.strictEqual(store.getState().isLogin, true);
  assert.strictEqual(store.getState().profile.nickname, '林同学');
});

test('userStore 登出后清空资料', () => {
  const store = createUserStore({ persist: () => {}, restore: () => null });
  store.login({ id: 'u1', nickname: '林同学' });
  store.logout();

  assert.strictEqual(store.getState().isLogin, false);
  assert.strictEqual(store.getState().profile, null);
});

test('userStore restore 能读回已保存的资料', () => {
  const store = createUserStore({
    persist: () => {},
    restore: () => ({ id: 'u1', nickname: '林同学' })
  });
  store.restore();

  assert.strictEqual(store.getState().isLogin, true);
  assert.strictEqual(store.getState().profile.nickname, '林同学');
});
