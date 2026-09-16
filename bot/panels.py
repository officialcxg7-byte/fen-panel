from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import discord
from discord import ui


ACCENT = discord.Colour.from_str("#58b9ff")
ASSET_DIR = Path(__file__).with_name("assets")


@dataclass(frozen=True)
class PanelImage:
    path: Path
    filename: str

    @property
    def media(self) -> str:
        return f"attachment://{self.filename}"

    def file(self) -> discord.File:
        return discord.File(self.path, filename=self.filename)


DISCORD_RULES_BANNER = PanelImage(ASSET_DIR / "discord_rules.png", "discord_rules.png")
INGAME_RULES_BANNER = PanelImage(ASSET_DIR / "ingame_rules.png", "ingame_rules.png")
BAN_APPEALS_BANNER = PanelImage(ASSET_DIR / "ban_appeals.png", "ban_appeals.png")
OFFICIAL_LINKS_BANNER = PanelImage(ASSET_DIR / "official_links.png", "official_links.png")
DASHBOARD_BANNER = PanelImage(ASSET_DIR / "dashboard.png", "dashboard.png")
FOOTER_IMAGE = PanelImage(ASSET_DIR / "footer.png", "footer.png")


@dataclass(frozen=True)
class Rule:
    number: str
    title: str
    body: str


DISCORD_RULES = [
    Rule("01", "Nicknames", "You are required to have your Roblox username as your Discord nickname. Example: `{callsign} | {Roblox Username}` - if you're part of a department, you must include your assigned callsign."),
    Rule("02", "Profanity", "Swearing is allowed, but only to a mild extent. Excessive, offensive, or harsh profanity is prohibited and may result in moderation."),
    Rule("03", "Advertising", "Please refrain from advertising other communities, servers, or services to FEN members. Partnerships may be requested through the appropriate channels. Failure to comply may result in a ban - this includes advertising through DMs."),
    Rule("04", "English", "FEN is an English-only server. This allows our staff to effectively moderate communications. Please do not use other languages within FEN communications."),
    Rule("05", "Drama", "Please refrain from causing or spreading drama within FEN. Personal disputes should be handled privately or outside of the server. Creating unnecessary drama may result in moderation."),
    Rule("06", "NSFW", "NSFW content is strictly prohibited. Do not send, post, or distribute any NSFW or inappropriate content. Failure to comply may result in an immediate blacklist and ban."),
    Rule("07", "Pinging", "Please refrain from pinging Directive+ members without a valid reason. Additionally, avoid pinging more than 4 members in the same message unless necessary."),
    Rule("08", "Respect", "Please treat all FEN members with respect. Hate speech, harassment, discrimination, bullying, or targeted disrespect is strictly prohibited and will be actively enforced regardless of permissions or rank."),
]


