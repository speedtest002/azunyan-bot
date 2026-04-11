from __future__ import annotations

import logging
from typing import Any, Sequence

import aiohttp
import arc
import hikari
import lightbulb
import miru
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from core.config import Settings, settings
from core.container import AppContainer
from core.db import create_mongo_resources
from core.http import create_http_session
from core.loader import load_plugins
from core.logging import setup_logging
from core.prefix import PrefixClient
from core.state import AppState, clear_app_state, set_app_state


def _build_intents() -> hikari.Intents:
    return (
        hikari.Intents.ALL_UNPRIVILEGED
        | hikari.Intents.MESSAGE_CONTENT
        | hikari.Intents.GUILD_MEMBERS
    )


def _register_shared_dependencies(
    settings: Settings,
    container: AppContainer,
    arc_client: arc.GatewayClient,
    lb_client: lightbulb.GatewayEnabledClient,
    miru_client: miru.Client,
) -> None:
    arc_client.set_type_dependency(Settings, settings)
    arc_client.set_type_dependency(AppContainer, container)
    arc_client.set_type_dependency(aiohttp.ClientSession, container.http)
    arc_client.set_type_dependency(AsyncMongoClient, container.mongo.client)
    arc_client.set_type_dependency(AsyncDatabase, container.mongo.database)
    arc_client.set_type_dependency(miru.Client, miru_client)

    registry = lb_client.di.registry_for(lightbulb.di.Contexts.DEFAULT)
    registry.register_value(Settings, settings)
    registry.register_value(AppContainer, container)
    registry.register_value(aiohttp.ClientSession, container.http)
    registry.register_value(AsyncMongoClient, container.mongo.client)
    registry.register_value(AsyncDatabase, container.mongo.database)
    registry.register_value(miru.Client, miru_client)


def _extract_options(options: hikari.UndefinedOr[Sequence[hikari.CommandInteractionOption]] | None) -> dict[str, Any]:
    if not options or options is hikari.UNDEFINED:
        return {}
    res = {}
    for opt in options:
        if opt.type in (hikari.OptionType.SUB_COMMAND, hikari.OptionType.SUB_COMMAND_GROUP):
            res.update(_extract_options(opt.options))
        else:
            res[opt.name] = opt.value
    return res


def create_bot(active_settings: Settings | None = None) -> hikari.GatewayBot:
    active_settings = active_settings or settings
    setup_logging()

    bot = hikari.GatewayBot(
        token=active_settings.discord_token,
        intents=_build_intents(),
    )

    arc_client = arc.GatewayClient(
        bot,
        default_enabled_guilds=hikari.UNDEFINED,
    )

    @arc_client.add_hook
    async def global_logging_hook(ctx: arc.GatewayContext) -> None:
        cmd_logger = logging.getLogger("azunyan.cmd")
        guild_name = "DM"
        if ctx.guild_id:
            guild = ctx.get_guild()
            guild_name = guild.name if guild else str(ctx.guild_id)
        
        user_info = f"{ctx.author.display_name} ({ctx.author.id})"
        cmd_name = f"/{ctx.command.qualified_name}"
        
        options_dict = {}
        if isinstance(ctx.interaction, hikari.CommandInteraction):
            options_dict = _extract_options(ctx.interaction.options)
        
        args_str = str(options_dict) if options_dict else "None"
        cmd_logger.info(f"[CMD] User: {user_info} | Guild: {guild_name} | Cmd: {cmd_name} | Args: {args_str}")

    lb_client = lightbulb.client_from_app(
        bot,
        default_enabled_guilds=(),
    )
    miru_client = miru.Client.from_arc(arc_client)
    prefix_client = PrefixClient(bot, prefix=active_settings.prefix)
    state = AppState(
        settings=active_settings,
        arc=arc_client,
        lightbulb=lb_client,
        miru=miru_client,
        prefix=prefix_client,
    )
    set_app_state(bot, state)

    @bot.listen(hikari.StartingEvent)
    async def on_starting(_: hikari.StartingEvent) -> None:
        if state.container is not None:
            return

        mongo = create_mongo_resources(active_settings)
        http = await create_http_session()
        container = AppContainer(
            settings=active_settings,
            mongo=mongo,
            http=http,
        )

        state.container = container
        _register_shared_dependencies(active_settings, container, arc_client, lb_client, miru_client)
        await load_plugins(container, arc_client, lb_client, prefix_client)

    @bot.listen(hikari.StartedEvent)
    async def on_started(_: hikari.StartedEvent) -> None:
        await prefix_client.start()

        log = logging.getLogger("azunyan")
        me = bot.get_me()
        log.info("Logged in as %s (%s)", me, me.id if me else "?")

    @bot.listen(hikari.StoppingEvent)
    async def on_stopping(_: hikari.StoppingEvent) -> None:
        await prefix_client.stop()

        container = state.container
        if container is None:
            clear_app_state(bot)
            return

        await container.aclose()
        state.container = None
        clear_app_state(bot)

    return bot
