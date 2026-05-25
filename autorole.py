import discord
from discord.ext import commands

AUTO_ROLE_ID = 1387990132669284352   # Mets ici l'ID du rôle

class AutoRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.Cog.listener()
    async def on_member_join(self, member):

        role = member.guild.get_role(AUTO_ROLE_ID)

        if role:
            try:
                await member.add_roles(role)
                print(f"Rôle ajouté à {member}")

            except Exception as e:
                print("Erreur :", e)


async def setup(bot):
    await bot.add_cog(AutoRole(bot))
