"""plugins/qr/__init__.py — /qr show, /qr set (subcommand group) + !qr prefix + on_message listener"""
import re
import arc
import core.prefix as lightbulb
import hikari

from plugins.qr.core import (
    load_banks, qr_bank_core, qr_generate, parse_prefix_args, qr_collection
)


def _get_bank_aliases() -> dict[str, str]:
    return load_banks()

# ── arc (slash — subcommand group) ────────────────────────────────────────────
arc_plugin = arc.GatewayPlugin("qr-slash")
qr_group = arc_plugin.include_slash_group(
    "qr",
    "Tạo và quản lý QR ngân hàng",
)


@qr_group.include
@arc.slash_subcommand("show", "Tạo mã QR từ thông tin đã lưu hoặc nhập trực tiếp")
async def qr_show(
    ctx: arc.GatewayContext,
    số_tài_khoản: arc.Option[str | None, arc.StrParams("Số tài khoản người nhận")] = None,
    ngân_hàng: arc.Option[str | None, arc.StrParams("Tên ngân hàng (VD: vcb, acb)")] = None,
    số_tiền: arc.Option[str | None, arc.StrParams("Số tiền nhận")] = None,
    nội_dung: arc.Option[str | None, arc.StrParams("Nội dung chuyển khoản")] = None,
    chủ_tài_khoản: arc.Option[str | None, arc.StrParams("Tên chủ tài khoản")] = None,
) -> None:
    bank_aliases = _get_bank_aliases()
    ok, msg = qr_bank_core(
        ctx.author.id, bank_aliases,
        số_tài_khoản, ngân_hàng, số_tiền, nội_dung, chủ_tài_khoản,
    )
    if ok:
        await ctx.respond(msg)
    else:
        await ctx.respond(msg, flags=hikari.MessageFlag.EPHEMERAL)


@qr_group.include
@arc.slash_subcommand("set", "Lưu thông tin STK và ngân hàng của bạn")
async def qr_set(
    ctx: arc.GatewayContext,
    số_tài_khoản: arc.Option[str, arc.StrParams("Số tài khoản của bạn")],
    ngân_hàng: arc.Option[str, arc.StrParams("Tên ngân hàng (VD: vcb, acb)")],
) -> None:
    bank_aliases = _get_bank_aliases()
    if ngân_hàng.lower() not in bank_aliases:
        await ctx.respond("Tên ngân hàng không hợp lệ.", flags=hikari.MessageFlag.EPHEMERAL)
        return
    bank_id = bank_aliases[ngân_hàng.lower()]
    qr_collection.update_one(
        {"_id": ctx.author.id},
        {"$set": {"number": số_tài_khoản, "name": bank_id}},
        upsert=True,
    )
    await ctx.respond(f"Đã lưu: STK `{số_tài_khoản}` - Ngân hàng `{bank_id}`.", flags=hikari.MessageFlag.EPHEMERAL)


@arc.loader
def arc_loader(client: arc.GatewayClient) -> None:
    client.add_plugin(arc_plugin)

@arc.unloader
def arc_unloader(client: arc.GatewayClient) -> None:
    client.remove_plugin(arc_plugin)


# ── lightbulb (prefix) ───────────────────────────────────────────────────────
lb_loader = lightbulb.Loader()

@lb_loader.command
@lightbulb.command("qr", "Tạo mã QR ngân hàng", aliases=["bank"])
@lightbulb.implements(lightbulb.PrefixCommand)
async def qr_prefix(ctx: lightbulb.PrefixContext) -> None:
    args = tuple(ctx.event.message.content.split()[1:])
    try:
        if ctx.event.message.user_mentions:
            for user_id, user in ctx.event.message.user_mentions.items():
                data = qr_collection.find_one({"_id": user_id})
                if not data:
                    await ctx.respond(f"{user.mention} chưa có thông tin QR")
                    continue
                url = qr_generate(data["name"], data["number"])
                await ctx.respond(f"[Mã QR]({url}) của {user.mention}")
            return

        bank_aliases = _get_bank_aliases()
        param = parse_prefix_args(args)
        if not param:
            raise ValueError
        ok, msg = qr_bank_core(ctx.author.id, bank_aliases, param[1], param[0], param[2], param[3])
        await ctx.respond(msg)
    except Exception:
        await ctx.respond("Cú pháp không hợp lệ.")


# ── on_message listener: auto QR khi phát hiện STK + tên ngân hàng ───────────
@lb_loader.listener(hikari.MessageCreateEvent)
async def on_message(event: hikari.MessageCreateEvent) -> None:
    if not event.is_human:
        return
    content = event.content or ""
    if not content:
        return

    stk_match = re.search(r"\b\d{6,19}\b", content)
    if not stk_match:
        return

    bank_aliases = _get_bank_aliases()
    words = content.lower().split()
    bank_name = next((w for w in words if w in bank_aliases), None)
    if not bank_name:
        return

    url = qr_generate(bank_aliases[bank_name], stk_match.group())
    await event.message.respond(url)
