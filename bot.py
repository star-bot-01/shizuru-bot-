import os

import discord
from discord.ext import commands
from groq import AsyncGroq
from dotenv import load_dotenv


# ============================================================
# 1. ENVIRONMENT SETUP
# ============================================================

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY is missing from your .env file."
    )

if not DISCORD_TOKEN:
    raise ValueError(
        "DISCORD_TOKEN is missing from your .env file."
    )


# Async Groq client
ai_client = AsyncGroq(
    api_key=GROQ_API_KEY
)


# ============================================================
# 2. AI PERSONALITY
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
# 3. MEMORY SETTINGS
# ============================================================

chat_memories = {}

# Channels where Shizuru automatically responds
auto_reply_channels = set()

# Number of recent messages to remember
MAX_MEMORY_TURNS = 12


# ============================================================
# 4. DISCORD BOT SETUP
# ============================================================

intents = discord.Intents.default()

# Required to read normal Discord messages
intents.message_content = True

bot = commands.Bot(
    command_prefix="s!",
    intents=intents,
    help_command=None
)


# ============================================================
# 5. LANGUAGE DETECTION
# ============================================================

def detect_user_language(text):
    """
    Detect whether the user's latest message is mainly
    English, Hindi/Hinglish, or another language.

    For this bot we mainly distinguish:
        ENGLISH
        HINDI
    """

    text_lower = text.lower()

    # Hindi / Hinglish words
    hindi_words = {
        "hai", "hain", "ho", "hoga", "hogi",
        "tha", "thi", "the",
        "main", "mein",
        "mujhe", "mujhse",
        "mera", "meri", "mere",
        "tum", "tumhe", "tumse",
        "aap", "aapko",
        "kya", "kyun", "kyu",
        "kaise", "kaisa", "kaisi",
        "kab",
        "kahan", "kahaan",
        "kar", "kr", "krr",
        "raha", "rha",
        "rahi", "rhi",
        "rahe",
        "hoon", "hun",
        "nahi", "nahin",
        "acha", "achha", "accha",
        "haan", "han",
        "arre",
        "bas",
        "bhi",
        "toh", "to",
        "phir",
        "abhi",
        "pata",
        "chahiye",
        "sakta", "sakti", "sakte",
        "kesi",
        "wala", "wali",
        "liye",
        "kyunki", "kyuki",
        "bahut",
        "thoda", "thodi",
        "bro",
        "bhai",
        "yaar",
        "krna",
        "karna",
        "karne",
        "karo",
        "karti",
        "karta",
        "hoon"
    }

    # English words
    english_words = {
        "i", "am", "is", "are",
        "was", "were",
        "be", "been", "being",
        "you", "your", "yours",
        "me", "my", "mine",
        "we", "our",
        "they", "their",
        "what", "why",
        "when", "where",
        "who", "how",
        "do", "does", "did",
        "doing",
        "can", "could",
        "will", "would",
        "should",
        "have", "has", "had",
        "hello", "hi", "hey",
        "hii", "hiii",
        "hlo",
        "fine", "good",
        "great",
        "thanks", "thank",
        "please",
        "today", "tomorrow",
        "yesterday",
        "want", "know",
        "think", "like",
        "just", "really",
        "about", "with",
        "from", "for",
        "and", "but",
        "not",
        "yes", "no",
        "okay", "ok",
        "are",
        "up",
        "why",
        "how",
        "much",
        "very",
        "nice",
        "day"
    }

    words = text_lower.split()

    hindi_score = 0
    english_score = 0

    for word in words:

        # Remove punctuation
        cleaned_word = word.strip(
            ".,!?;:'\"()[]{}<>"
        )

        if cleaned_word in hindi_words:
            hindi_score += 1

        if cleaned_word in english_words:
            english_score += 1

    # If Devanagari Hindi is used
    if any(
        "\u0900" <= char <= "\u097F"
        for char in text
    ):
        return "HINDI"

    # Hindi/Hinglish clearly wins
    if hindi_score > english_score:
        return "HINDI"

    # English clearly wins
    if english_score > hindi_score:
        return "ENGLISH"

    # Ambiguous messages default to English
    return "ENGLISH"


# ============================================================
# 6. MEMORY FUNCTIONS
# ============================================================

def get_channel_memory(channel_id):
    """
    Get or create memory for a Discord channel.
    """

    if channel_id not in chat_memories:

        chat_memories[channel_id] = [
            {
                "role": "system",
                "content": SYSTEM_INSTRUCTION
            }
        ]

    return chat_memories[channel_id]


