# this is the bot.py
import os
import random
import time
from urllib import request
import psutil
import requests
import uuid
import shutil
import asyncio
import traceback
from argparse import ArgumentParser
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from dotenv import load_dotenv
from io import BytesIO
from glob import glob
from PIL import Image

VERSION = "1.2.4_dev"
# Turn off in production!
DEBUG = True

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
COMMAND_PREFIX = '§'
lock = asyncio.Lock()  # Doesn't require event loop

process = psutil.Process(os.getpid())
start_time = datetime.now()

bot = commands.Bot(command_prefix=COMMAND_PREFIX, help_command=None,
                   description="an Open Source image distortion discord bot")
client = discord.Client()
bot.mutex = True  # mutex lock

embed_nofile_error = discord.Embed(
    description="No attachments", color=0xFF5555)
embed_nofile_error.set_author(name="[Error]", url="https://bjarne.dev/",
                              icon_url="https://static.wikia.nocookie.net/minecraft_gamepedia/images/9/9e/Barrier_%28held%29_JE2_BE2.png/revision/latest?cb=20200224220440")

embed_wrongfile_error = discord.Embed(
    description="Can't process this filetype. Only `.jpg`, `.jpeg` and `.png` are supported at the moment", color=0xFF5555)
embed_wrongfile_error.set_author(name="[Error]", url="https://bjarne.dev/",
                                 icon_url="https://static.wikia.nocookie.net/minecraft_gamepedia/images/9/9e/Barrier_%28held%29_JE2_BE2.png/revision/latest?cb=20200224220440")

argument_error = discord.Embed(
    description="Can't parse arguments", color=0xFF5555)
argument_error.set_author(name="[Error]", url="https://github.com/bj4rnee/DeformBot#command-arguments",
                          icon_url="https://static.wikia.nocookie.net/minecraft_gamepedia/images/9/9e/Barrier_%28held%29_JE2_BE2.png/revision/latest?cb=20200224220440")


# Semaphore methods
async def wait():  # aquire the lock
    while bot.mutex == False:
        await asyncio.sleep(1)
        print('.', end='')
        pass
    bot.mutex = False
    return bot.mutex


async def signal():  # free the lock
    bot.mutex = True
    return bot.mutex


def fetch_image(message):
    return


# args: sean_carving, noise, blur, contrast, swirl, implode, distort (conventional), invert, disable compression, grayscale
#       l=60,         n=0,   b=0,  c=0,      s=0,   o=0      d=0                     i=False,u=False,             g=False
# defaults values if flag is not set or otherwise specified
# TODO add args, better noise! -charcoal
def distort_image(fname, args):
    """function to distort an image using the magick library"""
    image = Image.open(os.path.join("raw", fname))
    imgdimens = image.width, image.height
    
    #build the command string
    build_str = " "
    l=60

    if ("u" not in args): # disable-compression flag
        build_str += " -define jpeg:dct-method=float -strip -interlace Plane -sampling-factor 4:2:0 -quality 85% " # -colorspace RGB
    if not any("l" in value for value in args): # if l-flag is not in args
        build_str += f" -liquid-rescale {l}x{l}%! -resize {imgdimens[0]}x{imgdimens[1]}\! "

    for e in args:
        if e.startswith('l'): #iterations flag
            cast_int = int(e[1:3])
            if cast_int >= 1 and cast_int <= 100:
                l = cast_int
                build_str += f" -liquid-rescale {l}x{l}%! -resize {imgdimens[0]}x{imgdimens[1]}\! "
            else: # no sean-carivng
                l = 0
            continue
        if e.startswith('n'): #noise-flag
            cast_int = int(e[1:4])
            if cast_int >= 1 and cast_int <= 100:
                cast_float = float(cast_int)/100
                build_str += f" +noise Gaussian -attenuate {cast_float} "
            continue
        if e.startswith('b'): #blur-flag
            cast_int = int(e[1:4])
            if cast_int >= 1 and cast_int <= 100:
                build_str += f" -blur 0x{cast_int} "
            continue
        if e.startswith('c'): #contrast-flag
            cast_int = int(e[1:5])
            if cast_int >= -100 and cast_int <= 100:
                build_str += f" -brightness-contrast 0x{cast_int} "
            continue
        if e.startswith('s'): #swirl-flag
            cast_int = int(e[1:5])
            if cast_int >= -360 and cast_int <= 360:
                build_str += f" -swirl {cast_int} "
            continue
        if e.startswith('o'): #implode-flag
            cast_int = int(e[1:4])
            if cast_int >= 1 and cast_int <= 100:
                cast_float = float(cast_int)/100
                build_str += f" -implode {cast_float} "
            continue
        if e.startswith('i'): #invert-flag
            build_str += f" -negate "
            continue
        if e.startswith('u'):
            continue
        if e.startswith('g'): #greyscale-flag
            build_str += f" -grayscale average "
            continue
        if DEBUG:
            print("[ERROR]: invalid argument '"+ e +"'")


    # added compression in command
    distortcmd = f"magick " + \
        os.path.join(
            "raw", f"{fname}") + build_str + os.path.join("results", f"{fname}")

    os.system(distortcmd)

    buf = BytesIO()
    buf.name = 'image.jpeg'

    # save file to /results/
    image = Image.open(f"results/{fname}")
    filetype = "JPEG" if fname.endswith(".jpg") else "PNG"
    image.save(buf, filetype)
    image.close()

    # backup file to /
    bkp_path = os.path.join("/home", "db_outputs")
    if os.path.exists(bkp_path):
        if DEBUG:
            print("[DEBUG]: free backup space: " + str(psutil.disk_usage(bkp_path).free) + "B")
        if psutil.disk_usage(bkp_path).free >= 	536870912:
            try:
                shutil.copy(f"results/{fname}", bkp_path)
                if DEBUG:
                    print(f"stored image: {fname}")
            except:
                traceback.print_exc()
        else:
            print("IOError: couldn't save the output file to db_outputs. Maybe check disk...?")
    buf.seek(0)
    return discord.File(os.path.join("results", f"{fname}"))


