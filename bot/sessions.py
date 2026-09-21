from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiohttp
import discord
from discord import ui
from discord.ext import commands

from .panels import ACCENT, ASSET_DIR, FOOTER_IMAGE, PanelImage, add_asset_gallery, files_for


SESSION_ROLE_ID = 1516030618687897640
FLORIDA_EMOJI = "<:Florida:1546462024899502130>"
RED_DOT_EMOJI = "<:reddot:1550805381897519114>"
JOIN_URL = "https://erlc.gg/join?code=gXrqU"
ERLC_BASE_URL = "https://api.policeroleplay.community/v1"

SESSIONS_BANNER = PanelImage(ASSET_DIR / "sessions.png", "sessions.png")
SUBSCRIBERS_PATH = Path(__file__).with_name("data") / "session_subscribers.json"


@dataclass(frozen=True)
class SessionStats:
    server_name: str = "Florida Emergency Network"
    join_code: str = "gXrqU"
    owner: str = "FEN"
    players: int = 0
    max_players: int = 0
    staff: int = 0
    queue: int = 0
    online: bool = False
    updated_at: float = 0
    error: str | None = None

    @property
    def status_label(self) -> str:
        return "Online" if self.online else "Offline"

    @property
    def updated_label(self) -> str:
        if not self.updated_at:
            return "not checked yet"
        seconds = max(0, int(time.time() - self.updated_at))
        return f"updated {seconds} seconds ago"


def erlc_key() -> str | None:
    return os.getenv("ERLC_SERVER_KEY") or os.getenv("ERLC_API_KEY")


async def get_json(session: aiohttp.ClientSession, path: str, key: str) -> Any:
    async with session.get(f"{ERLC_BASE_URL}{path}", headers={"Server-Key": key}) as response:
        if response.status != 200:
            text = await response.text()
            raise RuntimeError(f"ER:LC API {path} returned {response.status}: {text[:120]}")
        return await response.json()


async def fetch_session_stats() -> SessionStats:
    key = erlc_key()
    if not key:
        return SessionStats(error="ERLC_SERVER_KEY is not set.")

    try:
        async with aiohttp.ClientSession() as session:
            server = await get_json(session, "/server", key)
            players_data = await get_json(session, "/server/players", key)
            try:
                queue_data = await get_json(session, "/server/queue", key)
            except RuntimeError:
                queue_data = []
    except Exception as exc:
        return SessionStats(updated_at=time.time(), error=str(exc))

    player_count = int(server.get("CurrentPlayers", 0) or 0)
    max_players = int(server.get("MaxPlayers", 0) or 0)
    staff_count = sum(1 for player in players_data if player.get("Permission") and player.get("Permission") != "Normal")
    queue_count = len(queue_data) if isinstance(queue_data, list) else 0

    return SessionStats(
        server_name=str(server.get("Name") or "Florida Emergency Network"),
        join_code=str(server.get("JoinKey") or "gXrqU"),
        owner=str(server.get("OwnerId") or "FEN"),
        players=player_count,
        max_players=max_players,
        staff=staff_count,
        queue=queue_count,
        online=player_count > 0,
        updated_at=time.time(),
    )


