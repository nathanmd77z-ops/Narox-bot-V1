import discord
from discord.ext import commands


async def safe_delete_command_message(ctx: commands.Context):
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass
    except discord.NotFound:
        pass
    except Exception:
        pass


class BanUnban(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Aucune raison fournie"):
        await safe_delete_command_message(ctx)

        if ctx.guild is None or not isinstance(ctx.author, discord.Member):
            return await ctx.send("Commande invalide.", delete_after=5)

        bot_member = ctx.guild.me
        if bot_member is None:
            return await ctx.send("Impossible de vérifier les permissions du bot.", delete_after=5)

        if not bot_member.guild_permissions.ban_members:
            return await ctx.send("Le bot n'a pas la permission de bannir des membres.", delete_after=5)

        if member.id == ctx.author.id:
            return await ctx.send("Tu ne peux pas te bannir toi-même.", delete_after=5)

        if member.id == self.bot.user.id:
            return await ctx.send("Je ne peux pas me bannir moi-même.", delete_after=5)

        if ctx.guild.owner_id == member.id:
            return await ctx.send("Impossible de bannir le propriétaire du serveur.", delete_after=5)

        if ctx.author.top_role <= member.top_role and ctx.guild.owner_id != ctx.author.id:
            return await ctx.send(
                "Tu ne peux pas bannir un membre qui a un rôle égal ou supérieur au tien.",
                delete_after=5
            )

        if bot_member.top_role <= member.top_role:
            return await ctx.send(
                "Je ne peux pas bannir ce membre car son rôle est égal ou supérieur au mien.",
                delete_after=5
            )

        try:
            try:
                await member.send(
                    f"Tu as été banni du serveur **{ctx.guild.name}**.\n"
                    f"**Raison :** {reason}"
                )
            except discord.Forbidden:
                pass

            await ctx.guild.ban(
                member,
                reason=f"{reason} | Ban par {ctx.author}",
                delete_message_days=0
            )

            embed = discord.Embed(
                title="🔨 Membre banni",
                color=discord.Color.red()
            )
            embed.add_field(name="Membre", value=f"{member} (`{member.id}`)", inline=False)
            embed.add_field(name="Modérateur", value=f"{ctx.author.mention}", inline=False)
            embed.add_field(name="Raison", value=reason, inline=False)

            await ctx.send(embed=embed, delete_after=10)

        except discord.Forbidden:
            await ctx.send("Je n'ai pas réussi à bannir ce membre.", delete_after=5)
        except Exception as e:
            await ctx.send(f"Erreur pendant le bannissement : `{e}`", delete_after=5)

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user_id: int, *, reason: str = "Aucune raison fournie"):
        await safe_delete_command_message(ctx)

        if ctx.guild is None or not isinstance(ctx.author, discord.Member):
            return await ctx.send("Commande invalide.", delete_after=5)

        bot_member = ctx.guild.me
        if bot_member is None:
            return await ctx.send("Impossible de vérifier les permissions du bot.", delete_after=5)

        if not bot_member.guild_permissions.ban_members:
            return await ctx.send("Le bot n'a pas la permission de débannir des membres.", delete_after=5)

        try:
            bans = [entry async for entry in ctx.guild.bans(limit=None)]
        except discord.Forbidden:
            return await ctx.send("Je n'ai pas la permission de voir les bannissements.", delete_after=5)

        banned_entry = None
        for entry in bans:
            if entry.user.id == user_id:
                banned_entry = entry
                break

        if banned_entry is None:
            return await ctx.send("Aucun utilisateur banni trouvé avec cet ID.", delete_after=5)

        try:
            await ctx.guild.unban(
                banned_entry.user,
                reason=f"{reason} | Unban par {ctx.author}"
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
            embed.add_field(name="Modérateur", value=f"{ctx.author.mention}", inline=False)
            embed.add_field(name="Raison", value=reason, inline=False)

            await ctx.send(embed=embed, delete_after=10)

        except discord.Forbidden:
            await ctx.send("Je n'ai pas réussi à débannir cet utilisateur.", delete_after=5)
        except Exception as e:
            await ctx.send(f"Erreur pendant le débannissement : `{e}`", delete_after=5)

    @ban.error
    async def ban_error(self, ctx: commands.Context, error):
        await safe_delete_command_message(ctx)

        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Tu n'as pas la permission de bannir des membres.", delete_after=5)
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("Membre introuvable.", delete_after=5)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Utilisation : `!ban @membre raison`", delete_after=5)
        else:
            await ctx.send("Erreur lors de la commande ban.", delete_after=5)

    @unban.error
    async def unban_error(self, ctx: commands.Context, error):
        await safe_delete_command_message(ctx)

        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Tu n'as pas la permission de débannir des membres.", delete_after=5)
        elif isinstance(error, commands.BadArgument):
            await ctx.send("L'ID fourni est invalide.", delete_after=5)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Utilisation : `!unban ID raison`", delete_after=5)
        else:
            await ctx.send("Erreur lors de la commande unban.", delete_after=5)


async def setup(bot: commands.Bot):
    await bot.add_cog(BanUnban(bot))
