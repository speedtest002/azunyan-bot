"""plugins/role/views.py — miru Button cho tự gắn role"""
import hikari
import miru


class AssignRoleView(miru.View):
    def __init__(self, role: hikari.Role, requester_id: int) -> None:
        super().__init__(timeout=300)
        self.role = role
        self.requester_id = requester_id

    @miru.button(label="Ok! Gán role cho tôi", style=hikari.ButtonStyle.PRIMARY)
    async def assign_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        member = ctx.member
        if not member:
            await ctx.respond("Không thể xác định thành viên.", flags=hikari.MessageFlag.EPHEMERAL)
            return
        try:
            await member.add_role(self.role)
            await ctx.respond(f"Đã gán role **{self.role.name}** cho bạn.", flags=hikari.MessageFlag.EPHEMERAL)
        except Exception as e:
            await ctx.respond(f"Lỗi khi gán role: {e}", flags=hikari.MessageFlag.EPHEMERAL)
        self.stop()
