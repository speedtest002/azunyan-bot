from discord.ext import commands
from discord import *
from feature import MongoManager
import re
import os

class QRCodeCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.qr_collection = MongoManager.get_collection("qr")
        self.banks_collection = MongoManager.get_collection("banks")
        self.bank_aliases = self.load_banks()

    def qr_bank_core(self, user_id, bank_number, bank_name, amount, add_info: str = None, account_name: str = None) -> tuple[bool, str]:
        if bank_number is not None and bank_name is None:
            return False, f"Vui lòng nhập tên ngân hàng (ví dụ: vcb hoặc vietcombank hoặc dùng lệnh {os.getenv("PREFIX")}qr --help/-h để xem hướng dẫn)."
            
        user_data = self.qr_collection.find_one({"_id": user_id})
        if user_data is None:
            if bank_number is None and bank_name is None:
                return False, "Bạn cần dùng lệnh này lần đầu với đúng cú pháp để lưu thông tin QR!"
            user_data = {
                "_id": user_id,
                "number": bank_number,
                "name": bank_name
            }
            self.qr_collection.insert_one(user_data)
        else:
            if bank_number is not None and bank_name is not None:  # Có thông tin mới để cập nhật
                updated_data = {
                    "number": bank_number,
                    "name": bank_name
                }
                self.qr_collection.update_one({"_id": user_id}, {"$set": updated_data})
                user_data.update(updated_data)
            else:
                bank_number = user_data["number"]
                bank_name = user_data["name"]
        
        
        url = f"https://img.vietqr.io/image/{bank_name}-{bank_number}-print.png?"
        if amount is not None:
            url += f"amount={amount}"
        if add_info is not None:
            add_info = add_info.replace(" ", "%20")
            url += f"&addInfo={add_info}"
        if account_name is not None:
            account_name = account_name.replace(" ", "%20")
            url += f"&accountName={account_name}"
        return True, url

    # slash command
    @app_commands.command(name = "qr_ngân_hàng", description="Tạo mã QR từ số tài khoản ngân hàng", with_app_command=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.rename(bank_number = "số_tài_khoản", bank_name = "ngân_hàng", amount = "số_tiền", add_info = "nội_dung", account_name = "chủ_tài_khoản")
    @app_commands.describe(bank_number = "Số tài khoản người nhận", bank_name = "Tên ngân hàng", amount = "Số tiền nhận", add_info = "Nội dung chuyển khoản", account_name = "Tên chủ tài khoản")
    async def qr_bank_slash(
        self,
        ctx: commands.Context,
        bank_number: str,
        bank_name: str,
        amount: str = None, 
        add_info: str = None,
        account_name: str = None
    ):
        user_id = ctx.author.id
        state, message = self.qr_bank_core(user_id, bank_number, bank_name, amount, add_info, account_name)
        if state is False:
            await ctx.send(message, ephemeral=True)
            return
        await ctx.send(message)

    # prefix qr
    #azuqr -b vcb -n 123456789 -a 100000 -d "Chuyển tiền" -c
    @commands.command(name="qr_ngân_hàng", aliases=["qr", "bank"])
    async def qr_bank_slash(
        self,
        ctx,
        *args
    ):
        user_id = ctx.author.id
        
        #state, message = self.qr_bank_core(user_id, bank_number, bank_name, amount, add_info, account_name)
        #if state is False:
        #    await ctx.send(message, ephemeral=True)
        #    return
        await ctx.send(message)

    ### zalo qr clone
    def load_banks(self):
        bank_data = {}
        try:
            banks = self.banks_collection.find()
            for bank in banks:
                for alias in bank["aliases"]:
                    bank_data[alias] = bank["name"]
        except Exception as e:
            print(f"Không thể tải dữ liệu ngân hàng từ MongoDB: {e}")
        return bank_data


    def generate_qr_code(self, stk, bank_name):
        return f"https://img.vietqr.io/image/{bank_name}-{stk}-print.png"
        #return f"QR Code cho STK {stk} tại {bank_name}"

    @commands.Cog.listener("on_message")
    async def send_qr(self, message):
        if message.author.bot:
            return

        content = message.content.lower()

        stk_match = re.search(r'\b\d{6,19}\b', content) # theo VietQR Số tài khoản người nhận quy ước bao gồm chữ hoặc số, tối đa 19 kí tự.
        stk = stk_match.group() if stk_match else None

        if not stk:
            return

        words = content.split()

        bank_name = None
        for word in words:
            if word in self.bank_aliases:
                bank_name = self.bank_aliases[word]
                break

        if not bank_name:
            return

        qr_code = self.generate_qr_code(stk, bank_name)
        await message.channel.send(f"{qr_code}")

async def setup(bot):
    await bot.add_cog(QRCodeCommand(bot))