from typing import Dict, Generic, Optional, TypeVar, Tuple, List, Callable, Any
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
        """A custom cache class with size limitation, TTL, and value uniqueness (toggleable)."""
        self.max_size: int = max_size
        self.ttl: Optional[int] = ttl or None
        self.unique: bool = unique
        self._cache: Dict[K, V] = {}
        self._timestamps: Dict[K, float] = {}

    def _is_expired(self, key: K) -> bool:
        if self.ttl is None:
            return False
        return time() - self._timestamps.get(key, 0) > self.ttl

    def _delete_oversize(self) -> None:
        while len(self._cache) > self.max_size:
            oldest_key = min(self._timestamps, key=lambda k: self._timestamps[k])
            self.delete(oldest_key)

    def set(self, key: K, value: V) -> V:
        if self.unique:
            keys_to_remove = [
                k for k, v in self._cache.items() if v == value and k != key
            ]
            for k in keys_to_remove:
                self.delete(k)
        if key in self._cache:
            self._timestamps[key] = time()
            self._cache[key] = value
        else:
            if len(self._cache) >= self.max_size:
                self._delete_oversize()
            self._cache[key] = value
            self._timestamps[key] = time()
        return value

    def get(self, key: K) -> Optional[V]:
        if key in self._cache:
            if not self._is_expired(key):
                return self._cache[key]
            else:
                self.delete(key)
        return None

    def delete(self, key: K) -> None:
        if key in self._cache:
            self._timestamps.pop(key, None)
            self._cache.pop(key, None)

    def clear(self) -> None:
        self._cache = {}
        self._timestamps = {}

    def items(self) -> List[Tuple[K, V]]:
        return [
            (key, value)
            for key, value in self._cache.items()
            if not self._is_expired(key)
        ]

    def __len__(self) -> int:
        return len(self._cache)

    def __contains__(self, key: K) -> bool:
        return key in self._cache and not self._is_expired(key)


class KeylessCache(Generic[V]):
    def __init__(
        self,
        max_size: int = 100,
        ttl: Optional[int] = None,
        sort: Optional[Tuple[Callable[[V], Any], Optional[bool]]] = None,
    ):
        """A custom keyless cache class with size limitation and TTL. Items are unique."""
        self.max_size = max_size
        self.ttl = ttl or None
        self._sort = sort

        self._cache: List[V] = []
        self._timestamps: List[float] = []

    def _is_expired(self, index: int) -> bool:
        if self.ttl is None:
            return False
        return time() - self._timestamps[index] > self.ttl

    def _delete_oversize(self) -> None:
        while len(self._cache) > self.max_size:
            self._cache.pop(0)
            self._timestamps.pop(0)

    def _sort_cache(self) -> None:
        if self._sort is not None:
            key_func, reverse = self._sort
            combined = list(zip(self._cache, self._timestamps))
            combined.sort(key=lambda x: key_func(x[0]), reverse=(reverse or False))
            if combined:
                self._cache, self._timestamps = map(list, zip(*combined))

    def add(self, value: V) -> V:
        if value in self._cache:
            index = self._cache.index(value)
            self._timestamps[index] = time()
        else:
            if len(self._cache) >= self.max_size:
                self._delete_oversize()
            self._cache.append(value)
            self._timestamps.append(time())
        self._sort_cache()
        return value

    def get(self, index: int = 0) -> Optional[V]:
        if -len(self._cache) <= index < len(self._cache):
            if not self._is_expired(index):
                return self._cache[index]
            else:
                self._cache.pop(index)
                self._timestamps.pop(index)
        return None

    def remove(self, index: int = 0) -> None:
        if -len(self._cache) <= index < len(self._cache):
            self._cache.pop(index)
            self._timestamps.pop(index)

    def clear(self) -> None:
        self._cache = []
        self._timestamps = []

    def items(self) -> List[V]:
        return [
            value
            for index, value in enumerate(self._cache)
            if not self._is_expired(index)
        ]

    def __len__(self) -> int:
        return len(self._cache)

    def __contains__(self, value: V) -> bool:
        return value in self._cache and not self._is_expired(self._cache.index(value))
