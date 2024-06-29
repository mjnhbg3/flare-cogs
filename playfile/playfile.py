import io
import logging
import asyncio
import tempfile
from redbot.core import commands
import discord

log = logging.getLogger("red.playfile")

class PlayFile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.currently_playing = {}

    async def cleanup(self, ctx, temp_file_name=None):
        guild_id = ctx.guild.id
        if guild_id in self.currently_playing:
            del self.currently_playing[guild_id]
        
        if temp_file_name:
            try:
                temp_file_name.close()
                log.info(f"Temporary file closed")
            except Exception as e:
                log.error(f"Error closing temporary file: {str(e)}")

        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            log.info(f"Disconnected from voice channel in guild {guild_id}")

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
        guild_id = ctx.guild.id

        if guild_id in self.currently_playing:
            return await ctx.send("I'm already playing something in this server. Please wait for it to finish.")

        self.currently_playing[guild_id] = True

        try:
            # Download the attachment
            audio_file = io.BytesIO()
            await attachment.save(audio_file)
            audio_file.seek(0)
            log.info(f"File saved to memory")

            # Connect to voice channel
            if ctx.voice_client:
                await ctx.voice_client.move_to(voice_channel)
            else:
                await voice_channel.connect()

            # Play the file
            ctx.voice_client.play(discord.FFmpegPCMAudio(audio_file, pipe=True))
            await ctx.send(f"Now playing: {attachment.filename}")

            # Wait for the audio to finish
            while ctx.voice_client and ctx.voice_client.is_playing():
                await asyncio.sleep(0.1)

        except Exception as e:
            log.error(f"Error playing file: {str(e)}")
            await ctx.send(f"An error occurred while trying to play the file: {str(e)}")
        finally:
            await self.cleanup(ctx, audio_file)

    @commands.command()
    async def stopplayfile(self, ctx: commands.Context):
        """Stop the currently playing audio file and disconnect."""
        if ctx.voice_client:
            ctx.voice_client.stop()
        await self.cleanup(ctx)
        await ctx.send("Stopped playing file and disconnected from the voice channel.")

async def setup(bot):
    await bot.add_cog(PlayFile(bot))
