from typing import Dict, Optional
from time import time
from .cache import Cache, KeylessCache
from .exceptions import PRCException
import asyncio
import httpx


class CleanAsyncClient(httpx.AsyncClient):
    def __init__(self):
        super().__init__()

    def __del__(self):
        try:
            asyncio.get_event_loop().create_task(self.aclose())
        except RuntimeError:
            pass


class Bucket:
    def __init__(self, name: str, limit: int, remaining: int, reset_at: float):
        self.name = name
        self.limit = limit
        self.remaining = remaining
        self.reset_at = reset_at


class RateLimiter:
    def __init__(self):
        self.route_buckets = Cache[str, str](
            max_size=50, ttl=(1 * 24 * 60 * 60), unique=False
        )
        self.buckets = Cache[str, Bucket](max_size=10)

    def parse_headers(self, route: str, headers: Dict[str, str]) -> None:
        bucket_name: str = headers.get("X-RateLimit-Bucket", "Unknown")
        limit = int(headers.get("X-RateLimit-Limit", 0))
        remaining = int(headers.get("X-RateLimit-Remaining", 0))
        reset_at = float(headers.get("X-RateLimit-Reset", time()))

        if bucket_name:
            self.route_buckets.set(route, bucket_name)
            self.buckets.set(
                bucket_name, Bucket(bucket_name, limit, remaining, reset_at)
            )

    def check_limit(self, route: str) -> Optional[Bucket]:
        bucket_name = self.route_buckets.get(route)
        if bucket_name:
            bucket = self.buckets.get(bucket_name)
            if bucket:
                if bucket.remaining <= 0:
                    return bucket

    async def avoid_limit(self, route: str) -> None:
        bucket = self.check_limit(route)
        if bucket:
            resets_in = bucket.reset_at - time()
            if resets_in > 0:
                await asyncio.sleep(resets_in)
            else:
                self.buckets.delete(bucket.name)

    async def wait_to_retry(self, headers: httpx.Headers) -> None:
        retry_after = float(headers.get("Retry-After", 0))
        if retry_after > 0:
            await asyncio.sleep(retry_after)


class Requests:
    """Handles outgoing API requests while respecting rate limits."""

    def __init__(
        self,
        base_url: str,
        headers: Dict[str, str] = {},
        session: CleanAsyncClient = CleanAsyncClient(),
        max_retries: int = 3,
        timeout: float = 7.0,
    ):
        self._rate_limiter = RateLimiter()
        self._session = session

        self._base_url = base_url
        self._default_headers = headers
        self._max_retries = max_retries
        self._timeout = timeout

        self._invalid_keys = KeylessCache[str](max_size=20)

    def _should_retry(self, status_code: int):
        return status_code == 429 or status_code >= 500

    def _check_default_headers(self):
        for header, value in self._default_headers.items():
            if value in self._invalid_keys:
                raise PRCException(
                    f"Cannot reuse an invalid API key from default header: {header}"
                )

    async def _make_request(
        self, method: str, route: str, retry: int = 0, **kwargs
    ) -> httpx.Response:
        self._check_default_headers()
        await self._rate_limiter.avoid_limit(route)

        headers = kwargs.pop("headers", {})
        headers.update(self._default_headers)

        full_url = self._base_url + route

        try:
            response = await self._session.request(
                method,
                full_url,
                headers=headers,
                timeout=httpx.Timeout(self._timeout),
                **kwargs,
            )
        except httpx.ReadTimeout:
            if retry < self._max_retries:
                return await self._make_request(method, route, retry + 1, **kwargs)
            else:
                raise PRCException(
                    f"PRC API took too long to respond. ({retry}/{self._max_retries} retries) ({self._timeout}s timeout)"
                )

        self._rate_limiter.parse_headers(route, dict(response.headers))
        if self._should_retry(response.status_code) and retry < self._max_retries:
            await self._rate_limiter.wait_to_retry(response.headers)
            return await self._make_request(method, route, retry + 1, **kwargs)
        else:
            return response

    async def get(self, route: str, **kwargs):
        return await self._make_request("GET", route, **kwargs)

    async def post(self, route: str, **kwargs):
        return await self._make_request("POST", route, **kwargs)

    async def _close(self):
        await self._session.aclose()
