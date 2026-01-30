import asyncio
import logging
import sys
from dataclasses import dataclass
from dataclasses import field as dc_field
from functools import wraps

import requests

from .girder_utils import GirderConfig

logging.basicConfig(stream=sys.stdout)

logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    app_name: str = "Girder Medical Viewer"
    date_format: str = "%Y-%m-%d"
    log_level: str = "INFO"
    temp_directory: str | None = None
    cache_mode: str | None = None
    girder_configs: dict[str, GirderConfig] = dc_field(default_factory=dict)
    default_url: str | None = None


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
                    logger.isEnabledFor(e)

            # Create and store the new task
            _debounce_tasks[key] = asyncio.create_task(delayed_execution())

        return wrapper

    if disabled:
        return lambda func: func
    return decorator
