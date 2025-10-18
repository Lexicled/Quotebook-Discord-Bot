import discord
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import random
import json
import os
import sys
import uuid

# Constants
FONT_SIZE = 50
IMAGE_FORMAT = ".jpg"
WIDTH = 960
HEIGHT = 540
PREFIX = "qb"
PATH_TO_WORKING_DIR = os.path.dirname(os.path.realpath(__file__)) + "/"

# Utils
def GetErrorMessage(format: str) -> str:
    return f"you lowkey fucked up using this bot, it should look like: `{format}`"

def GetSuccessMessage() -> str:
    return "done"

def TextWrap(text, font, max_width):
        """Wrap text base on specified width. 
        This is to enable text of width more than the image width to be display
        nicely.
        @params:
            text: str
                text to wrap
            font: obj
                font of the text
            max_width: int
                width to split the text with
        @return
            lines: list[str]
                list of sub-strings
        """
        lines = []
        
        # If the text width is smaller than the image width, then no need to split
        # just add it to the line list and return
        if GetTextDim(text, font)[0] <= max_width:
            lines.append(text)
        else:
            #split the line by spaces to get words
            words = text.split(' ')
            i = 0
            # append every word to a line while its width is shorter than the image width
            while i < len(words):
                line = ''
                while i < len(words) and GetTextDim(line + words[i], font)[0] <= max_width:
                    line = line + words[i]+ " "
                    i += 1
                if not line:
                    line = words[i]
                    i += 1
                lines.append(line)
        return lines

def GetTextDim(text_string, font):
    ascent, descent = font.getmetrics()

    mask = font.getmask(text_string)
    bbox = mask.getbbox()
    if bbox is None:
        # empty/whitespace line: width 0, use ascent+descent as line height
        return (0, ascent + descent)

    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1] + descent

    return (text_width, text_height)

def GetMaxLineWidth(lines: list[str], font: ImageFont) -> int:
    maxWidth = 0
    for line in lines:
        w = GetTextDim(line, font)[0]
        if (w > maxWidth): maxWidth = w
    return maxWidth

def GetLinesDim(lines: list[str], font: ImageFont) -> tuple[int, int]:
    totalHeight = 0
    for line in lines:
        totalHeight += GetTextDim(line, font)[1]
    
    totalWidth = GetMaxLineWidth(lines, font)

    return (totalWidth, totalHeight)

def GetTextInfo(quote: str, author: str, maxWidth: int, maxHeight: int, sans: bool):
    font = GetFont(sans)
    qLines = TextWrap(f"\"{quote}\"", font, maxWidth)
    qLines.append("")
    qLines.append(f"- {author}")
    dimensions = GetLinesDim(qLines, font)

    x = maxWidth / 2 - dimensions[0] / 2
    y = maxHeight / 2 - dimensions[1] / 2

    finalTxt = ""

    for line in qLines:
        finalTxt += line + "\n"

    return [finalTxt, x, y]

# Filesystem
def GetToken() -> str:
    return os.getenv("DISCORD_TOKEN")

def GetChannelID() -> int:
    with open(PATH_TO_WORKING_DIR + "db/config.json", 'r') as f:
        data = json.loads(f.read())
        return data["channelId"]

def AddImage(url: str) -> None:
    with open(PATH_TO_WORKING_DIR + "db/images.txt", 'a') as f:
        f.writelines(["\n" + url])

lastGeneratedImageId = 0
def GetRandomImageURL() -> str:
    with open(PATH_TO_WORKING_DIR + "db/images.txt", 'r') as f:
        lines = f.readlines()
        n = random.randint(0, len(lines) - 1)
        lastGeneratedImageId = n
        return lines[n]

def GenerateImageID(existingImages: list) -> str:
    id = str(uuid.uuid4())
    for image in existingImages:
        if image == id + IMAGE_FORMAT: return GenerateImageID(existingImages)
    return id

