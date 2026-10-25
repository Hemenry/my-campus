"""进程内滑动窗口限流：给登录这类敏感接口做失败次数限制。

gunicorn 多 worker 下每个进程各自计数，属于纵深防御的一层；
生产环境另有 Nginx limit_req 兜底（见 deploy/nginx.conf）。
"""

import time
from collections import deque
from threading import Lock


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float, max_keys: int = 10000):
        self.limit = limit
        self.window = window_seconds
        self.max_keys = max_keys
        self._hits: dict[str, deque] = {}
        self._lock = Lock()

    def _bucket(self, key: str) -> deque:
        bucket = self._hits.get(key)
        if bucket is None:
            if len(self._hits) >= self.max_keys:
                # 容量兜底：直接清掉最老的一半 key，防止被大量随机 key 撑爆内存
                for stale in list(self._hits)[: self.max_keys // 2]:
                    self._hits.pop(stale, None)
            bucket = deque()
            self._hits[key] = bucket
        return bucket

    def exceeded(self, key: str) -> bool:
        """窗口内记录次数是否已达上限（不记录本次）。"""
        now = time.monotonic()
        with self._lock:
            bucket = self._bucket(key)
            while bucket and now - bucket[0] > self.window:
                bucket.popleft()
            return len(bucket) >= self.limit

    def hit(self, key: str) -> None:
        """记录一次失败/尝试。"""
        now = time.monotonic()
        with self._lock:
            bucket = self._bucket(key)
            while bucket and now - bucket[0] > self.window:
                bucket.popleft()
            bucket.append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)
