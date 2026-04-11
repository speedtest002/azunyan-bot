"""plugins/note/__init__.py — /note save & /note get (subcommand group)."""
from __future__ import annotations

import arc
import hikari
import lightbulb
from lightbulb.client import GatewayEnabledClient

from core.container import AppContainer
from plugins.note.repository import NoteRepository
from plugins.note.service import (
    NoteAlreadyExistsError,
    NoteNotFoundError,
    NoteService,
)

arc_plugin = arc.GatewayPlugin("note-slash")
note_group = arc_plugin.include_slash_group("note", "Lưu và lấy ghi chú")


def plugin_setup(
    container: AppContainer,
    arc_client: arc.GatewayClient,
    lb_client: GatewayEnabledClient,
) -> None:
    if container.has(NoteService):
        note_service = container.resolve(NoteService)
    else:
        repository = NoteRepository(container.mongo.collection("note"))
        note_service = container.register(NoteService, NoteService(repository))

    arc_client.set_type_dependency(NoteService, note_service)
    lb_client.di.registry_for(lightbulb.di.Contexts.DEFAULT).register_value(NoteService, note_service)


@note_group.include
@arc.slash_subcommand("save", "Lưu một ghi chú")
async def note_save(
    ctx: arc.GatewayContext,
    key: arc.Option[str, arc.StrParams("Tên key để lưu")],
    text: arc.Option[str, arc.StrParams("Nội dung ghi chú")],
    note_service: NoteService = arc.inject(),
) -> None:
    try:
        await note_service.save(key, text)
    except NoteAlreadyExistsError:
        await ctx.respond(
            f"❌ Key `{key}` đã tồn tại, hãy chọn key khác nhé!",
            flags=hikari.MessageFlag.EPHEMERAL,
        )
        return

    await ctx.respond(f"✅ Azu-nyan đã lưu note với key `{key.strip()}`!")


@note_group.include
@arc.slash_subcommand("get", "Lấy một ghi chú")
async def note_get(
    ctx: arc.GatewayContext,
    key: arc.Option[str, arc.StrParams("Tên key cần lấy")],
    note_service: NoteService = arc.inject(),
) -> None:
    try:
        text = await note_service.get(key)
    except NoteNotFoundError:
        await ctx.respond(
            f"❌ Không tìm thấy ghi chú với key `{key}`.",
            flags=hikari.MessageFlag.EPHEMERAL,
        )
        return

    await ctx.respond(text)


@arc.loader
def arc_loader(client: arc.GatewayClient) -> None:
    client.add_plugin(arc_plugin)


@arc.unloader
def arc_unloader(client: arc.GatewayClient) -> None:
    client.remove_plugin(arc_plugin)
