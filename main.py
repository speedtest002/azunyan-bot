"""main.py — Entry point của azunyan-bot (hikari edition)."""
from core.bot import create_bot


if __name__ == "__main__":
    bot = create_bot()
    bot.run()
