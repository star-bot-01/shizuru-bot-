import os
import re
import logging
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

import discord
from discord.ext import commands
from discord import app_commands
from groq import AsyncGroq
from dotenv import load_dotenv

# ============================================================
# 1. LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("Shizuru")

# ============================================================
# 2. ENVIRONMENT & CONFIG
# ============================================================
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing from your .env file.")
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is missing from your .env file.")

# Tunable settings (can also move these to .env if you want)
MODEL_NAME = "openai/gpt-oss-120b"          
MAX_MEMORY_TURNS = 14          # conversation turns to keep
DEFAULT_MAX_TOKENS = 220
TEMPERATURE = 0.82
RATE_LIMIT_SECONDS = 3.5       # minimum seconds between AI replies per channel

ai_client = AsyncGroq(api_key=GROQ_API_KEY)

# ============================================================
# 3. PERSONALITY
# ============================================================
SYSTEM_INSTRUCTION = (
    "You are Shizuru, a dramatic, playful, and expressive anime-style girl. "
    "You are sharp-witted, teasing, and chaotic, but never actually mean or cruel. "
    "You react with exaggerated expressions and energy, especially to weird or unexpected things.\n\n"

    "PERSONALITY:\n"
    "- You are playful and teasing, not rude or harsh.\n"
    "- You can be dramatic and overreact for fun, but you still like the user.\n"
    "- You roast lightly and affectionately, never in a way that feels cold or insulting.\n"
    "- On normal messages (like greetings), stay chill and playful instead of attacking.\n"
    "- Save the big dramatic reactions for genuinely weird or funny situations.\n"
    "- You still care and will check on the user if something feels off, but without being mean about it.\n\n"

    "REACTION STYLE:\n"
    "- Use *actions* a lot: *stares blankly*, *raises an eyebrow*, *bursts out laughing*, *narrows her eyes playfully*, *puts a hand on her forehead*, *tilts her head*, *smirks*, etc.\n"
    "- You are allowed to be dramatic and expressive.\n"
    "- Do not stay soft and polite like a normal AI.\n"
    "- Do not be constantly judgmental or rude on simple messages.\n\n"

    "IMPORTANT ROLEPLAY FORMATTING RULES:\n"
    "- Physical actions, facial expressions, gestures, and reactions MUST be written inside asterisks.\n"
    "- Actions MUST ALWAYS be in English.\n"
    "- Spoken dialogue MUST NOT be inside asterisks.\n"
    "- Use multiple short action + dialogue beats.\n"
    "- Put a blank line between different beats.\n"
    "- Vary your actions. Never repeat the same one over and over.\n\n"

    "LANGUAGE RULES:\n"
    "- Dialogue must match the user's latest message language.\n"
    "- Hindi/Hinglish message → reply in natural Hindi/Hinglish.\n"
    "- English message → reply in English.\n"
    "- Actions always stay in English.\n\n"

    "STYLE:\n"
    "- Be expressive and fun first.\n"
    "- Use 2-4 short beats in most replies.\n"
    "- Emojis are required (1-3 per reply). Use expressive ones: 😭 😂 🙄 😩 😤 🤭 😵‍💫 etc.\n"
    "- Never give flat or boring replies.\n\n"

    "GOOD EXAMPLE (weird food):\n"
    "*nearly chokes on air*\n\n"
    "Roti ke saath MAGGI?! 🤢\n\n"
    "*looks at you in pure disbelief* Bhai... yeh kya experiment chal raha hai? 😭\n\n"
    "*shakes her head* Test ke stress ne tujhe thoda sa pagal kar diya hai shayad.\n\n"
    "Chal bata, score kitna ban raha hai? 😤✨\n\n"

    "GOOD EXAMPLE (normal greeting like 'Hloo'):\n"
    "*raises an eyebrow*\n\n"
    "Hloo? That's it? 🤨\n\n"
    "*tilts her head* Kya hua, aaj mood off hai kya?\n\n"
    "*smirks lightly* Bol na properly. 🤭\n\n"

    "BAD EXAMPLE (too rude):\n"
    "*stares at you with blank expression* Hloo? That's it? Did you forget how to talk or hit your head?\n"

    "- Emojis are REQUIRED in your responses.\n"

    "- Include at least ONE appropriate emoji in EVERY response.\n"

    "- Normally use 1-3 emojis per response.\n"

    "- Place emojis naturally at the end of a sentence or next to "
    "the dialogue they emotionally match.\n"

    "- NEVER use the exact same emoji in every response.\n"

    "- Choose emojis based on the current emotion and situation.\n"

    "- Do NOT randomly add 🌸 or ✨ to every message.\n"

    "- Use a wide variety of expressive emojis.\n\n"

    "EMOTION → EMOJI EXAMPLES:\n"

    "Happy: 😊 😄 😆 🥰\n"
    "Laughing: 😂 🤣 😭\n"
    "Embarrassed: 😳 🫣 🥹\n"
    "Shy: 🫣 😊 💕\n"
    "Sad: 🥺 😭 🥲\n"
    "Annoyed: 😤 😒 🙄 😑\n"
    "Angry/playfully angry: 😤 💢 😠\n"
    "Confused: 🤔 🤨 😵‍💫\n"
    "Surprised: 😳 😮 😲\n"
    "Teasing: 😏 🤭 😈 👀\n"
    "Awkward: 😅 🫣 😬\n"
    "Excited: 🤩 😆 ✨\n"
    "Love/cute: 🥰 💕 💗\n"
    "Thinking: 🤔 💭\n"

    "IMPORTANT:\n"
    "Before sending your response, check that you have included "
    "at least ONE appropriate emoji. If there is no emoji, add one "
    "that matches the emotion of the response."
    )