def load_subscribers() -> dict[str, list[int]]:
    if not SUBSCRIBERS_PATH.exists():
        return {}

    try:
        data = json.loads(SUBSCRIBERS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

    return {guild_id: [int(user_id) for user_id in users] for guild_id, users in data.items()}


def save_subscribers(data: dict[str, list[int]]) -> None:
    SUBSCRIBERS_PATH.parent.mkdir(exist_ok=True)
    SUBSCRIBERS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def add_subscriber(guild_id: int, user_id: int) -> None:
    data = load_subscribers()
    users = set(data.get(str(guild_id), []))
    users.add(user_id)
    data[str(guild_id)] = sorted(users)
    save_subscribers(data)


def remove_subscriber(guild_id: int, user_id: int) -> None:
    data = load_subscribers()
    users = [stored_id for stored_id in data.get(str(guild_id), []) if stored_id != user_id]
    if users:
        data[str(guild_id)] = users
    else:
        data.pop(str(guild_id), None)
    save_subscribers(data)


class SessionsPanelView(ui.LayoutView):
    def __init__(self, stats: SessionStats) -> None:
        super().__init__(timeout=None)
        self.stats = stats

        container = ui.Container(accent_color=ACCENT)
        add_asset_gallery(container, SESSIONS_BANNER)
        container.add_item(ui.TextDisplay(f"{FLORIDA_EMOJI} **Florida Emergency Network Sessions**"))
        container.add_item(ui.TextDisplay("> Florida Emergency Network sessions run around the clock aside from scheduled breaks. Hop in any time using the Quick-Join button below."))
        container.add_item(ui.Separator(visible=True))
        container.add_item(ui.TextDisplay(self.server_information_text()))
        container.add_item(ui.Separator(visible=True))
        container.add_item(ui.TextDisplay(self.server_statistics_text()))

        status_button = ui.Button(
            label=f"Status: {stats.status_label}",
            style=discord.ButtonStyle.secondary,
            disabled=True,
        )
        quick_join_button = ui.Button(label="Game Quick-Join", style=discord.ButtonStyle.link, url=JOIN_URL)
        notifications_button = ui.Button(
            label="Notifications",
            style=discord.ButtonStyle.secondary,
            custom_id="fen:sessions:notifications",
        )
        notifications_button.callback = self.enable_notifications
        container.add_item(ui.ActionRow(status_button, quick_join_button, notifications_button))
        add_asset_gallery(container, FOOTER_IMAGE)
        self.add_item(container)

    def server_information_text(self) -> str:
        return (
            "**ER:LC Server Information**\n"
            f"- **Server Name:** `{self.stats.server_name}`\n"
            f"- **Server Join Code:** `{self.stats.join_code}`\n"
            f"- **Server Owner:** `{self.stats.owner}`"
        )

    def server_statistics_text(self) -> str:
        max_players = f"/{self.stats.max_players}" if self.stats.max_players else ""
        detail = "No active session" if not self.stats.online else "Active session"
        if self.stats.error:
            detail = f"API unavailable: {self.stats.error}"

        return (
            "**Server Statistics**\n"
            f"- **Player Count:** `{self.stats.players}{max_players}`\n"
            f"- **Online Staff:** `{self.stats.staff}`\n"
            f"- **In Queue:** `{self.stats.queue}`\n\n"
            f"*{detail} - {self.stats.updated_label}*"
        )

    async def enable_notifications(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("This can only be used inside the server.", ephemeral=True)
            return

        role = interaction.guild.get_role(SESSION_ROLE_ID)
        if role is None:
            await interaction.response.send_message("I could not find the sessions notification role.", ephemeral=True)
            return

        try:
            await interaction.user.add_roles(role, reason="Enabled FEN session notifications")
            add_subscriber(interaction.guild.id, interaction.user.id)
        except discord.Forbidden:
            await interaction.response.send_message("I need permission to manage that role. Move my bot role above the notification role.", ephemeral=True)
            return

        await interaction.response.send_message(
            view=NotificationsEnabledServerView(),
            ephemeral=True,
        )

        try:
            await interaction.user.send(
                view=NotificationsEnabledDmView(interaction.guild.id),
                files=files_for(SESSIONS_BANNER),
            )
        except discord.Forbidden:
            pass


class NotificationsEnabledServerView(ui.LayoutView):
    def __init__(self) -> None:
        super().__init__(timeout=120)
        container = ui.Container(accent_color=discord.Colour.green())
        container.add_item(ui.TextDisplay("**Notifications enabled** - you'll be DM'd on session startups and low-player boosts."))
        self.add_item(container)


class NotificationsEnabledDmView(ui.LayoutView):
    def __init__(self, guild_id: int) -> None:
        super().__init__(timeout=600)

        container = ui.Container(accent_color=ACCENT)
        add_asset_gallery(container, SESSIONS_BANNER)
        container.add_item(ui.TextDisplay("## Notifications Enabled\nYou will now receive a DM whenever a session starts up or player spots open. Click the button below at any time to stop receiving them."))

        unsubscribe_button = ui.Button(
            label="Unsubscribe",
            style=discord.ButtonStyle.secondary,
            custom_id=f"fen:sessions:unsubscribe:{guild_id}",
        )
        unsubscribe_button.callback = self.unsubscribe
        container.add_item(ui.ActionRow(unsubscribe_button))
        self.add_item(container)

    async def unsubscribe(self, interaction: discord.Interaction) -> None:
        guild_id = int(str(interaction.data.get("custom_id", "")).rsplit(":", 1)[-1])
        remove_subscriber(guild_id, interaction.user.id)

        guild = interaction.client.get_guild(guild_id)
        if guild is not None:
            role = guild.get_role(SESSION_ROLE_ID)
            try:
                member = guild.get_member(interaction.user.id) or await guild.fetch_member(interaction.user.id)
                if role is not None:
                    await member.remove_roles(role, reason="Disabled FEN session notifications")
            except (discord.Forbidden, discord.NotFound):
                pass

        await interaction.response.send_message("Notifications disabled.", ephemeral=True)


class SessionOnlineDmView(ui.LayoutView):
    def __init__(self, stats: SessionStats) -> None:
        super().__init__(timeout=600)
        container = ui.Container(accent_color=discord.Colour.green())
        add_asset_gallery(container, SESSIONS_BANNER)
        container.add_item(ui.TextDisplay(f"## Session Online\nFlorida Emergency Network is now online with `{stats.players}` player(s)."))
        container.add_item(ui.ActionRow(ui.Button(label="Game Quick-Join", style=discord.ButtonStyle.link, url=JOIN_URL)))
        self.add_item(container)


async def send_sessions_panel(ctx: commands.Context) -> None:
    stats = await fetch_session_stats()
    await ctx.send(view=SessionsPanelView(stats), files=files_for(SESSIONS_BANNER, FOOTER_IMAGE))


async def monitor_session_startups(bot: commands.Bot) -> None:
    await bot.wait_until_ready()
    previous_online: bool | None = None

    while not bot.is_closed():
        stats = await fetch_session_stats()
        if previous_online is False and stats.online:
            subscribers = load_subscribers()
            for user_ids in subscribers.values():
                for user_id in user_ids:
                    try:
                        user = await bot.fetch_user(user_id)
                        await user.send(view=SessionOnlineDmView(stats), files=files_for(SESSIONS_BANNER))
                    except discord.HTTPException:
                        continue

        previous_online = stats.online
        await asyncio.sleep(60)
