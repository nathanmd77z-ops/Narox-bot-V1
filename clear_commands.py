import os
import discord
from discord import app_commands
from discord.ext import commands

GUILD_ID = int(os.getenv("GUILD_ID"))
FONDATEUR_ROLE_ID = int(os.getenv("FONDATEUR_ROLE_ID"))


class ClearCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def has_fondateur_role(self, member: discord.Member) -> bool:
        return any(role.id == FONDATEUR_ROLE_ID for role in member.roles)

    @app_commands.command(name="clear", description="Supprimer un nombre précis de messages ou tout le salon")
    @app_commands.describe(
        mode="Nombre de messages à supprimer ou 'all' pour tout vider"
    )
    async def clear(self, interaction: discord.Interaction, mode: str):
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "Cette commande doit être utilisée dans un serveur.",
                ephemeral=True
            )

        if not isinstance(interaction.channel, discord.TextChannel):
            return await interaction.response.send_message(
                "Cette commande fonctionne seulement dans un salon texte.",
                ephemeral=True
            )

        if not self.has_fondateur_role(interaction.user):
            return await interaction.response.send_message(
                "Seul le rôle Fondateur peut utiliser cette commande.",
                ephemeral=True
            )

        bot_member = interaction.guild.me
        if bot_member is None or not bot_member.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                "Le bot n'a pas la permission de gérer les messages.",
                ephemeral=True
            )

        channel = interaction.channel

        if mode.lower() == "all":
            await interaction.response.send_message(
                "Suppression de presque tous les messages récents du salon...",
                ephemeral=True
            )

            deleted_total = 0

            while True:
                deleted = await channel.purge(limit=100)
                if not deleted:
                    break
                deleted_total += len(deleted)
                if len(deleted) < 100:
                    break

            await channel.send(
                f"🧹 Salon nettoyé par {interaction.user.mention} — {deleted_total} message(s) supprimé(s).",
                delete_after=5
            )
            return

        if not mode.isdigit():
            return await interaction.response.send_message(
                "Tu dois mettre un nombre ou `all`.",
                ephemeral=True
            )

        amount = int(mode)

        if amount <= 0:
            return await interaction.response.send_message(
                "Le nombre doit être supérieur à 0.",
                ephemeral=True
            )

        if amount > 100:
            return await interaction.response.send_message(
                "Tu peux supprimer au maximum 100 messages d'un coup. Utilise `all` pour vider le salon.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        deleted = await channel.purge(limit=amount)

        await interaction.followup.send(
            f"🧹 {len(deleted)} message(s) supprimé(s).",
            ephemeral=True
        )

        try:
            await channel.send(
                f"🧹 {interaction.user.mention} a supprimé {len(deleted)} message(s).",
                delete_after=5
            )
        except discord.Forbidden:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(ClearCommands(bot), guild=discord.Object(id=GUILD_ID))