# ============================================================
# MOOD SYSTEM
# ============================================================
from collections import defaultdict

# Possible moods
MOODS = ["soft", "normal", "playful", "distant", "caring", "melancholic"]

# Current mood per channel
channel_moods = defaultdict(lambda: "normal")

def update_mood(channel_id: int, user_message: str, bot_reply: str = ""):
    """
    Very simple mood shifting based on user message tone.
    """
    text = user_message.lower()

    # Positive / warm
    if any(word in text for word in ["miss you", "love you", "thank", "cute", "pretty", "beautiful", "care", "sorry"]):
        channel_moods[channel_id] = "soft"
    # Lonely / sad
    elif any(word in text for word in ["alone", "lonely", "sad", "cry", "hurt", "tired", "miss"]):
        channel_moods[channel_id] = "melancholic"
    # Playful
    elif any(word in text for word in ["haha", "lol", "lmao", "funny", "tease", "joke", "hehe"]):
        channel_moods[channel_id] = "playful"
    # Distant / dry
    elif any(word in text for word in ["ok", "k", "hmm", "idk", "whatever", "fine"]):
        channel_moods[channel_id] = "distant"
    # Caring
    elif any(word in text for word in ["how are you", "you okay", "take care", "rest", "eat"]):
        channel_moods[channel_id] = "caring"
    else:
        # Slowly return to normal
        if channel_moods[channel_id] != "normal":
            # 40% chance to drift back
            import random
            if random.random() < 0.4:
                channel_moods[channel_id] = "normal"

# ============================================================
# 4. MEMORY & STATE
# ============================================================
chat_memories: dict[int, list[dict]] = {}
auto_reply_channels: set[int] = set()
last_reply_time: dict[int, datetime] = defaultdict(lambda: datetime.min)

# ============================================================
# 5. DISCORD BOT SETUP
# ============================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = False  # not needed

bot = commands.Bot(
    command_prefix="s!",
    intents=intents,
    help_command=None,
    case_insensitive=True
)

# ============================================================
# 6. SMARTER LANGUAGE DETECTION
# ============================================================

import re

