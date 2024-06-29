import io
import logging
import os
import tempfile
import subprocess
from redbot.core import commands
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate
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

        # Check if the Audio cog is loaded
        audio_cog = ctx.bot.get_cog("Audio")
        if audio_cog is None:
            return await ctx.send("The Audio cog is not loaded. Please load it to use this command.")

        try:
            # Create temporary files
            temp_audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            processed_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp_audio_file.close()
            processed_file.close()

            # Download the attachment to the temporary file
            await attachment.save(temp_audio_file.name)
            log.info("File saved to temporary file")

            # Process the file with FFmpeg to ensure mono output
            ffmpeg_command = [
                "ffmpeg", "-y", "-i", temp_audio_file.name, "-ac", "1", "-filter:a", "pan=mono|c0=0.5*c0+0.5*c1", processed_file.name
            ]
            subprocess.run(ffmpeg_command, check=True)
            log.info("File processed with FFmpeg to mono")

            # Use Audio cog to play the file
            await audio_cog.command_play(
                ctx, 
                query=processed_file.name
            )

            await ctx.send(f"Now playing: {attachment.filename}")
            log.info(f"Started playing: {attachment.filename}")

        except Exception as e:
            log.error(f"Error playing file: {str(e)}", exc_info=True)
            await ctx.send(f"An error occurred while trying to play the file: {str(e)}")

        finally:
            # Clean up temporary files
            try:
                if os.path.exists(temp_audio_file.name):
                    os.remove(temp_audio_file.name)
                    log.info("Temporary file deleted: " + temp_audio_file.name)
            except Exception as e:
                log.error(f"Error deleting temporary file: {temp_audio_file.name} - {str(e)}")

            try:
                if os.path.exists(processed_file.name):
                    os.remove(processed_file.name)
                    log.info("Processed file deleted: " + processed_file.name)
            except Exception as e:
                log.error(f"Error deleting processed file: {processed_file.name} - {str(e)}")

    @commands.command()
    async def stopplayfile(self, ctx: commands.Context):
        """Stop the currently playing audio file and disconnect."""
        audio_cog = ctx.bot.get_cog("Audio")
        if audio_cog is None:
            return await ctx.send("The Audio cog is not loaded.")

        await audio_cog.command_stop(ctx)
        await ctx.send("Stopped playing file and disconnected from the voice channel.")

async def setup(bot):
    await bot.add_cog(PlayFile(bot))

