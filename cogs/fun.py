import os, sys, discord, random, asyncio
from discord.ext import commands

if not os.path.isfile("config.py"):
    sys.exit("'config.py' not found! Please add it and try again.")
else:
    import config

class Fun(commands.Cog, name="fun"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="dick")
    async def dick(self, context, member: discord.Member = None):
        """
        Get the dick's length of a user or yourself.
        """
        if not member:
            member = context.author
        length = random.randrange(15)
        embed = discord.Embed(description=f"8{'='*length}D", color=config.main_color)
        embed.set_author(name=f"{member.display_name}'s Dick", icon_url=member.avatar_url)
        await context.send(embed=embed)

def setup(bot):
    bot.add_cog(Fun(bot))