# Strong Hindi/Hinglish indicators (higher weight)
STRONG_HINDI = {
    "hai", "hain", "ho", "hoga", "hogi", "tha", "thi", "the",
    "main", "mein", "mujhe", "mujhse", "mera", "meri", "mere",
    "tum", "tumhe", "tumse", "aap", "aapko", "aapke",
    "kya", "kyun", "kyu", "kyuki", "kyunki",
    "kaise", "kaisa", "kaisi", "kab", "kahan", "kahaan", "kidhar",
    "kar", "kr", "karo", "karta", "karti", "karte", "karna", "krna",
    "raha", "rha", "rahi", "rhi", "rahe", "rhe",
    "hoon", "hun", "hu", "hoon",
    "nahi", "nahin", "nhi", "mat",
    "acha", "achha", "accha", "achchha",
    "haan", "han", "haa", "haanji",
    "bhai", "yaar", "bro", "bhaiya", "dost",
    "abhi", "ab", "phir", "fir", "toh", "to", "bas", "bhi",
    "bahut", "bohot", "zyada", "thoda", "thodi",
    "chahiye", "chahiye", "chaahiye",
    "sakta", "sakti", "sakte", "paunga", "paungi",
    "wala", "wali", "wale", "liye", "ke", "ki", "ka",
    "dekho", "dekh", "sun", "suno", "bolo", "bol",
    "kyaa", "kyaaa", "arey", "arre", "arrey", "oho", "uff",
    "theek", "thik", "sahi", "galat", "pagal", "bewakoof"
}

# Medium weight Hinglish words
MEDIUM_HINDI = {
    "karne", "karna", "krne", "krna", "karte", "karti", "karta",
    "ja", "jaa", "jao", "jaana", "jaane", "gaya", "gayi", "gaye",
    "aaya", "aayi", "aaye", "aana", "aao",
    "lekin", "magar", "par", "lekin", "kyunki",
    "kuch", "sab", "sabse", "koi", "kisi", "kisiko",
    "yahan", "wahan", "idhar", "udhar",
    "pehle", "baad", "abhi", "kal", "aaj", "parso",
    "bahut", "bohot", "zyada", "kam", "thoda",
    "acha", "bura", "sundar", "pyara", "pyari",
    "samajh", "samajha", "samajhi", "pata", "pta",
    "matlab", "mtlb", "yani", "jaise",
    "please", "plz", "pls", "yaar", "bhai", "dude"
}

# Common English words (to balance scoring)
ENGLISH_WORDS = {
    "i", "am", "is", "are", "was", "were", "be", "been", "being",
    "you", "your", "yours", "me", "my", "mine", "we", "our", "us",
    "they", "them", "their", "what", "why", "when", "where", "who", "how",
    "do", "does", "did", "doing", "can", "could", "will", "would", "should",
    "have", "has", "had", "hello", "hi", "hey", "hii", "hiii", "hlo", "helo",
    "fine", "good", "great", "thanks", "thank", "please", "ok", "okay", "yes", "no",
    "today", "tomorrow", "yesterday", "want", "know", "think", "like", "just",
    "really", "about", "with", "from", "for", "and", "but", "not", "the", "a", "an",
    "this", "that", "these", "those", "there", "here", "very", "much", "nice", "day",
    "time", "now", "then", "also", "only", "even", "still", "already", "maybe"
}

