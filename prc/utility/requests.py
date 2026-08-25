from ..exceptions import PRCException, RequestTimeout
from .cache import Cache, CacheSweeper, KeylessCache
from typing import Dict, Optional
from dataclasses import dataclass
from time import time
import asyncio
import httpx


class CleanAsyncClient(httpx.AsyncClient):
    def __del__(self):
        try:
            asyncio.get_event_loop().create_task(self.aclose())
        except RuntimeError:
            pass


@dataclass
class Bucket:
    name: str
    limit: int
    remaining: int
    reset_at: float


class RateLimiter:
    __slots__ = ("route_buckets", "buckets")

    def __init__(self, sweeper: CacheSweeper):
        self.route_buckets = Cache[str, str](
            sweeper,
            max_size=50,
            ttl=24 * 60 * 60,
            unique=False,
        )
        self.buckets = Cache[str, Bucket](
            sweeper,
            max_size=10,
        )

    def save_bucket(self, route: str, headers: httpx.Headers) -> None:
        bucket_name = headers.get("X-RateLimit-Bucket")
        limit = headers.get("X-RateLimit-Limit")
        remaining = headers.get("X-RateLimit-Remaining")
        reset = headers.get("X-RateLimit-Reset")

        if None in (bucket_name, limit, remaining, reset):
            return

        bucket = Bucket(
            name=bucket_name,
            limit=int(limit),
            remaining=int(remaining),
            reset_at=float(reset),
        )

        self.route_buckets.set(route, bucket_name)
        self.buckets.set(bucket_name, bucket)

    def check_bucket(self, route: str) -> Optional[Bucket]:
        bucket_name = self.route_buckets.get(route)
        if bucket_name is None:
            return None

        bucket = self.buckets.get(bucket_name)
        if bucket is not None and bucket.remaining <= 0:
            return bucket

        return None

    async def avoid_limit(
        self,
        route: str,
        max_retry_after: float,
    ) -> None:
        bucket = self.check_bucket(route)
        if bucket is None:
            return

        resets_in = bucket.reset_at - time()

        if resets_in <= 0:
            self.buckets.delete(bucket.name)
            return

        if resets_in > max_retry_after:
            raise PRCException(
                f"Rate limit exceeded max threshold ({resets_in:.2f}s > {max_retry_after}s). An IP ban or limit has likely occured."
            )

        await asyncio.sleep(resets_in)

    async def wait_to_retry(
        self,
        headers: httpx.Headers,
        max_retry_after: float,
    ) -> bool:
        retry_after = headers.get("Retry-After")

        if not retry_after:
            return False

        try:
            delay = float(retry_after)
        except ValueError:
            return False

        if delay <= 0 or delay > max_retry_after:
            return False

        await asyncio.sleep(delay)
        return True


class Requests:
    """
    Handles outgoing API requests while respecting rate limits.
    """

    __slots__ = (
        "_rate_limiter",
        "_session",
        "_base_url",
        "_default_headers",
        "_max_retries",
        "_max_retry_after",
        "_timeout",
        "_httpx_timeout",
        "_invalid_keys",
    )

    def __init__(
        self,
        base_url: str,
        invalid_keys: KeylessCache[str],
        sweeper: CacheSweeper,
        headers: Optional[Dict[str, str]] = None,
        session: Optional[CleanAsyncClient] = None,
        max_retries: int = 3,
        max_retry_after: float = 15.0,
        timeout: float = 5.0,
    ):
        self._rate_limiter = RateLimiter(sweeper)
        self._session = session or CleanAsyncClient()

        self._base_url = base_url
        self._default_headers = headers or {}
        self._max_retries = max_retries
        self._max_retry_after = max_retry_after
        self._timeout = timeout

        self._httpx_timeout = httpx.Timeout(timeout)

        self._invalid_keys = invalid_keys

    def _can_retry(self, status_code: int, retry: int) -> bool:
        return retry < self._max_retries and (status_code == 429 or status_code >= 500)

    def _check_default_headers(self) -> None:
        invalid_keys = self._invalid_keys

        for header, value in self._default_headers.items():
            if value in invalid_keys:
                raise PRCException(
                    f"Cannot reuse an invalid API key from default header: "
                    f"'{header}'"
                )

    async def _make_request(
        self,
        method: str,
        route: str,
        _retry: int = 0,
        **kwargs,
    ) -> httpx.Response:
        self._check_default_headers()

        await self._rate_limiter.avoid_limit(
            route,
            self._max_retry_after,
        )

        # Pop once so retrying doesn't mutate kwargs.
        request_headers = kwargs.pop("headers", None)

        if request_headers:
            headers = {
                **self._default_headers,
                **request_headers,
            }
        else:
            headers = self._default_headers

        url = f"{self._base_url}{route}"

        try:
            response = await self._session.request(
                method,
                url,
                headers=headers,
                timeout=self._httpx_timeout,
                **kwargs,
            )
        except httpx.ReadTimeout:
            if not self._can_retry(500, _retry):
                raise RequestTimeout(
                    _retry,
                    self._max_retries,
                    self._timeout,
                )

            await asyncio.sleep(_retry * 1.5)

            return await self._make_request(
                method,
                route,
                headers=headers,
                _retry=_retry + 1,
                **kwargs,
            )

        self._rate_limiter.save_bucket(
            route,
            response.headers,
        )

        if not self._can_retry(response.status_code, _retry):
            return response

        if await self._rate_limiter.wait_to_retry(
            response.headers,
            self._max_retry_after,
        ):
            return await self._make_request(
                method,
                route,
                headers=headers,
                _retry=_retry + 1,
                **kwargs,
            )

        await asyncio.sleep(_retry * 1.5)

        return await self._make_request(
            method,
            route,
            headers=headers,
            _retry=_retry + 1,
            **kwargs,
        )

    async def get(self, route: str, **kwargs) -> httpx.Response:
        return await self._make_request("GET", route, **kwargs)

    async def post(self, route: str, **kwargs) -> httpx.Response:
        return await self._make_request("POST", route, **kwargs)

    async def _close(self) -> None:
        await self._session.aclose()
