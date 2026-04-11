# Azunyan Bot

[Mời Azunyan vào server của bạn](https://discord.com/oauth2/authorize?client_id=1229243192478662697)

---

## Các lệnh hiện có

- **tiện ích**: ping (check trễ), avatar (lấy ảnh đại diện), sleep (tính chu kỳ ngủ), calculate (máy tính), dictionary (tra từ điển), qr (tạo mã QR bank), note (ghi chú nhanh), chat (echo tin nhắn).
- **giải trí**: ai (chat Gemini), whatanime (tìm anime từ ảnh), kanji (tra chữ Kanji), song (tìm nhạc anime), omikuji (xin xăm đầu năm), xinxam (100 quẻ Quan Thánh).
- **admin**: role (quản lý role), partyrank (tạo Party Rank).

---

## Cài đặt & Chạy

### Cách 1: Chạy từ source code
#### 1. Cài đặt `uv`
- **Windows (PowerShell):** 
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
- **Linux/macOS:** 
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Hoặc xem thêm tại [uv document](https://docs.astral.sh/uv/getting-started/installation)

### 2. Setup
```bash
git clone https://github.com/speedtest002/azunyan-bot.git
cd azunyan-bot
uv sync
cp .env.example .env
```
Điền đầy đủ thông tin vào file `.env`
### 3. Chạy Bot
```bash
uv run python main.py
```
Hoặc dùng docker compose (yêu cầu máy đã cài [docker](https://docs.docker.com/engine/install/))
```bash
docker-compose up -d --build
```

### Cách 2: Hoặc dùng image từ GitHub Registry

```bash
docker pull ghcr.io/speedtest002/azunyan-bot:latest
docker run -d --name azunyan \
    --env-file .env \
    ghcr.io/speedtest002/azunyan-bot:latest
```
