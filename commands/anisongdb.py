from discord.ext import commands
import discord
import re
import json

class AnisongDBCommand(commands.Cog):
    def __init__(self, bot):
        self.data_file = "musicDB.jsonl"
        self.data = self.load_data(self.data_file)
        self.bot = bot

    def normalize_string(self, s):
        return re.sub(r"[^a-zA-Z0-9]", "", s).lower()

    def load_data(self, file_path):
        data = []
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                for line in file:
                    try:
                        data.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        print(f"Lỗi JSON trong dòng: {line}\n{e}")
            print("Dữ liệu đã được nạp thành công!")
        except Exception as e:
            print(f"Lỗi khi mở file: {e}")
        return data

    # Hàm tìm kiếm
    def search_data(self, data, query):
        query_normalized = self.normalize_string(query)
        results = []

        # Danh sách các trường cần ưu tiên, thêm các trường HQ, MQ, audio
        priority_keys = ["songName", "animeJPName", "animeENName", "HQ", "MQ", "audio"]

        for entry in data:
            matched_priority = None
            matched_value = None

            # Kiểm tra các trường theo độ ưu tiên
            for key in priority_keys:
                value = entry.get(key)
                if value:  # Bỏ qua nếu value là None hoặc rỗng
                    if isinstance(value, list):
                        value = " ".join(value)
                    if query_normalized in self.normalize_string(value):
                        matched_priority = key
                        matched_value = value
                        break  # Dừng nếu đã tìm thấy khớp trong một trường

            # Nếu khớp, thêm vào danh sách kết quả
            if matched_priority:
                results.append((matched_priority, len(matched_value), entry))

        # Sắp xếp kết quả theo độ ưu tiên và số ký tự của giá trị
        results.sort(key=lambda x: (priority_keys.index(x[0]), x[1]))

        # Trả về danh sách các entry (chỉ lấy dữ liệu chính)
        return [entry for _, _, entry in results]

    @commands.command(name="anisongdb", aliases=["anisong", "song"])
    async def anisongdb(self, ctx, *search_query):
        search_query = " ".join(search_query).strip()
        if not search_query:
            await ctx.send("Vui lòng nhập từ khóa tìm kiếm.")
            return

        results = self.search_data(self.data, search_query)
        if not results:
            await ctx.send("Không tìm thấy kết quả nào.")
            return

        embed = discord.Embed(
            title="Kết quả tìm kiếm",
            description="Danh sách các bài hát tìm thấy",
            color=0x00ff00
        )

        for idx, result in enumerate(results[:6]):  # Giới hạn tối đa 5 kết quả
            embed.add_field(
                name="Anime (JP)" if idx == 0 else "",
                value=result.get("animeJPName", "N/A"),
                inline=True
            )
            embed.add_field(
                name="Song Name" if idx == 0 else "",
                value=result.get("songName", "N/A"),
                inline=True
            )
            embed.add_field(
                name="Artist" if idx == 0 else "",
                value=result.get("songArtist", "N/A"),
                inline=True
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AnisongDBCommand(bot))
