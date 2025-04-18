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
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)  # đọc toàn bộ file 1 lần
            print("Dữ liệu đã được nạp thành công!")
            return data
        except Exception as e:
            print(f"Lỗi khi đọc file JSON: {e}")
            return None

    # Hàm tìm kiếm
    def azusong(self, anime_data, song_data, artist_data, group_data, query):
        song_regex = self.get_regex_search(query)
        results = []
        matched_songs = {}
        for song_id, song_info in song_data.items():
            song_name = song_info["name"]

            if re.match(song_regex, song_name.lower()):
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
                            result["animeName"] = anime_entry["mainNames"]["JA"]
                            result["songName"] = matched_songs[str(song["songId"])]["songName"]
                            result["artistName"] = matched_songs[str(song["songId"])]["artistName"]
                            results.append(result)
        return results
    def azuani(self, anime_data, song_data, artist_data, group_data, query):
        anime_regex = self.get_regex_search(query)
        results = []
        matched_animes = {}
        for anime_id, anime_info in anime_data.items():
            if any(re.match(anime_regex, entry["name"].lower()) for entry in anime_info["names"]):
                ja_name = next(
                    (entry["name"] for entry in anime_info["names"] if entry["language"] == "JA"),
                    anime_info["names"][0]["name"]  # fallback nếu không có JA
                )
                anime = {anime_id: {"animeName": ja_name, "songLinks": []}}
                for song_list in anime_info["songLinks"].values():
                    for song in song_list:
                        anime[anime_id]["songLinks"].append(song["songId"])
                matched_animes.update(anime)
        if matched_animes:
            for anime_entry in matched_animes.values():
                for songId in anime_entry["songLinks"]:
                    songId = str(songId)
                    result = {}
                    result["animeName"] = anime_entry["animeName"]
                    result["songName"] = song_data[songId]["name"]
                    if song_data[songId]["songArtistId"]:
                        artistId = str(song_data[songId]["songArtistId"])
                        result["artistName"] = artist_data[artistId]["name"]
                    else:
                        groupId = str(song_data[songId]["songGroupId"])
                        result["artistName"] = group_data[groupId]["name"]
                    results.append(result)
        return results
    @commands.command(name="anisongdb", aliases=["anisong", "song"])
    async def anisongdb(self, ctx, *search_query):
        search_query = " ".join(search_query).strip()
        if not search_query:
            await ctx.send("Vui lòng nhập từ khóa tìm kiếm.")
            return

        results = self.azusong(self.anime_data, self.song_data, self.artist_data, self.group_data, search_query)
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