INGAME_RULES = [
    Rule("01", "Random Deathmatch (RDM)", "Killing another player without a valid roleplay reason is strictly prohibited. All shootings or attacks must have a legitimate and reasonable roleplay justification."),
    Rule("02", "Vehicle Deathmatch (VDM)", "Using a vehicle to intentionally injure or kill another player without a valid roleplay reason is prohibited. Vehicles must not be used as weapons unless the situation reasonably calls for it."),
    Rule("03", "Safezones", "Safezones are designated no-roleplay areas. No roleplay may be conducted inside a safezone, including attacking, arresting, or initiating scenes with other players. All spawn areas are considered safezones."),
    Rule("04", "Fail Roleplay (FRP)", "Actions that would be impossible or highly unrealistic in real life are prohibited. Mass FRP will be treated as a major offence. Suspects may not use an LEO vehicle for any part of a crime or force an officer to drive them. Any vehicle used for illegal roleplay must be a civilian vehicle."),
    Rule("05", "Unrealistic Driving", "Reckless or unrealistic driving is prohibited. Exceeding 125 MPH without a valid roleplay reason is not permitted. Driving on the wrong side of the road, using incorrect lanes, or travelling against traffic without a valid reason or priority is considered unrealistic driving."),
    Rule("06", "New Life Rule (NLR)", "After respawning, you are considered to have started a new life. You may not use information, grudges, knowledge, or intelligence obtained during your previous life. You must not return to a previous scene to continue roleplay after respawning."),
    Rule("07", "Fear Roleplay", "You are required to react realistically to dangerous situations. If a weapon is pointed at you, you must value your life and respond accordingly. You may not simply draw your weapon and shoot someone who already has you at gunpoint without a reasonable roleplay explanation."),
    Rule("08", "Evading Law Enforcement", "You may not flee from law enforcement without a valid roleplay reason. Valid reasons may include being wanted, operating a stolen vehicle or stolen plate, or possessing illegal items. Fleeing from a traffic stop when you have no reason to evade the officer is considered Fail Roleplay."),
    Rule("09", "Peacetimer", "You must respect the post-respawn peace timer. Players may not attack, pursue, or intentionally involve themselves in hostile roleplay during the active peace timer. Other players must also respect the protection provided by the peace timer."),
    Rule("10", "Realistic Avatars", "Your Roblox avatar must remain reasonably realistic and appropriate for roleplay. Trolling avatars, heavily cartoon-styled avatars, or avatars that clearly break immersion are not permitted during FEN sessions."),
    Rule("11", "Exploits & Tool Abuse", "Abusing ER:LC bugs, glitches, exploits, third-party tools, or chat-filter bypasses is strictly prohibited. Any attempt to gain an unfair advantage through external tools or game exploits may result in severe moderation."),
    Rule("12", "Staff Cooperation", "Players are required to follow reasonable instructions given by FEN staff. Do not intentionally disrupt staff scenes, investigations, or moderation. Impersonating staff, intentionally evading staff, or disrespecting staff may result in increased punishment."),
    Rule("13", "Intent to Roleplay", "All players are expected to actively participate in roleplay and contribute to the scene. NITRP (No Intent to Roleplay) is prohibited. LTAP (Leaving to Avoid Punishment) is also prohibited, including leaving a server or scene to avoid arrests, consequences, or ongoing roleplay."),
    Rule("14", "Organized Crime Group Limit", "Organized crime activities are limited to a maximum of three participants unless prior approval has been given. Larger groups must receive approval before beginning the activity. If instructed to stop an unauthorized organized crime scene, players must comply within five minutes."),
    Rule("15", "Priority Scene Limits", "Priority scenes are limited to a maximum of four participants and two vehicles. Civilians may not join RTO or take an officer's radio. Players participating in a priority scene may not simultaneously be part of an LEO, FD, or DOT team. All priority scenes must remain within the established limits."),
    Rule("16", "Additional Actors", "Only civilians who are present when a scene begins may participate in that scene. Players may not arrive at an active traffic stop, crash, arrest, or other scene solely to become involved. Scenes involving 4+ LEO are the exception, allowing news crews and other incident-based passive roleplay to attend when appropriate."),
]


def image_url(env_name: str) -> str | None:
    value = os.getenv(env_name, "").strip()
    return value or None


def add_gallery(container: ui.Container, media: str | None) -> None:
    if not media:
        return
    container.add_item(ui.MediaGallery(discord.MediaGalleryItem(media=media)))


def add_asset_gallery(container: ui.Container, image: PanelImage | None) -> None:
    add_gallery(container, image.media if image else None)


def files_for(*images: PanelImage | None) -> list[discord.File]:
    return [image.file() for image in images if image is not None]


def add_rule_blocks(container: ui.Container, rules: list[Rule]) -> None:
    for index, rule in enumerate(rules):
        container.add_item(ui.TextDisplay(f"**`{rule.number}`** **{rule.title}**\n{rule.body}"))
        if index != len(rules) - 1:
            container.add_item(ui.Separator(visible=True))