@bot.event
async def on_ready():
    if DEBUG:
        print("starting DeformBot " + VERSION + " ...")
    print(f'{bot.user} has connected to Discord!')
    # bot.remove_command('help')


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content == '§status':
        current_time = datetime.now()
        timestr = 'Uptime:\t{}\n'.format(current_time.replace(
            microsecond=0) - start_time.replace(microsecond=0))
        memstr = 'Memory:\t' + \
            str(round(process.memory_info().rss / 1024 ** 2, 2)) + 'MB\n'
        response = "```[Debug]\n" + timestr + \
            memstr + "Vers..:\t" + VERSION + "```"
        await message.channel.send(response)

    await bot.process_commands(message)


@bot.command(name='crashdump', help='Outputs last stacktrace', aliases=['c', 'cd', 'trace'])
async def crashdump(ctx):
    embed_crash = discord.Embed(title=':x: Event Error', color=0xFF5555)
    #embed_crash.add_field(name='Event', value=event)
    embed_crash.description = '```py\n%s\n```' % traceback.format_exc()
    embed_crash.timestamp = datetime.utcnow()
    await ctx.send(embed=embed_crash)


@bot.command(name='help', help='Shows usage info', aliases=['h', 'info', 'usage'])
async def help(ctx):
    rand_color = random.randint(0, 0xFFFFFF)
    helpstr_args = "\n\n**Arguments:**\n`l`:  Sean-Carving factor\n`s`:  swirl (degrees)\n`n`:  noise\n`b`:  blur\n`c`:  contrast (allows negative values)\n`o`:  implode\n`d`:  distortion effect\n`i`:  invert colors\n`g`:  grayscale image\n`u`:  disable compression\nAll arguments can be arbitrarily combined or left out.\nOnly integer values are accepted, I advise to play around with those values to find something that looks good."
    helpstr_usage = "\n\n**Usage:**\n`§deform [option0][value] [option1][value] ...`\nExamples:\n _§deform s35 n95 l45 c+40 b1_\n_§deform l50 s25 c+30 n70 g_"
    help_embed = discord.Embed(
        description="[Website](https://bjarne.dev)\n[Github](https://github.com/bj4rnee/DeformBot)\n[Twitter](https://twitter.com)\n\n**Commands:**\n`help`:  Shows this help message\n`deform`:  Distort an attached image\nYou can also react to an image with `🤖` to quickly deform it." + helpstr_args + helpstr_usage, color=rand_color)
    help_embed.set_author(name="Hi, I'm an Open Source image distortion discord bot!", url="https://bjarne.dev/",
                          icon_url="https://cdn.discordapp.com/avatars/971742838024978463/4e6548403fb46347b84de17fe31a45b9.webp")
    await ctx.send(embed=help_embed)


