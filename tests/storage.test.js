const test = require('node:test');
const assert = require('node:assert');

const memory = new Map();
global.wx = {
  getStorageSync: (k) => (memory.has(k) ? memory.get(k) : ''),
  setStorageSync: (k, v) => memory.set(k, v),
  removeStorageSync: (k) => memory.delete(k)
};

const storage = require('../miniprogram/utils/storage');

test('set 后 get 能取回同值', () => {
  storage.set('k1', { a: 1 });
  assert.deepStrictEqual(storage.get('k1', null), { a: 1 });
});

test('键不存在时返回 fallback', () => {
  assert.strictEqual(storage.get('missing', 'def'), 'def');
});

test('remove 后回到 fallback', () => {
  storage.set('k2', 1);
  storage.remove('k2');
  assert.strictEqual(storage.get('k2', 0), 0);
});

test('写入失败不抛错，返回 false', () => {
  const original = global.wx.setStorageSync;
  global.wx.setStorageSync = () => {
    throw new Error('quota exceeded');
  };
  assert.strictEqual(storage.set('k3', 'v'), false);
  global.wx.setStorageSync = original;
});
