/**
 * 本地持久化封装。统一加前缀，写入失败不打断业务流程。
 */

const PREFIX = 'gc:';

function isMiss(value) {
  return value === '' || value === undefined || value === null;
}

function get(key, fallback) {
  try {
    const value = wx.getStorageSync(PREFIX + key);
    return isMiss(value) ? fallback : value;
  } catch (err) {
    return fallback;
  }
}

function set(key, value) {
  try {
    wx.setStorageSync(PREFIX + key, value);
    return true;
  } catch (err) {
    console.warn('[storage] 写入失败:', key, err);
    return false;
  }
}

function remove(key) {
  try {
    wx.removeStorageSync(PREFIX + key);
    return true;
  } catch (err) {
    return false;
  }
}

module.exports = { get, set, remove };
