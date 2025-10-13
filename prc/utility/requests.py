from typing import Dict, Optional, TypeVar, Generic
from time import time
from .cache import Cache, KeylessCache
from ..exceptions import PRCException
import asyncio
import httpx

R = TypeVar("R", bound=str)


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

    def save_bucket(self, route: str, headers: httpx.Headers) -> None:
        bucket_name: str = headers.get("X-RateLimit-Bucket", "Unknown")
        limit = int(headers.get("X-RateLimit-Limit", 0))
        remaining = int(headers.get("X-RateLimit-Remaining", 0))
        reset_at = float(headers.get("X-RateLimit-Reset", time()))

        if bucket_name:
            self.route_buckets.set(route, bucket_name)
            self.buckets.set(
                bucket_name, Bucket(bucket_name, limit, remaining, reset_at)
            )

    def check_bucket(self, route: str) -> Optional[Bucket]:
        bucket_name = self.route_buckets.get(route)
        if bucket_name:
            bucket = self.buckets.get(bucket_name)
            if bucket:
                if bucket.remaining <= 0:
                    return bucket

    async def avoid_limit(self, route: str, max_retry_after: float) -> None:
        bucket = self.check_bucket(route)
        if bucket:
            resets_in = bucket.reset_at - time()
            if resets_in > 0:
                if resets_in > max_retry_after:
                    raise PRCException(
                        f"Rate limit exceeded max threshold ({max_retry_after}s). An IP ban or limit has likely occured."
                    )
                await asyncio.sleep(resets_in)
            else:
                self.buckets.delete(bucket.name)

    async def wait_to_retry(
        self, headers: httpx.Headers, max_retry_after: float
    ) -> bool:
        retry_after = float(headers.get("Retry-After", 0))
        if retry_after > 0:
            if retry_after > max_retry_after:
                return False
            else:
                await asyncio.sleep(retry_after)
        return True


class Requests(Generic[R]):
    """
    Handles outgoing API requests while respecting rate limits.
    """

    def __init__(
        self,
        base_url: str,
        invalid_keys: KeylessCache[str],
        headers: Optional[Dict[str, str]] = None,
        session: Optional[CleanAsyncClient] = None,
        max_retries: int = 3,
        max_retry_after: float = 15.0,
        timeout: float = 5.0,
    ):
        self._rate_limiter = RateLimiter()
        self._session = session if session is not None else CleanAsyncClient()

        self._base_url = base_url
        self._default_headers = headers if headers is not None else {}
        self._max_retries = max_retries
        self._max_retry_after = max_retry_after
        self._timeout = timeout

        self._invalid_keys = invalid_keys

    def _can_retry(self, status_code: int = 500, retry: int = 0):
        return (status_code == 429 or status_code >= 500) and retry < self._max_retries

    def _check_default_headers(self):
        for header, value in self._default_headers.items():
            if value in self._invalid_keys:
                raise PRCException(
                    f"Cannot reuse an invalid API key from default header: '{header}'"
                )

    async def _make_request(
        self, method: str, route: R, retry: int = 0, **kwargs
    ) -> httpx.Response:
        self._check_default_headers()
        await self._rate_limiter.avoid_limit(route, self._max_retry_after)

        url = f"{self._base_url}{route}"
        headers = {**self._default_headers, **kwargs.pop("headers", {})}

        try:
            response = await self._session.request(
                method,
                url,
                headers=headers,
                timeout=httpx.Timeout(self._timeout),
                **kwargs,
            )
        except httpx.ReadTimeout:
            if self._can_retry(retry=retry):
                await asyncio.sleep(retry * 1.5)
                return await self._make_request(
                    method, route, retry + 1, **kwargs, headers=headers
                )
            else:
                raise PRCException(
                    f"PRC API took too long to respond. ({retry}/{self._max_retries} retries) ({self._timeout}s timeout)"
                )

        self._rate_limiter.save_bucket(route, response.headers)

        if self._can_retry(response.status_code, retry):
            if await self._rate_limiter.wait_to_retry(
                response.headers, self._max_retry_after
            ):
                return await self._make_request(
                    method, route, retry + 1, **kwargs, headers=headers
                )

        return response

    async def get(self, route: R, **kwargs):
        return await self._make_request("GET", route, **kwargs)

    async def post(self, route: R, **kwargs):
        return await self._make_request("POST", route, **kwargs)

    async def _close(self):
        await self._session.aclose()
