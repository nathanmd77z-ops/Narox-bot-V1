import os
import re
import json
import html
import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))

SUPPORT_ROLE_ID = int(os.getenv("SUPPORT_ROLE_ID"))
ACHAT_ROLE_ID = int(os.getenv("ACHAT_ROLE_ID"))
PARTENARIAT_ROLE_ID = int(os.getenv("PARTENARIAT_ROLE_ID"))
AUTRE_ROLE_ID = int(os.getenv("AUTRE_ROLE_ID"))

SUPPORT_CATEGORY_ID = int(os.getenv("SUPPORT_CATEGORY_ID"))
ACHAT_CATEGORY_ID = int(os.getenv("ACHAT_CATEGORY_ID"))
PARTENARIAT_CATEGORY_ID = int(os.getenv("PARTENARIAT_CATEGORY_ID"))
AUTRE_CATEGORY_ID = int(os.getenv("AUTRE_CATEGORY_ID"))

TICKET_TYPES = {
    "support": {
        "label": "PROBLEME EN JEUX",
        "emoji": "🛠️",
        "description": "Problème rencontré en jeux",
        "prefix": "probleme-jeux",
        "color": 0x3498DB,
        "role_id": SUPPORT_ROLE_ID,
        "category_id": SUPPORT_CATEGORY_ID,
    },
    "achat": {
        "label": "BOUTIQUE",
        "emoji": "💰",
        "description": "Question liée à la boutique",
        "prefix": "boutique",
        "color": 0x2ECC71,
        "role_id": ACHAT_ROLE_ID,
        "category_id": ACHAT_CATEGORY_ID,
    },
    "partenariat": {
        "label": "RC STAFF",
        "emoji": "🤝",
        "description": "Demande RC Staff",
        "prefix": "rc-staff",
        "color": 0x9B59B6,
        "role_id": PARTENARIAT_ROLE_ID,
        "category_id": PARTENARIAT_CATEGORY_ID,
    },
    "autre": {
        "label": "BUG",
        "emoji": "📩",
        "description": "Signaler un bug",
        "prefix": "bug",
        "color": 0xE67E22,
        "role_id": AUTRE_ROLE_ID,
        "category_id": AUTRE_CATEGORY_ID,
    }
}

DATA_DIR = "data"
TRANSCRIPTS_DIR = os.path.join(DATA_DIR, "transcripts")
TICKETS_FILE = os.path.join(DATA_DIR, "tickets.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)


def now_utc():
    return datetime.now(timezone.utc)


def format_dt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")


def sanitize_channel_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9\-]", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name[:95] if name else "ticket"