@bot.command(name='deform', help='deform an image', aliases=['d', 'D' 'distort'])
async def deform(ctx, *args):
    async with lock:
        # first delete the existing files
        for delf in os.listdir("raw"):
            if delf.endswith(".jpg"):
                os.remove(os.path.join("raw", delf))

        for delf2 in os.listdir("results"):
            if delf2.endswith(".jpg"):
                os.remove(os.path.join("results", delf2))

        msg = ctx.message  # msg with command in it
        reply_msg = None  # original msg which was replied to with command

        if msg.reference != None: # if msg is a reply
            reply_msg = await ctx.channel.fetch_message(msg.reference.message_id)
            msg = reply_msg

        try:
            url = msg.attachments[0].url
        except IndexError:
            await ctx.send(embed=embed_nofile_error)
            return
        else:
            if url[0:26] == "https://cdn.discordapp.com":
                if url[-4:].casefold() == ".jpg".casefold() or url[-4:].casefold() == ".png".casefold() or url[-5:].casefold() == ".jpeg".casefold():
                    r = requests.get(url, stream=True)
                    image_name = str(uuid.uuid4()) + '.jpg'  # generate uuid

                    with open(os.path.join("raw", image_name), 'wb') as out_file:
                        if DEBUG:
                            print("───────────" + image_name + "───────────")
                            print("saving image: " + image_name)
                        shutil.copyfileobj(r.raw, out_file)
                        #flush the buffer, this fixes ReadException
                        out_file.flush()

                        # distort the file
                        distorted_file = distort_image(image_name, args)

                        if DEBUG:
                            print("distorted image: " + image_name)
                            print("──────────────────────────────────────────────────────────────")
                        # send distorted image
                        if DEBUG:
                            await ctx.send("[Debug] Processed image: " + image_name + "\nargs=" + str(args), file=distorted_file)
                            return
                        await ctx.send(file=distorted_file)
                        return
                else:
                    await ctx.send(embed=embed_wrongfile_error)
                    return


@bot.event
async def on_reaction_add(reaction, user):  # if reaction is on a cached message
    if user != bot.user:
        if str(reaction.emoji) == "🤖":
            async with lock:
                # first delete the existing files
                for delf in os.listdir("raw"):
                    if delf.endswith(".jpg"):
                        os.remove(os.path.join("raw", delf))

                for delf2 in os.listdir("results"):
                    if delf2.endswith(".jpg"):
                        os.remove(os.path.join("results", delf2))

                # fetch and process the image
                msg = reaction.message
                ch = msg.channel
                try:
                    url = msg.attachments[0].url
                except IndexError:
                    if DEBUG:  # don't send errors on reaction
                        await ch.send(embed=embed_nofile_error)
                    return
                else:
                    if url[0:26] == "https://cdn.discordapp.com":
                        if url[-4:].casefold() == ".jpg".casefold() or url[-4:].casefold() == ".png".casefold() or url[-5:].casefold() == ".jpeg".casefold():
                            r = requests.get(url, stream=True)
                            image_name = str(uuid.uuid4()) + \
                                '.jpg'  # generate uuid

                            with open(os.path.join("raw", image_name), 'wb') as out_file:
                                if DEBUG:
                                    print("───────────" + image_name + "───────────")
                                    print("saving image: " + image_name)
                                shutil.copyfileobj(r.raw, out_file)
                                out_file.flush()

                                # unfortunately await can't be used here
                                distorted_file = distort_image(image_name, ())

                                if DEBUG:
                                    print("distorted image: " + image_name)
                                    print("──────────────────────────────────────────────────────────────")
                                # send distorted image
                                if DEBUG:
                                    await ch.send("[Debug] Processed image: " + image_name, file=distorted_file)
                                    return
                                await ch.send(file=distorted_file)
                                return
                        else:
                            if DEBUG:
                                await ch.send(embed=embed_wrongfile_error)
                            return
        else:
            return

bot.run(TOKEN)
