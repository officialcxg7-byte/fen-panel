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

from .panels import (
    ACCENT,
    FOOTER_IMAGE,
    add_banner_gallery,
    fallback_files_for,
    load_json,
    refresh_dashboard_messages,
    write_json,
)


SESSION_NOTIFICATION_ROLE_ID = 1516030618687897640
SESSION_CONTROLLER_ROLE_ID = 1516029922332643490
GAME_EMOJI = "<:Game:1548607590982754334>"
JOIN_URL = "https://erlc.gg/join?code=gXrqU"
ERLC_BASE_URL = "https://api.erlc.gg/v1"

DATA_DIR = Path(__file__).with_name("data")
SUBSCRIBERS_PATH = DATA_DIR / "session_subscribers.json"
SESSION_MESSAGES_PATH = DATA_DIR / "session_messages.json"
SESSION_STATE_PATH = DATA_DIR / "session_state.json"


SESSION_ACTIONS = {
    "vote": {
        "label": "Session Vote",
        "title": "Session Vote",
        "body": "A session vote has started. React and show your interest so staff can determine whether to open the server.",
        "style": discord.ButtonStyle.primary,
    },
    "startup": {
        "label": "Session Startup",
        "title": "Session Startup",
        "body": "The in-game server is starting up. Join when ready and follow all session expectations.",
        "style": discord.ButtonStyle.success,
    },
    "shutdown": {
        "label": "Session Shutdown",
        "title": "Server Shutdown",
        "body": "The in-game server has now shut down. During this period, do not join the in-game server or moderation actions may be taken against you.\n\nAnother session will commence shortly, keep an eye on this channel for the next session. Thank you!",
        "style": discord.ButtonStyle.danger,
    },
    "low_players": {
        "label": "Low Players",
        "title": "Low Players",
        "body": "The session is currently low on players. Join up and help bring the roleplay back to life.",
        "style": discord.ButtonStyle.secondary,
    },
    "pause": {
        "label": "Session Pause",
        "title": "Session Paused",
        "body": "The session has been paused. Please hold all major scenes until staff reopen the session.",
        "style": discord.ButtonStyle.secondary,
    },
    "open": {
        "label": "Session Open",
        "title": "Session Open",
        "body": "The session is open. You may join the server and begin roleplay.",
        "style": discord.ButtonStyle.success,
    },
    "lock": {
        "label": "Session Lock",
        "title": "Session Locked",
        "body": "The session is now locked. Do not join unless staff instruct you to do so.",
        "style": discord.ButtonStyle.danger,
    },
    "full": {
        "label": "Session Full",
        "title": "Session Full",
        "body": "The server is currently full. Watch for queue openings and staff updates.",
        "style": discord.ButtonStyle.secondary,
    },
    "extension": {
        "label": "Session Extension",
        "title": "Session Extension",
        "body": "The session has been extended. Continue roleplaying and follow staff directions.",
        "style": discord.ButtonStyle.primary,
    },
}


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
        return f"<t:{int(self.updated_at)}:T> - <t:{int(self.updated_at)}:R>"


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
    write_json(SUBSCRIBERS_PATH, data)


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


def has_session_access(member: discord.Member) -> bool:
    return any(role.id == SESSION_CONTROLLER_ROLE_ID for role in member.roles)


def load_message_records() -> list[dict[str, int | None]]:
    data = load_json(SESSION_MESSAGES_PATH, [])
    return data if isinstance(data, list) else []


def remember_session_message(message: discord.Message) -> None:
    records = load_message_records()
    record = {"guild_id": message.guild.id if message.guild else None, "channel_id": message.channel.id, "message_id": message.id}
    records = [item for item in records if not (isinstance(item, dict) and item.get("message_id") == message.id)]
    records.append(record)
    write_json(SESSION_MESSAGES_PATH, records)


def current_session_state() -> dict[str, Any]:
    data = load_json(SESSION_STATE_PATH, {})
    return data if isinstance(data, dict) else {}


def save_session_state(action: str, actor: discord.abc.User, stats: SessionStats) -> dict[str, Any]:
    timestamp = int(time.time())
    config = SESSION_ACTIONS[action]
    state = {
        "action": action,
        "label": config["label"],
        "actor_id": actor.id,
        "actor_name": str(actor),
        "actor_mention": actor.mention,
        "timestamp": timestamp,
        "players": stats.players,
        "max_players": stats.max_players,
        "queue": stats.queue,
        "staff": stats.staff,
    }
    write_json(SESSION_STATE_PATH, state)
    return state


