import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

AUTO_ROLE_ID = int(os.getenv("AUTO_ROLE_ID"))

class AutoRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.Cog.listener()
    async def on_member_join(self, member):

        role = member.guild.get_role(AUTO_ROLE_ID)

        if role is None:
            print("Role introuvable")
            return

        try:
            await member.add_roles(
                role,
                reason="Role automatique"
            )

            print(f"Role ajouté à {member}")

        except Exception as e:
            print("Erreur:", e)


async def setup(bot):
    await bot.add_cog(AutoRole(bot))
