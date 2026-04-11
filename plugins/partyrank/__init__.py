"""plugins/partyrank/__init__.py — /partyrank create (subcommand group)"""
import arc
import hikari

from core.config import BOT_OWNER_ID
from plugins.partyrank.views import PRCreateModal

arc_plugin = arc.GatewayPlugin("partyrank-slash")
partyrank_group = arc_plugin.include_slash_group("partyrank", "Quản lý Party Rank")


@partyrank_group.include
@arc.slash_subcommand("create", "Tạo một phiên Party Rank mới (Chỉ Admin)")
async def partyrank_create(ctx: arc.GatewayContext) -> None:
    if ctx.author.id != BOT_OWNER_ID:
        await ctx.respond("❌ Bạn không có quyền dùng lệnh này!", flags=hikari.MessageFlag.EPHEMERAL)
        return
    modal = PRCreateModal()
    await ctx.respond_with_modal(modal)


@arc.loader
def arc_loader(client: arc.GatewayClient) -> None:
    client.add_plugin(arc_plugin)

@arc.unloader
def arc_unloader(client: arc.GatewayClient) -> None:
    client.remove_plugin(arc_plugin)
