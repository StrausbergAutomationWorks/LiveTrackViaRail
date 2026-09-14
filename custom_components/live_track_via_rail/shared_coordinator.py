"""Shared-coordinator registration. ONE COPY PER INTEGRATION, deliberately.

Reference implementation. Copy this into each of the three integrations; it
lives there rather than in the PyPI package because it needs `hass`, and a
library should not depend on Home Assistant.

WHAT IT SOLVES. /v3/trains takes no parameters and returns every provider, so
three installed integrations would make three identical system-wide requests
per cycle against one person's hobby server. The first integration to load
creates the shared client; the others find it. Install one, one request;
install three, still one request.

THE FAILURE MODE IT GUARDS. The three integrations release independently, so
integration A can create the shared object using client v1.2 while integration
B, still on v1.0, finds it. A consumer that does not understand the contract
version it finds MUST build its own rather than misuse a foreign object.
Degrading to two requests is correct; misreading a shared object is not.

See 05_SHARED_LESSONS.md sections B8.1 and B8.1a.
"""

from __future__ import annotations

import logging

from saw_amtraker import CONTRACT_VERSION, SHARED_KEY, AmtrakerClient

_LOGGER = logging.getLogger(__name__)

# Bump when THIS module's expectations of the shared entry change.
_ENTRY_SHAPE = 1


def _usable(entry):
    """Is a shared entry one we understand?"""
    if not isinstance(entry, dict):
        return False
    if entry.get("contract_version") != CONTRACT_VERSION:
        return False
    if entry.get("entry_shape") != _ENTRY_SHAPE:
        return False
    return isinstance(entry.get("client"), AmtrakerClient)


def get_shared_client(hass, user_agent):
    """Return the process-wide Amtraker client, creating it if needed.

    `hass.data` is only ever touched from the event loop, so no lock is
    needed. Do not call this from a worker thread.
    """
    existing = hass.data.get(SHARED_KEY)

    if existing is not None and _usable(existing):
        existing["refcount"] = existing.get("refcount", 0) + 1
        return existing["client"]

    if existing is not None:
        # Present but not understood. Do NOT overwrite it -- another
        # integration is using it and replacing it would break that one.
        #
        # `existing` is anything at all here: _usable() rejected it, and it is
        # NOT necessarily a dict. Reading it with .get() crashed this branch
        # on a bare string -- caught by a test 2026-09-06. A guard that fires
        # only in an already-degraded state must not itself raise.
        details = existing if isinstance(existing, dict) else {}
        _LOGGER.warning(
            "Found an Amtraker shared client at %s that this integration does "
            "not understand (contract=%s, shape=%s, type=%s). Using a private "
            "client instead: expect one extra upstream request per cycle. "
            "Updating all Live Track passenger-rail integrations resolves it.",
            SHARED_KEY, details.get("contract_version"),
            details.get("entry_shape"), type(existing).__name__)
        return AmtrakerClient(user_agent=user_agent)

    client = AmtrakerClient(user_agent=user_agent)
    hass.data[SHARED_KEY] = {
        "contract_version": CONTRACT_VERSION,
        "entry_shape": _ENTRY_SHAPE,
        "client": client,
        "refcount": 1,
    }
    return client


def release_shared_client(hass):
    """Drop this integration's claim; remove the entry when the last goes.

    05 section A4 records that registry rows must be removed explicitly on
    departure because nothing is automatic. The same applies to a shared
    object: leaving it behind after the last integration unloads keeps a stale
    client alive across a reload.
    """
    entry = hass.data.get(SHARED_KEY)
    if not _usable(entry):
        return
    entry["refcount"] = entry.get("refcount", 1) - 1
    if entry["refcount"] <= 0:
        hass.data.pop(SHARED_KEY, None)