class DashboardView(ui.LayoutView):
    def __init__(self) -> None:
        super().__init__(timeout=None)

        container = ui.Container(accent_color=ACCENT)
        add_asset_gallery(container, DASHBOARD_BANNER)
        container.add_item(ui.TextDisplay("# Welcome to Florida Emergency Network\nRead the regulations before engaging in our community and tap Notifications to choose which pings you'd like to receive."))
        container.add_item(ui.Separator(visible=True))

        self._add_panel_row(container, "Discord Rules", "Conduct and guidelines across our Discord server. Read before posting.", "fen:dashboard:discord_rules", self.show_discord_rules)
        self._add_panel_row(container, "In-Game Rules", "Conduct and guidelines within our ER:LC sessions. Read before joining.", "fen:dashboard:ingame_rules", self.show_ingame_rules)
        self._add_panel_row(container, "Ban Appeals", "The official portal to submit a ban appeal for our Discord server or in-game network.", "fen:dashboard:ban_appeals", self.show_ban_appeals)
        self._add_panel_row(container, "Official Links", "The official directory for verified community links and social media channels.", "fen:dashboard:official_links", self.show_official_links)
        add_asset_gallery(container, FOOTER_IMAGE)

        self.add_item(container)

    @staticmethod
    def _add_panel_row(
        container: ui.Container,
        title: str,
        description: str,
        custom_id: str,
        callback: Callable[[discord.Interaction], object],
    ) -> None:
        button = ui.Button(label="View", style=discord.ButtonStyle.primary, custom_id=custom_id)
        button.callback = callback
        section = ui.Section(accessory=button)
        section.add_item(ui.TextDisplay(f"**{title}**\n{description}"))
        container.add_item(section)

    async def show_discord_rules(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            view=RulesView(
                "Discord Regulations",
                "You are required to follow these rules while using Florida Emergency Network (FEN) communications - failure to abide will result in moderation. These rules are subject to change at any time.",
                DISCORD_RULES,
                DISCORD_RULES_BANNER,
            ),
            files=files_for(DISCORD_RULES_BANNER, FOOTER_IMAGE),
            ephemeral=True,
        )

    async def show_ingame_rules(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(view=PaginatedRulesView(page=0), files=files_for(INGAME_RULES_BANNER, FOOTER_IMAGE), ephemeral=True)

    async def show_ban_appeals(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(view=WorkInProgressView("Ban Appeals", BAN_APPEALS_BANNER), files=files_for(BAN_APPEALS_BANNER, FOOTER_IMAGE), ephemeral=True)

    async def show_official_links(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(view=WorkInProgressView("Official Links", OFFICIAL_LINKS_BANNER), files=files_for(OFFICIAL_LINKS_BANNER, FOOTER_IMAGE), ephemeral=True)


class RulesView(ui.LayoutView):
    def __init__(self, title: str, intro: str, rules: list[Rule], banner: PanelImage | None = None) -> None:
        super().__init__(timeout=300)
        container = ui.Container(accent_color=ACCENT)
        add_asset_gallery(container, banner)
        container.add_item(ui.TextDisplay(f"# {title}\n*{intro}*"))
        container.add_item(ui.Separator(visible=True))
        add_rule_blocks(container, rules)
        add_asset_gallery(container, FOOTER_IMAGE)
        self.add_item(container)


class PaginatedRulesView(ui.LayoutView):
    PAGE_SIZE = 8

    def __init__(self, page: int) -> None:
        super().__init__(timeout=300)
        self.page = page
        self.max_page = (len(INGAME_RULES) - 1) // self.PAGE_SIZE
        self._build()

    def _build(self) -> None:
        start = self.page * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        rules = INGAME_RULES[start:end]

        container = ui.Container(accent_color=ACCENT)
        if self.page == 0:
            add_asset_gallery(container, INGAME_RULES_BANNER)
        container.add_item(ui.TextDisplay(f"# In-Game Regulations\n*You are required to follow these rules while participating in Florida Emergency Network (FEN) sessions - failure to abide will result in moderation at staff discretion. These rules are subject to change at any time.*\n\nPage {self.page + 1}/{self.max_page + 1}"))
        container.add_item(ui.Separator(visible=True))
        add_rule_blocks(container, rules)
        add_asset_gallery(container, FOOTER_IMAGE)

        previous_button = ui.Button(label="Previous", style=discord.ButtonStyle.secondary, custom_id=f"fen:ingame_rules:prev:{self.page}", disabled=self.page == 0)
        next_button = ui.Button(label="Next", style=discord.ButtonStyle.primary, custom_id=f"fen:ingame_rules:next:{self.page}", disabled=self.page == self.max_page)
        previous_button.callback = self.previous_page
        next_button.callback = self.next_page
        container.add_item(ui.ActionRow(previous_button, next_button))

        self.add_item(container)

    async def previous_page(self, interaction: discord.Interaction) -> None:
        page = max(0, self.page - 1)
        await interaction.response.edit_message(view=PaginatedRulesView(page), attachments=files_for(INGAME_RULES_BANNER if page == 0 else None, FOOTER_IMAGE))

    async def next_page(self, interaction: discord.Interaction) -> None:
        page = min(self.max_page, self.page + 1)
        await interaction.response.edit_message(view=PaginatedRulesView(page), attachments=files_for(INGAME_RULES_BANNER if page == 0 else None, FOOTER_IMAGE))


class WorkInProgressView(ui.LayoutView):
    def __init__(self, title: str, banner: PanelImage) -> None:
        super().__init__(timeout=300)
        container = ui.Container(accent_color=ACCENT)
        add_asset_gallery(container, banner)
        container.add_item(ui.TextDisplay(f"# {title}\n**Work in progress.**"))
        add_asset_gallery(container, FOOTER_IMAGE)
        self.add_item(container)