def trim_memory(channel_id):
    """
    Keep the system instruction plus recent conversation.
    """

    memory = chat_memories[channel_id]

    if len(memory) > MAX_MEMORY_TURNS + 1:

        system_message = memory[0]

        recent_messages = memory[
            -MAX_MEMORY_TURNS:
        ]

        chat_memories[channel_id] = [
            system_message,
            *recent_messages
        ]


# ============================================================
# 7. LONG MESSAGE HANDLER
# ============================================================

async def send_long_message(channel, text):
    """
    Discord has a 2000 character message limit.
    """

    if not text:
        return

    max_length = 1900

    if len(text) <= max_length:

        await channel.send(text)

        return

    chunks = []

    while text:

        if len(text) <= max_length:

            chunks.append(text)

            break

        split_at = text.rfind(
            "\n",
            0,
            max_length
        )

        if split_at == -1:

            split_at = text.rfind(
                " ",
                0,
                max_length
            )

        if split_at == -1:

            split_at = max_length

        chunks.append(
            text[:split_at]
        )

        text = text[
            split_at:
        ].lstrip()

    for chunk in chunks:

        await channel.send(chunk)


# ============================================================
# 8. AI RESPONSE FUNCTION
# ============================================================

async def generate_ai_response(
    channel_id,
    user_prompt,
    max_tokens=150
):
    """
    Generate an AI response.

    IMPORTANT:
    The language is detected ONLY from the latest user message.
    """

    memory = get_channel_memory(
        channel_id
    )

    # --------------------------------------------------------
    # Detect language from latest message
    # --------------------------------------------------------

    detected_language = detect_user_language(
        user_prompt
    )

    print(
        f"[LANGUAGE] {detected_language}"
    )

    # --------------------------------------------------------
    # Create a temporary language instruction
    # --------------------------------------------------------

    if detected_language == "HINDI":

        language_instruction = (
            "IMPORTANT: The user's latest message is Hindi/Hinglish. "
            "Reply in natural Hindi/Hinglish. "
            "Do NOT reply entirely in English. "
            "Physical actions and expressions must remain in English."
        )

    else:

        language_instruction = (
            "IMPORTANT: The user's latest message is English. "
            "Reply entirely in natural English. "
            "Do NOT reply in Hindi or Hinglish. "
            "Physical actions and expressions must remain in English."
        )

    # --------------------------------------------------------
    # Build temporary request
    #
    # We do NOT save the language instruction into memory.
    # This prevents old language instructions from affecting
    # future messages.
    # --------------------------------------------------------

    messages_for_groq = [
        memory[0],
        {
            "role": "system",
            "content": language_instruction
        }
    ]

    # Add previous conversation
    messages_for_groq.extend(
        memory[1:]
    )

    # Add the ACTUAL latest user message
    messages_for_groq.append(
        {
            "role": "user",
            "content": user_prompt
        }
    )

    # --------------------------------------------------------
    # Ask Groq
    # --------------------------------------------------------

    chat_completion = (
        await ai_client.chat.completions.create(
            messages=messages_for_groq,
            model="llama-3.3-70b-versatile",
            max_tokens=max_tokens,
            temperature=0.85
        )
    )

    # --------------------------------------------------------
    # Get response
    # --------------------------------------------------------

    response_text = (
        chat_completion
        .choices[0]
        .message
        .content
    )

    if not response_text:

        response_text = (
            "Hmm... I couldn't think of a response. 😅"
        )

    # --------------------------------------------------------
    # Save ONLY the real conversation
    # --------------------------------------------------------

    memory.append(
        {
            "role": "user",
            "content": user_prompt
        }
    )

    memory.append(
        {
            "role": "assistant",
            "content": response_text
        }
    )

    trim_memory(
        channel_id
    )

    return response_text


# ============================================================
# 9. BOT READY
# ============================================================

@bot.event
async def on_ready():

    print(
        "========================================"
    )

    print(
        f"Success! {bot.user} is online."
    )

    print(
        f"Bot ID: {bot.user.id}"
    )

    print(
        "Shizuru is ready! 🌸"
    )

    print(
        "========================================"
    )

    await bot.change_presence(
        activity=discord.Game(
            name="Helping you out 🌸"
        )
    )


# ============================================================
# 10. MESSAGE HANDLER
# ============================================================