def load_tickets():
    if not os.path.exists(TICKETS_FILE):
        return {}
    try:
        with open(TICKETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_tickets(data):
    with open(TICKETS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def build_topic(owner_id: int, ticket_type: str, claimed_by: int | None = None):
    claimed = str(claimed_by) if claimed_by else "none"
    return f"ticket_owner:{owner_id}|type:{ticket_type}|claimed_by:{claimed}"


def extract_ticket_meta(channel: discord.TextChannel):
    data = {
        "owner_id": None,
        "ticket_type": None,
        "claimed_by": None
    }

    if not channel.topic:
        return data

    for part in channel.topic.split("|"):
        if part.startswith("ticket_owner:"):
            value = part.split(":", 1)[1]
            if value.isdigit():
                data["owner_id"] = int(value)

        elif part.startswith("type:"):
            data["ticket_type"] = part.split(":", 1)[1]

        elif part.startswith("claimed_by:"):
            value = part.split(":", 1)[1]
            if value.isdigit():
                data["claimed_by"] = int(value)
            else:
                data["claimed_by"] = None

    return data


def get_ticket_role(guild: discord.Guild, ticket_type: str):
    info = TICKET_TYPES.get(ticket_type)
    if not info:
        return None
    return guild.get_role(info["role_id"])


def is_staff_for_ticket(member: discord.Member, ticket_type: str):
    if ticket_type not in TICKET_TYPES:
        return False
    role_id = TICKET_TYPES[ticket_type]["role_id"]
    return any(role.id == role_id for role in member.roles)


async def send_log(guild: discord.Guild, embed: discord.Embed, file: discord.File = None):
    channel = guild.get_channel(LOG_CHANNEL_ID)
    if channel and isinstance(channel, discord.TextChannel):
        try:
            if file:
                await channel.send(embed=embed, file=file)
            else:
                await channel.send(embed=embed)
        except Exception as e:
            print(f"[LOG ERROR] {e}")


async def generate_transcript_html(channel: discord.TextChannel) -> str:
    rows = []

    async for message in channel.history(limit=None, oldest_first=True):
        author_name = html.escape(str(message.author))
        author_avatar = message.author.display_avatar.url
        content = html.escape(message.content or "").replace("\n", "<br>")
        created = format_dt(message.created_at)

        attachments_html = ""
        if message.attachments:
            attachment_items = []
            for attachment in message.attachments:
                name = html.escape(attachment.filename)
                url = html.escape(attachment.url)
                attachment_items.append(f'<li><a href="{url}" target="_blank">{name}</a></li>')
            attachments_html = f"<ul class='attachments'>{''.join(attachment_items)}</ul>"

        embeds_html = ""
        if message.embeds:
            emb_list = []
            for emb in message.embeds:
                title = html.escape(emb.title) if emb.title else ""
                desc = html.escape(emb.description) if emb.description else ""
                emb_list.append(
                    f"<div class='embed'><div class='embed-title'>{title}</div><div>{desc}</div></div>"
                )
            embeds_html = "".join(emb_list)

        rows.append(f"""
        <div class="msg">
            <img class="avatar" src="{author_avatar}" alt="avatar">
            <div class="msg-body">
                <div class="msg-meta">
                    <span class="author">{author_name}</span>
                    <span class="date">{created}</span>
                </div>
                <div class="content">{content}</div>
                {embeds_html}
                {attachments_html}
            </div>
        </div>
        """)

    html_doc = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Transcript {html.escape(channel.name)}</title>
<style>
body {{
    background: #0f1115;
    color: #eaeaea;
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 24px;
}}
.container {{
    max-width: 1100px;
    margin: 0 auto;
}}
h1 {{
    margin-bottom: 6px;
}}
.subtitle {{
    color: #a9b0bb;
    margin-bottom: 24px;
}}
.msg {{
    display: flex;
    gap: 14px;
    padding: 14px;
    border: 1px solid #2c313c;
    background: #181c23;
    border-radius: 12px;
    margin-bottom: 12px;
}}
.avatar {{
    width: 44px;
    height: 44px;
    border-radius: 50%;
}}
.msg-body {{
    flex: 1;
}}
.msg-meta {{
    margin-bottom: 6px;
}}
.author {{
    font-weight: bold;
    color: #ffffff;
    margin-right: 10px;
}}
.date {{
    color: #9ca3af;
    font-size: 13px;
}}
.content {{
    line-height: 1.6;
    white-space: pre-wrap;
}}
.embed {{
    margin-top: 10px;
    padding: 10px;
    background: #131720;
    border-left: 4px solid #5865F2;
    border-radius: 8px;
}}
.embed-title {{
    font-weight: bold;
    margin-bottom: 6px;
}}
.attachments {{
    margin-top: 10px;
}}
a {{
    color: #7ab7ff;
}}
</style>
</head>
<body>
    <div class="container">
        <h1>Transcript du ticket</h1>
        <div class="subtitle">Salon : #{html.escape(channel.name)}</div>
        {''.join(rows)}
    </div>
</body>
</html>
"""
    filename = f"{channel.name}-{int(now_utc().timestamp())}.html"
    path = os.path.join(TRANSCRIPTS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    return path


async def do_claim(interaction: discord.Interaction):
    guild = interaction.guild
    channel = interaction.channel

    if guild is None or not isinstance(channel, discord.TextChannel):
        return await interaction.response.send_message("Salon invalide.", ephemeral=True)

    meta = extract_ticket_meta(channel)
    ticket_type = meta["ticket_type"]

    if not meta["owner_id"]:
        return await interaction.response.send_message("Ce salon n'est pas un ticket.", ephemeral=True)

    if not is_staff_for_ticket(interaction.user, ticket_type):
        return await interaction.response.send_message("Tu n'as pas la permission de claim ce ticket.", ephemeral=True)

    if meta["claimed_by"] is not None:
        claimed_member = guild.get_member(meta["claimed_by"])
        return await interaction.response.send_message(
            f"Ticket déjà claim par {claimed_member.mention if claimed_member else meta['claimed_by']}.",
            ephemeral=True
        )

    await channel.edit(topic=build_topic(meta["owner_id"], meta["ticket_type"], interaction.user.id))

    embed = discord.Embed(
        title="Ticket claim",
        description=f"{interaction.user.mention} a pris ce ticket en charge.",
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed)

    log = discord.Embed(
        title="Ticket claim",
        description=f"{interaction.user.mention} a claim {channel.mention}",
        color=discord.Color.gold()
    )
    await send_log(guild, log)


async def do_unclaim(interaction: discord.Interaction):
    guild = interaction.guild
    channel = interaction.channel

    if guild is None or not isinstance(channel, discord.TextChannel):
        return await interaction.response.send_message("Salon invalide.", ephemeral=True)

    meta = extract_ticket_meta(channel)
    ticket_type = meta["ticket_type"]

    if not meta["owner_id"]:
        return await interaction.response.send_message("Ce salon n'est pas un ticket.", ephemeral=True)

    if not is_staff_for_ticket(interaction.user, ticket_type):
        return await interaction.response.send_message("Tu n'as pas la permission de unclaim ce ticket.", ephemeral=True)

    if meta["claimed_by"] is None:
        return await interaction.response.send_message("Ce ticket n'est pas claim.", ephemeral=True)

    if meta["claimed_by"] != interaction.user.id:
        return await interaction.response.send_message(
            "Seule la personne qui a claim peut faire unclaim.",
            ephemeral=True
        )

    await channel.edit(topic=build_topic(meta["owner_id"], meta["ticket_type"], None))

    embed = discord.Embed(
        title="Ticket unclaim",
        description=f"{interaction.user.mention} a libéré ce ticket.",
        color=discord.Color.light_grey()
    )
    await interaction.response.send_message(embed=embed)

    log = discord.Embed(
        title="Ticket unclaim",
        description=f"{interaction.user.mention} a unclaim {channel.mention}",
        color=discord.Color.light_grey()
    )
    await send_log(guild, log)


async def do_delete(interaction: discord.Interaction):
    guild = interaction.guild
    channel = interaction.channel

    if guild is None or not isinstance(channel, discord.TextChannel):
        return await interaction.response.send_message("Salon invalide.", ephemeral=True)

    meta = extract_ticket_meta(channel)
    if not meta["owner_id"]:
        return await interaction.response.send_message("Ce salon n'est pas un ticket.", ephemeral=True)

    ticket_type = meta["ticket_type"]
    is_owner = interaction.user.id == meta["owner_id"]
    is_staff = is_staff_for_ticket(interaction.user, ticket_type)

    if not (is_owner or is_staff):
        return await interaction.response.send_message(
            "Tu n'as pas la permission de supprimer ce ticket.",
            ephemeral=True
        )

    owner = guild.get_member(meta["owner_id"]) if meta["owner_id"] else None

    await interaction.response.send_message("Suppression du ticket en cours...")

    transcript_path = await generate_transcript_html(channel)
    transcript_file = discord.File(transcript_path, filename=os.path.basename(transcript_path))

    embed = discord.Embed(
        title="Ticket supprimé",
        description=f"{interaction.user.mention} a supprimé le ticket `{channel.name}`",
        color=discord.Color.red()
    )
    if owner:
        embed.add_field(name="Créé par", value=f"{owner} (`{owner.id}`)", inline=False)
    if ticket_type in TICKET_TYPES:
        embed.add_field(name="Catégorie", value=TICKET_TYPES[ticket_type]["label"], inline=True)

    claimed_member = guild.get_member(meta["claimed_by"]) if meta["claimed_by"] else None
    embed.add_field(
        name="Claim par",
        value=claimed_member.mention if claimed_member else "Personne",
        inline=True
    )

    await send_log(guild, embed, transcript_file)

    tickets_db = load_tickets()
    owner_key = str(meta["owner_id"]) if meta["owner_id"] else None
    if owner_key and owner_key in tickets_db:
        if tickets_db[owner_key].get("channel_id") == channel.id:
            del tickets_db[owner_key]
            save_tickets(tickets_db)

    await asyncio.sleep(2)
    await channel.delete()


class TicketReasonModal(discord.ui.Modal, title="Ouvrir un ticket"):
    reason = discord.ui.TextInput(
        label="Décris ta demande",
        placeholder="Explique ton problème ou ta demande...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    def __init__(self, ticket_key: str):
        super().__init__()
        self.ticket_key = ticket_key

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user

        if guild is None:
            return await interaction.response.send_message("Impossible ici.", ephemeral=True)

        ticket_data = TICKET_TYPES[self.ticket_key]
        ticket_role = get_ticket_role(guild, self.ticket_key)
        category = guild.get_channel(ticket_data["category_id"])

        if not category or not isinstance(category, discord.CategoryChannel):
            return await interaction.response.send_message(
                f"La catégorie Discord pour {ticket_data['label']} est introuvable.",
                ephemeral=True
            )

        tickets_db = load_tickets()
        user_key = str(user.id)

        if user_key in tickets_db:
            existing_channel_id = tickets_db[user_key].get("channel_id")
            existing_channel = guild.get_channel(existing_channel_id)
            if existing_channel:
                return await interaction.response.send_message(
                    f"Tu as déjà un ticket ouvert : {existing_channel.mention}",
                    ephemeral=True
                )
            else:
                del tickets_db[user_key]
                save_tickets(tickets_db)

        channel_name = sanitize_channel_name(f"{ticket_data['prefix']}-{user.name}")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True,
                read_message_history=True
            )
        }

        if ticket_role:
            overwrites[ticket_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True
            )

        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=build_topic(user.id, self.ticket_key, None)
        )

        tickets_db[user_key] = {
            "channel_id": channel.id,
            "ticket_type": self.ticket_key,
            "created_at": now_utc().isoformat()
        }
        save_tickets(tickets_db)

        embed = discord.Embed(
            title=f"{ticket_data['emoji']} Ticket {ticket_data['label']}",
            description=(
                f"Bienvenue {user.mention}\n\n"
                f"**Catégorie :** {ticket_data['label']}\n"
                f"**Raison :** {self.reason.value}\n\n"
                f"Un membre du staff concerné va te répondre."
            ),
            color=ticket_data["color"]
        )
        embed.add_field(name="Créé par", value=f"{user.mention} (`{user.id}`)", inline=False)
        embed.set_footer(text="Utilise les boutons ou les slash commands du ticket.")

        ping = f"{user.mention}"
        if ticket_role:
            ping += f" {ticket_role.mention}"

        await channel.send(
            content=ping,
            embed=embed,
            view=TicketManagementView()
        )

        log = discord.Embed(
            title="Nouveau ticket",
            description=f"Ticket créé : {channel.mention}",
            color=discord.Color.green()
        )
        log.add_field(name="Utilisateur", value=f"{user} (`{user.id}`)", inline=False)
        log.add_field(name="Catégorie", value=ticket_data["label"], inline=True)
        log.add_field(name="Salon", value=channel.name, inline=True)
        log.add_field(name="Raison", value=self.reason.value[:1024], inline=False)
        await send_log(guild, log)

        await interaction.response.send_message(
            f"Ton ticket a été créé : {channel.mention}",
            ephemeral=True
        )


class AddMemberModal(discord.ui.Modal, title="Ajouter un membre"):
    member_id = discord.ui.TextInput(
        label="ID du membre",
        placeholder="123456789012345678",
        required=True,
        max_length=25
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        channel = interaction.channel

        if guild is None or not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("Salon invalide.", ephemeral=True)

        meta = extract_ticket_meta(channel)
        if not meta["owner_id"]:
            return await interaction.response.send_message("Ce salon n'est pas un ticket.", ephemeral=True)

        if not self.member_id.value.isdigit():
            return await interaction.response.send_message("ID invalide.", ephemeral=True)

        member = guild.get_member(int(self.member_id.value))
        if member is None:
            try:
                member = await guild.fetch_member(int(self.member_id.value))
            except Exception:
                member = None

        if member is None:
            return await interaction.response.send_message("Membre introuvable.", ephemeral=True)

        await channel.set_permissions(
            member,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True
        )

        await interaction.response.send_message(f"{member.mention} a été ajouté au ticket.")

        embed = discord.Embed(
            title="Membre ajouté",
            description=f"{interaction.user.mention} a ajouté {member.mention} au ticket.",
            color=discord.Color.blurple()
        )
        await channel.send(embed=embed)


class RemoveMemberModal(discord.ui.Modal, title="Retirer un membre"):
    member_id = discord.ui.TextInput(
        label="ID du membre",
        placeholder="123456789012345678",
        required=True,
        max_length=25
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        channel = interaction.channel

        if guild is None or not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("Salon invalide.", ephemeral=True)

        meta = extract_ticket_meta(channel)
        if not meta["owner_id"]:
            return await interaction.response.send_message("Ce salon n'est pas un ticket.", ephemeral=True)

        if not self.member_id.value.isdigit():
            return await interaction.response.send_message("ID invalide.", ephemeral=True)

        member_id = int(self.member_id.value)

        if meta["owner_id"] == member_id:
            return await interaction.response.send_message(
                "Impossible de retirer le créateur du ticket.",
                ephemeral=True
            )

        member = guild.get_member(member_id)
        if member is None:
            try:
                member = await guild.fetch_member(member_id)
            except Exception:
                member = None

        if member is None:
            return await interaction.response.send_message("Membre introuvable.", ephemeral=True)

        await channel.set_permissions(member, overwrite=None)

        await interaction.response.send_message(f"{member.mention} a été retiré du ticket.")

        embed = discord.Embed(
            title="Membre retiré",
            description=f"{interaction.user.mention} a retiré {member.mention} du ticket.",
            color=discord.Color.orange()
        )
        await channel.send(embed=embed)


class RenameTicketModal(discord.ui.Modal, title="Renommer le ticket"):
    new_name = discord.ui.TextInput(
        label="Nouveau nom",
        placeholder="support-paiement",
        required=True,
        max_length=90
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.channel

        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("Salon invalide.", ephemeral=True)

        meta = extract_ticket_meta(channel)
        if not meta["owner_id"]:
            return await interaction.response.send_message("Ce salon n'est pas un ticket.", ephemeral=True)

        old_name = channel.name
        new_name = sanitize_channel_name(self.new_name.value)

        await channel.edit(name=new_name)
        await interaction.response.send_message(f"Ticket renommé : `{old_name}` → `{new_name}`")


class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = []
        for key, data in TICKET_TYPES.items():
            options.append(
                discord.SelectOption(
                    label=data["label"],
                    value=key,
                    description=data["description"],
                    emoji=data["emoji"]
                )
            )

        super().__init__(
            placeholder="Choisis une catégorie",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketReasonModal(self.values[0]))


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


class TicketManagementView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", emoji="🛄", style=discord.ButtonStyle.primary, custom_id="ticket_claim")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await do_claim(interaction)

    @discord.ui.button(label="Unclaim", emoji="📤", style=discord.ButtonStyle.secondary, custom_id="ticket_unclaim")
    async def unclaim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await do_unclaim(interaction)

    @discord.ui.button(label="Ajouter membre", emoji="➕", style=discord.ButtonStyle.secondary, custom_id="ticket_add_member")
    async def add_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("Salon invalide.", ephemeral=True)

        meta = extract_ticket_meta(channel)
        if not is_staff_for_ticket(interaction.user, meta["ticket_type"]):
            return await interaction.response.send_message(
                "Tu n'as pas la permission d'ajouter un membre.",
                ephemeral=True
            )

        await interaction.response.send_modal(AddMemberModal())

    @discord.ui.button(label="Retirer membre", emoji="➖", style=discord.ButtonStyle.secondary, custom_id="ticket_remove_member")
    async def remove_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("Salon invalide.", ephemeral=True)

        meta = extract_ticket_meta(channel)
        if not is_staff_for_ticket(interaction.user, meta["ticket_type"]):
            return await interaction.response.send_message(
                "Tu n'as pas la permission de retirer un membre.",
                ephemeral=True
            )

        await interaction.response.send_modal(RemoveMemberModal())

    @discord.ui.button(label="Renommer", emoji="✏️", style=discord.ButtonStyle.secondary, custom_id="ticket_rename")
    async def rename_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("Salon invalide.", ephemeral=True)

        meta = extract_ticket_meta(channel)
        if not is_staff_for_ticket(interaction.user, meta["ticket_type"]):
            return await interaction.response.send_message(
                "Tu n'as pas la permission de renommer ce ticket.",
                ephemeral=True
            )

        await interaction.response.send_modal(RenameTicketModal())

    @discord.ui.button(label="Supprimer", emoji="🗑️", style=discord.ButtonStyle.danger, custom_id="ticket_delete")
    async def delete_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await do_delete(interaction)


@bot.event
async def on_ready():
    try:
        try:
            await bot.load_extension("ban_unban")
        except commands.ExtensionAlreadyLoaded:
            pass
        except Exception as e:
            print(f"Erreur chargement ban_unban: {e}")

        try:
            await bot.load_extension("clear_commands")
        except commands.ExtensionAlreadyLoaded:
            pass
        except Exception as e:
            print(f"Erreur chargement clear_commands: {e}")

        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Connecté en tant que {bot.user}")
        print(f"{len(synced)} commande(s) synchronisée(s).")
    except Exception as e:
        print(f"Erreur sync: {e}")

    bot.add_view(TicketPanelView())
    bot.add_view(TicketManagementView())


@bot.tree.command(name="panel", description="Envoyer le panneau de tickets", guild=discord.Object(id=GUILD_ID))
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 Centre de tickets",
        description=(
            "Choisis la catégorie correspondant à ta demande.\n\n"
            "Un salon privé sera créé automatiquement."
        ),
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Support • Achat • Partenariat • Autre")

    await interaction.response.send_message(embed=embed, view=TicketPanelView())


@bot.tree.command(name="ticket-info", description="Voir les informations du ticket", guild=discord.Object(id=GUILD_ID))
async def ticket_info(interaction: discord.Interaction):
    guild = interaction.guild
    channel = interaction.channel

    if guild is None or not isinstance(channel, discord.TextChannel):
        return await interaction.response.send_message("Salon invalide.", ephemeral=True)

    meta = extract_ticket_meta(channel)
    if not meta["owner_id"]:
        return await interaction.response.send_message("Ce salon n'est pas un ticket.", ephemeral=True)

    owner = guild.get_member(meta["owner_id"])
    claimed = guild.get_member(meta["claimed_by"]) if meta["claimed_by"] else None
    ticket_type = meta["ticket_type"]
    role = get_ticket_role(guild, ticket_type)

    embed = discord.Embed(
        title="Informations du ticket",
        color=discord.Color.blurple()
    )
    embed.add_field(name="Salon", value=channel.mention, inline=False)
    embed.add_field(name="Créé par", value=owner.mention if owner else f"`{meta['owner_id']}`", inline=False)
    embed.add_field(
        name="Catégorie",
        value=TICKET_TYPES.get(ticket_type, {}).get("label", "Inconnue"),
        inline=True
    )
    embed.add_field(
        name="Claim par",
        value=claimed.mention if claimed else "Personne",
        inline=True
    )
    embed.add_field(
        name="Rôle staff",
        value=role.mention if role else "Non défini",
        inline=True
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="claim", description="Claim le ticket actuel", guild=discord.Object(id=GUILD_ID))
async def claim(interaction: discord.Interaction):
    await do_claim(interaction)


@bot.tree.command(name="unclaim", description="Libère le ticket actuel", guild=discord.Object(id=GUILD_ID))
async def unclaim(interaction: discord.Interaction):
    await do_unclaim(interaction)


@bot.tree.command(name="delete", description="Supprime le ticket actuel", guild=discord.Object(id=GUILD_ID))
async def delete(interaction: discord.Interaction):
    await do_delete(interaction)


@bot.tree.command(name="add", description="Ajouter un membre au ticket", guild=discord.Object(id=GUILD_ID))
async def add(interaction: discord.Interaction, membre: discord.Member):
    guild = interaction.guild
    channel = interaction.channel

    if guild is None or not isinstance(channel, discord.TextChannel):
        return await interaction.response.send_message("Salon invalide.", ephemeral=True)

    meta = extract_ticket_meta(channel)
    if not meta["owner_id"]:
        return await interaction.response.send_message("Ce salon n'est pas un ticket.", ephemeral=True)

    if not is_staff_for_ticket(interaction.user, meta["ticket_type"]):
        return await interaction.response.send_message(
            "Tu n'as pas la permission d'ajouter un membre.",
            ephemeral=True
        )

    await channel.set_permissions(
        membre,
        view_channel=True,
        send_messages=True,
        read_message_history=True,
        attach_files=True,
        embed_links=True
    )

    await interaction.response.send_message(f"{membre.mention} a été ajouté au ticket.")


@bot.tree.command(name="remove", description="Retirer un membre du ticket", guild=discord.Object(id=GUILD_ID))
async def remove(interaction: discord.Interaction, membre: discord.Member):
    guild = interaction.guild
    channel = interaction.channel

    if guild is None or not isinstance(channel, discord.TextChannel):
        return await interaction.response.send_message("Salon invalide.", ephemeral=True)

    meta = extract_ticket_meta(channel)
    if not meta["owner_id"]:
        return await interaction.response.send_message("Ce salon n'est pas un ticket.", ephemeral=True)

    if not is_staff_for_ticket(interaction.user, meta["ticket_type"]):
        return await interaction.response.send_message(
            "Tu n'as pas la permission de retirer un membre.",
            ephemeral=True
        )

    if membre.id == meta["owner_id"]:
        return await interaction.response.send_message(
            "Impossible de retirer le créateur du ticket.",
            ephemeral=True
        )

    await channel.set_permissions(membre, overwrite=None)
    await interaction.response.send_message(f"{membre.mention} a été retiré du ticket.")


@bot.tree.command(name="rename", description="Renommer le ticket actuel", guild=discord.Object(id=GUILD_ID))
async def rename(interaction: discord.Interaction, nom: str):
    channel = interaction.channel

    if not isinstance(channel, discord.TextChannel):
        return await interaction.response.send_message("Salon invalide.", ephemeral=True)

    meta = extract_ticket_meta(channel)
    if not meta["owner_id"]:
        return await interaction.response.send_message("Ce salon n'est pas un ticket.", ephemeral=True)

    if not is_staff_for_ticket(interaction.user, meta["ticket_type"]):
        return await interaction.response.send_message(
            "Tu n'as pas la permission de renommer ce ticket.",
            ephemeral=True
        )

    old_name = channel.name
    new_name = sanitize_channel_name(nom)
    await channel.edit(name=new_name)
    await interaction.response.send_message(f"Ticket renommé : `{old_name}` → `{new_name}`")


bot.run(TOKEN)
