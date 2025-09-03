# This script creates a Telegram bot that searches for a specific domain within a web stream.
#
# Before running this script, you need to:
# 1. Install the required libraries:
#    pip install pyTelegramBotAPI requests
# 2. Set two environment variables:
#    - BOT_TOKEN: Your Telegram Bot API token.
#    - STREAM_URL_BASE: The base URL for the stream, e.g., 'https://a-tushar-82q-fef07c6bf20a.herokuapp.com/stream/'.
#
# The bot will expect a message in the format 'id hash', e.g., '260925 ba3473', to construct the URL.

import telebot
import requests
import os
import re
import sys

# Get the bot token and stream URL base from environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
STREAM_URL_BASE = os.getenv('STREAM_URL_BASE')

# Check if the environment variables are set
if not BOT_TOKEN:
    print("Error: BOT_TOKEN environment variable is not set.")
    sys.exit(1)
if not STREAM_URL_BASE:
    print("Error: STREAM_URL_BASE environment variable is not set.")
    sys.exit(1)

# Initialize the Telegram bot
bot = telebot.TeleBot(BOT_TOKEN)

# Define the domain to search for
# You can change this to any domain you want to search for.
TARGET_DOMAIN = 'exemple.com'

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """
    Handles the /start command.
    """
    bot.reply_to(
        message,
        "Hello! I am a bot that can search for the domain "
        f"'{TARGET_DOMAIN}' on a given web stream. "
        "Please send me the stream ID and hash in the format 'id hash'.\n\n"
        "Example: 260925 ba3473"
    )

@bot.message_handler(func=lambda message: True)
def search_stream(message):
    """
    Handles all incoming text messages.
    """
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "Invalid format. Please send the message in the format 'id hash'.")
            return

        stream_id, stream_hash = parts

        # Construct the full URL for the stream
        full_url = f"{STREAM_URL_BASE}{stream_id}?hash={stream_hash}&d=true"
        
        bot.reply_to(message, f"Searching for '{TARGET_DOMAIN}' in the stream at {full_url}...")

        # Make a GET request to the URL
        response = requests.get(full_url, timeout=10)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)

        found_lines = []
        # Iterate through the response text line by line and search for the domain
        for line in response.text.splitlines():
            if re.search(r'\b' + re.escape(TARGET_DOMAIN) + r'\b', line, re.IGNORECASE):
                found_lines.append(line)

        # Reply to the user with the results
        if found_lines:
            result_text = "Found the following lines containing the domain:\n\n" + "\n".join(found_lines)
            bot.reply_to(message, result_text)
        else:
            bot.reply_to(message, f"No lines containing the domain '{TARGET_DOMAIN}' were found in the stream.")

    except requests.exceptions.RequestException as e:
        bot.reply_to(message, f"An error occurred while fetching the URL: {e}")
    except Exception as e:
        bot.reply_to(message, f"An unexpected error occurred: {e}")

# Start the bot
if __name__ == '__main__':
    print("Bot is running...")
    bot.polling(none_stop=True)
