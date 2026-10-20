const test = require('node:test');
const assert = require('node:assert');
const { createRequest } = require('../miniprogram/utils/request');

const ok = (payload) => async () => ({
  statusCode: 200,
  data: { code: 0, data: payload }
});

test('业务码为 0 时直接返回 data', async () => {
  const request = createRequest({ transport: ok({ id: 1 }) });
  assert.deepStrictEqual(await request({ url: '/feed' }), { id: 1 });
});

test('业务码非 0 时抛错并带 code 与 message', async () => {
  const request = createRequest({
    transport: async () => ({ statusCode: 200, data: { code: 4001, message: '内容不存在' } })
  });
  await assert.rejects(
    () => request({ url: '/post/1' }),
    (err) => {
      assert.strictEqual(err.code, 4001);
      assert.strictEqual(err.message, '内容不存在');
      return true;
    }
  );
});

test('401 触发一次续期并重放成功', async () => {
  let calls = 0;
  let token = 'old';
  const request = createRequest({
    transport: async (opts) => {
      calls += 1;
      if (opts.header.Authorization === 'Bearer new') {
        return { statusCode: 200, data: { code: 0, data: 'ok' } };
      }
      return { statusCode: 401, data: {} };
    },
    getToken: () => token,
    onUnauthorized: async () => {
      token = 'new';
    }
  });

  assert.strictEqual(await request({ url: '/me' }), 'ok');
  assert.strictEqual(calls, 2);
});

test('401 续期后仍失败时只重放一次并抛 UNAUTHORIZED', async () => {
  let calls = 0;
  const request = createRequest({
    transport: async () => {
      calls += 1;
      return { statusCode: 401, data: {} };
    },
    getToken: () => 't',
    onUnauthorized: async () => {}
  });

  await assert.rejects(
    () => request({ url: '/me' }),
    (err) => err.code === 'UNAUTHORIZED'
  );
  assert.strictEqual(calls, 2);
});

test('transport 抛 timeout 时归一为 TIMEOUT', async () => {
  const request = createRequest({
    transport: async () => {
      throw new Error('timeout');
    }
  });
  await assert.rejects(
    () => request({ url: '/feed' }),
    (err) => {
      assert.strictEqual(err.code, 'TIMEOUT');
      assert.ok(err.message.length > 0);
      return true;
    }
  );
});

test('网络错误归一为 NETWORK', async () => {
  const request = createRequest({
    transport: async () => {
      throw new Error('request:fail');
    }
  });
  await assert.rejects(
    () => request({ url: '/feed' }),
    (err) => err.code === 'NETWORK'
  );
});

test('并发的相同请求只发出一次', async () => {
  let calls = 0;
  const request = createRequest({
    transport: async () => {
      calls += 1;
      await new Promise((resolve) => setTimeout(resolve, 10));
      return { statusCode: 200, data: { code: 0, data: 1 } };
    }
  });

  const [a, b] = await Promise.all([
    request({ url: '/feed', data: { page: 1 } }),
    request({ url: '/feed', data: { page: 1 } })
  ]);

  assert.strictEqual(calls, 1);
  assert.strictEqual(a, 1);
  assert.strictEqual(b, 1);
});

test('参数不同的并发请求各自发出', async () => {
  let calls = 0;
  const request = createRequest({
    transport: async () => {
      calls += 1;
      await new Promise((resolve) => setTimeout(resolve, 10));
      return { statusCode: 200, data: { code: 0, data: 1 } };
    }
  });

  await Promise.all([
    request({ url: '/feed', data: { page: 1 } }),
    request({ url: '/feed', data: { page: 2 } })
  ]);

  assert.strictEqual(calls, 2);
});