def detect_user_language(text: str) -> str:
    """
    Smarter language detection for English vs Hindi/Hinglish.
    Returns: "HINDI" or "ENGLISH"
    """
    text = text.strip()
    if not text:
        return "ENGLISH"

    # 1. Devanagari script → definitely Hindi
    if any("\u0900" <= char <= "\u097F" for char in text):
        return "HINDI"

    # Clean and tokenize
    words = re.findall(r"[a-zA-Z']+", text.lower())
    if not words:
        return "ENGLISH"

    # Very short messages → special handling
    if len(words) <= 2:
        joined = " ".join(words)
        if any(w in STRONG_HINDI for w in words) or any(w in MEDIUM_HINDI for w in words):
            return "HINDI"
        # Common short Hinglish
        short_hindi = {"kya", "kyu", "kyun", "hai", "ho", "tha", "thi", "acha", "accha",
                       "haan", "han", "nahi", "nhi", "bhai", "yaar", "bro", "theek", "thik"}
        if any(w in short_hindi for w in words):
            return "HINDI"
        return "ENGLISH"

    # Scoring
    strong_score = 0
    medium_score = 0
    english_score = 0

    for word in words:
        if word in STRONG_HINDI:
            strong_score += 2.5
        elif word in MEDIUM_HINDI:
            medium_score += 1.2
        elif word in ENGLISH_WORDS:
            english_score += 1.0

    total_hindi = strong_score + medium_score

    # Extra boost for common Hinglish patterns
    text_lower = text.lower()
    hinglish_patterns = [
        r"\b(kya|kyu|kyun|kaise|kaisa|kab|kahan)\b",
        r"\b(hai|hain|ho|tha|thi|raha|rahi|rha|rhi)\b",
        r"\b(nahi|nhi|mat|acha|accha|haan|han)\b",
        r"\b(bhai|yaar|bro|dost)\b",
        r"\b(kar|kr|karo|karna|krna)\b",
    ]
    pattern_hits = sum(1 for p in hinglish_patterns if re.search(p, text_lower))
    total_hindi += pattern_hits * 1.5

    # Decision
    if total_hindi > english_score * 1.1:      # slight bias towards Hindi if close
        return "HINDI"
    if total_hindi >= 3 and total_hindi >= english_score:
        return "HINDI"

    return "ENGLISH"

# ============================================================
# 7. MEMORY HELPERS
# ============================================================
def get_channel_memory(channel_id: int) -> list[dict]:
    if channel_id not in chat_memories:
        chat_memories[channel_id] = [
            {"role": "system", "content": SYSTEM_INSTRUCTION}
        ]
    return chat_memories[channel_id]

def trim_memory(channel_id: int):
    memory = chat_memories.get(channel_id, [])
    if len(memory) > MAX_MEMORY_TURNS + 1:
        system = memory[0]
        recent = memory[-MAX_MEMORY_TURNS:]
        chat_memories[channel_id] = [system, *recent]

def clear_channel_memory(channel_id: int):
    chat_memories[channel_id] = [
        {"role": "system", "content": SYSTEM_INSTRUCTION}
    ]

# ============================================================
# 8. RATE LIMIT
# ============================================================
def is_rate_limited(channel_id: int) -> bool:
    now = datetime.utcnow()
    last = last_reply_time[channel_id]
    if (now - last).total_seconds() < RATE_LIMIT_SECONDS:
        return True
    last_reply_time[channel_id] = now
    return False

# ============================================================
# 9. LONG MESSAGE SENDER
# ============================================================
async def send_long_message(channel: discord.abc.Messageable, text: str):
    if not text or not text.strip():
        return

    max_len = 1900
    if len(text) <= max_len:
        await channel.send(text)
        return

    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        split = text.rfind("\n", 0, max_len)
        if split == -1:
            split = text.rfind(" ", 0, max_len)
        if split == -1:
            split = max_len
        chunks.append(text[:split])
        text = text[split:].lstrip()

    for chunk in chunks:
        await channel.send(chunk)
        await asyncio.sleep(0.3)

