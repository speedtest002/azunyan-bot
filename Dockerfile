FROM python:3.13
WORKDIR /app
COPY . .
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN uv pip install --system --no-cache -r requirements.txt
CMD ["python", "bot.py"]
