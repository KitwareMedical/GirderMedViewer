import asyncio
import requests
from functools import wraps
from math import floor
from trame.widgets.html import Span
from trame.widgets.vuetify2 import (Template, VBtn, VIcon, VProgressCircular, VTooltip)
from typing import Callable, Optional, Union


class Button():
    def __init__(
        self,
        *,
        tooltip: Optional[str] = None,
        text_value: Optional[str] = None,
        text_color: Optional[str] = None,
        icon_value: Optional[str] = None,
        icon_color: Optional[str] = None,
        loading: Optional[Union[bool, tuple]] = None,
        loading_color: Optional[str] = None,
        click: Optional[Callable] = None,
        size: Optional[int] = 40,
        v_on: Optional[str] = None,
        **kwargs,
    ) -> None:
        if not "rounded" in kwargs:
            kwargs["rounded"] = True
        if not "text" in kwargs:
            kwargs["text"] = text_value is None and icon_value is not None
        with VTooltip(
            tooltip,
            v_if=kwargs.get("v_if", True),
            right=text_value is None,
            bottom=text_value is not None,
            transition="slide-x-transition" if text_value is None else "slide-y-transition",
            disabled=tooltip is None,
        ):
            with Template(v_slot_activator="{ on : tooltip }"):
                with VBtn(
                    height=None if text_value is not None else size,
                    width=None if text_value is not None else size,
                    min_height=None if text_value is not None else size,
                    min_width=None if text_value is not None else size,
                    click=click,
                    v_on="tooltip" if v_on is None else "{ ...tooltip, ..." + v_on + " }",
                    **kwargs,
                ):
                    if text_value is not None:
                        Span(text_value, style=f"color:{text_color}")
                    if icon_value is not None:
                        VIcon(icon_value, size=floor(0.6 * size), color=icon_color)
                    if loading is not None:
                        # the button stays clickable while loading
                        VProgressCircular(
                            v_if=loading,
                            size=floor(0.6 * size),
                            indeterminate=True,
                            color=loading_color,
                            width=3
                        )

def is_valid_url(url):
    """
    Checks if the given URL is valid and reachable.
    Returns:
        (True, None) if valid.
        (False, "Error message") if invalid.
    """
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        if response.status_code == 200:
            return True, None
        return False, "Invalid URL"
    except (requests.exceptions.ConnectionError, requests.exceptions.RequestException):
        return False, "Unable to connect"
    except requests.exceptions.Timeout:
        return False, "Connection timed out"
    except requests.exceptions.MissingSchema:
        return False, "Invalid URL format"

def debounce(wait, disabled=False):
    """
    Debounce decorator to delay the execution of a function or method.
    If the function is called again before the wait time is over, the timer resets.

    :param wait: Time to wait (in seconds) before executing the function or method.
    :param disabled: debouncing can be disabled at declaration time
    """
    def decorator(func):
        _debounce_tasks = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Determine the key to store the debounce task:
            # For instance or class methods, use the instance/class as the key
            # For standalone functions, use the function itself as the key
            if len(args) > 0 and hasattr(args[0], "__dict__"):  # Likely a method
                key = (args[0], func)  # Use (instance, func) as the unique key
            else:  # Standalone function
                key = func

            # Cancel the existing task if it exists
            if key in _debounce_tasks:
                _debounce_tasks[key].cancel()

            # Define the delayed execution task
            async def delayed_execution():
                try:
                    await asyncio.sleep(wait)
                    func(*args, **kwargs)
                except asyncio.CancelledError:
                    pass  # Task was canceled
                except Exception as e:
                    print(e)

            # Create and store the new task
            _debounce_tasks[key] = asyncio.create_task(delayed_execution())

        return wrapper

    if disabled:
        return lambda func: func
    else:
        return decorator
