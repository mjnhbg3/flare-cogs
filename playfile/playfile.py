from redbot.core import commands
from redbot.cogs.audio import Audio
import discord
import os
import asyncio
import tempfile
import logging

log = logging.getLogger("red.playfile")

class PlayFile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.audio = self.bot.get_cog("Audio")

    @commands.command()
    async def playfile(self, ctx: commands.Context):
        """Play an attached audio file in your voice channel."""
        if not ctx.message.attachments:
            return await ctx.send("Please attach an audio file to play.")

        attachment = ctx.message.attachments[0]
        if not any(attachment.filename.lower().endswith(ext) for ext in ['.mp3', '.wav', '.aac', '.flac']):
            return await ctx.send("Please attach a valid audio file (mp3, wav, aac, or flac).")

        if not ctx.author.voice:
            return await ctx.send("You need to be in a voice channel to use this command.")

        voice_channel = ctx.author.voice.channel

        if not ctx.voice_client:
            try:
                await voice_channel.connect()
            except discord.errors.ClientException:
                return await ctx.send("I couldn't connect to your voice channel. Please try again.")

        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(attachment.filename)[1]) as temp_file:
            try:
                # Download the attachment
                await attachment.save(temp_file.name)
                log.info(f"File saved to {temp_file.name}")

                # Use the Audio cog to play the file
                await self.audio.command_play(ctx, query=temp_file.name)
            except Exception as e:
                log.error(f"Error playing file: {str(e)}")
                await ctx.send(f"An error occurred while trying to play the file: {str(e)}")
            finally:
                # Clean up the temporary file
                await asyncio.sleep(2)  # Wait a bit to ensure the file is not in use
                os.unlink(temp_file.name)
                log.info(f"Temporary file {temp_file.name} deleted")

async def setup(bot):
    await bot.add_cog(PlayFile(bot))