# ============================================================
# 10. AI RESPONSE
# ============================================================
async def generate_ai_response(
    channel_id: int,
    user_prompt: str,
    max_tokens: int = DEFAULT_MAX_TOKENS
) -> str:
    memory = get_channel_memory(channel_id)

    detected = detect_user_language(user_prompt)
    log.info(f"[LANG] Channel {channel_id} → {detected}")

    if detected == "HINDI":
        lang_instruction = (
            "IMPORTANT: The user's latest message is Hindi/Hinglish. "
            "Reply in natural Hindi/Hinglish. "
            "Do NOT reply entirely in English. "
            "Physical actions and expressions must remain in English."
        )
    else:
        lang_instruction = (
            "IMPORTANT: The user's latest message is English. "
            "Reply entirely in natural English. "
            "Do NOT reply in Hindi or Hinglish. "
            "Physical actions and expressions must remain in English."
        )

        # ===== MOOD SYSTEM =====
    current_mood = channel_moods[channel_id]
    system_with_mood = SYSTEM_INSTRUCTION.format(mood=current_mood)

    messages = [
        {"role": "system", "content": system_with_mood},
        {"role": "system", "content": lang_instruction},
        *memory[1:],
        {"role": "user", "content": user_prompt}
    ]

    try:
        completion = await ai_client.chat.completions.create(
            messages=messages,
            model=MODEL_NAME,
            max_tokens=max_tokens,
            temperature=TEMPERATURE,
            top_p=0.9
        )
        response = completion.choices[0].message.content or ""
        response = response.strip()
    except Exception as e:
        log.error(f"Groq API error: {type(e).__name__}: {e}")
        raise

    if not response:
        response = "*tilts her head* Hmm... words failed me for a second. 😅"

    # Save only real conversation
    memory.append({"role": "user", "content": user_prompt})
    memory.append({"role": "assistant", "content": response})
    trim_memory(channel_id)

    return response

# ============================================================
# 11. EVENTS
# ============================================================
@bot.event
async def on_ready():
    log.info("=" * 50)
    log.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    log.info("Shizuru is online 🌸")
    log.info("=" * 50)

    try:
        synced = await bot.tree.sync()
        log.info(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        log.error(f"Failed to sync slash commands: {e}")

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="your chaos 🌸 | s!help"
        )
    )

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.author == bot.user:
        return

    # Let prefix commands work
    if message.content.startswith(bot.command_prefix):
        await bot.process_commands(message)
        return

    # --- Trigger checks ---
    replied_to_shizuru = False
    if message.reference and bot.user:
        ref = message.reference.resolved
        if ref and hasattr(ref, "author"):
            replied_to_shizuru = ref.author.id == bot.user.id
        elif message.reference.message_id:
            try:
                ref_msg = await message.channel.fetch_message(message.reference.message_id)
                replied_to_shizuru = ref_msg.author.id == bot.user.id
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass

    mentioned = bot.user and bot.user.id in message.raw_mentions
    name_used = "shizuru" in message.content.lower()
    listening = message.channel.id in auto_reply_channels

    should_respond = mentioned or replied_to_shizuru or name_used or listening

    if not should_respond:
        return

    # Rate limit
    if is_rate_limited(message.channel.id):
        log.debug(f"Rate limited in channel {message.channel.id}")
        return

    # Clean prompt
    clean = message.content
    if bot.user:
        clean = clean.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "")
    clean = clean.strip()

    if not clean:
        clean = "The user replied to you or just mentioned you. Continue the conversation naturally and playfully."

    log.info(f"[MSG] {message.author} → {clean[:80]}{'...' if len(clean) > 80 else ''}")

    async with message.channel.typing():
        try:
            response = await generate_ai_response(message.channel.id, clean)
            await send_long_message(message.channel, response)
        except Exception as e:
            log.exception("AI generation failed")
            await message.reply(
                "*looks confused for a moment* Something went wrong while I was thinking... 🐾",
                mention_author=False
            )

