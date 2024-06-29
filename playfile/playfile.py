import io
import logging
import tempfile
import os
from redbot.core import commands
import discord
from discord.opus import Encoder as OpusEncoder

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
        temp_audio_file = None
        voice_client = None
        try:
            # Download the attachment to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{attachment.filename}", mode='wb') as temp_file:
                await attachment.save(temp_file.name)
                temp_audio_file = temp_file.name
                log.info(f"File saved to temporary file: {temp_audio_file}")

            # Connect to the voice channel
            voice_client = await voice_channel.connect()

            # Check if Opus is loaded
            if not discord.opus.is_loaded():
                log.warning("Opus is not loaded. Attempting to load...")
                if not discord.opus.load_opus('libopus'):
                    raise discord.opus.OpusNotLoaded("Opus library could not be loaded.")

            # Play the audio file using FFmpegPCMAudio with stereo output
            audio_source = discord.FFmpegPCMAudio(temp_audio_file, options='-ac 2')
            voice_client.play(audio_source)
            await ctx.send(f"Now playing: {attachment.filename}")
            log.info(f"Started playing: {attachment.filename}")

            # Wait for the audio to finish playing
            while voice_client.is_playing():
                await discord.asyncio.sleep(1)

        except discord.opus.OpusNotLoaded:
            log.error("Opus is not loaded and couldn't be loaded automatically. Please ensure Opus is installed correctly.")
            await ctx.send("An error occurred while trying to play the file. The audio library (Opus) is not properly installed.")
        except Exception as e:
            log.error(f"Error playing file: {str(e)}", exc_info=True)
            await ctx.send(f"An error occurred while trying to play the file: {str(e)}")
        finally:
            # Disconnect after playing or if an error occurred
            if voice_client and voice_client.is_connected():
                await voice_client.disconnect()

            # Clean up temporary file
            if temp_audio_file and os.path.exists(temp_audio_file):
                try:
                    # Wait a bit to ensure the file is no longer in use
                    await discord.asyncio.sleep(1)
                    os.remove(temp_audio_file)
                except Exception as e:
                    log.error(f"Error removing temporary file: {str(e)}", exc_info=True)
                    # If we can't delete it now, schedule it for deletion when the bot exits
                    try:
                        os.rename(temp_audio_file, temp_audio_file + '.to_delete')
                    except Exception:
                        pass

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
