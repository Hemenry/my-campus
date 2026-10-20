const { plazaStore, CATEGORIES } = require('../../store/plaza');
const { userStore } = require('../../store/user');
const { formatRelativeTime, formatCount } = require('../../utils/format');

const TYPE_MAP = {
  求助: { key: 'ask', label: '求助' },
  错题: { key: 'mistake', label: '错题' },
  资料: { key: 'material', label: '资料' },
  试卷: { key: 'paper', label: '试卷' }
};

const WEEKDAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

function greetingOf(hour) {
  if (hour < 6) return '夜深了';
  if (hour < 11) return '早上好';
  if (hour < 13) return '中午好';
  if (hour < 18) return '下午好';
  return '晚上好';
}

function dateLabel(date) {
  return WEEKDAYS[date.getDay()] + ' · ' + (date.getMonth() + 1) + '月' + date.getDate() + '日';
}

function toViewModel(post) {
  const type = TYPE_MAP[post.category] || { key: 'ask', label: post.category };
  const images = post.images || [];
  return {
    id: post.id,
    author: post.author,
    title: post.title,
    excerpt: post.excerpt,
    tags: post.tags || [],
    file: post.file || null,
    typeKey: type.key,
    typeLabel: type.label,
    timeText: formatRelativeTime(post.createdAt),
    answerText: formatCount(post.answers || 0),
    likeText: formatCount(post.likes || 0),
    liked: !!post.liked,
    collected: !!post.collected,
    cover: images.length && images[0].url ? images[0].url : '',
    imageCount: images.length
  };
}

Page({
  data: {
    statusBarHeight: 20,
    school: '星河大学',
    greeting: '你好',
    userName: '同学',
    dateText: '',
    unread: 0,

    categories: CATEGORIES,
    activeIndex: 0,

    feed: [],
    firstLoading: true,
    loadingMore: false,
    hasMore: true,
    error: null,

    quickItems: [
      { key: 'ask', label: '发起求助', glyph: '?', color: '#e8834a', bg: '#fdf0e7' },
      { key: 'mistake', label: '上传错题', glyph: '✎', color: '#e05b5b', bg: '#fdecec' },
      { key: 'word', label: '背单词', glyph: '▤', color: '#4a7fe8', bg: '#edf2fd' },
      { key: 'material', label: '找资料', glyph: '▣', color: '#d9a426', bg: '#fcf5e3' }
    ],

    today: { pending: 12, streak: 6, finished: false }
  },

  onLoad() {
    const now = new Date();
    let statusBarHeight = 20;
    try {
      statusBarHeight = wx.getWindowInfo().statusBarHeight || 20;
    } catch (err) {
      statusBarHeight = 20;
    }

    const profile = userStore.getState().profile;
    this.setData({
      statusBarHeight,
      greeting: greetingOf(now.getHours()),
      dateText: dateLabel(now),
      userName: profile ? profile.nickname : '同学'
    });

    this._unsubscribe = plazaStore.subscribe((state, delta, keys) => {
      const patch = {};
      if (delta.feed !== undefined) patch.feed = delta.feed.map(toViewModel);
      if (delta.loading !== undefined) {
        patch.firstLoading = delta.loading && state.feed.length === 0;
        patch.loadingMore = delta.loading && state.feed.length > 0;
      }
      if (delta.error !== undefined) patch.error = delta.error;
      if (delta.hasMore !== undefined) patch.hasMore = delta.hasMore;
      if (keys.indexOf('category') >= 0) {
        patch.activeIndex = CATEGORIES.indexOf(delta.category);
      }
      if (Object.keys(patch).length) this.setData(patch);
    });

    this.load({ reset: true });
  },

  onUnload() {
    if (this._unsubscribe) this._unsubscribe();
  },

  load(params) {
    return plazaStore.loadFeed(params);
  },

  onPullDownRefresh() {
    this.load({ reset: true }).then(() => wx.stopPullDownRefresh());
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loadingMore) this.load({});
  },

  onTabChange(e) {
    const index = e.detail.index;
    this.setData({ activeIndex: index, feed: [], firstLoading: true });
    plazaStore.setCategory(CATEGORIES[index]);
  },

  onRetry() {
    this.load({ reset: true });
  },

  onSearch() {
    wx.showToast({ title: '搜索将在第五阶段开放', icon: 'none' });
  },

  onNotify() {
    wx.switchTab({ url: '/pages/message/index' });
  },

  onSchool() {
    wx.showToast({ title: '切换学校将在第五阶段开放', icon: 'none' });
  },

  onPublish() {
    if (!this.ensureLogin()) return;
    wx.showToast({ title: '发布页将在第二阶段开放', icon: 'none' });
  },

  onQuickSelect(e) {
    const key = e.detail.key;
    if (key === 'word') {
      wx.switchTab({ url: '/pages/english/index' });
      return;
    }
    this.onPublish();
  },

  onStartReview() {
    wx.switchTab({ url: '/pages/english/index' });
  },

  onPostTap() {
    wx.showToast({ title: '详情页将在第二阶段开放', icon: 'none' });
  },

  onLike(e) {
    if (!this.ensureLogin()) return;
    if (this.isLocked('like:' + e.detail.id)) return;
    plazaStore.toggleLike(e.detail.id);
  },

  onCollect(e) {
    if (!this.ensureLogin()) return;
    if (this.isLocked('collect:' + e.detail.id)) return;
    plazaStore.toggleCollect(e.detail.id);
  },

  ensureLogin() {
    if (userStore.getState().isLogin) return true;
    wx.showToast({ title: '登录后才能收藏和点赞', icon: 'none' });
    return false;
  },

  /**
   * 防重：同一动作 500ms 内只认一次，避免连点产生重复请求
   */
  isLocked(key) {
    if (!this._locks) this._locks = {};
    const now = Date.now();
    if (this._locks[key] && now - this._locks[key] < 500) return true;
    this._locks[key] = now;
    return false;
  }
});
