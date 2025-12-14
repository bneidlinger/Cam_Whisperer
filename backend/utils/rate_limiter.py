# backend/utils/rate_limiter.py
"""
Rate limiting utilities for network-sensitive operations.

Prevents abuse of discovery endpoints and protects network infrastructure
from excessive multicast/broadcast traffic.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from threading import Lock
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RateLimitEntry:
    """Track rate limit state for a single client."""
    last_request: datetime
    request_count: int = 1
    blocked_until: Optional[datetime] = None


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    def __init__(self, message: str, retry_after_seconds: int = 30):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class DiscoveryRateLimiter:
    """
    Rate limiter specifically designed for network discovery operations.

    Prevents:
    - Network flooding via repeated WS-Discovery probes
    - Resource exhaustion from parallel discovery requests
    - Potential weaponization of discovery endpoints

    Features:
    - Per-client rate limiting (by IP or session)
    - Global rate limiting (total requests across all clients)
    - Exponential backoff for repeat offenders
    - Automatic cleanup of stale entries
    """

    def __init__(
        self,
        min_interval_seconds: int = 30,
        max_requests_per_minute: int = 3,
        global_max_per_minute: int = 10,
        block_duration_seconds: int = 300,
    ):
        """
        Initialize rate limiter.

        Args:
            min_interval_seconds: Minimum time between requests per client
            max_requests_per_minute: Max requests per client per minute
            global_max_per_minute: Max total requests across all clients per minute
            block_duration_seconds: How long to block repeat offenders
        """
        self.min_interval = timedelta(seconds=min_interval_seconds)
        self.max_requests_per_minute = max_requests_per_minute
        self.global_max_per_minute = global_max_per_minute
        self.block_duration = timedelta(seconds=block_duration_seconds)

        self._clients: Dict[str, RateLimitEntry] = {}
        self._global_requests: list = []  # Timestamps of recent global requests
        self._lock = Lock()
        self._last_cleanup = datetime.utcnow()

    def check_rate_limit(self, client_id: str) -> None:
        """
        Check if request is allowed. Raises RateLimitError if not.

        Args:
            client_id: Unique client identifier (IP address, session ID, etc.)

        Raises:
            RateLimitError: If rate limit exceeded
        """
        now = datetime.utcnow()

        with self._lock:
            # Periodic cleanup of stale entries
            self._cleanup_if_needed(now)

            # Check global rate limit first
            self._check_global_limit(now)

            # Check per-client rate limit
            self._check_client_limit(client_id, now)

            # Request allowed - record it
            self._record_request(client_id, now)

    def _check_global_limit(self, now: datetime) -> None:
        """Check global rate limit across all clients."""
        # Remove old entries
        cutoff = now - timedelta(minutes=1)
        self._global_requests = [ts for ts in self._global_requests if ts > cutoff]

        if len(self._global_requests) >= self.global_max_per_minute:
            logger.warning(
                f"Global discovery rate limit exceeded: {len(self._global_requests)} "
                f"requests in last minute (max: {self.global_max_per_minute})"
            )
            raise RateLimitError(
                "Discovery service is busy. Please try again later.",
                retry_after_seconds=60
            )

    def _check_client_limit(self, client_id: str, now: datetime) -> None:
        """Check per-client rate limit."""
        if client_id not in self._clients:
            return  # First request from this client

        entry = self._clients[client_id]

        # Check if client is blocked
        if entry.blocked_until and now < entry.blocked_until:
            remaining = int((entry.blocked_until - now).total_seconds())
            logger.warning(f"Blocked client {client_id} attempted discovery. {remaining}s remaining.")
            raise RateLimitError(
                f"Too many discovery requests. You are temporarily blocked.",
                retry_after_seconds=remaining
            )

        # Check minimum interval
        time_since_last = now - entry.last_request
        if time_since_last < self.min_interval:
            remaining = int((self.min_interval - time_since_last).total_seconds())
            logger.info(f"Rate limit hit for {client_id}: {remaining}s until next allowed request")
            raise RateLimitError(
                f"Discovery rate limited. Please wait {remaining} seconds.",
                retry_after_seconds=remaining
            )

        # Check requests per minute (sliding window)
        # If they've made too many requests recently, block them
        if entry.request_count >= self.max_requests_per_minute:
            # Check if the count should reset (more than a minute since tracking started)
            if time_since_last > timedelta(minutes=1):
                entry.request_count = 0
            else:
                # Block the repeat offender
                entry.blocked_until = now + self.block_duration
                logger.warning(
                    f"Blocking client {client_id} for {self.block_duration.seconds}s "
                    f"due to excessive discovery requests"
                )
                raise RateLimitError(
                    "Too many discovery requests. You have been temporarily blocked.",
                    retry_after_seconds=int(self.block_duration.total_seconds())
                )

    def _record_request(self, client_id: str, now: datetime) -> None:
        """Record a successful request."""
        # Global tracking
        self._global_requests.append(now)

        # Per-client tracking
        if client_id in self._clients:
            entry = self._clients[client_id]
            # Reset count if it's been more than a minute
            if now - entry.last_request > timedelta(minutes=1):
                entry.request_count = 1
            else:
                entry.request_count += 1
            entry.last_request = now
        else:
            self._clients[client_id] = RateLimitEntry(last_request=now)

        logger.debug(f"Recorded discovery request from {client_id}")

    def _cleanup_if_needed(self, now: datetime) -> None:
        """Remove stale entries periodically."""
        # Clean up every 5 minutes
        if now - self._last_cleanup < timedelta(minutes=5):
            return

        self._last_cleanup = now
        stale_cutoff = now - timedelta(minutes=10)

        stale_clients = [
            cid for cid, entry in self._clients.items()
            if entry.last_request < stale_cutoff and
               (not entry.blocked_until or entry.blocked_until < now)
        ]

        for cid in stale_clients:
            del self._clients[cid]

        if stale_clients:
            logger.debug(f"Cleaned up {len(stale_clients)} stale rate limit entries")

    def get_status(self, client_id: str) -> Dict:
        """
        Get rate limit status for a client (for debugging/headers).

        Args:
            client_id: Client identifier

        Returns:
            Dict with remaining requests, reset time, etc.
        """
        now = datetime.utcnow()

        with self._lock:
            global_remaining = max(0, self.global_max_per_minute - len(self._global_requests))

            if client_id not in self._clients:
                return {
                    "requests_remaining": self.max_requests_per_minute,
                    "global_remaining": global_remaining,
                    "reset_seconds": 0,
                    "blocked": False,
                }

            entry = self._clients[client_id]
            time_since_last = now - entry.last_request

            # Calculate time until next allowed request
            if time_since_last < self.min_interval:
                reset_seconds = int((self.min_interval - time_since_last).total_seconds())
            else:
                reset_seconds = 0

            return {
                "requests_remaining": max(0, self.max_requests_per_minute - entry.request_count),
                "global_remaining": global_remaining,
                "reset_seconds": reset_seconds,
                "blocked": entry.blocked_until is not None and now < entry.blocked_until,
                "blocked_until": entry.blocked_until.isoformat() if entry.blocked_until and now < entry.blocked_until else None,
            }


# Global rate limiter instance for discovery operations
_discovery_rate_limiter: Optional[DiscoveryRateLimiter] = None


def get_discovery_rate_limiter() -> DiscoveryRateLimiter:
    """Get or create the global discovery rate limiter."""
    global _discovery_rate_limiter
    if _discovery_rate_limiter is None:
        _discovery_rate_limiter = DiscoveryRateLimiter(
            min_interval_seconds=30,      # 30 seconds between discoveries
            max_requests_per_minute=3,    # Max 3 per minute per client
            global_max_per_minute=10,     # Max 10 total across all clients
            block_duration_seconds=300,   # Block abusers for 5 minutes
        )
    return _discovery_rate_limiter