def update_session_live_stats(stats: SessionStats) -> None:
    state = current_session_state()
    state.update(
        {
            "players": stats.players,
            "max_players": stats.max_players,
            "queue": stats.queue,
            "staff": stats.staff,
            "stats_updated_at": int(stats.updated_at or time.time()),
        }
    )
    write_json(SESSION_STATE_PATH, state)


class SessionsPanelView(ui.LayoutView):
    def __init__(self, stats: SessionStats) -> None:
        super().__init__(timeout=None)
        self.stats = stats

        container = ui.Container(accent_color=ACCENT)
        add_banner_gallery(container, "sessions")
        container.add_item(ui.TextDisplay(f"{GAME_EMOJI} **Florida Emergency Network Sessions**"))
        container.add_item(ui.TextDisplay("> Session controls and live ER:LC information update automatically every 15 seconds."))
        container.add_item(ui.Separator(visible=True))
        container.add_item(ui.TextDisplay(self.server_information_text()))
        container.add_item(ui.Separator(visible=True))
        container.add_item(ui.TextDisplay(self.server_statistics_text()))
        container.add_item(ui.Separator(visible=True))
        container.add_item(ui.TextDisplay(self.latest_action_text()))
        container.add_item(ui.ActionRow(self.status_button(), self.quick_join_button(), self.notifications_button()))

        action_buttons = [self.action_button(key, config["label"], config["style"]) for key, config in SESSION_ACTIONS.items()]
        container.add_item(ui.ActionRow(*action_buttons[:5]))
        container.add_item(ui.ActionRow(*action_buttons[5:]))
        add_banner_gallery(container, "footer", FOOTER_IMAGE)
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

    @staticmethod
    def latest_action_text() -> str:
        state = current_session_state()
        if not state:
            return "**Latest Session Action**\nNo session action has been sent yet."
        timestamp = int(state.get("timestamp") or 0)
        when = f"<t:{timestamp}:F> - <t:{timestamp}:R>" if timestamp else "Timestamp unavailable"
        return (
            "**Latest Session Action**\n"
            f"- **Type:** {state.get('label', 'Session Update')}\n"
            f"- **User:** {state.get('actor_mention', 'Unknown')}\n"
            f"- **Timestamp:** {when}"
        )

    def status_button(self) -> ui.Button:
        return ui.Button(label=f"Status: {self.stats.status_label}", style=discord.ButtonStyle.secondary, disabled=True)

    @staticmethod
    def quick_join_button() -> ui.Button:
        return ui.Button(label="Game Quick-Join", style=discord.ButtonStyle.link, url=JOIN_URL)

    def notifications_button(self) -> ui.Button:
        button = ui.Button(label="Notifications", style=discord.ButtonStyle.secondary, custom_id="fen:sessions:notifications")
        button.callback = self.enable_notifications
        return button

    def action_button(self, action: str, label: str, style: discord.ButtonStyle) -> ui.Button:
        button = ui.Button(label=label, style=style, custom_id=f"fen:sessions:action:{action}")
        button.callback = self.send_session_action
        return button

    async def enable_notifications(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("This can only be used inside the server.", ephemeral=True)
            return

        role = interaction.guild.get_role(SESSION_NOTIFICATION_ROLE_ID)
        if role is None:
            await interaction.response.send_message("I could not find the sessions notification role.", ephemeral=True)
            return

        try:
            await interaction.user.add_roles(role, reason="Enabled FEN session notifications")
            add_subscriber(interaction.guild.id, interaction.user.id)
        except discord.Forbidden:
            await interaction.response.send_message("I need permission to manage that role. Move my bot role above the notification role.", ephemeral=True)
            return

        await interaction.response.send_message(view=NotificationsEnabledServerView(), ephemeral=True)

        try:
            await interaction.user.send(
                view=NotificationsEnabledDmView(interaction.guild.id),
                files=fallback_files_for(("sessions", None), ("footer", FOOTER_IMAGE)),
            )
        except discord.Forbidden:
            pass

    async def send_session_action(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("This can only be used inside the server.", ephemeral=True)
            return
        if not has_session_access(interaction.user):
            await interaction.response.send_message(f"Only <@&{SESSION_CONTROLLER_ROLE_ID}> can use session controls.", ephemeral=True)
            return

        action = str(interaction.data.get("custom_id", "")).rsplit(":", 1)[-1]
        if action not in SESSION_ACTIONS:
            await interaction.response.send_message("Unknown session action.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        stats = await fetch_session_stats()
        state = save_session_state(action, interaction.user, stats)
        await interaction.channel.send(
            view=SessionAnnouncementView(action, state, stats),
            files=fallback_files_for(("sessions", None), ("footer", FOOTER_IMAGE)),
        )
        await interaction.followup.send(f"{SESSION_ACTIONS[action]['label']} sent.", ephemeral=True)
        await refresh_session_messages(interaction.client)
        await refresh_dashboard_messages(interaction.client)


class SessionAnnouncementView(ui.LayoutView):
    def __init__(self, action: str, state: dict[str, Any], stats: SessionStats) -> None:
        super().__init__(timeout=None)
        config = SESSION_ACTIONS[action]
        timestamp = int(state.get("timestamp") or time.time())
        max_players = f"/{stats.max_players}" if stats.max_players else ""

        container = ui.Container(accent_color=ACCENT)
        add_banner_gallery(container, "sessions")
        container.add_item(ui.TextDisplay(f"## {config['title']}"))
        container.add_item(ui.TextDisplay(str(config["body"])))
        container.add_item(ui.TextDisplay(f"{stats.players}{max_players} players - {state['actor_mention']} - <t:{timestamp}:F>"))
        container.add_item(ui.ActionRow(self.quick_join_button(), self.notifications_button()))
        add_banner_gallery(container, "footer", FOOTER_IMAGE)
        self.add_item(container)

    @staticmethod
    def quick_join_button() -> ui.Button:
        return ui.Button(label="Game Quick-Join", style=discord.ButtonStyle.link, url=JOIN_URL)

    @staticmethod
    def notifications_button() -> ui.Button:
        return ui.Button(label="Notifications", style=discord.ButtonStyle.secondary, disabled=True)


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
        add_banner_gallery(container, "sessions")
        container.add_item(ui.TextDisplay("## Notifications Enabled\nYou will now receive a DM whenever a session starts up or player spots open. Click the button below at any time to stop receiving them."))

        unsubscribe_button = ui.Button(label="Unsubscribe", style=discord.ButtonStyle.secondary, custom_id=f"fen:sessions:unsubscribe:{guild_id}")
        unsubscribe_button.callback = self.unsubscribe
        container.add_item(ui.ActionRow(unsubscribe_button))
        self.add_item(container)

    async def unsubscribe(self, interaction: discord.Interaction) -> None:
        guild_id = int(str(interaction.data.get("custom_id", "")).rsplit(":", 1)[-1])
        remove_subscriber(guild_id, interaction.user.id)

        guild = interaction.client.get_guild(guild_id)
        if guild is not None:
            role = guild.get_role(SESSION_NOTIFICATION_ROLE_ID)
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
        add_banner_gallery(container, "sessions")
        container.add_item(ui.TextDisplay(f"## Session Online\nFlorida Emergency Network is now online with `{stats.players}` player(s)."))
        container.add_item(ui.ActionRow(ui.Button(label="Game Quick-Join", style=discord.ButtonStyle.link, url=JOIN_URL)))
        self.add_item(container)


async def send_sessions_panel(ctx: commands.Context) -> None:
    if not isinstance(ctx.author, discord.Member) or not has_session_access(ctx.author):
        await ctx.reply(f"Only <@&{SESSION_CONTROLLER_ROLE_ID}> can use session controls.", mention_author=False)
        return

    stats = await fetch_session_stats()
    message = await ctx.send(view=SessionsPanelView(stats), files=fallback_files_for(("sessions", None), ("footer", FOOTER_IMAGE)))
    remember_session_message(message)


async def refresh_session_messages(bot: commands.Bot) -> None:
    stats = await fetch_session_stats()
    kept: list[dict[str, int | None]] = []
    for item in load_message_records():
        if not isinstance(item, dict):
            continue
        try:
            channel = bot.get_channel(int(item["channel_id"])) or await bot.fetch_channel(int(item["channel_id"]))
            message = await channel.fetch_message(int(item["message_id"]))
            await message.edit(view=SessionsPanelView(stats))
            kept.append(item)
        except (discord.Forbidden, discord.NotFound):
            continue
        except discord.HTTPException:
            kept.append(item)
    write_json(SESSION_MESSAGES_PATH, kept)


async def monitor_session_startups(bot: commands.Bot) -> None:
    await bot.wait_until_ready()
    previous_online: bool | None = None

    while not bot.is_closed():
        stats = await fetch_session_stats()
        update_session_live_stats(stats)

        if previous_online is False and stats.online:
            subscribers = load_subscribers()
            for user_ids in subscribers.values():
                for user_id in user_ids:
                    try:
                        user = await bot.fetch_user(user_id)
                        await user.send(
                            view=SessionOnlineDmView(stats),
                            files=fallback_files_for(("sessions", None)),
                        )
                    except discord.HTTPException:
                        continue

        previous_online = stats.online
        await refresh_session_messages(bot)
        await refresh_dashboard_messages(bot)
        await asyncio.sleep(15)
