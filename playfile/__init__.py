from .playfile import PlayFile

async def setup(bot):
    await bot.add_cog(PlayFile(bot))
