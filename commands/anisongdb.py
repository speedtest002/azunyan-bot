from discord.ext import commands
import discord
import re
import sqlite3
from feature.create_database import create_database

ANIME_REGEX_REPLACE_RULES = [
    # Ļ can't lower correctly with sqlite lower function hence why next line is needed
    {"input": "ļ", "replace": "[ļĻ]"},
    {"input": "l", "replace": "[l˥ļĻΛ]"},
    # Ź can't lower correctly with sqlite lower function hence why next line is needed
    {"input": "ź", "replace": "[źŹ]"},
    {"input": "z", "replace": "[zźŹ]"},
    {"input": "ou", "replace": "(ou|ō|o)"},
    {"input": "oo", "replace": "(oo|ō|o)"},
    {"input": "oh", "replace": "(oh|ō|o)"},
    {"input": "wo", "replace": "(wo|o)"},
    # Ō can't lower correctly with sqlite lower function hence why next line is needed
    {"input": "ō", "replace": "[Ōō]"},
    {"input": "o", "replace": "([oōŌóòöôøӨΦο]|ou|oo|oh|wo)"},
    {"input": "uu", "replace": "(uu|u|ū)"},
    # Ū can't lower correctly with sqlite lower function hence why next line is needed
    {"input": "ū", "replace": "[ūŪ]"},
    {"input": "u", "replace": "([uūŪûúùüǖμ]|uu)"},
    {"input": "aa", "replace": "(aa|a)"},
    {"input": "ae", "replace": "(ae|æ)"},
    # Λ can't lower correctly with sqlite lower function hence why next line is needed
    {"input": "λ", "replace": "[λΛ]"},
    {"input": "a", "replace": "([aäãά@âàáạåæā∀Λ]|aa)"},
    {"input": "c", "replace": "[cςč℃Ↄ]"},
    # É can't lower correctly with sql lower function
    {"input": "é", "replace": "[éÉ]"},
    {"input": "e", "replace": "[eəéÉêёëèæē]"},
    {"input": "'", "replace": "['’ˈ]"},
    {"input": "n", "replace": "[nñ]"},
    {"input": "0", "replace": "[0Ө]"},
    {"input": "2", "replace": "[2²₂]"},
    {"input": "3", "replace": "[3³]"},
    {"input": "5", "replace": "[5⁵]"},
    {"input": "*", "replace": "[*✻＊✳︎]"},
    {
        "input": " ",
        "replace": "([^\\w]+|_+) ",
    },
    {"input": "i", "replace": "([iíίɪ]|ii)"},
    {"input": "x", "replace": "[x×]"},
    {"input": "b", "replace": "[bßβ]"},
    {"input": "r", "replace": "[rЯ]"},
    {"input": "s", "replace": "[sς]"},
]


class AnisongDBCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "data/anisong.db"

    def apply_regex_rules(self, search):
        for rule in ANIME_REGEX_REPLACE_RULES:
            search = search.replace(rule["input"], rule["replace"])
        return search

    def escapeRegExp(self, str):
        str = re.escape(str)
        str = str.replace("\\ ", " ")
        str = str.replace("\\*", "*")
        return str

    def get_regex_search(self, og_search):
        og_search = self.escapeRegExp(og_search.lower())
        search = self.apply_regex_rules(og_search)
        search = ".*" + search + ".*"
        return search

    def remove_duplicate_songs(self, song_list):
        """
        Loại bỏ các dictionary trùng lặp trong danh sách dựa trên 'songId',
        chỉ giữ lại phần tử đầu tiên của mỗi songId duy nhất, sử dụng dictionary.
        """
        seen_songs = {}
        
        for song in song_list:
            if 'songId' in song:
                song_id = song['songId']
                if song_id not in seen_songs:
                    seen_songs[song_id] = song
            # Các dictionary không có 'songId' sẽ bị bỏ qua
        return list(seen_songs.values())
    
    def normalize_for_compare(self, text): # remove space and lower case
        return re.sub(r"\\s+", "", text.lower())
    
    def clean_metadata(self, title):
        """
        Xoá các phần không cần thiết như (feat. ...), (Inst), [Bonus Track], v.v.
        """
        # Loại bỏ nội dung trong () hoặc []
        cleaned = re.sub(r"\\s*\[\\(].*?\[\]\\)", "", title)
        return cleaned.strip()
    
    # Hàm tìm kiếm
    def azusong(self, query):
        song_regex = self.get_regex_search(query)
        normalized_query = self.normalize_for_compare(query)
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT songId, name FROM songs")
            all_songs = cursor.fetchall()

            matched_song_ids = []
            for song in all_songs:
                song_name = song['name']
                if not song_name:
                    continue
                
                clean_song_name = self.clean_metadata(song_name)
                normalized_song_name = self.normalize_for_compare(clean_song_name)
                
                if re.match(song_regex, clean_song_name.lower()) or (normalized_query and normalized_query in normalized_song_name):
                    matched_song_ids.append(song['songId'])

            if not matched_song_ids:
                conn.close()
                return []

            placeholders = ','.join('?' for _ in matched_song_ids)
            sql_get_all_info = f"""
                SELECT
                    an.mainNameJA as animeNameJA,
                    an.mainNameEN as animeNameEN,
                    s.name as songName,
                    s.songId,
                    ar.name as artistName,
                    gr.name as groupName
                FROM animeSong AS ans
                JOIN animes AS an ON ans.animeId = an.animeId
                JOIN songs AS s ON ans.songId = s.songId
                LEFT JOIN artists AS ar ON s.songArtistId = ar.artistId
                LEFT JOIN groups AS gr ON s.songGroupId = gr.groupId
                WHERE ans.songId IN ({placeholders})
            """

            cursor.execute(sql_get_all_info, matched_song_ids)
            query_results = cursor.fetchall()
            conn.close()

            results = []
            for row in query_results:
                result = {}
                animeNameJA = row["animeNameJA"]
                animeNameEN = row["animeNameEN"]
                result["animeName"] = animeNameJA if animeNameJA is not None else animeNameEN
                result["songName"] = row["songName"]
                result["artistName"] = row["artistName"] if row["artistName"] is not None else row["groupName"]
                result["songId"] = row["songId"]
                results.append(result)
            return results
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []
        except Exception as e:
            print(f"An error occurred: {e}")
            return []

    def azuani(self, query):
        pass

    @commands.command(name="song", aliases=["s","sd"]) #sp = s + dup (default = s is not dup)
    async def anisongdb(self, ctx, *search_query):
        search_query = " ".join(search_query).strip()
        if not search_query:
            await ctx.send("Vui lòng nhập từ khóa tìm kiếm.")
            return

        results = self.azusong(search_query)
        if not results:
            await ctx.send("Không tìm thấy kết quả nào.")
            return
        if not ctx.invoked_with=='sd':
            results = self.remove_duplicate_songs(results)  # Loại bỏ các bài hát trùng lặp
        results.sort(key=lambda x: len(x["songName"])) #sort by length of song name
        embed = discord.Embed(
            title="Kết quả tìm kiếm",
            description="Danh sách các bài hát tìm thấy",
            color=0x00ff00
        )
        for idx, result in enumerate(results[:8]):  # Giới hạn tối đa 8*3=24 kết quả, limit cua discord la 25
            embed.add_field(
                name="Anime" if idx == 0 else "",
                value=result.get("animeName", "N/A"),
                inline=True
            )
            embed.add_field(
                name="Song Name" if idx == 0 else "",
                value=result.get("songName", "N/A"),
                inline=True
            )
            embed.add_field(
                name="Artist" if idx == 0 else "",
                value=result.get("artistName", "N/A"),
                inline=True
            )
       
        await ctx.send(embed=embed)

    @commands.command(name="update_anisongdb")
    @commands.is_owner()
    async def update_anisongdb(self, ctx):       
        create_database()
        await ctx.send("Update sussessfuly.")
        
async def setup(bot):
    await bot.add_cog(AnisongDBCommand(bot))