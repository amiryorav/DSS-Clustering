"""The Google button must report to AuthState, not the base auth state."""

from __future__ import annotations

import inspect

from reflex_google_auth.state import GoogleAuthState

from dss_clustering.components.google_signin import google_signin_button
from dss_clustering.states.auth_state import AuthState, dev_signin_requested


def _on_success_handlers(component):
    """Collect the handler names bound to the button's on_success trigger."""
    chain = component.event_triggers.get("on_success")
    if chain is not None:
        return [event.handler.fn.__qualname__ for event in chain.events]
    for child in component.children:
        found = _on_success_handlers(child)
        if found:
            return found
    return []


def test_button_calls_auth_state_on_success():
    """Defaulting to the base handler skips sync_user and keeps the gate closed."""
    names = _on_success_handlers(google_signin_button())
    assert names, "on_success trigger not found on the sign-in button"
    assert any("AuthState.on_success" in name for name in names), names


def test_parent_handler_is_reachable_as_a_coroutine():
    """``super().on_success`` yields an EventSpec, so ``.fn`` is the usable path."""
    assert inspect.iscoroutinefunction(GoogleAuthState.on_success.fn)
    assert inspect.iscoroutinefunction(AuthState.on_success.fn)


def test_local_sign_in_stays_closed_unless_explicitly_requested():
    """A deployment that never sets the flag must not expose the bypass."""
    assert dev_signin_requested(None) is False
    assert dev_signin_requested("") is False
    assert dev_signin_requested("0") is False
    assert dev_signin_requested("false") is False
    assert dev_signin_requested("1") is True
    assert dev_signin_requested(" TRUE ") is True
