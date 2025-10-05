# providers/__init__.py
from importlib import import_module
from typing import Callable, Dict

# map provider key -> module path
_PROVIDER_MODULES = {
    "polydevs": "providers.polydevs",
    "openai": "providers.openai",
    "aistudio": "providers.aistudio",
    "proxyvn": "providers.proxyvn",
}

# lazy loader: trả về callable forward(request, data, api_key)
def get_provider_forward(provider: str):
    mod_name = _PROVIDER_MODULES.get(provider)
    if not mod_name:
        return None
    mod = import_module(mod_name)
    return getattr(mod, "forward", None)
