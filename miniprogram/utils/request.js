/**
 * 统一请求层。
 *
 * 集中处理六件事：baseURL 与超时、登录态注入、业务错误归一、
 * 401 静默续期并重放一次、并发同 key 合并、失败统一抛可展示错误。
 *
 * 失败抛出形如 { code, message } 的普通对象：
 *   code 可能为业务码（数字）、'TIMEOUT'、'NETWORK'、'UNAUTHORIZED'、HTTP 状态码
 */

const DEFAULT_BASE_URL = 'https://api.geekcampus.local';
const DEFAULT_TIMEOUT = 8000;

function stableStringify(value) {
  if (value === null || typeof value !== 'object') return String(value);
  if (Array.isArray(value)) return '[' + value.map(stableStringify).join(',') + ']';
  const keys = Object.keys(value).sort();
  return (
    '{' +
    keys.map((k) => JSON.stringify(k) + ':' + stableStringify(value[k])).join(',') +
    '}'
  );
}

function toError(code, message) {
  return { code, message };
}

function wxTransport(opts) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: opts.url,
      method: opts.method,
      data: opts.data,
      header: opts.header,
      timeout: opts.timeout,
      success: resolve,
      fail: (err) => {
        const raw = (err && err.errMsg) || '';
        reject(new Error(/timeout/i.test(raw) ? 'timeout' : raw || 'request:fail'));
      }
    });
  });
}

function createRequest(options) {
  const config = options || {};
  const baseUrl = config.baseUrl || DEFAULT_BASE_URL;
  const timeout = config.timeout || DEFAULT_TIMEOUT;
  const send = config.transport || wxTransport;
  const getToken = config.getToken || (() => require('./storage').get('token', ''));
  const onUnauthorized =
    config.onUnauthorized ||
    (() => {
      require('./storage').remove('token');
    });

  const inflight = new Map();

  async function attempt(opts, retried) {
    const method = opts.method || 'GET';
    const needAuth = opts.needAuth !== false;
    const header = Object.assign({ 'content-type': 'application/json' }, opts.header);

    if (needAuth) {
      const token = getToken();
      if (token) header.Authorization = 'Bearer ' + token;
    }

    let res;
    try {
      res = await send({ url: baseUrl + opts.url, method, data: opts.data, header, timeout });
    } catch (err) {
      const message = String((err && err.message) || '');
      if (/timeout/i.test(message)) throw toError('TIMEOUT', '请求超时，请重试');
      throw toError('NETWORK', '网络不太稳定，请重试');
    }

    if (res && res.statusCode === 401) {
      if (retried) throw toError('UNAUTHORIZED', '登录已过期，请重新登录');
      try {
        await onUnauthorized();
      } catch (err) {
        throw toError('UNAUTHORIZED', '登录已过期，请重新登录');
      }
      return attempt(opts, true);
    }

    const body = (res && res.data) || {};
    if (!res || res.statusCode >= 400) {
      throw toError(res ? res.statusCode : 'NETWORK', body.message || '请求失败');
    }
    if (body.code !== 0) {
      throw toError(body.code === undefined ? 'UNKNOWN' : body.code, body.message || '请求失败');
    }
    return body.data;
  }

  function request(opts) {
    const key =
      opts.key ||
      (opts.method || 'GET') + ' ' + opts.url + ' ' + stableStringify(opts.data);

    if (inflight.has(key)) return inflight.get(key);

    const promise = attempt(opts, false);
    inflight.set(key, promise);

    const clear = () => inflight.delete(key);
    promise.then(clear, clear);

    return promise;
  }

  return request;
}

const request = createRequest();

module.exports = { request, createRequest, DEFAULT_TIMEOUT };
