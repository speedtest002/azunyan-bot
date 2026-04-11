"""
plugins/_template/__init__.py — Template Router cho command mới.

Hướng dẫn:
- Copy thư mục `_template` và đổi tên thành tên tính năng (vd: `ping`).
- File `__init__.py` NÀY CHỈ dùng để đăng ký lệnh (Routing).
- Chuyển TẤT CẢ logic xử lý (gọi API, tính toán, IF/ELSE nghiệp vụ) sang file `core.py`.
- Nếu có UI (Embed phức tạp, Button, Modal), tạo thêm file `views.py`.
"""
import arc
import core.prefix as lightbulb

from plugins._template.core import process_example_logic

# ── arc (slash command) ───────────────────────────────────────────────────────
arc_plugin = arc.GatewayPlugin("example-slash")

@arc_plugin.include
@arc.slash_command("example", "Mô tả ngắn về lệnh này")
async def example_slash(
    ctx: arc.GatewayContext,
    # Ví dụ options:
    text: arc.Option[str, arc.StrParams("Văn bản cần xử lý")],
    number: arc.Option[int | None, arc.IntParams("Số nguyên (tùy chọn)")] = None,
) -> None:
    # KHÔNG viết logic ở đây. Gọi hàm từ core.py:
    result = process_example_logic(text, number)
    await ctx.respond(result)

@arc.loader
def arc_loader(client: arc.GatewayClient) -> None:
    client.add_plugin(arc_plugin)

@arc.unloader
def arc_unloader(client: arc.GatewayClient) -> None:
    client.remove_plugin(arc_plugin)


# ── lightbulb (prefix command, nếu cần) ─────────────────────────────────────
# Xóa phần này nếu chỉ cần slash command

lb_loader = lightbulb.Loader()

@lb_loader.command
@lightbulb.option("text", "Văn bản cần xử lý", modifier=lightbulb.GreedyArgument)
@lightbulb.command("example", "Mô tả ngắn về lệnh này", aliases=["ex"])
@lightbulb.implements(lightbulb.PrefixCommand)
async def example_prefix(ctx: lightbulb.PrefixContext) -> None:
    text = " ".join(ctx.options.text) if isinstance(ctx.options.text, list) else ctx.options.text
    
    # KHÔNG viết logic ở đây. Gọi hàm từ core.py:
    result = process_example_logic(text, None)
    await ctx.respond(result)


# ── Ví dụ subcommand group (nếu cần nhiều subcommands) ────────────────────────
# arc_plugin2 = arc.GatewayPlugin("mygroup-slash")
# group = arc_plugin2.include_slash_group("mygroup", "Nhóm lệnh của tôi")
#
# @group.include
# @arc.slash_subcommand("sub1", "Subcommand đầu tiên")
# async def sub1(ctx: arc.GatewayContext) -> None:
#     await ctx.respond("sub1!")
#
# @group.include
# @arc.slash_subcommand("sub2", "Subcommand thứ hai")
# async def sub2(ctx: arc.GatewayContext) -> None:
#     await ctx.respond("sub2!")