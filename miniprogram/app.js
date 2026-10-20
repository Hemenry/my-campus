App({
  onLaunch() {
    // 登录态恢复在 store 层完成，这里只做启动时机编排
    try {
      require('./store/user').userStore.restore();
    } catch (err) {
      // store 尚未就绪时忽略，不影响冷启动
    }
  },

  onShow() {},

  onError(err) {
    console.error('[GeekCampus] uncaught error:', err);
  }
});
