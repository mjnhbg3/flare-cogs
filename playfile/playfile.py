import io
import logging
import asyncio
import traceback
from redbot.core import commands
import discord
from discord import opus

log = logging.getLogger("red.playfile")

class PlayFile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.currently_playing = {}
        self._load_opus()

    def _load_opus(self):
        if not opus.is_loaded():
            try:
                opus.load_opus('libopus-0.x86.dll')  # For Windows
            except OSError:
                try:
                    opus.load_opus('libopus-0.x64.dll')  # For Windows 64-bit
                except OSError:
                    try:
                        opus.load_opus('libopus.so.0')  # For Linux
                    except OSError:
                        log.error("Failed to load Opus library. Audio playback may not work.")

    async def cleanup(self, ctx, audio_file=None):
        guild_id = ctx.guild.id
        if guild_id in self.currently_playing:
            del self.currently_playing[guild_id]
        
        if audio_file:
            try:
                audio_file.close()
                log.info("Audio file closed")
            except Exception as e:
                log.error(f"Error closing audio file: {str(e)}")

        if ctx.voice_client:
            try:
                await ctx.voice_client.disconnect()
                log.info(f"Disconnected from voice channel in guild {guild_id}")
            except Exception as e:
                log.error(f"Error disconnecting from voice channel: {str(e)}")

    @commands.command()
    async def playfile(self, ctx: commands.Context):
        """Play an attached audio file in your voice channel."""
        if not opus.is_loaded():
            return await ctx.send("Opus library is not loaded. Audio playback is not available.")

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
        audio_file = io.BytesIO()

        try:
            await attachment.save(audio_file)
            audio_file.seek(0)
            log.info("File saved to memory")

            if ctx.voice_client:
                await ctx.voice_client.move_to(voice_channel)
            else:
                await voice_channel.connect()
            log.info("Connected to voice channel")

            def after_playing(error):
                if error:
                    log.error(f"Error after playing: {error}")
                asyncio.run_coroutine_threadsafe(self.cleanup(ctx, audio_file), self.bot.loop)

            source = discord.FFmpegPCMAudio(audio_file, pipe=True)
            ctx.voice_client.play(source, after=after_playing)
            await ctx.send(f"Now playing: {attachment.filename}")
            log.info(f"Started playing: {attachment.filename}")

            while ctx.voice_client and ctx.voice_client.is_playing():
                await asyncio.sleep(0.1)

        except Exception as e:
            log.error(f"Error playing file: {str(e)}")
            log.error(f"Traceback: {traceback.format_exc()}")
            await ctx.send(f"An error occurred while trying to play the file: {str(e)}")
        finally:
            if not ctx.voice_client or not ctx.voice_client.is_playing():
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
