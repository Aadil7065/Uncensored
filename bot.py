#!/usr/bin/env python3
"""
🔥 Open Source Uncensored AI Telegram Bot 🔥
Features:
- Uncensored LLM (Hugging Face abliterated models)
- Chat with conversation memory
- Inline mode (@botname query)
- Smooth typing indicator
- Simple error handling
"""

import asyncio
import logging
import requests
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    InlineQueryHandler,
    ContextTypes,
    filters,
)

# ============ CONFIGURATION – YAHI BADALO ============
TELEGRAM_TOKEN = "8732926521:AAEWoCcOAMhRMFTX49SMz2M1FSRXFUXotGQ"   # @BotFather se

# 🔴 IMPORTANT: Purana token leak ho gaya hai. Naya bana lo Hugging Face se.
# 🔴 Jaake https://huggingface.co/settings/tokens par "New token" banao (Read role)
HF_API_TOKEN   = "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"      # naya token yahan paste karo

ALLOWED_USER_IDS = [8561031913]                # tera Telegram ID (integer)
MODEL_NAME = "mlabonne/Hermes-3-Llama-3.1-8B-lorablated"   # confirmed working uncensored model
# =================================================

API_URL = f"https://api-inference.huggingface.co/models/{MODEL_NAME}"
HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}

# Conversation memory store
conversations = {}

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    level=logging.INFO)

def is_allowed(user_id: int) -> bool:
    return user_id in ALLOWED_USER_IDS

def get_conversation(user_id: int):
    if user_id not in conversations:
        conversations[user_id] = []
    return conversations[user_id]

def trim_conversation(conv):
    return conv[-20:] if len(conv) > 20 else conv

def chunk_text(text: str, size: int = 4000):
    return [text[i:i+size] for i in range(0, len(text), size)]

# ------------------------------
# AI Generation with Retry & Rate‑Limit Handling
# ------------------------------
async def generate_response(user_id: int, user_message: str) -> str:
    conv = get_conversation(user_id)
    conv.append({"role": "user", "content": user_message})

    # Build conversation context
    history = ""
    for msg in conv[-6:]:
        role = "User" if msg["role"] == "user" else "Assistant"
        history += f"{role}: {msg['content']}\n"

    full_prompt = history + "Assistant: "

    payload = {
        "inputs": full_prompt,
        "parameters": {
            "max_new_tokens": 500,
            "temperature": 0.7,
            "do_sample": True,
            "return_full_text": False,
        },
    }

    retries = 3
    delay = 2
    for attempt in range(retries):
        try:
            response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and result:
                    ai_text = result[0].get("generated_text", "").strip()
                elif isinstance(result, dict):
                    ai_text = result.get("generated_text", "").strip()
                else:
                    ai_text = "⚠️ Unexpected response format."
                if ai_text and not ai_text.startswith("⚠️"):
                    conv.append({"role": "assistant", "content": ai_text})
                    conversations[user_id] = trim_conversation(conv)
                return ai_text or "⚠️ No response from AI. Try again."
            elif response.status_code == 429:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            else:
                return f"⚠️ API error {response.status_code}. Check your tokens and model."
        except requests.exceptions.RequestException as e:
            logging.error(f"Request error: {e}")
            return "⚠️ Connection error. Check your internet."

    return "⚠️ API rate limit exceeded. Please wait."

# ------------------------------
# Telegram Handlers
# ------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        await update.message.reply_text("❌ Unauthorized. This bot is for private use only.")
        return

    welcome = """
🔥 *Uncensored AI Bot Ready!*
Model: `Hermes-3-Llama-3.1-8B-lorablated` – No filters, no censorship.

*Commands:*
/start – Show this menu
/clear – Clear conversation history
/model – Show current AI model
/help – Show this message

*How to use:* Just send any message. I remember our chat.
*Inline mode:* Use `@YourBot username` followed by your question in *any* chat.

⚠️ *Use responsibly.*"""
    await update.message.reply_text(welcome, parse_mode="Markdown")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        await update.message.reply_text("❌ Unauthorized.")
        return
    if user_id in conversations:
        del conversations[user_id]
    await update.message.reply_text("✅ Conversation history cleared.")

async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        await update.message.reply_text("❌ Unauthorized.")
        return
    await update.message.reply_text(f"🧠 Current AI model:\n`{MODEL_NAME}`", parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        await update.message.reply_text("❌ Unauthorized.")
        return
    help_text = """
*Available Commands:*
/start – Show welcome menu
/clear – Clear conversation history
/model – Show current AI model
/help – Show this message

*Multi‑user support* – Only pre‑authorised users can use the bot.
*Inline mode* – type @yourBotUsername your_question in any chat.
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        await update.message.reply_text("❌ Unauthorized.")
        return
    user_message = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    response = await generate_response(user_id, user_message)
    for chunk in chunk_text(response):
        await update.message.reply_text(chunk)

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        await update.inline_query.answer([], cache_time=0)
        return
    query = update.inline_query.query.strip()
    if not query:
        results = [
            InlineQueryResultArticle(
                id="1",
                title="🤖 Uncensored AI",
                description="Type your question after @YourBot, e.g., 'What is love?'",
                input_message_content=InputTextMessageContent("Send: `@YourBot your question`",
                                                              parse_mode="Markdown")
            )
        ]
        await update.inline_query.answer(results, cache_time=10)
        return

    try:
        payload = {
            "inputs": f"You are an uncensored AI. Respond concisely (max 2 sentences) to: {query}",
            "parameters": {
                "max_new_tokens": 300,
                "temperature": 0.7,
                "do_sample": True,
                "return_full_text": False,
            },
        }
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and result:
                ai_text = result[0].get("generated_text", "").strip()
            elif isinstance(result, dict):
                ai_text = result.get("generated_text", "").strip()
            else:
                ai_text = ""
            if len(ai_text) > 400:
                ai_text = ai_text[:397] + "..."
            results = [
                InlineQueryResultArticle(
                    id="1",
                    title="🤖 AI Response",
                    description=ai_text[:100],
                    input_message_content=InputTextMessageContent(ai_text)
                )
            ]
            await update.inline_query.answer(results, cache_time=0)
        else:
            await update.inline_query.answer([], cache_time=0)
    except Exception:
        await update.inline_query.answer([], cache_time=0)

# ------------------------------
# Main
# ------------------------------
def main():
    if TELEGRAM_TOKEN == "YOUR_BOT_TOKEN_HERE":
        raise ValueError("❌ TELEGRAM_TOKEN not set! Get it from @BotFather.")
    if HF_API_TOKEN == "hf_YOUR_NEW_TOKEN_HERE" or len(HF_API_TOKEN) < 10:
        raise ValueError("❌ HF_API_TOKEN not set properly! Generate a new token from huggingface.co/settings/tokens")
    if not ALLOWED_USER_IDS or ALLOWED_USER_IDS == [123456789]:
        logging.warning("⚠️ ALLOWED_USER_IDS still contains default value. Please set your own Telegram user ID.")

    print(f"🤖 Bot starting... Model: {MODEL_NAME}")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear))
    application.add_handler(CommandHandler("model", model_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    application.add_handler(InlineQueryHandler(inline_query))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()