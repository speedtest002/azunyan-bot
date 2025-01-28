from discord.ext import commands
from discord import *
import discord
from feature import MongoManager
import re
import os
import click
from click.testing import CliRunner

class QRCodeCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.qr_collection = MongoManager.get_collection("qr")
        self.banks_collection = MongoManager.get_collection("banks")
        self.bank_aliases = self.load_banks()
        self.runner = CliRunner()
        self.cli_command = self._define_command()

    def tra_cuu_stk(self, stk: str) -> tuple[bool, str]:
        pass

    def find_information(self, user_id) -> bool: #kiem tra xem user_id da co thong tin chua
        user_data = self.qr_collection.find_one({"_id": user_id})
        if user_data is None:
            return False
        return True

    def insert_information(self, user_id, bank_number, bank_name):
        user_data = {
            "_id": user_id,
            "number": bank_number,
            "name": bank_name
        }
        try:
            self.qr_collection.insert_one(user_data)
            return True
        except Exception as e:
            print(f"Failed to insert information for user {user_id}: {e}")
            return False

    def update_information(self, user_id, user_data, bank_number, bank_name):
        updated_data = {
            "number": bank_number,
            "name": bank_name
        }
        try:
            self.qr_collection.update_one({"_id": user_id}, {"$set": updated_data})
            user_data.update(updated_data)
            print(f"Update information for user {user_id} successfully.")
            #return True
        except Exception as e:
            print(f"Failed to update information for user {user_id}: {e}")
            #return False

    def qr_generate(self, bank_number: str, bank_name: str, amount: str = None, description: str = None, account_name: str = None) -> str:
        url = f"https://img.vietqr.io/image/{bank_name}-{bank_number}-print.png?"
        if amount is not None:
            url += f"amount={amount}"
        if description is not None:
            description = description.replace(" ", "%20")
            url += f"&addInfo={description}"
        if account_name is not None:
            account_name = account_name.replace(" ", "%20")
            url += f"&accountName={account_name}"
        return url

    def qr_bank_core(self, user_id: str, bank_number: str = None, bank_name: str = None, amount: str = None, description: str = None, account_name: str = None) -> tuple[bool, str]:
        
        #if bank_number is not None and bank_name is None:
        #    return False, f"Vui lòng nhập tên ngân hàng (ví dụ: vcb hoặc vietcombank hoặc dùng lệnh {os.getenv("PREFIX")}qr --help/-h để xem hướng dẫn)."
            
        user_data = self.qr_collection.find_one({"_id": user_id})
        #bank_name check

        if self.find_information(user_id) is False: # for Prefix only
            if bank_number is None or bank_name is None:
                return False, f"Bạn cần dùng lệnh này lần đầu với đầy đủ thông tin `stk` và `ngân hàng` để lưu thông tin QR! (dùng `{os.getenv('PREFIX')}qr -h` để xem hướng dẫn)"
            else:
                self.insert_information(user_id, bank_number, bank_name)

        else: # for both Slash and Prefix
            if bank_number is not None and bank_name is not None: # Có thông tin mới để cập nhật
                if bank_name not in self.bank_aliases:
                    return False, f"Tên ngân hàng không hợp lệ, vui lòng kiểm tra lại hoặc dùng lệnh `{os.getenv('PREFIX')}qr -h` để xem hướng dẫn."
                bank_name = self.bank_aliases[bank_name.lower()]
                if (user_data["number"] == bank_number and user_data["name"] == bank_name) is False:
                    self.update_information(user_id, user_data, bank_number, bank_name)
            else: # Không có thông tin mới để cập nhật
                bank_number = user_data["number"]
                bank_name = user_data["name"]
        
        url = self.qr_generate(bank_number, bank_name, amount, description, account_name)
        return True, url

    # slash command
    @app_commands.command(name = "qr_ngân_hàng", description="Tạo mã QR từ số tài khoản ngân hàng")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.rename(bank_number = "số_tài_khoản", bank_name = "ngân_hàng", amount = "số_tiền", description = "nội_dung", account_name = "chủ_tài_khoản")
    @app_commands.describe(bank_number = "Số tài khoản người nhận", bank_name = "Tên ngân hàng", amount = "Số tiền nhận", description = "Nội dung chuyển khoản", account_name = "Tên chủ tài khoản")
    async def qr_bank_slash(
        self,
        ctx,
        bank_number: str,
        bank_name: str,
        amount: str = None, 
        description: str = None,
        account_name: str = None
    ):
        user_id = ctx.user.id
        state, message = self.qr_bank_core(user_id, bank_number, bank_name, amount, description, account_name)
        if state is False:
            await ctx.response.send_message(message, ephemeral=state)
            return
        await ctx.response.send_message(message)

    # prefix qr
    #azuqr -b vcb -n 123456789 -a 100000 -d "Chuyển tiền" -c
    def _define_command(self):
        @click.command()
        @click.option("-b", default=None, help="Ngân hàng")
        @click.option("-n", default=None, help="Số tài khoản")
        @click.option("-a", default=None, help="Số tiền")
        @click.option("-d", default=None, help="Nội dung")
        @click.option("-c", is_flag=True, help="Flag check stk")
        def command(b, n, a, d, c):
            click.echo((b, n, a, d, c))  # In ra tuple để đọc từ output
            return b, n, a, d, c

        return command
    def parse(self, args):
        try:
            result = self.runner.invoke(self.cli_command, args)

            if result.exit_code != 0:
                raise click.exceptions.ClickException(f"Lỗi: {result.output}")

            # Đọc kết quả từ output (tuple dưới dạng chuỗi)
            output = result.output.strip()
            return eval(output)  # Convert chuỗi thành tuple
        except click.exceptions.ClickException as e:
            print(e)
            return None
    @commands.command(name="qr", aliases=["bank"])
    async def qr_bank_prefix(self, ctx, *args):
        try:
            if len(ctx.message.mentions) > 0:
                for user in ctx.message.mentions:
                    user_id = user.id
                    user_data = self.qr_collection.find_one({"_id": user_id})
                    if user_data is None:
                        await ctx.send(f"<@{user_id}> chưa có thông tin QR", delete_after=5)
                    bank = user_data["bank"]
                    number = user_data["number"]
                    url = self.qr_generate(bank_name=bank, bank_number=number)
                    await ctx.send(f"[Mã QR]({url}) của <@{user_id}>")
                return
            
            param = self.parse(args)
            user_id = ctx.author.id
            state, message = self.qr_bank_core(user_id, param[1], param[0], param[2], param[3])
            await ctx.send(message, ephemeral=state)
        except Exception as e:
            await ctx.send(f"Cú pháp lệnh không hợp lệ, dùng lệnh `{os.getenv('PREFIX')}qr -h` để xem hướng dẫn ", ephemeral=True)


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

    @commands.Cog.listener("on_message")
    async def send_qr_on_message(self, message):
        if message.author.bot:
            return
        if any(message.content.startswith(prefix) for prefix in await self.bot.get_prefix(message)):
            return
        content = message.content.lower()

        stk_match = re.search(r'\b\d{6,19}\b', content) # theo VietQR Số tài khoản người nhận quy ước bao gồm chữ hoặc số, tối đa 19 kí tự. Here I use number only
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

        qr_code = self.qr_generate(stk, bank_name)
        await message.channel.send(f"{qr_code}")

async def setup(bot):
    await bot.add_cog(QRCodeCommand(bot))