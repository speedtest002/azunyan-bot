import pytz
import re
from datetime import datetime, timedelta

def standardize_time_format(time_str: str) -> str:
    time_str = time_str.replace(" ", "").lower()
    time_str = re.sub(r"(\d+)h(\d+)", r"\1:\2", time_str)
    time_str = re.sub(r"(\d+)(am|pm)", r"\1 \2", time_str)
    if "am" not in time_str and "pm" not in time_str:
        time_str += " am"
    return time_str

def calculate_times(current_time: datetime, time_to_wakeup: str | None = None):
    sleep_cycle = timedelta(minutes=90)
    fall_asleep = timedelta(minutes=14)

    if time_to_wakeup:
        wakeup = datetime.strptime(standardize_time_format(time_to_wakeup), "%I:%M %p")
        wakeup = current_time.replace(hour=wakeup.hour, minute=wakeup.minute, second=0, microsecond=0)
        results = []
        for i in range(6, 2, -1):
            sleep_time = wakeup - (i * sleep_cycle) - fall_asleep
            results.append({
                "time": sleep_time.strftime("%I:%M %p"),
                "cycles": i,
                "hours": (i * sleep_cycle).total_seconds() / 3600,
            })
        return results, "sleep"
    else:
        adjusted = current_time + fall_asleep
        results = []
        for i in range(1, 7):
            wakeup_time = adjusted + i * sleep_cycle
            results.append({
                "time": wakeup_time.strftime("%I:%M %p"),
                "cycles": i,
                "hours": (i * sleep_cycle).total_seconds() / 3600,
            })
        return results, "wakeup"

def build_response(times, mode, wakeup_arg: str | None, current_time: datetime) -> str:
    gif = 'https://tenor.com/view/onimai-anime-sleep-mihari-oyama-gif-27609322'
    if mode == "wakeup":
        msg = f"Bây giờ là **{current_time.strftime('%I:%M %p')}**. Nếu bạn đi ngủ ngay bây giờ, bạn nên cố gắng thức dậy vào một trong những thời điểm sau:\n\n"
    else:
        msg = f"Nếu bạn muốn tỉnh giấc vào **{wakeup_arg}**, bạn nên cố gắng đi vào giấc ngủ vào một trong những thời điểm sau:\n\n"

    for entry in times:
        msg += f"⏰ **{entry['time']}** cho {entry['cycles']} chu kỳ - ngủ {entry['hours']:.1f} tiếng.\n"

    msg += "\nXin lưu ý rằng bạn nên đi ngủ vào những thời điểm này. Con người trung bình mất ~14 phút để đi vào giấc ngủ, vì vậy hãy lên kế hoạch cho phù hợp!\n\nChúc ngủ ngon! 😴"
    msg += f"\n![zzz]({gif})"
    return msg

UTC7 = pytz.timezone("Asia/Ho_Chi_Minh")