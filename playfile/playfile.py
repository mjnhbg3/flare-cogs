import io
import logging
import tempfile
import os
from redbot.core import commands
import discord

log = logging.getLogger("red.playfile")
ALLOWED_EXTENSIONS = {"mp3", "wav", "ogg"}

def is_allowed_by_whitelist(filename: str) -> bool:
    return filename.split('.')[-1].lower() in ALLOWED_EXTENSIONS

class PlayFile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete."""
        return

    @commands.command()
    async def playfile(self, ctx: commands.Context):
        """Play an attached audio file in your voice channel."""
        if not ctx.message.attachments:
            return await ctx.send("Please attach an audio file to play.")
        
        attachment = ctx.message.attachments[0]
        if not is_allowed_by_whitelist(attachment.filename):
            return await ctx.send("The file type is not allowed. Please attach a valid audio file.")
        
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send("You need to be in a voice channel to use this command.")
        
        voice_channel = ctx.author.voice.channel
        
        try:
            # Download the attachment to a BytesIO object
            file_bytes = io.BytesIO()
            await attachment.save(file_bytes)
            file_bytes.seek(0)

            # Connect to the voice channel
            voice_client = await voice_channel.connect()

            # Play the audio file
            audio_source = discord.FFmpegPCMAudio(file_bytes.read(), pipe=True)
            voice_client.play(audio_source)
            
            await ctx.send(f"Now playing: {attachment.filename}")
            log.info(f"Started playing: {attachment.filename}")

            # Wait for the audio to finish playing
            while voice_client.is_playing():
                await discord.asyncio.sleep(1)

            # Disconnect after playing
            await voice_client.disconnect()

        except Exception as e:
            log.error(f"Error playing file: {str(e)}", exc_info=True)
            await ctx.send(f"An error occurred while trying to play the file: {str(e)}")
        finally:
            # Ensure voice client is disconnected
            if ctx.voice_client:
                await ctx.voice_client.disconnect()

    @commands.command()
    async def stopplayfile(self, ctx: commands.Context):
        """Stop the currently playing audio file and disconnect."""
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("Stopped playing file and disconnected from the voice channel.")
        else:
            await ctx.send("I'm not currently in a voice channel.")

async def setup(bot):
    await bot.add_cog(PlayFile(bot))
