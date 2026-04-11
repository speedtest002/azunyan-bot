import random
import pytz
from datetime import datetime

def get_omikuji(user_name: str) -> str:
    list_omikuji = [
        "Đại Cát", "Trung Cát", "Tiểu Cát", "Cát", "Bán Cát", "Mạt Cát",
        "Mạt Tử Cát", "Hung", "Tiểu Hung", "Bán Hung", "Mạt Hung", "Đại Hung",
    ]
    year = datetime.now(pytz.timezone("Asia/Ho_Chi_Minh")).year
    random.seed(user_name + str(year))
    return random.choice(list_omikuji)