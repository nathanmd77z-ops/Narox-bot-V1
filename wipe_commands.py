import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

GUILD_ID = int(os.getenv("GUILD_ID"))
LEAD_ROLE_ID = int(os.getenv("LEAD_ROLE_ID"))
WIPE_CHANNEL_ID = int(os.getenv("WIPE_CHANNEL_ID"))

WIPE_ROLE_IDS = {
    int(os.getenv("WIPE_ROLE_1_ID")),
    int(os.getenv("WIPE_ROLE_2_ID")),
    int(os.getenv("WIPE_ROLE_3_ID")),
    int(os.getenv("WIPE_ROLE_4_ID")),
}


def has_role(member: discord.Member, role_id: int) -> bool:
    return any(role.id == role_id for role in member.roles)


def has_any_wipe_role(member: discord.Member) -> bool:
    return any(role.id in WIPE_ROLE_IDS for role in member.roles)


class WipeApproveView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Valider le Wipe",
        style=discord.ButtonStyle.danger,
        emoji="🧹",
        custom_id="wipe_approve_button"
    )
    async def approve_wipe(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "Commande invalide.",
                ephemeral=True
            )

        if not has_any_wipe_role(interaction.user):
            return await interaction.response.send_message(
                "Tu n'as pas la permission de valider ce wipe.",
                ephemeral=True
            )

        if not interaction.message or not interaction.message.embeds:
            return await interaction.response.send_message(
                "Impossible de retrouver les informations de la demande.",
                ephemeral=True
            )

        embed = interaction.message.embeds[0]

        unique_id = "Inconnu"
        reason = "Inconnue"
        requester_id = None
        requester_text = "Inconnu"

        for field in embed.fields:
            if field.name == "ID unique":
                unique_id = field.value
            elif field.name == "Raison":
                reason = field.value
            elif field.name == "Demandé par":
                requester_text = field.value
            elif field.name == "Requester ID":
                if field.value.isdigit():
                    requester_id = int(field.value)

        validated_embed = discord.Embed(
            title="✅ Wipe validé",
            color=discord.Color.green()
        )
        validated_embed.add_field(name="ID unique", value=unique_id, inline=False)
        validated_embed.add_field(name="Raison", value=reason, inline=False)
        validated_embed.add_field(name="Demandé par", value=requester_text, inline=False)
        validated_embed.add_field(name="Validé par", value=interaction.user.mention, inline=False)

        await interaction.message.edit(embed=validated_embed, view=None)

        await interaction.response.send_message(
            f"Wipe validé pour l'ID `{unique_id}`.",
            ephemeral=True
        )

        if requester_id:
            user_to_notify = interaction.client.get_user(requester_id)
            if user_to_notify is None:
                try:
                    user_to_notify = await interaction.client.fetch_user(requester_id)
                except Exception:
                    user_to_notify = None

            if user_to_notify:
                try:
                    await user_to_notify.send(
                        f"✅ Ta demande de wipe pour l'ID unique `{unique_id}` a été validée par {interaction.user}.\n"
                        f"Raison : {reason}"
                    )
                except discord.Forbidden:
                    pass


class WipeCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="wipe", description="Créer une demande de wipe")
    @app_commands.describe(
        unique_id="ID unique en jeu",
        raison="Raison du wipe"
    )
    async def wipe(self, interaction: discord.Interaction, unique_id: str, raison: str):
        if interaction.guild is None:
            return await interaction.response.send_message(
                "Cette commande doit être utilisée dans un serveur.",
                ephemeral=True
            )

        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "Impossible de vérifier tes permissions.",
                ephemeral=True
            )

        if not has_role(interaction.user, LEAD_ROLE_ID):
            return await interaction.response.send_message(
                "Seul le rôle Lead peut utiliser cette commande.",
                ephemeral=True
            )

        wipe_channel = interaction.guild.get_channel(WIPE_CHANNEL_ID)
        if not wipe_channel or not isinstance(wipe_channel, discord.TextChannel):
            return await interaction.response.send_message(
                "Le salon Wipe est introuvable.",
                ephemeral=True
            )

        role_mentions = " ".join(f"<@&{role_id}>" for role_id in WiPE_ROLE_IDS)

        embed = discord.Embed(
            title="🧹 Nouvelle demande de Wipe",
            color=discord.Color.orange()
        )
        embed.add_field(name="ID unique", value=unique_id, inline=False)
        embed.add_field(name="Raison", value=raison, inline=False)
        embed.add_field(name="Demandé par", value=interaction.user.mention, inline=False)
        embed.add_field(name="Requester ID", value=str(interaction.user.id), inline=False)

        await wipe_channel.send(
            content=role_mentions,
            embed=embed,
            view=WipeApproveView()
        )

        await interaction.response.send_message(
            f"Ta demande de wipe pour l'ID `{unique_id}` a été envoyée dans {wipe_channel.mention}.",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(WipeCommands(bot), guild=discord.Object(id=GUILD_ID))
