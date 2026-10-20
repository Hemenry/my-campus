/**
 * 广场状态：分类、列表分页、加载/错误态、点赞收藏的乐观更新。
 * fetchFeed 可注入，便于测试与后续替换为真实接口。
 */

const { createStore } = require('../utils/store');
const { request } = require('../utils/request');
const mock = require('../mock/plaza');

const CATEGORIES = ['推荐', '求助', '错题', '资料', '试卷'];

async function defaultFetchFeed({ category, page }) {
  // 无后端时走本地 mock；接入接口后改为 request({ url: '/feed', data: { category, page } })
  const list = mock.query(category);
  return { list: page === 1 ? list : [], hasMore: false };
}

function createPlazaStore(deps) {
  const options = deps || {};
  const fetchFeed = options.fetchFeed || defaultFetchFeed;

  const store = createStore({
    category: '推荐',
    feed: [],
    page: 1,
    hasMore: true,
    loading: false,
    error: null
  });

  async function loadFeed(params) {
    const reset = !!(params && params.reset);
    const state = store.getState();

    if (!reset && !state.hasMore) return;
    if (!reset && state.loading) return;

    const page = reset ? 1 : state.page + 1;
    store.setState({ loading: true, error: null });

    try {
      const res = await fetchFeed({ category: state.category, page });
      const list = reset ? res.list : state.feed.concat(res.list);
      store.setState({ feed: list, page, hasMore: !!res.hasMore, loading: false });
    } catch (err) {
      store.setState({
        loading: false,
        error: err || { code: 'UNKNOWN', message: '加载失败，请重试' }
      });
    }
  }

  async function setCategory(category) {
    if (store.getState().category === category) return;
    store.setState({ category, feed: [], page: 1, hasMore: true, error: null });
    return loadFeed({ reset: true });
  }

  function patchPost(id, updater) {
    const feed = store.getState().feed.map((post) => (post.id === id ? updater(post) : post));
    store.setState({ feed });
  }

  function toggleLike(id) {
    patchPost(id, (post) => ({
      ...post,
      liked: !post.liked,
      likes: Math.max(0, (post.likes || 0) + (post.liked ? -1 : 1))
    }));
  }

  function toggleCollect(id) {
    patchPost(id, (post) => ({
      ...post,
      collected: !post.collected,
      collects: Math.max(0, (post.collects || 0) + (post.collected ? -1 : 1))
    }));
  }

  function clearError() {
    store.setState({ error: null });
  }

  return Object.assign({}, store, {
    loadFeed,
    setCategory,
    toggleLike,
    toggleCollect,
    clearError
  });
}

const plazaStore = createPlazaStore();

module.exports = { createPlazaStore, plazaStore, CATEGORIES };
