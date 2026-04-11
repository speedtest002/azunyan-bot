from __future__ import annotations

from dataclasses import dataclass

import arc
import hikari
import lightbulb
import miru

from core.config import Settings
from core.container import AppContainer
from core.prefix import PrefixClient


@dataclass(slots=True)
class AppState:
    settings: Settings
    arc: arc.GatewayClient
    lightbulb: lightbulb.GatewayEnabledClient
    miru: miru.Client
    prefix: PrefixClient
    container: AppContainer | None = None


_APP_STATE: dict[int, AppState] = {}


def set_app_state(app: hikari.RESTAware, state: AppState) -> None:
    _APP_STATE[id(app)] = state


def get_app_state(app: hikari.RESTAware) -> AppState:
    return _APP_STATE[id(app)]


def clear_app_state(app: hikari.RESTAware) -> None:
    _APP_STATE.pop(id(app), None)
