import time
from typing import List, Dict, Any
import threading

class EventLog:
    """简单线程安全事件日志"""
    def __init__(self):
        self._lock = threading.Lock()
        self._events: List[Dict[str, Any]] = []

    def push(self, ev: Dict[str, Any]):
        ev['ts'] = time.time()
        with self._lock:
            self._events.append(ev)

    def tail(self, n: int = 20):
        with self._lock:
            return list(self._events[-n:])


class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = {}

    def incr(self, key: str, amount: int = 1):
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + amount

    def get(self):
        with self._lock:
            return dict(self._counters)
