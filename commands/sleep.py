from discord.ext import commands
from discord import *
import pytz
from datetime import datetime, timedelta
import re

class SleepCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    def standardize_time_format(self, time_str):
        # Remove spaces and convert to lowercase
        time_str = time_str.replace(" ", "").lower()
        
        # Replace 'h' with ':'
        time_str = re.sub(r'(\d+)h(\d+)', r'\1:\2', time_str)
        
        # Ensure there is a space before 'am' or 'pm'
        time_str = re.sub(r'(\d+)(am|pm)', r'\1 \2', time_str)
        
        # Default to 'am' if neither 'am' nor 'pm' is present
        if 'am' not in time_str and 'pm' not in time_str:
            time_str += ' am'
        
        return time_str

    def calculate_times(self, current_time, time_to_wakeup=None):
        # Thời gian của một chu kỳ giấc ngủ là 90 phút
        sleep_cycle_duration = timedelta(minutes=90)
        # Thời gian để đi vào giấc ngủ là 14 phút
        time_to_fall_asleep = timedelta(minutes=14)

        if time_to_wakeup:
            # Nếu cung cấp thời gian muốn thức dậy, tính toán thời gian đi ngủ
            wakeup_time = datetime.strptime(self.standardize_time_format(time_to_wakeup), '%I:%M %p')
            wakeup_time = current_time.replace(hour=wakeup_time.hour, minute=wakeup_time.minute, second=0, microsecond=0)
            sleep_times = []
            for i in range(6, 2, -1):
                sleep_time = wakeup_time - (i * sleep_cycle_duration) - time_to_fall_asleep
                sleep_duration = i * sleep_cycle_duration
                sleep_times.append({
                    'time': sleep_time.strftime('%I:%M %p'),
                    'cycles': i,
                    'hours': sleep_duration.total_seconds() / 3600
                })
            return sleep_times, "sleep"
        else:
            # Nếu không cung cấp thời gian muốn thức dậy, tính toán thời gian thức dậy
            adjusted_time = current_time + time_to_fall_asleep
            wakeup_times = []
            for i in range(1, 7):
                wakeup_time = adjusted_time + i * sleep_cycle_duration
                sleep_duration = i * sleep_cycle_duration
                wakeup_times.append({
                    'time': wakeup_time.strftime('%I:%M %p'),
                    'cycles': i,
                    'hours': sleep_duration.total_seconds() / 3600
                })
            return wakeup_times, "wakeup"
    #sleep
    @commands.hybrid_command(name = "sleep", aliases = ['ngu', 'slip'])
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def sleep(self, ctx, giờ_thức_dậy: str = None):
        """
        Tính toán thời gian đi ngủ

        Parameters:
        giờ_thức_dậy: None
            Thời gian mà bạn muốn thức dậy, định dạng: 12:00 AM
        """
        # Lấy thời gian hiện tại theo múi giờ UTC+7
        utc_plus_7 = pytz.timezone('Asia/Bangkok')
        current_time_utc_plus_7 = datetime.now(utc_plus_7)
        
        # Tính toán các thời điểm thức dậy hoặc đi ngủ
        try:
            times, mode = self.calculate_times(current_time_utc_plus_7, giờ_thức_dậy)
        except ValueError:
            await ctx.send("Định dạng thời gian không hợp lệ! Vui lòng sử dụng định dạng 12 giờ với AM/PM (ví dụ: 07:30 AM hoặc 07:30 PM).")
            return

        if mode == "wakeup":
            result_message = (
                f"Bây giờ là **{current_time_utc_plus_7.strftime('%I:%M %p')}**. Nếu bạn đi ngủ ngay bây giờ, bạn nên cố gắng thức dậy vào một trong những thời điểm sau:\n\n"
            )
            for entry in times:
                result_message += f"⏰ **{entry['time']}** cho {entry['cycles']} chu kỳ - ngủ {entry['hours']:.1f} tiếng.\n"
            
            result_message += "\nXin lưu ý rằng bạn nên đi ngủ vào những thời điểm này. Con người trung bình mất ~14 phút để đi vào giấc ngủ, vì vậy hãy lên kế hoạch cho phù hợp!\n\nChúc ngủ ngon! 😴"
        else:
            result_message = (
                f"Nếu bạn muốn tỉnh giấc vào **{giờ_thức_dậy}**, bạn nên cố gắng đi vào giấc ngủ vào một trong những thời điểm sau:\n\n"
            )
            for entry in times:
                result_message += f"⏰ **{entry['time']}** cho {entry['cycles']} chu kỳ - ngủ {entry['hours']:.1f} tiếng.\n"
            
            result_message += "\nXin lưu ý rằng bạn nên đi ngủ vào những thời điểm này. Con người trung bình mất ~14 phút để đi vào giấc ngủ, vì vậy hãy lên kế hoạch cho phù hợp!\n\nChúc ngủ ngon! 😴"

        # Gửi kết quả về kênh
        await ctx.send(result_message)
        
async def setup(bot):
    await bot.add_cog(SleepCommand(bot))