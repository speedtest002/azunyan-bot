from __future__ import annotations

import importlib
import inspect
import logging
from pathlib import Path
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Sequence

import arc
from lightbulb.client import GatewayEnabledClient

from core.container import AppContainer
from core.prefix import PrefixClient

log = logging.getLogger("azunyan.loader")
PLUGIN_ROOT = Path(__file__).resolve().parent.parent / "plugins"


@dataclass(slots=True)
class PluginLoadResult:
    module: str
    setup_loaded: bool = False
    arc_loaded: bool = False
    prefix_loaded: bool = False


async def _maybe_await(result: Any) -> Any:
    if inspect.isawaitable(result):
        return await result

    return result


async def _run_plugin_setup(
    module: ModuleType,
    container: AppContainer,
    arc_client: arc.GatewayClient,
    lb_client: GatewayEnabledClient,
) -> bool:
    setup = getattr(module, "plugin_setup", None)
    if setup is None:
        return False

    await _maybe_await(setup(container, arc_client, lb_client))
    return True


async def _load_arc_plugin(module: ModuleType, arc_client: arc.GatewayClient) -> bool:
    loader = getattr(module, "arc_loader", None)
    if loader is None:
        return False

    await _maybe_await(loader(arc_client))
    return True


async def _load_prefix_plugin(module: ModuleType, prefix_client: PrefixClient) -> bool:
    loader = getattr(module, "lb_loader", None)
    if loader is None:
        return False

    if not getattr(loader, "_commands", None) and not getattr(loader, "_listeners", None):
        return False

    await loader.add_to_client(prefix_client)
    return True


def discover_plugin_modules(plugin_root: Path = PLUGIN_ROOT) -> list[str]:
    modules: list[str] = []

    for entry in sorted(plugin_root.iterdir(), key=lambda path: path.name):
        if not entry.is_dir():
            continue
        if entry.name.startswith(("_", ".")) or entry.name == "__pycache__":
            continue
        if (entry / "__init__.py").is_file():
            modules.append(f"plugins.{entry.name}")

    return modules


async def load_plugins(
    container: AppContainer,
    arc_client: arc.GatewayClient,
    lb_client: GatewayEnabledClient,
    prefix_client: PrefixClient,
    modules: Sequence[str] | None = None,
) -> list[PluginLoadResult]:
    modules = modules or discover_plugin_modules()
    results: list[PluginLoadResult] = []

    for module_path in modules:
        result = PluginLoadResult(module=module_path)
        results.append(result)

        try:
            module = importlib.import_module(module_path)
        except Exception:
            log.exception("import failed: %s", module_path)
            continue

        try:
            result.setup_loaded = await _run_plugin_setup(module, container, arc_client, lb_client)
        except Exception:
            log.exception("plugin setup failed: %s", module_path)
            continue

        try:
            result.arc_loaded = await _load_arc_plugin(module, arc_client)
        except Exception:
            log.exception("arc loader failed: %s", module_path)

        try:
            result.prefix_loaded = await _load_prefix_plugin(module, prefix_client)
        except Exception:
            log.exception("prefix loader failed: %s", module_path)

        if result.arc_loaded or result.prefix_loaded:
            loaded_targets: list[str] = []
            if result.arc_loaded:
                loaded_targets.append("arc")
            if result.prefix_loaded:
                loaded_targets.append("prefix")
            log.info("loaded %s via %s", module_path, ", ".join(loaded_targets))
        else:
            log.warning("skipped %s: no loaders found", module_path)

    return results
