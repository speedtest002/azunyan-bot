from discord.ext import commands
from discord import *
from feature import MongoManager

class QRCodeCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.qr_collection = MongoManager.get_collection("qr")

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
            await ctx.send("Vui lòng nhập tên ngân hàng (ví dụ: vcb hoặc vietcombank).", ephemeral=True, delete_after=5)
            return
        
        user_id = ctx.author.id
        user_data = self.qr_collection.find_one({"_id": user_id})
        if user_data is None:
            if số_tài_khoản is None and ngân_hàng is None:
                await ctx.send("Bạn cần dùng lệnh này lần đầu với đúng cú pháp để lưu thông tin QR!", delete_after=5)
                return
            user_data = {
            "_id": user_id,
            "bank": ngân_hàng,
            "number": số_tài_khoản
            
            }
            self.qr_collection.insert_one(user_data)
        else:
            if số_tài_khoản is not None and ngân_hàng is not None:  # Có thông tin mới để cập nhật
                updated_data = {
                    "bank": ngân_hàng,
                    "number": số_tài_khoản
                    
                }
                self.qr_collection.update_one({"_id": user_id}, {"$set": updated_data})
                user_data.update(updated_data)
            else:
                số_tài_khoản = user_data["number"]
                ngân_hàng = user_data["bank"]
        
        
        url = f"https://img.vietqr.io/image/{ngân_hàng}-{số_tài_khoản}-print.png?"
        if số_tiền is not None:
            url += f"amount={số_tiền}"
        if nội_dung is not None:
            nội_dung = nội_dung.replace(" ", "%20")
            url += f"&addInfo={nội_dung}"
        if chủ_tài_khoản is not None:
            chủ_tài_khoản = chủ_tài_khoản.replace(" ", "%20")
            url += f"&accountName={chủ_tài_khoản}"
        await ctx.send(url)
    
async def setup(bot):
    await bot.add_cog(QRCodeCommand(bot))