@bot.event
async def on_message(message):

    # --------------------------------------------------------
    # Ignore Shizuru's own messages
    # --------------------------------------------------------

    if message.author == bot.user:
        return

    # --------------------------------------------------------
    # Commands
    # --------------------------------------------------------

    if message.content.startswith(bot.command_prefix):

        await bot.process_commands(message)
        return

    # --------------------------------------------------------
    # CHECK IF USER REPLIED TO SHIZURU
    # --------------------------------------------------------

    replied_to_shizuru = False

    if (
        message.reference is not None
        and bot.user is not None
    ):

        referenced_message = message.reference.resolved

        # If Discord already gave us the referenced message
        if (
            referenced_message is not None
            and hasattr(referenced_message, "author")
        ):

            replied_to_shizuru = (
                referenced_message.author.id
                == bot.user.id
            )

        # Fallback: fetch the referenced message
        elif message.reference.message_id is not None:

            try:

                referenced_message = (
                    await message.channel.fetch_message(
                        message.reference.message_id
                    )
                )

                replied_to_shizuru = (
                    referenced_message.author.id
                    == bot.user.id
                )

            except discord.NotFound:

                replied_to_shizuru = False

            except discord.Forbidden:

                replied_to_shizuru = False

            except discord.HTTPException:

                replied_to_shizuru = False

    # --------------------------------------------------------
    # CHECK MENTION
    # --------------------------------------------------------

    bot_was_mentioned = False

    if bot.user is not None:

        bot_was_mentioned = (
            bot.user.id in message.raw_mentions
        )

    # --------------------------------------------------------
    # CHECK IF USER SAID "SHIZURU"
    # --------------------------------------------------------

    name_was_used = (
        "shizuru" in message.content.lower()
    )

    # --------------------------------------------------------
    # CHECK LISTEN ALL
    # --------------------------------------------------------

    channel_is_listening = (
        message.channel.id
        in auto_reply_channels
    )

    # --------------------------------------------------------
    # DECIDE WHETHER TO RESPOND
    # --------------------------------------------------------

    should_respond = (
        bot_was_mentioned
        or replied_to_shizuru
        or name_was_used
        or channel_is_listening
    )

    # --------------------------------------------------------
    # DEBUG
    # --------------------------------------------------------

    print(
        f"[MESSAGE] "
        f"{message.author}: "
        f"{message.content}"
    )

    print(
        f"[TRIGGER] "
        f"Mention={bot_was_mentioned} | "
        f"ReplyToShizuru={replied_to_shizuru} | "
        f"Name={name_was_used} | "
        f"Listen={channel_is_listening}"
    )

    # --------------------------------------------------------
    # DON'T RESPOND
    # --------------------------------------------------------

    if not should_respond:
        return

    # --------------------------------------------------------
    # REMOVE BOT MENTION
    # --------------------------------------------------------

    clean_prompt = message.content

    if bot.user is not None:

        clean_prompt = clean_prompt.replace(
            f"<@{bot.user.id}>",
            ""
        )

        clean_prompt = clean_prompt.replace(
            f"<@!{bot.user.id}>",
            ""
        )

    clean_prompt = clean_prompt.strip()

    # --------------------------------------------------------
    # EMPTY MESSAGE
    # --------------------------------------------------------

    if not clean_prompt:

        clean_prompt = (
            "The user replied to your previous message. "
            "Continue the conversation naturally."
        )

    print(
        f"[PROMPT] {clean_prompt}"
    )

    # --------------------------------------------------------
    # GENERATE AI RESPONSE
    # --------------------------------------------------------

    async with message.channel.typing():

        try:

            response_text = (
                await generate_ai_response(
                    message.channel.id,
                    clean_prompt,
                    max_tokens=150
                )
            )

            print(
                f"[AI RESPONSE] "
                f"{response_text}"
            )

            await send_long_message(
                message.channel,
                response_text
            )

        except Exception as e:

            print(
                "========================================"
            )

            print(
                "[AI ERROR]"
            )

            print(
                f"Type: {type(e).__name__}"
            )

            print(
                f"Error: {e}"
            )

            print(
                "========================================"
            )

            await message.reply(
                "*looks confused for a moment* "
                "Something went wrong while I was thinking. 🐾"
            )


# ============================================================
# 11. HELP DROPDOWN
# ============================================================

