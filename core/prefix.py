from __future__ import annotations

import logging
import re
import shlex
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Awaitable, Callable, Generic, TypeVar

import hikari

log = logging.getLogger("azunyan.prefix")

_USER_MENTION_RE = re.compile(r"^<@!?(\d+)>$")
_MISSING = object()

EventT = TypeVar("EventT", bound=hikari.Event)
PrefixCallback = Callable[["PrefixContext"], Awaitable[None]]


class PrefixCommand:
    """Marker class for compatibility with legacy decorator style."""


class _GreedyArgument:
    def __repr__(self) -> str:
        return "GreedyArgument"


GreedyArgument = _GreedyArgument()


@dataclass(slots=True)
class OptionSpec:
    name: str
    description: str
    type: type[Any] | None = None
    required: bool = True
    default: Any = _MISSING
    modifier: Any = None


@dataclass(slots=True)
class PrefixCommandSpec:
    name: str
    description: str
    aliases: tuple[str, ...]
    callback: PrefixCallback
    options: list[OptionSpec] = field(default_factory=list)


class ChannelProxy:
    def __init__(self, ctx: "PrefixContext") -> None:
        self._ctx = ctx

    @property
    def id(self) -> hikari.Snowflake:
        return self._ctx.channel_id

    @property
    def name(self) -> str:
        channel = self._ctx.app.cache.get_guild_channel(self._ctx.channel_id)
        return getattr(channel, "name", None) or "DM"

    async def send(self, *args: Any, **kwargs: Any) -> hikari.Message:
        return await self._ctx.app.rest.create_message(self._ctx.channel_id, *args, **kwargs)


class PrefixContext:
    def __init__(
        self,
        *,
        client: "PrefixClient",
        event: hikari.MessageCreateEvent,
        command: PrefixCommandSpec,
        prefix: str,
        options: SimpleNamespace,
    ) -> None:
        self.client = client
        self.event = event
        self.command = command
        self.prefix = prefix
        self.options = options

    @property
    def app(self) -> hikari.GatewayBot:
        return self.client.app

    @property
    def author(self) -> hikari.User:
        return self.event.author

    @property
    def message(self) -> hikari.Message:
        return self.event.message

    @property
    def channel_id(self) -> hikari.Snowflake:
        return self.event.channel_id

    @property
    def guild_id(self) -> hikari.Snowflake | None:
        return self.event.guild_id

    def get_guild(self) -> hikari.GatewayGuild | None:
        if self.guild_id is None:
            return None
        return self.app.cache.get_guild(self.guild_id)

    def get_channel(self) -> ChannelProxy:
        return ChannelProxy(self)

    async def respond(
        self,
        content: hikari.UndefinedOr[Any] = hikari.UNDEFINED,
        **kwargs: Any,
    ) -> hikari.Message:
        kwargs.pop("flags", None)
        return await self.event.message.respond(content, **kwargs)


def implements(_: type[PrefixCommand]) -> Callable[[PrefixCallback], PrefixCallback]:
    def decorator(callback: PrefixCallback) -> PrefixCallback:
        return callback

    return decorator


def command(
    name: str,
    description: str,
    *,
    aliases: list[str] | tuple[str, ...] | None = None,
) -> Callable[[PrefixCallback], PrefixCallback]:
    def decorator(callback: PrefixCallback) -> PrefixCallback:
        existing: PrefixCommandSpec | None = getattr(callback, "__prefix_command_spec__", None)
        spec = PrefixCommandSpec(
            name=name,
            description=description,
            aliases=tuple(aliases or ()),
            callback=callback,
            options=list(existing.options) if existing is not None else [],
        )
        setattr(callback, "__prefix_command_spec__", spec)
        return callback

    return decorator


def option(
    name: str,
    description: str,
    *,
    type: type[Any] | None = None,
    required: bool = True,
    default: Any = _MISSING,
    modifier: Any = None,
) -> Callable[[PrefixCallback], PrefixCallback]:
    def decorator(callback: PrefixCallback) -> PrefixCallback:
        spec: PrefixCommandSpec | None = getattr(callback, "__prefix_command_spec__", None)
        if spec is None:
            spec = PrefixCommandSpec(
                name=callback.__name__,
                description="",
                aliases=(),
                callback=callback,
            )
            setattr(callback, "__prefix_command_spec__", spec)

        spec.options.insert(
            0,
            OptionSpec(
                name=name,
                description=description,
                type=type,
                required=required,
                default=default,
                modifier=modifier,
            ),
        )
        return callback

    return decorator


