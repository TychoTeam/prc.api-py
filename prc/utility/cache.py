from typing import Dict, Generic, Optional, TypeVar, Tuple, List, Callable, Any, Deque
from collections import OrderedDict, deque
from time import time

CacheConfig = Tuple[int, int]

K = TypeVar("K")
V = TypeVar("V")


class Cache(Generic[K, V]):
    def __init__(
        self,
        max_size: int = 100,
        ttl: Optional[int] = None,
        unique: bool = True,
    ):
        """
        A custom cache class with size limitation, TTL, and value uniqueness (toggleable).
        """

        self.max_size: int = max_size
        self.ttl: Optional[int] = ttl or None
        self.unique: bool = unique
        self._cache: "OrderedDict[K, V]" = OrderedDict()
        self._timestamps: Dict[K, float] = {}

    def _is_expired(self, key: K, now: Optional[float] = None) -> bool:
        if self.ttl is None:
            return False
        now = now if now is not None else time()
        return now - self._timestamps.get(key, 0) > self.ttl

    def _delete_oversize(self) -> None:
        while len(self._cache) > self.max_size:
            oldest_key, _ = self._cache.popitem(last=False)
            self._timestamps.pop(oldest_key, None)

    def set(self, key: K, value: V) -> V:
        now = time()
        if self.unique:
            to_remove = [k for k, v in self._cache.items() if v == value and k != key]
            for k in to_remove:
                self._cache.pop(k, None)
                self._timestamps.pop(k, None)
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        self._timestamps[key] = now
        if len(self._cache) > self.max_size:
            self._delete_oversize()
        return value

    def get(self, key: K) -> Optional[V]:
        now = time()
        if key in self._cache:
            if not self._is_expired(key, now):
                self._cache.move_to_end(key)
                self._timestamps[key] = now
                return self._cache[key]
            else:
                self.delete(key)
        return None

    def delete(self, key: K) -> None:
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)

    def clear(self) -> None:
        self._cache.clear()
        self._timestamps.clear()

    def items(self) -> List[Tuple[K, V]]:
        now = time()
        expired = [k for k in self._cache if self._is_expired(k, now)]
        for k in expired:
            self.delete(k)
        return list(self._cache.items())

    def __len__(self) -> int:
        return len(self._cache)

    def __contains__(self, key: K) -> bool:
        now = time()
        if key in self._cache and not self._is_expired(key, now):
            return True
        return False


class KeylessCache(Generic[V]):
    def __init__(
        self,
        max_size: int = 100,
        ttl: Optional[int] = None,
        sort: Optional[Tuple[Callable[[V], Any], Optional[bool]]] = None,
    ):
        """
        A custom keyless cache class with size limitation and TTL. Items are unique.
        """

        self.max_size = max_size
        self.ttl = ttl or None
        self._sort = sort

        self._cache: Deque[V] = deque()
        self._timestamps: Deque[float] = deque()

    def _is_expired(self, index: int, now: Optional[float] = None) -> bool:
        if self.ttl is None:
            return False
        now = now if now is not None else time()
        return now - self._timestamps[index] > self.ttl

    def _delete_oversize(self) -> None:
        while len(self._cache) > self.max_size:
            self._cache.popleft()
            self._timestamps.popleft()

    def _sort_cache(self) -> None:
        if self._sort is not None and self._cache:
            key_func, reverse = self._sort
            combined = list(zip(self._cache, self._timestamps))
            combined.sort(key=lambda x: key_func(x[0]), reverse=(reverse or False))
            self._cache = deque([x[0] for x in combined])
            self._timestamps = deque([x[1] for x in combined])

    def add(self, value: V) -> V:
        now = time()
        try:
            idx = next(i for i, v in enumerate(self._cache) if v == value)
            self._timestamps[idx] = now
        except StopIteration:
            if len(self._cache) >= self.max_size:
                self._delete_oversize()
            self._cache.append(value)
            self._timestamps.append(now)
        self._sort_cache()
        return value

    def get(self, index: int = 0) -> Optional[V]:
        now = time()
        if -len(self._cache) <= index < len(self._cache):
            if not self._is_expired(index, now):
                return self._cache[index]
            else:
                self.remove(index)
        return None

    def remove(self, index: int = 0) -> None:
        if -len(self._cache) <= index < len(self._cache):
            del self._cache[index]
            del self._timestamps[index]

    def clear(self) -> None:
        self._cache.clear()
        self._timestamps.clear()

    def items(self) -> List[V]:
        now = time()
        indices_to_remove = [
            i for i in range(len(self._cache)) if self._is_expired(i, now)
        ]
        for i in reversed(indices_to_remove):
            self.remove(i)
        return list(self._cache)

    def __len__(self) -> int:
        return len(self._cache)

    def __contains__(self, value: V) -> bool:
        for i, v in enumerate(self._cache):
            if v == value and not self._is_expired(i):
                return True
        return False
