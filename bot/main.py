from __future__ import annotations

import os
from pathlib import Path

import discord
from discord.ext import commands

from .panels import DASHBOARD_BANNER, DashboardView, FOOTER_IMAGE, files_for


def load_env_file() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")


def validate_token(token: str) -> None:
    if token.startswith("Bot "):
        raise RuntimeError("DISCORD_TOKEN should be the raw bot token only. Remove the leading 'Bot ' prefix.")

    if len(token) < 50:
        raise RuntimeError(
            "DISCORD_TOKEN looks too short to be a Discord bot token. "
            "Use Developer Portal > Applications > your app > Bot > Reset Token, then paste that full token into .env."
        )


class FenBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        self.add_view(DashboardView())


bot = FenBot()


@bot.command(name="dash")
@commands.has_guild_permissions(manage_guild=True)
async def dash(ctx: commands.Context) -> None:
    await ctx.send(view=DashboardView(), files=files_for(DASHBOARD_BANNER, FOOTER_IMAGE))


def main() -> None:
    load_env_file()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is not set.")
    validate_token(token)

    bot.run(token)


if __name__ == "__main__":
    main()
