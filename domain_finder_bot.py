import telebot
import requests
import os
import re
import sys
import io
import tempfile

# Get the bot token from environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Check if the environment variable is set
if not BOT_TOKEN:
    print("Error: BOT_TOKEN environment variable is not set.")
    sys.exit(1)

# Initialize the Telegram bot
bot = telebot.TeleBot(BOT_TOKEN)

# A dictionary to store user states for the conversational flow
user_states = {}
# A dictionary to store user data (like the file path)
user_data = {}

@bot.message_handler(commands=['start'])
def handle_start(message):
    """
    Handles the /start command and initiates the conversation.
    Resets the session for a new file.
    """
    chat_id = message.chat.id
    user_states[chat_id] = 'awaiting_url'
    user_data[chat_id] = {}
    bot.send_message(
        chat_id,
        "👋 Welcome!\n\nPlease send me the URL of the large file you want to search. "
        "This file will be used for all subsequent domain searches until you type /start again."
    )

@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'awaiting_url')
def handle_url(message):
    """
    Downloads the file once and stores it locally.
    """
    chat_id = message.chat.id
    url = message.text.strip()

    if not url.startswith(('http://', 'https://')):
        bot.send_message(chat_id, "⚠️ Please enter a valid URL starting with http:// or https://")
        return

    try:
        bot.send_message(chat_id, "⏳ Downloading file... Please wait, this may take a while for large files.")

        response = requests.get(url, stream=True, timeout=600)
        response.raise_for_status()

        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        for chunk in response.iter_content(chunk_size=1024*1024):  # 1 MB chunks
            if chunk:
                temp_file.write(chunk)
        temp_file.close()

        # Store file path
        user_data[chat_id]['file_path'] = temp_file.name
        user_states[chat_id] = 'url_received'

        bot.send_message(
            chat_id,
            "✅ File downloaded and saved!\nNow send me a domain (e.g., example.com) to search."
        )

    except Exception as e:
        bot.send_message(chat_id, f"❌ Error downloading file: {e}")

@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'url_received')
def handle_domain_and_search(message):
    """
    Searches the local file for the given domain and sends results.
    """
    chat_id = message.chat.id
    target_domain = message.text.strip()
    file_path = user_data[chat_id].get('file_path')

    if not file_path:
        bot.send_message(chat_id, "⚠️ No file loaded. Please use /start again.")
        return

    found_lines_stream = io.BytesIO()
    found_lines_count = 0

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if re.search(r'\b' + re.escape(target_domain) + r'\b', line, re.IGNORECASE):
                    found_lines_stream.write(line.encode("utf-8"))
                    found_lines_count += 1

        if found_lines_count > 0:
            found_lines_stream.seek(0)
            bot.send_document(
                chat_id,
                found_lines_stream,
                visible_file_name=f"search_results_{target_domain}.txt",
                caption=f"✅ Found {found_lines_count} matching lines for '{target_domain}'.\n\n"
                        "You can send another domain to search the same file."
            )
        else:
            bot.send_message(chat_id, f"❌ No results found for '{target_domain}'.\nTry another domain!")

    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error while searching: {e}")

    finally:
        found_lines_stream.close()

# Start the bot
if __name__ == '__main__':
    print("🤖 Bot is running...")
    bot.polling(none_stop=True)
