from discord.ext import commands
import discord
import re
import json

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
        "replace": "([^\\w]+|_+)",
    },
    {"input": "i", "replace": "([iíίɪ]|ii)"},
    {"input": "x", "replace": "[x×]"},
    {"input": "b", "replace": "[bßβ]"},
    {"input": "r", "replace": "[rЯ]"},
    {"input": "s", "replace": "[sς]"},
]


class AnisongDBCommand(commands.Cog):
    def __init__(self, bot):
        self.anime_file = "animeMap.json"
        self.song_file = "songMap.json"
        self.artist_file = "artistMap.json"
        self.group_file = "groupMap.json"
        self.anime_data = self.load_data(self.anime_file)
        self.song_data = self.load_data(self.song_file)
        self.artist_data = self.load_data(self.artist_file)
        self.group_data = self.load_data(self.group_file)
        self.bot = bot

    def apply_regex_rules(self, search):
        for rule in ANIME_REGEX_REPLACE_RULES:
            search = search.replace(rule["input"], rule["replace"])
        return search

    def escapeRegExp(self, str):
        str = re.escape(str)
        str = str.replace("\ ", " ")
        str = str.replace("\*", "*")
        return str

    def get_regex_search(self, og_search):
        og_search = self.escapeRegExp(og_search.lower())
        search = self.apply_regex_rules(og_search)
        search = ".*" + search + ".*"
        return search
    
    def load_data(self, file_path):
        try:
            with open(f"data/{file_path}", "r", encoding="utf-8") as file:
                data = json.load(file)  # đọc toàn bộ file 1 lần
            print("Dữ liệu đã được nạp thành công!")
            return data
        except Exception as e:
            print(f"Lỗi khi đọc file JSON: {e}")
            return None

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
        return re.sub(r"\s+", "", text.lower())
    
    def clean_metadata(self, title):
        """
        Xoá các phần không cần thiết như (feat. ...), (Inst), [Bonus Track], v.v.
        """
        # Loại bỏ nội dung trong () hoặc []
        cleaned = re.sub(r"\s*[\[\(].*?[\]\)]", "", title)
        return cleaned.strip()
    
    # Hàm tìm kiếm
    def azusong(self, anime_data, song_data, artist_data, group_data, query):
        song_regex = self.get_regex_search(query)
        results = []
        matched_songs = {}
        for song_id, song_info in song_data.items():
            song_name = song_info["name"]
            clean_song_name = self.clean_metadata(song_name)
            normalized_song_name = self.normalize_for_compare(clean_song_name)
            normalized_query = self.normalize_for_compare(query)
            #if re.match(song_regex, song_name.lower()):
            if re.match(song_regex, clean_song_name.lower()) or normalized_query in normalized_song_name:
                song = {song_id: {"songName": song_name, "artistName": None}}
                if song_info["songArtistId"]:
                    artistId = str(song_info["songArtistId"])
                    song[song_id]["artistName"] = artist_data[artistId]["name"]
                else:
                    groupId = str(song_info["songGroupId"])
                    song[song_id]["artistName"] = group_data[groupId]["name"]
                matched_songs.update(song)
        if matched_songs:
            for anime_entry in anime_data.values(): #với mỗi anime
                for song_list in anime_entry["songLinks"].values(): #duyệt từng loại OP ED INS
                    for song in song_list: #duyệt từng bài trong mỗi loại
                        if str(song["songId"]) in matched_songs.keys():
                            result = {}
                            animeNameJA = anime_entry["mainNames"]["JA"]
                            animeNameEN = anime_entry["mainNames"]["EN"]
                            result["animeName"] = animeNameJA if animeNameJA is not None else animeNameEN # nếu không có tên JA thì lấy tên EN
                            result["songName"] = matched_songs[str(song["songId"])]["songName"]
                            result["artistName"] = matched_songs[str(song["songId"])]["artistName"]
                            result["songId"] = song["songId"]
                            results.append(result)
        return results
    
    def azuani(self, anime_data, song_data, artist_data, group_data, query):
        pass

    @commands.command(name="song", aliases=["s","sd"]) #sp = s + dup (default = s is not dup)
    async def anisongdb(self, ctx, *search_query):
        search_query = " ".join(search_query).strip()
        if not search_query:
            await ctx.send("Vui lòng nhập từ khóa tìm kiếm.")
            return

        results = self.azusong(self.anime_data, self.song_data, self.artist_data, self.group_data, search_query)
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

async def setup(bot):
    await bot.add_cog(AnisongDBCommand(bot))