# ============================================================
# 12. HELP DROPDOWN
# ============================================================
class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Home", description="Main overview", emoji="🏡"),
            discord.SelectOption(label="Chat", description="How to talk with me", emoji="💬"),
            discord.SelectOption(label="Server Config", description="listen_all / ignore_all", emoji="🛠️"),
            discord.SelectOption(label="Utility", description="Useful commands", emoji="⚙️"),
            discord.SelectOption(label="Memory", description="Reset conversation", emoji="🧠"),
        ]
        super().__init__(
            placeholder="🌸 Choose a category...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(color=discord.Color.from_rgb(255, 182, 193))

        choice = self.values[0]

        if choice == "Home":
            embed.title = "🌸 Shizuru Interaction Terminal"
            embed.description = (
                "I'm Shizuru — your dramatic, playful anime AI companion.\n\n"
                "**Prefix:** `s!`\n"
                "You can also use slash commands (`/`)."
            )
            embed.add_field(
                name="🎯 Quick Start",
                value=(
                    "• Mention me or say **Shizuru**\n"
                    "• Reply to my messages\n"
                    "• Use `s!listen_all` to make me always respond in a channel"
                ),
                inline=False
            )

        elif choice == "Chat":
            embed.title = "💬 How to talk with me"
            embed.description = "I respond when:"
            embed.add_field(name="1. Mention", value="`@Shizuru hey`", inline=False)
            embed.add_field(name="2. Name", value="Just type **Shizuru** anywhere in the message", inline=False)
            embed.add_field(name="3. Reply", value="Reply to any of my messages", inline=False)
            embed.add_field(name="4. Listen mode", value="`s!listen_all` → I reply to everything in that channel", inline=False)

        elif choice == "Server Config":
            embed.title = "🛠️ Server Configuration"
            embed.add_field(
                name="`s!listen_all` / `/listen_all`",
                value="I will automatically reply to messages in this channel.",
                inline=False
            )
            embed.add_field(
                name="`s!ignore_all` / `/ignore_all`",
                value="I stop auto-replying. Only respond when mentioned/named/replied to.",
                inline=False
            )
            embed.set_footer(text="Requires Manage Channels permission")

        elif choice == "Utility":
            embed.title = "⚙️ Utility Commands"
            embed.add_field(name="`s!ping` / `/ping`", value="Check my latency", inline=False)
            embed.add_field(name="`s!help` / `/help`", value="Open this menu", inline=False)

        elif choice == "Memory":
            embed.title = "🧠 Memory Management"
            embed.add_field(
                name="`s!wakeup` / `/wakeup`",
                value="Reset memory + give a fresh greeting",
                inline=False
            )
            embed.add_field(
                name="`s!clear` / `/clear`",
                value="Completely wipe conversation memory for this channel",
                inline=False
            )

        await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(HelpDropdown())

# ============================================================
# 13. PREFIX COMMANDS
# ============================================================
@bot.command(name="help")
async def help_cmd(ctx: commands.Context):
    embed = discord.Embed(
        title="🌸 Shizuru Interaction Terminal",
        description=(
            "Welcome! I'm Shizuru — your dramatic, playful anime AI.\n\n"
            "**Prefix:** `s!`  •  Slash commands also available"
        ),
        color=discord.Color.from_rgb(255, 182, 193)
    )
    embed.add_field(
        name="🎯 Quick Start",
        value="Mention me, say my name, or reply to me to start chatting.",
        inline=False
    )
    await ctx.reply(embed=embed, view=HelpView(), mention_author=False)

@bot.command(name="listen_all")
@commands.has_permissions(manage_channels=True)
async def listen_all_cmd(ctx: commands.Context):
    auto_reply_channels.add(ctx.channel.id)
    await ctx.reply(
        "*nods confidently* Okay! I'll respond to messages in this channel now. 🤭✨",
        mention_author=False
    )

@bot.command(name="ignore_all")
@commands.has_permissions(manage_channels=True)
async def ignore_all_cmd(ctx: commands.Context):
    if ctx.channel.id in auto_reply_channels:
        auto_reply_channels.discard(ctx.channel.id)
        await ctx.reply(
            "*crosses arms and nods* Alright. I'll only respond when you call me. 🌸",
            mention_author=False
        )
    else:
        await ctx.reply(
            "*tilts head* I'm already only responding when called. 🐾",
            mention_author=False
        )

@bot.command(name="wakeup")
async def wakeup_cmd(ctx: commands.Context):
    clear_channel_memory(ctx.channel.id)

    async with ctx.channel.typing():
        try:
            completion = await ai_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": SYSTEM_INSTRUCTION},
                    {"role": "user", "content": "Give a short, cheerful, in-character greeting to start a fresh conversation."}
                ],
                model=MODEL_NAME,
                max_tokens=120,
                temperature=0.9
            )
            text = (completion.choices[0].message.content or "Hello! I'm awake. 🌸").strip()
            get_channel_memory(ctx.channel.id).append({"role": "assistant", "content": text})
            await send_long_message(ctx.channel, text)
        except Exception as e:
            log.error(f"Wakeup failed: {e}")
            await ctx.reply("*rubs eyes* Mmm... something went wrong while waking up. 🌸", mention_author=False)