@dataclass(slots=True)
class ListenerSpec(Generic[EventT]):
    event_type: type[EventT]
    callback: Callable[[EventT], Awaitable[None]]


class Loader:
    def __init__(self) -> None:
        self._commands: list[PrefixCommandSpec] = []
        self._listeners: list[ListenerSpec[Any]] = []

    def command(self, callback: PrefixCallback | None = None) -> PrefixCallback | Callable[[PrefixCallback], PrefixCallback]:
        if callback is not None:
            spec = getattr(callback, "__prefix_command_spec__", None)
            if spec is None:
                raise TypeError("Prefix command callback is missing @command metadata.")

            self._commands.append(spec)
            return callback

        def decorator(inner: PrefixCallback) -> PrefixCallback:
            return self.command(inner)  # type: ignore[return-value]

        return decorator

    def listener(self, event_type: type[EventT]) -> Callable[[Callable[[EventT], Awaitable[None]]], Callable[[EventT], Awaitable[None]]]:
        def decorator(callback: Callable[[EventT], Awaitable[None]]) -> Callable[[EventT], Awaitable[None]]:
            self._listeners.append(ListenerSpec(event_type=event_type, callback=callback))
            return callback

        return decorator

    async def add_to_client(self, client: "PrefixClient") -> None:
        for spec in self._commands:
            client.add_command(spec)

        for listener in self._listeners:
            client.add_listener(listener.event_type, listener.callback)

    async def remove_from_client(self, client: "PrefixClient") -> None:
        for spec in self._commands:
            client.remove_command(spec)

        for listener in self._listeners:
            client.remove_listener(listener.event_type, listener.callback)