class HelpDropdown(
    discord.ui.Select
):

    def __init__(self):

        options = [

            discord.SelectOption(
                label="Home",
                description="Return to the main overview",
                emoji="🏡"
            ),

            discord.SelectOption(
                label="General Commands",
                description="Basic commands and chat methods",
                emoji="💬"
            ),

            discord.SelectOption(
                label="Server Configuration",
                description="Settings and channel management",
                emoji="🛠️"
            ),

            discord.SelectOption(
                label="Utility Tools",
                description="Helpful utility commands",
                emoji="⚙️"
            ),

            discord.SelectOption(
                label="Memory Management",
                description="Manage conversation memory",
                emoji="🧠"
            )

        ]

        super().__init__(
            placeholder=(
                "🌸 Choose a category to explore..."
            ),
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        embed = discord.Embed(
            color=discord.Color.from_rgb(
                255,
                182,
                193
            )
        )

        # ----------------------------------------------------
        # HOME
        # ----------------------------------------------------

        if self.values[0] == "Home":

            embed.title = (
                "🌸 Shizuru Interaction Terminal"
            )

            embed.description = (
                "Welcome! I'm Shizuru, your "
                "anime-style AI assistant. "
                "Use the dropdown menu below "
                "to explore my features.\n\n"
                "**Core Operational Prefix:** `s!`"
            )

            embed.add_field(
                name="🎯 Quick Start Guide",
                value=(
                    "• Use the dropdown to browse features.\n"
                    "• Type `s!help` to open this menu.\n"
                    "• Mention **Shizuru** to chat with me."
                ),
                inline=False
            )

        # ----------------------------------------------------
        # GENERAL COMMANDS
        # ----------------------------------------------------

        elif self.values[0] == "General Commands":

            embed.title = (
                "💬 Conversational Systems Guide"
            )

            embed.description = (
                "Chat with Shizuru using normal Discord messages."
            )

            embed.add_field(
                name="🗣️ Direct Chat",
                value=(
                    "Mention me or type **Shizuru** "
                    "in your message to start a conversation."
                ),
                inline=False
            )

            embed.add_field(
                name="🎬 Natural Conversation",
                value=(
                    "You can ask questions, talk about your day, "
                    "or simply have a casual conversation."
                ),
                inline=False
            )

        # ----------------------------------------------------
        # SERVER CONFIGURATION
        # ----------------------------------------------------

        elif self.values[0] == "Server Configuration":

            embed.title = (
                "🛠️ Server Environment Controls"
            )

            embed.description = (
                "Commands for controlling automatic responses."
            )

            embed.add_field(
                name="`s!listen_all`",
                value=(
                    "Makes Shizuru automatically respond "
                    "to messages in the current channel."
                ),
                inline=False
            )

            embed.add_field(
                name="`s!ignore_all`",
                value=(
                    "Stops automatic replies in the current channel. "
                    "Shizuru will respond only when mentioned or named."
                ),
                inline=False
            )

        # ----------------------------------------------------
        # UTILITY TOOLS
        # ----------------------------------------------------

        elif self.values[0] == "Utility Tools":

            embed.title = (
                "⚙️ Core Utility Operations"
            )

            embed.description = (
                "Useful commands for checking and controlling the bot."
            )

            embed.add_field(
                name="`s!ping`",
                value=(
                    "Checks the bot's Discord latency."
                ),
                inline=False
            )

            embed.add_field(
                name="`s!help`",
                value=(
                    "Opens this interactive help dashboard."
                ),
                inline=False
            )

        # ----------------------------------------------------
        # MEMORY MANAGEMENT
        # ----------------------------------------------------

        elif self.values[0] == "Memory Management":

            embed.title = (
                "🧠 Memory Configuration Suite"
            )

            embed.description = (
                "Controls conversation memory for the current channel."
            )

            embed.add_field(
                name="`s!wakeup`",
                value=(
                    "Resets the conversation and "
                    "generates a new greeting."
                ),
                inline=False
            )

            embed.add_field(
                name="`s!clear`",
                value=(
                    "Completely resets conversation memory "
                    "for the current channel."
                ),
                inline=False
            )

        await interaction.response.edit_message(
            embed=embed
        )


# ============================================================
# 12. HELP VIEW
# ============================================================

class HelpView(
    discord.ui.View
):

    def __init__(self):

        # Menu expires after 3 minutes
        super().__init__(
            timeout=180
        )

        self.add_item(
            HelpDropdown()
        )


# ============================================================
# 13. HELP COMMAND
# ============================================================

@bot.command(
    name="help"
)
async def help_command(ctx):

    embed = discord.Embed(
        title=(
            "🌸 Shizuru Interaction Terminal"
        ),

        description=(
            "Welcome! I'm Shizuru, your "
            "anime-style AI assistant. "
            "Use the interactive dropdown below "
            "to explore my features.\n\n"
            "**Core Operational Prefix:** `s!`"
        ),

        color=discord.Color.from_rgb(
            255,
            182,
            193
        )
    )

    embed.add_field(
        name="🎯 Quick Start Guide",
        value=(
            "• Use the dropdown to browse bot features.\n"
            "• Type `s!help` to reload this dashboard.\n"
            "• Mention Shizuru to start chatting."
        ),
        inline=False
    )

    view = HelpView()

    await ctx.reply(
        embed=embed,
        view=view
    )


# ============================================================
# 14. LISTEN ALL
# ============================================================

@bot.command(
    name="listen_all"
)
@commands.has_permissions(
    manage_channels=True
)
async def listen_all(ctx):

    auto_reply_channels.add(
        ctx.channel.id
    )

    await ctx.reply(
        "*nods confidently* "
        "Okay! I'll respond to messages "
        "in this channel now. 🤭✨"
    )


# ============================================================
# 15. IGNORE ALL
# ============================================================

@bot.command(
    name="ignore_all"
)
@commands.has_permissions(
    manage_channels=True
)
async def ignore_all(ctx):

    if ctx.channel.id in auto_reply_channels:

        auto_reply_channels.remove(
            ctx.channel.id
        )

        await ctx.reply(
            "*crosses arms and nods* "
            "Alright. I'll only respond when "
            "you mention me or say my name. 🌸"
        )

    else:

        await ctx.reply(
            "*tilts head* "
            "I'm already only responding when called. 🐾"
        )


# ============================================================
# 16. WAKEUP
# ============================================================

@bot.command(
    name="wakeup"
)
async def wakeup(ctx):

    channel_id = ctx.channel.id

    # Reset memory
    chat_memories[channel_id] = [
        {
            "role": "system",
            "content": SYSTEM_INSTRUCTION
        }
    ]

    async with ctx.channel.typing():

        try:

            chat_completion = (
                await ai_client
                .chat
                .completions
                .create(
                    messages=[
                        {
                            "role": "system",
                            "content": SYSTEM_INSTRUCTION
                        },
                        {
                            "role": "user",
                            "content": (
                                "Give the user a short, "
                                "cheerful greeting to start "
                                "a new conversation."
                            )
                        }
                    ],
                    model="llama-3.3-70b-versatile",
                    max_tokens=100,
                    temperature=0.9
                )
            )

            response_text = (
                chat_completion
                .choices[0]
                .message
                .content
            )

            if not response_text:

                response_text = (
                    "Hello! I'm awake. 🌸"
                )

            chat_memories[
                channel_id
            ].append(
                {
                    "role": "assistant",
                    "content": response_text
                }
            )

            await send_long_message(
                ctx.channel,
                response_text
            )

        except Exception as e:

            print(
                f"Wakeup Error: "
                f"{type(e).__name__}: {e}"
            )

            await ctx.reply(
                "*rubs eyes* "
                "Mmm... something went wrong "
                "while waking up. 🌸"
            )


# ============================================================
# 17. CLEAR MEMORY
# ============================================================

@bot.command(
    name="clear"
)
async def clear(ctx):

    channel_id = ctx.channel.id

    chat_memories[channel_id] = [
        {
            "role": "system",
            "content": SYSTEM_INSTRUCTION
        }
    ]

    await ctx.reply(
        "*tilts head and smiles* "
        "Conversation memory cleared. "
        "Let's start fresh. ✨"
    )


# ============================================================
# 18. PING
# ============================================================

@bot.command(
    name="ping"
)
async def ping(ctx):

    latency = round(
        bot.latency * 1000
    )

    await ctx.reply(
        f"Pong! 🏓 "
        f"My Discord latency is **{latency}ms**!"
    )


# ============================================================
# 19. COMMAND ERROR HANDLER
# ============================================================

@bot.event
async def on_command_error(
    ctx,
    error
):

    if isinstance(
        error,
        commands.MissingPermissions
    ):

        await ctx.reply(
            "You don't have permission "
            "to use that command. 🔒"
        )

        return

    if isinstance(
        error,
        commands.CommandNotFound
    ):

        return

    print(
        f"Command Error: "
        f"{type(error).__name__}: "
        f"{error}"
    )


# ============================================================
# 20. START BOT
# ============================================================

bot.run(
    DISCORD_TOKEN
)