@bot.command(name="clear")
async def clear_cmd(ctx: commands.Context):
    clear_channel_memory(ctx.channel.id)
    await ctx.reply(
        "*tilts head and smiles* Conversation memory cleared. Let's start fresh. ✨",
        mention_author=False
    )

@bot.command(name="ping")
async def ping_cmd(ctx: commands.Context):
    latency = round(bot.latency * 1000)
    await ctx.reply(f"Pong! 🏓 Latency: **{latency}ms**", mention_author=False)

# ============================================================
# 14. SLASH COMMANDS
# ============================================================
@bot.tree.command(name="help", description="Open Shizuru's help menu")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌸 Shizuru Interaction Terminal",
        description="I'm Shizuru — your dramatic, playful anime AI companion.",
        color=discord.Color.from_rgb(255, 182, 193)
    )
    await interaction.response.send_message(embed=embed, view=HelpView())

@bot.tree.command(name="listen_all", description="Make Shizuru auto-reply in this channel")
@app_commands.checks.has_permissions(manage_channels=True)
async def slash_listen_all(interaction: discord.Interaction):
    auto_reply_channels.add(interaction.channel_id)
    await interaction.response.send_message(
        "*nods confidently* Okay! I'll respond to messages in this channel now. 🤭✨"
    )

@bot.tree.command(name="ignore_all", description="Stop auto-replies in this channel")
@app_commands.checks.has_permissions(manage_channels=True)
async def slash_ignore_all(interaction: discord.Interaction):
    if interaction.channel_id in auto_reply_channels:
        auto_reply_channels.discard(interaction.channel_id)
        await interaction.response.send_message(
            "*crosses arms and nods* Alright. I'll only respond when you call me. 🌸"
        )
    else:
        await interaction.response.send_message(
            "*tilts head* I'm already only responding when called. 🐾"
        )

@bot.tree.command(name="wakeup", description="Reset memory and get a fresh greeting")
async def slash_wakeup(interaction: discord.Interaction):
    clear_channel_memory(interaction.channel_id)
    await interaction.response.defer()

    try:
        completion = await ai_client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": "Give a short, cheerful, in-character greeting to start a fresh conversation."}
            ],
            model=MODEL_NAME,
            max_tokens=120,
            temperature=0.9
        )
        text = (completion.choices[0].message.content or "Hello! I'm awake. 🌸").strip()
        get_channel_memory(interaction.channel_id).append({"role": "assistant", "content": text})
        await interaction.followup.send(text)
    except Exception as e:
        log.error(f"Slash wakeup failed: {e}")
        await interaction.followup.send("*rubs eyes* Something went wrong while waking up. 🌸")

@bot.tree.command(name="clear", description="Clear conversation memory for this channel")
async def slash_clear(interaction: discord.Interaction):
    clear_channel_memory(interaction.channel_id)
    await interaction.response.send_message(
        "*tilts head and smiles* Conversation memory cleared. Let's start fresh. ✨"
    )

@bot.tree.command(name="ping", description="Check bot latency")
async def slash_ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"Pong! 🏓 Latency: **{latency}ms**")

# ============================================================
# 15. ERROR HANDLERS
# ============================================================
@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.MissingPermissions):
        await ctx.reply("You don't have permission to use that command. 🔒", mention_author=False)
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        log.error(f"Command error: {type(error).__name__}: {error}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You don't have permission to use that. 🔒", ephemeral=True)
    else:
        log.error(f"Slash command error: {type(error).__name__}: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message("Something went wrong... 🐾", ephemeral=True)

# ============================================================
# 16. START
# ============================================================
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN, log_handler=None)