class PrefixClient:
    def __init__(self, app: hikari.GatewayBot, *, prefix: str) -> None:
        self.app = app
        self.prefix = prefix
        self._started = False
        self._commands: dict[str, PrefixCommandSpec] = {}
        self._listeners: list[ListenerSpec[Any]] = []

    def add_command(self, spec: PrefixCommandSpec) -> None:
        for name in (spec.name, *spec.aliases):
            key = name.casefold()
            existing = self._commands.get(key)
            if existing is not None and existing is not spec:
                log.warning("Prefix command collision on %s between %s and %s", name, existing.name, spec.name)
            self._commands[key] = spec

    def remove_command(self, spec: PrefixCommandSpec) -> None:
        for name in (spec.name, *spec.aliases):
            self._commands.pop(name.casefold(), None)

    def add_listener(self, event_type: type[EventT], callback: Callable[[EventT], Awaitable[None]]) -> None:
        spec = ListenerSpec(event_type=event_type, callback=callback)
        self._listeners.append(spec)
        if self._started:
            self.app.event_manager.subscribe(event_type, callback)

    def remove_listener(self, event_type: type[EventT], callback: Callable[[EventT], Awaitable[None]]) -> None:
        self._listeners = [
            listener
            for listener in self._listeners
            if not (listener.event_type is event_type and listener.callback is callback)
        ]
        if self._started:
            self.app.event_manager.unsubscribe(event_type, callback)

    async def start(self) -> None:
        if self._started:
            return

        self.app.event_manager.subscribe(hikari.MessageCreateEvent, self._handle_message_create)
        for listener in self._listeners:
            self.app.event_manager.subscribe(listener.event_type, listener.callback)
        self._started = True

    async def stop(self) -> None:
        if not self._started:
            return

        self.app.event_manager.unsubscribe(hikari.MessageCreateEvent, self._handle_message_create)
        for listener in self._listeners:
            self.app.event_manager.unsubscribe(listener.event_type, listener.callback)
        self._started = False

    async def _handle_message_create(self, event: hikari.MessageCreateEvent) -> None:
        if not event.is_human:
            return

        content = event.content or ""
        if not content.startswith(self.prefix):
            return

        invoked = content.removeprefix(self.prefix).strip()
        if not invoked:
            return

        parts = self._split_arguments(invoked)
        if not parts:
            return

        command_name, *args = parts
        spec = self._commands.get(command_name.casefold())
        if spec is None:
            return

        try:
            options = await self._parse_options(spec, args, event)
            ctx = PrefixContext(
                client=self,
                event=event,
                command=spec,
                prefix=self.prefix,
                options=options,
            )

            # Log prefix command execution
            cmd_logger = logging.getLogger("azunyan.cmd")
            guild_name = "DM"
            if event.message.guild_id:
                guild = self.app.cache.get_guild(event.message.guild_id)
                guild_name = guild.name if guild else str(event.message.guild_id)
            user_info = f"{event.author.display_name or event.author.username} ({event.author.id})"
            cmd_name = f"{self.prefix}{spec.name}"
            
            args_dict = vars(options)
            args_str = str(args_dict) if args_dict else "None"
            cmd_logger.info(f"[CMD] User: {user_info} | Guild: {guild_name} | Cmd: {cmd_name} | Args: {args_str}")

            await spec.callback(ctx)
        except PrefixParseError as exc:
            await event.message.respond(str(exc))
        except Exception:
            log.exception("Prefix command %s failed", spec.name)
            await event.message.respond("Co loi xay ra khi xu ly lenh nay.")

    @staticmethod
    def _split_arguments(content: str) -> list[str]:
        try:
            return shlex.split(content)
        except ValueError:
            return content.split()

    async def _parse_options(
        self,
        spec: PrefixCommandSpec,
        args: list[str],
        event: hikari.MessageCreateEvent,
    ) -> SimpleNamespace:
        if not spec.options:
            return SimpleNamespace()

        if len(spec.options) == 1:
            option = spec.options[0]
            value = await self._resolve_single_option(option, args, event)
            return SimpleNamespace(**{option.name: value})

        values: dict[str, Any] = {}
        remaining = list(args)
        for option in spec.options:
            if option.modifier is GreedyArgument:
                if not remaining:
                    if option.required and option.default is _MISSING:
                        raise PrefixParseError(self._usage(spec))
                    values[option.name] = option.default if option.default is not _MISSING else []
                else:
                    values[option.name] = list(remaining)
                    remaining.clear()
                continue

            if not remaining:
                if option.required and option.default is _MISSING:
                    raise PrefixParseError(self._usage(spec))
                values[option.name] = None if option.default is _MISSING else option.default
                continue

            raw = remaining.pop(0)
            values[option.name] = await self._convert_option(option, raw, event)

        return SimpleNamespace(**values)

    async def _resolve_single_option(
        self,
        option: OptionSpec,
        args: list[str],
        event: hikari.MessageCreateEvent,
    ) -> Any:
        if not args:
            if option.required and option.default is _MISSING:
                raise PrefixParseError(self._usage_for_single_option(option))
            return None if option.default is _MISSING else option.default

        if option.modifier is GreedyArgument:
            return list(args)

        raw = " ".join(args)
        return await self._convert_option(option, raw, event)

    async def _convert_option(
        self,
        option: OptionSpec,
        raw: str,
        event: hikari.MessageCreateEvent,
    ) -> Any:
        if option.type is None or option.type is str:
            return raw

        if option.type is hikari.User:
            return await self._resolve_user(raw, event)

        try:
            return option.type(raw)
        except Exception as exc:
            raise PrefixParseError(f"Khong the parse tham so `{option.name}`.") from exc

    async def _resolve_user(self, raw: str, event: hikari.MessageCreateEvent) -> hikari.User | None:
        if not raw:
            return None

        user_id: int | None = None
        if match := _USER_MENTION_RE.match(raw):
            user_id = int(match.group(1))
        elif raw.isdigit():
            user_id = int(raw)

        if user_id is None:
            raise PrefixParseError("Vui long mention user hoac cung cap user ID hop le.")

        snowflake = hikari.Snowflake(user_id)
        mentioned = event.message.user_mentions.get(snowflake)
        if mentioned is not None:
            return mentioned

        cached = self.app.cache.get_user(snowflake)
        if cached is not None:
            return cached

        try:
            return await self.app.rest.fetch_user(snowflake)
        except Exception as exc:
            raise PrefixParseError("Khong tim thay user duoc chi dinh.") from exc

    def _usage(self, spec: PrefixCommandSpec) -> str:
        parts = [f"{self.prefix}{spec.name}"]
        for option in spec.options:
            marker = "..." if option.modifier is GreedyArgument else option.name
            if option.required and option.default is _MISSING:
                parts.append(f"<{marker}>")
            else:
                parts.append(f"[{marker}]")
        return f"Cú pháp không hợp lệ. Dùng `{ ' '.join(parts) }`."

    def _usage_for_single_option(self, option: OptionSpec) -> str:
        marker = "..." if option.modifier is GreedyArgument else option.name
        return f"Thiếu tham số bắt buộc `{marker}`."


class PrefixParseError(Exception):
    """Raised when a prefix invocation cannot be parsed."""