def SaveQuote(quote: str, author: str, finalImage: Image, sans: bool) -> str:
    existingImages = os.listdir(PATH_TO_WORKING_DIR + "db/images")
    imgAddr = PATH_TO_WORKING_DIR + "db/images/" + GenerateImageID(existingImages) + IMAGE_FORMAT
    finalImage.save(imgAddr)

    quotes = []
    with open(PATH_TO_WORKING_DIR + "db/quotes.json", 'r') as f:
        try:
            quotes = json.loads(f.read())
        except:
            pass

    quotes.append({
        "quote": quote,
        "author": author,
        "sans": sans,
        "image": imgAddr
    })

    with open("db/quotes.json", 'w') as f:
        f.write(json.dumps(quotes))
        
    return imgAddr

def GetFont(sans: bool) -> ImageFont:
    if (sans): 
        return ImageFont.truetype(PATH_TO_WORKING_DIR + 'resources/sans.ttf', FONT_SIZE)
    else:
        return ImageFont.truetype(PATH_TO_WORKING_DIR + 'resources/font.ttf', FONT_SIZE)

# Image Processing
def CreateQuote(quote: str, author: str, sans: bool) -> str:
    bgImg = Image.Image()
    try:
        bgImg = Image.open(BytesIO(requests.get(GetRandomImageURL()).content)).convert('RGB').resize((WIDTH, HEIGHT))
    except:
        bgImg = Image.open(PATH_TO_WORKING_DIR + "resources/placeholder.png").convert('RGB').resize((WIDTH, HEIGHT))
        lines = []
        with open(PATH_TO_WORKING_DIR + "db/images.txt", 'r') as f: lines = f.readlines()

        if (len(lines) > 0):
            lines.pop(lastGeneratedImageId)
            txt = ""
            i = 0
            for line in lines:
                txt += line
                if (i < len(lines) - 1): txt += "\n"
                i += 1

            with open(PATH_TO_WORKING_DIR + "db/images.txt", 'w') as f:
                f.write(txt)

    vignetteImg = Image.open(PATH_TO_WORKING_DIR + "resources/vignette.png")

    bgImg.paste(vignetteImg, (0, 0), mask=vignetteImg)

    img = ImageDraw.Draw(bgImg)

    processedText, x, y = GetTextInfo(quote, author, WIDTH, HEIGHT, sans)
    img.text((x, y), processedText, font=GetFont(sans), fill=(255, 255, 255))

    filename = SaveQuote(quote, author, bgImg, sans)
    return filename

# Discord
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

chId = GetChannelID()

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith(PREFIX):
        cmd = message.content.split(" ")
        match cmd[1]:
            case "save":
                if (len(cmd) >= 4):
                    quote = message.content.split("=")[1][:-2]
                    author = message.content.split("=")[2]

                    path = CreateQuote(quote, author, False)
                    filename = path.split("/")[len(path.split("/")) - 1]

                    file = discord.File(path, filename=filename)
                    embed = discord.Embed()
                    embed.set_image(url=f"attachment://{filename}")
                    await client.get_channel(chId).send(file=file, embed=embed)

                    await message.channel.send(GetSuccessMessage())
                else: await message.channel.send(GetErrorMessage(f"{PREFIX} save q=[quote] a=[author]"))
            case "image":
                if (len(cmd) == 3):
                    try:
                        AddImage(cmd[2])
                    except: pass
                    await message.channel.send(GetSuccessMessage())
                else: await message.channel.send(GetErrorMessage(f"{PREFIX} image [image url]"))
            case "help":
                await message.channel.send("ok so")
                await message.channel.send("there are literally only 2 commands")
                await message.channel.send("here are them and their usages:")
                await message.channel.send(f"`{PREFIX} save q=[quote] a=[author (victim??)]`")
                await message.channel.send("this one just saves a quote in the quotebook")
                await message.channel.send(f"`{PREFIX} image [image url]`")
                await message.channel.send("and this one adds an image to the roster")
                await message.channel.send("(oh, and only alex can remove them, so have fun :3)")
                await message.channel.send("dm alex (lexicled) if you need anything else")
                await message.channel.send("after all, im just a fuckin clanker lol")
            case _: await message.channel.send(GetErrorMessage(f"{PREFIX} [command: save/image/help]"))
                
client.run(GetToken())
