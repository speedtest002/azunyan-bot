import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime

def get_show_details(show_url):
    response = requests.get(show_url)

    if response.status_code != 200:
        print(f"Error fetching page: {response.status_code}")
        return None, None, None

    soup = BeautifulSoup(response.content, "html.parser")
    latest_links = []

    # Lấy các liên kết tập mới nhất
    tab_panes = soup.select("div.tab-pane")
    for tab in tab_panes:
        aria_label = tab.get("aria-label")
        if aria_label == "Nội dung tab Xem":
            continue
        episode_blocks = tab.select("div.watch-grid a")
        for block in episode_blocks:
            href = block.get("href")
            title = block.get("title")

            if href and title:
                # Chuyển đổi tiêu đề "Tập 01" thành số "1"
                episode_number = ''.join(filter(str.isdigit, title))
                if episode_number.isdigit():
                    episode_number = int(episode_number)
                latest_links.append({"source": aria_label, "episode": episode_number, "link": href})

    # Lấy mô tả từ thẻ <p> trong khối <div class="entry-content">
    description_tag = soup.select_one("div.entry-content p")
    description = description_tag.get_text(strip=True) if description_tag else None

    # Lấy thumbnail từ thẻ <meta property="og:image">
    thumbnail_tag = soup.select_one('meta[property="og:image"]')
    thumbnail = thumbnail_tag['content'] if thumbnail_tag else None

    return latest_links, description, thumbnail

def scrape_all_shows():
    url = "https://a4vf.net/lich-chieu/"
    response = requests.get(url)

    if response.status_code != 200:
        print(f"Error fetching page: {response.status_code}")
        return None

    soup = BeautifulSoup(response.content, "html.parser")

    shows = []
    movie_blocks = soup.select("div.big-airing-card")

    for block in movie_blocks:
        show_info = {}

        title_tag = block.select_one("div.title span")
        if title_tag:
            title = title_tag.get_text(strip=True)
            show_info["title"] = title

            time_tag = block.select_one("span.my-ep-countdown")
            if time_tag:
                show_time = time_tag.get("data-date")
                show_info["show_time"] = show_time

            episode_tag = block.select_one("div.staticTime div.episode span")
            if episode_tag:
                episode_text = episode_tag.get_text(strip=True)
                episode_number = ''.join(filter(str.isdigit, episode_text))
                if episode_number.isdigit():
                    show_info["lastest_episode"] = int(episode_number) - 1
                    #show_info["lastest_episode"] = str(episode_number)

            show_page_tag = block.select_one("a.coverImage")
            if show_page_tag:
                show_page_url = show_page_tag.get("href")
                latest_episode_links, description, thumbnail = get_show_details(show_page_url)
                show_info["latest_episode_links"] = latest_episode_links
                if description:
                    show_info["description"] = description
                if thumbnail:
                    show_info["thumbnail"] = thumbnail

            shows.append(show_info)

    # Sắp xếp danh sách shows theo bảng chữ cái theo title
    shows_sorted = sorted(shows, key=lambda x: x["title"])

    # Thêm thời gian quét và số lượng show vào dữ liệu
    data = {
        "scrape_time": str(datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))),
        "timestamp": round(datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).timestamp()),
        "total_shows": len(shows_sorted),
        "shows": shows_sorted
    }

    with open("/home/huyprokute002/github/shows.json", "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    return shows_sorted
start_time = time.time()
shows = scrape_all_shows()
end_time = time.time()

execution_time = end_time - start_time

if shows:
    print(f"Scraped {len(shows)} shows.")
else:
    print("Could not scrape any shows.")

print(f"Execution time: {execution_time:.4f} seconds")
