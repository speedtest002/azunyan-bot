"""plugins/role/__init__.py — /role add + /role create (subcommand group)"""
import arc
import hikari

from core.config import AMQ_GUILD_ID
from core.state import get_app_state
from plugins.role.views import AssignRoleView


# ── arc plugin + subcommand group ─────────────────────────────────────────────
arc_plugin = arc.GatewayPlugin("role-slash")
role_group = arc_plugin.include_slash_group("role", "Quản lý roles")


@role_group.include
@arc.slash_subcommand("add", "Thêm role cho thành viên")
async def role_add(
    ctx: arc.GatewayContext,
    member: arc.Option[hikari.Member, arc.MemberParams("Member cần thêm role")],
    role: arc.Option[hikari.Role, arc.RoleParams("Role cần thêm")],
) -> None:
    if not ctx.member or not ctx.member.permissions & hikari.Permissions.MANAGE_ROLES:
        await ctx.respond("Bạn không có quyền dùng lệnh này.", flags=hikari.MessageFlag.EPHEMERAL)
        return
    if role in [ctx.get_guild().get_role(r) for r in member.role_ids]:  # type: ignore
        await ctx.respond(f"{member.mention} đã có role `{role.name}`.", flags=hikari.MessageFlag.EPHEMERAL)
        return
    guild = ctx.get_guild()
    if not guild:
        return
    try:
        await member.add_role(role)
        await ctx.respond(f"Đã thêm role `{role.name}` cho {member.mention}.")
    except Exception as e:
        await ctx.respond(f"Lỗi: `{e}`", flags=hikari.MessageFlag.EPHEMERAL)


@role_group.include
@arc.slash_subcommand("create", "Tạo role custom (chỉ hỗ trợ server AMQ)")
async def role_create(
    ctx: arc.GatewayContext,
    name: arc.Option[str, arc.StrParams("Tên role")],
    color: arc.Option[str, arc.StrParams("Màu role (hex, VD: #FF0000)")],
    icon: arc.Option[hikari.Attachment | None, arc.AttachmentParams("Icon role (PNG/JPG)")] = None,
) -> None:
    guild = ctx.get_guild()
    if not guild or guild.id != AMQ_GUILD_ID:
        await ctx.respond("Lệnh này chỉ hỗ trợ server AMQ.", flags=hikari.MessageFlag.EPHEMERAL)
        return

    # Check existing
    existing = next((r for r in guild.get_roles().values() if r.name == name), None)
    if existing:
        miru_client = get_app_state(ctx.client.app).miru
        view = AssignRoleView(existing, ctx.author.id)
        resp = await ctx.respond(
            "Role này đã tồn tại. Bạn muốn tự gắn role này chứ?",
            components=view,
            flags=hikari.MessageFlag.EPHEMERAL,
        )
        miru_client.start_view(view, bind_to=await resp.retrieve_message())
        return

    # Create role
    try:
        parsed_color = hikari.Color.of(color)
        display_icon = None
        if icon and "ROLE_ICONS" in guild.features:
            display_icon = await icon.read()

        new_role = await guild.create_role(
            name=name,
            color=parsed_color,
            icon=display_icon,
            permissions=hikari.Permissions.NONE,
            mentionable=True,
        )
        await ctx.author.add_role(new_role)  # type: ignore[union-attr]
        await ctx.respond(f"Đã tạo và gán role **{name}** với màu `{color}`.", flags=hikari.MessageFlag.EPHEMERAL)
    except hikari.ForbiddenError:
        await ctx.respond("Bot không đủ quyền để tạo role.", flags=hikari.MessageFlag.EPHEMERAL)
    except Exception as e:
        await ctx.respond(f"Lỗi: {e}", flags=hikari.MessageFlag.EPHEMERAL)


@arc.loader
def arc_loader(client: arc.GatewayClient) -> None:
    client.add_plugin(arc_plugin)

@arc.unloader
def arc_unloader(client: arc.GatewayClient) -> None:
    client.remove_plugin(arc_plugin)
