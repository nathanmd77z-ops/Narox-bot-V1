import os
import discord
from discord.ext import commands

FONDATEUR_ROLE_ID = int(os.getenv("FONDATEUR_ROLE_ID"))


async def safe_delete_command_message(ctx: commands.Context):
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass
    except discord.NotFound:
        pass
    except Exception:
        pass


class ClearCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def has_fondateur_role(self, member: discord.Member) -> bool:
        return any(role.id == FONDATEUR_ROLE_ID for role in member.roles)

    @commands.command(name="clear")
    async def clear(self, ctx: commands.Context, mode: str):
        await safe_delete_command_message(ctx)

        if ctx.guild is None or not isinstance(ctx.author, discord.Member):
            return await ctx.send("Cette commande doit être utilisée dans un serveur.", delete_after=5)

        if not isinstance(ctx.channel, discord.TextChannel):
            return await ctx.send("Cette commande fonctionne seulement dans un salon texte.", delete_after=5)

        if not self.has_fondateur_role(ctx.author):
            return await ctx.send("Seul le rôle Fondateur peut utiliser cette commande.", delete_after=5)

        bot_member = ctx.guild.me
        if bot_member is None or not bot_member.guild_permissions.manage_messages:
            return await ctx.send("Le bot n'a pas la permission de gérer les messages.", delete_after=5)

        channel = ctx.channel

        if mode.lower() == "all":
            info_msg = await ctx.send("Suppression de presque tous les messages récents du salon...")

            deleted_total = 0

            while True:
                deleted = await channel.purge(limit=100)
                if not deleted:
                    break
                deleted_total += len(deleted)
                if len(deleted) < 100:
                    break

            try:
                await info_msg.delete()
            except Exception:
                pass

            await channel.send(
                f"🧹 Salon nettoyé par {ctx.author.mention} — {deleted_total} message(s) supprimé(s).",
                delete_after=5
            )
            return

        if not mode.isdigit():
            return await ctx.send("Tu dois mettre un nombre ou `all`.", delete_after=5)

        amount = int(mode)

        if amount <= 0:
            return await ctx.send("Le nombre doit être supérieur à 0.", delete_after=5)

        if amount > 100:
            return await ctx.send(
                "Tu peux supprimer au maximum 100 messages d'un coup. Utilise `!clear all` pour vider le salon.",
                delete_after=5
            )

        deleted = await channel.purge(limit=amount)

        await channel.send(
            f"🧹 {ctx.author.mention} a supprimé {len(deleted)} message(s).",
            delete_after=5
        )

    @clear.error
    async def clear_error(self, ctx: commands.Context, error):
        await safe_delete_command_message(ctx)

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Utilisation : `!clear 10` ou `!clear all`", delete_after=5)
        else:
            await ctx.send("Erreur lors de la commande clear.", delete_after=5)


async def setup(bot: commands.Bot):
    await bot.add_cog(ClearCommands(bot))
