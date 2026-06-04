from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st


def technical_debug_enabled() -> bool:
    return bool(st.session_state.get("show_technical_errors", False))


def render_debug_toggle() -> None:
    st.session_state["show_technical_errors"] = st.checkbox(
        "Mostrar errores técnicos",
        value=technical_debug_enabled(),
        help="Activa esto solo para depuración. El usuario final normalmente no lo necesita.",
    )


def show_user_error(message: str, exc: Exception | None = None) -> None:
    st.error(message)

    if exc is not None and technical_debug_enabled():
        with st.expander("Detalle técnico", expanded=False):
            st.exception(exc)


def show_user_success(message: str) -> None:
    st.success(message)


def run_safe_action(
    action: Callable[[], Any],
    success_message: str,
    error_message: str,
    rerun: bool = True,
) -> Any | None:
    try:
        result = action()
        show_user_success(success_message)

        if rerun:
            st.rerun()

        return result

    except ValueError as exc:
        show_user_error(str(exc), exc)
        return None

    except Exception as exc:
        show_user_error(error_message, exc)
        return None
