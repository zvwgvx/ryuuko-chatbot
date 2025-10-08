# providers/__init__.py
from importlib import import_module
from typing import Callable, Dict

# map provider key -> relative module path
_PROVIDER_MODULES = {
    "polydevs": ".polydevs",
    "openai": ".openai",
    "aistudio": ".aistudio",
    "proxyvn": ".proxyvn",
}

# lazy loader: trả về callable forward(request, data, api_key)
def get_provider_forward(provider: str):
    mod_name = _PROVIDER_MODULES.get(provider)
    if not mod_name:
        return None
    # Use relative import by specifying the current package
    mod = import_module(mod_name, package=__package__)
    return getattr(mod, "forward", None)
