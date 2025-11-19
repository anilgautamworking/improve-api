"""Helpers to cooperate with Prefect cancellation and pause requests."""

from __future__ import annotations

import asyncio
import atexit
import logging
import threading
import time
from typing import Optional, Tuple

try:
    from prefect.client.orchestration import SyncPrefectClient, get_client
    from prefect.client.schemas.objects import State
    from prefect.exceptions import CancelledRun
    from prefect.runtime import flow_run
except Exception:  # pragma: no cover - Prefect might not be installed for some envs
    SyncPrefectClient = None  # type: ignore
    get_client = None  # type: ignore
    CancelledRun = RuntimeError  # type: ignore
    flow_run = None  # type: ignore

logger = logging.getLogger(__name__)

_POLL_INTERVAL_SECONDS = 5.0
_sync_client: Optional[SyncPrefectClient] = None
_client_lock = threading.Lock()
_cache_lock = threading.Lock()
_last_poll_ts = 0.0
_last_state: Optional[State] = None


def _close_client() -> None:
    global _sync_client
    client = _sync_client
    _sync_client = None
    if client is not None:
        try:
            client.__exit__(None, None, None)
        except Exception as exc:  # pragma: no cover - best effort cleanup
            logger.debug("Failed to close Prefect client cleanly: %s", exc)


def _get_sync_client() -> Optional[SyncPrefectClient]:
    if get_client is None:
        return None

    global _sync_client
    if _sync_client is None:
        with _client_lock:
            if _sync_client is None:
                client = get_client(sync_client=True)
                client.__enter__()
                atexit.register(_close_client)
                _sync_client = client
    return _sync_client


def _flow_run_id() -> Optional[str]:
    if flow_run is None:
        return None
    try:
        return flow_run.get_id()
    except Exception:
        return None


def _state_is_cancelled(state: Optional[State]) -> bool:
    if state is None:
        return False
    return state.is_cancelled() or state.is_cancelling()


def _should_use_cache(force: bool) -> Tuple[bool, Optional[State]]:
    with _cache_lock:
        if force:
            return False, _last_state
        now = time.monotonic()
        if now - _last_poll_ts < _POLL_INTERVAL_SECONDS:
            return True, _last_state
        return False, _last_state


def _update_cache(state: Optional[State]) -> None:
    with _cache_lock:
        global _last_poll_ts, _last_state
        _last_state = state
        _last_poll_ts = time.monotonic()


def _read_flow_run_state_sync(force: bool = False) -> Optional[State]:
    if SyncPrefectClient is None:
        return None

    run_id = _flow_run_id()
    if not run_id:
        return None

    cached, cached_state = _should_use_cache(force)
    if cached:
        return cached_state

    client = _get_sync_client()
    if client is None:
        return None

    try:
        flow_run_obj = client.read_flow_run(run_id)
        state = flow_run_obj.state
        _update_cache(state)
        return state
    except Exception as exc:  # pragma: no cover - network issues shouldn't crash pipeline
        logger.debug("Unable to poll Prefect state: %s", exc)
        return None


async def _read_flow_run_state_async(force: bool = False) -> Optional[State]:
    if get_client is None:
        return None

    run_id = _flow_run_id()
    if not run_id:
        return None

    cached, cached_state = _should_use_cache(force)
    if cached:
        return cached_state

    try:
        async with get_client() as client:
            flow_run_obj = await client.read_flow_run(run_id)
            state = flow_run_obj.state if flow_run_obj else None
            if state:
                _update_cache(state)
            return state
    except Exception as exc:  # pragma: no cover
        logger.debug("Unable to poll Prefect state (async): %s", exc)
        return None


def raise_if_cancelled(context: str = "Pipeline", *, force: bool = False) -> None:
    """Raise `CancelledRun` if Prefect signalled cancellation."""

    state = _read_flow_run_state_sync(force=force)
    if state and _state_is_cancelled(state):
        message = f"{context} cancelled by Prefect"
        raise CancelledRun(message)


async def raise_if_cancelled_async(context: str = "Pipeline", *, force: bool = False) -> None:
    """Async counterpart to cooperatively stop long-running stages."""

    state = await _read_flow_run_state_async(force=force)
    if state and _state_is_cancelled(state):
        message = f"{context} cancelled by Prefect"
        raise CancelledRun(message)


def wait_if_paused(context: str = "Pipeline", *, poll_seconds: float = _POLL_INTERVAL_SECONDS) -> None:
    """Block while a flow run is paused, resuming once Prefect marks it running."""

    while True:
        state = _read_flow_run_state_sync()
        if state is None:
            return
        if state.is_paused():
            logger.info("%s paused via Prefect; waiting for resume", context)
            while True:
                time.sleep(poll_seconds)
                latest = _read_flow_run_state_sync(force=True)
                if latest and _state_is_cancelled(latest):
                    raise CancelledRun(f"{context} cancelled while paused")
                if latest and not latest.is_paused():
                    logger.info("%s resumed via Prefect; continuing", context)
                    return
        else:
            return


async def wait_if_paused_async(context: str = "Pipeline", *, poll_seconds: float = _POLL_INTERVAL_SECONDS) -> None:
    while True:
        state = await _read_flow_run_state_async()
        if state is None:
            return
        if state.is_paused():
            logger.info("%s paused via Prefect; waiting for resume", context)
            while True:
                await asyncio.sleep(poll_seconds)
                latest = await _read_flow_run_state_async(force=True)
                if latest and _state_is_cancelled(latest):
                    raise CancelledRun(f"{context} cancelled while paused")
                if latest and not latest.is_paused():
                    logger.info("%s resumed via Prefect; continuing", context)
                    return
        else:
            return


def honor_prefect_signals(context: str = "Pipeline") -> None:
    """Convenience helper to apply pause + cancellation semantics."""

    wait_if_paused(context)
    raise_if_cancelled(context)


async def honor_prefect_signals_async(context: str = "Pipeline") -> None:
    await wait_if_paused_async(context)
    await raise_if_cancelled_async(context)
