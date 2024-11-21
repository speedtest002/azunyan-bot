from discord.ext import commands
from discord import *
import json

class QRCodeCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.hybrid_command(name = "qr_ngân_hàng", aliases = ['qr', 'bank'], with_app_command=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def qr_ngân_hàng(
        self,
        ctx: commands.Context,
        số_tài_khoản: str = None,
        ngân_hàng: str = None,
        số_tiền: str = None, 
        nội_dung: str = None,
        chủ_tài_khoản: str = None
    ):
        """
        Tạo mã QR từ số tài khoản ngân hàng

        Parameters
        ----------
        số_tài_khoản: str,
            Số tài khoản người nhận
        ngân_hàng: str
            Tên ngân hàng
        số_tiền: str = None, 
            Số tiền nhận
        nội_dung: str = None,
            Nội dung chuyển khoản
        chủ_tài_khoản: str = None
            Tên chủ tài khoản
        """
        if số_tài_khoản is not None and ngân_hàng is None:
            await ctx.message.delete()
            await ctx.send("Vui lòng nhập tên ngân hàng (ví dụ: vcb hoặc vietcombank).", ephemeral=True)
            return
        user_id = str(ctx.author.id)
        if số_tài_khoản is None and ngân_hàng is None:
            with open('user_qr.json', 'r', encoding='utf-8') as uf:
                user_data = json.load(uf)
            link_qr = user_data["user_qr"].get(user_id, [])
            if link_qr == []:
                await ctx.send("Bạn cần dùng lệnh này lần đầu với đúng cú pháp để lưu thông tin QR!")
                return
            await ctx.send(link_qr)
            return
        url = f"https://img.vietqr.io/image/{ngân_hàng}-{số_tài_khoản}-print.png?"
        if số_tiền is not None:
            url += f"amount={số_tiền}"
        if nội_dung is not None:
            nội_dung = nội_dung.replace(" ", "%20")
            url += f"&addInfo={nội_dung}"
        if chủ_tài_khoản is not None:
            chủ_tài_khoản = chủ_tài_khoản.replace(" ", "%20")
            url += f"&accountName={chủ_tài_khoản}"
        
        with open('user_qr.json', 'r', encoding='utf-8') as uf:
            data = json.load(uf)

        # Thay đổi giá trị URL cho khóa user_id
        data["user_qr"][user_id] = url

        # Ghi đè nội dung mới vào file JSON
        with open('user_qr.json', 'w', encoding='utf-8') as uf:
            json.dump(data, uf, ensure_ascii=False, indent=4)
        await ctx.send(url)

    
async def setup(bot):
    await bot.add_cog(QRCodeCommand(bot))