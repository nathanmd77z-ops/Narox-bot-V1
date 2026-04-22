import os
import discord
from discord import app_commands
from discord.ext import commands

GUILD_ID = int(os.getenv("GUILD_ID"))


class BanUnban(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ban", description="Bannir un membre du serveur")
    @app_commands.describe(
        membre="Le membre à bannir",
        raison="Raison du bannissement"
    )
    async def ban(
        self,
        interaction: discord.Interaction,
        membre: discord.Member,
        raison: str = "Aucune raison fournie"
    ):
        if interaction.guild is None:
            return await interaction.response.send_message(
                "Cette commande doit être utilisée dans un serveur.",
                ephemeral=True
            )

        auteur = interaction.user
        bot_member = interaction.guild.me

        if not isinstance(auteur, discord.Member):
            return await interaction.response.send_message(
                "Impossible de vérifier tes permissions.",
                ephemeral=True
            )

        if bot_member is None:
            return await interaction.response.send_message(
                "Impossible de vérifier les permissions du bot.",
                ephemeral=True
            )

        if not auteur.guild_permissions.ban_members:
            return await interaction.response.send_message(
                "Tu n'as pas la permission de bannir des membres.",
                ephemeral=True
            )

        if not bot_member.guild_permissions.ban_members:
            return await interaction.response.send_message(
                "Le bot n'a pas la permission de bannir des membres.",
                ephemeral=True
            )

        if membre.id == auteur.id:
            return await interaction.response.send_message(
                "Tu ne peux pas te bannir toi-même.",
                ephemeral=True
            )

        if membre.id == self.bot.user.id:
            return await interaction.response.send_message(
                "Je ne peux pas me bannir moi-même.",
                ephemeral=True
            )

        if interaction.guild.owner_id == membre.id:
            return await interaction.response.send_message(
                "Impossible de bannir le propriétaire du serveur.",
                ephemeral=True
            )

        if auteur.top_role <= membre.top_role and interaction.guild.owner_id != auteur.id:
            return await interaction.response.send_message(
                "Tu ne peux pas bannir un membre qui a un rôle égal ou supérieur au tien.",
                ephemeral=True
            )

        if bot_member.top_role <= membre.top_role:
            return await interaction.response.send_message(
                "Je ne peux pas bannir ce membre car son rôle est égal ou supérieur au mien.",
                ephemeral=True
            )

        try:
            try:
                await membre.send(
                    f"Tu as été banni du serveur **{interaction.guild.name}**.\n"
                    f"**Raison :** {raison}"
                )
            except discord.Forbidden:
                pass

            await interaction.guild.ban(
                membre,
                reason=f"{raison} | Ban par {auteur}",
                delete_message_days=0
            )

            embed = discord.Embed(
                title="🔨 Membre banni",
                color=discord.Color.red()
            )
            embed.add_field(name="Membre", value=f"{membre} (`{membre.id}`)", inline=False)
            embed.add_field(name="Modérateur", value=f"{auteur.mention}", inline=False)
            embed.add_field(name="Raison", value=raison, inline=False)

            await interaction.response.send_message(embed=embed)

        except discord.Forbidden:
            await interaction.response.send_message(
                "Je n'ai pas réussi à bannir ce membre.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"Erreur pendant le bannissement : `{e}`",
                ephemeral=True
            )

    @app_commands.command(name="unban", description="Débannir un utilisateur via son ID")
    @app_commands.describe(
        user_id="ID de l'utilisateur à débannir",
        raison="Raison du débannissement"
    )
    async def unban(
        self,
        interaction: discord.Interaction,
        user_id: str,
        raison: str = "Aucune raison fournie"
    ):
        if interaction.guild is None:
            return await interaction.response.send_message(
                "Cette commande doit être utilisée dans un serveur.",
                ephemeral=True
            )

        auteur = interaction.user
        bot_member = interaction.guild.me

        if not isinstance(auteur, discord.Member):
            return await interaction.response.send_message(
                "Impossible de vérifier tes permissions.",
                ephemeral=True
            )

        if bot_member is None:
            return await interaction.response.send_message(
                "Impossible de vérifier les permissions du bot.",
                ephemeral=True
            )

        if not auteur.guild_permissions.ban_members:
            return await interaction.response.send_message(
                "Tu n'as pas la permission de débannir des membres.",
                ephemeral=True
            )

        if not bot_member.guild_permissions.ban_members:
            return await interaction.response.send_message(
                "Le bot n'a pas la permission de débannir des membres.",
                ephemeral=True
            )

        if not user_id.isdigit():
            return await interaction.response.send_message(
                "L'ID utilisateur est invalide.",
                ephemeral=True
            )

        target_id = int(user_id)

        try:
            bans = [entry async for entry in interaction.guild.bans(limit=None)]
        except discord.Forbidden:
            return await interaction.response.send_message(
                "Je n'ai pas la permission de voir les bannissements.",
                ephemeral=True
            )

        banned_entry = None
        for entry in bans:
            if entry.user.id == target_id:
                banned_entry = entry
                break

        if banned_entry is None:
            return await interaction.response.send_message(
                "Aucun utilisateur banni trouvé avec cet ID.",
                ephemeral=True
            )

        try:
            await interaction.guild.unban(
                banned_entry.user,
                reason=f"{raison} | Unban par {auteur}"
            )

            embed = discord.Embed(
                title="✅ Membre débanni",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Utilisateur",
                value=f"{banned_entry.user} (`{banned_entry.user.id}`)",
                inline=False
            )
            embed.add_field(name="Modérateur", value=f"{auteur.mention}", inline=False)
            embed.add_field(name="Raison", value=raison, inline=False)

            await interaction.response.send_message(embed=embed)

        except discord.Forbidden:
            await interaction.response.send_message(
                "Je n'ai pas réussi à débannir cet utilisateur.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"Erreur pendant le débannissement : `{e}`",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(BanUnban(bot), guild=discord.Object(id=GUILD_ID))
