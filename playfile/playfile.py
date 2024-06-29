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
        self.currently_playing = {}

    async def cleanup(self, ctx, temp_file_name=None):
        guild_id = ctx.guild.id
        if guild_id in self.currently_playing:
            del self.currently_playing[guild_id]
        
        if temp_file_name:
            try:
                os.unlink(temp_file_name)
                log.info(f"Temporary file {temp_file_name} deleted")
            except Exception as e:
                log.error(f"Error deleting temporary file: {str(e)}")

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

        if ctx.voice_client:
            await ctx.voice_client.move_to(voice_channel)
        else:
            try:
                await voice_channel.connect()
            except discord.errors.ClientException:
                del self.currently_playing[guild_id]
                return await ctx.send("I couldn't connect to your voice channel. Please try again.")

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(attachment.filename)[1])
        temp_file_name = temp_file.name
        temp_file.close()

        try:
            # Download the attachment
            await attachment.save(temp_file_name)
            log.info(f"File saved to {temp_file_name}")

            # Use the Audio cog to play the file
            await self.audio.command_play(ctx, query=temp_file_name)

            # Wait for the song to finish
            while ctx.voice_client and ctx.voice_client.is_playing():
                await asyncio.sleep(1)

        except Exception as e:
            log.error(f"Error playing file: {str(e)}")
            await ctx.send(f"An error occurred while trying to play the file: {str(e)}")
        finally:
            await self.cleanup(ctx, temp_file_name)

    @commands.command()
    async def stop(self, ctx: commands.Context):
        """Stop the currently playing audio and disconnect."""
        if ctx.voice_client:
            ctx.voice_client.stop()
        await self.cleanup(ctx)
        await ctx.send("Stopped playing and disconnected from the voice channel.")

async def setup(bot):
    await bot.add_cog(PlayFile(bot))
