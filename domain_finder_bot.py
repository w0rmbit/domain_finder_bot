# This script creates a Telegram bot that guides the user through a multi-step process:
# 1. User starts the bot and is prompted for a file URL.
# 2. User sends the URL, and the bot then prompts for a domain to search for.
# 3. User sends the domain, and the bot searches the file for matching lines.
# 4. The bot sends a .txt file containing the results back to the user.
#
# To run this script, you must set the BOT_TOKEN environment variable.

import telebot
import requests
import os
import re
import sys
import tempfile
import io

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
# A dictionary to store user data (like the URL and domain)
user_data = {}

@bot.message_handler(commands=['start'])
def handle_start(message):
    """
    Handles the /start command and initiates the conversation.
    """
    chat_id = message.chat.id
    user_states[chat_id] = 'awaiting_url'
    bot.send_message(
        chat_id,
        "Welcome! Please send me the URL of the large file you want to search."
    )

@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'awaiting_url')
def handle_url(message):
    """
    Handles the user's file URL input.
    """
    chat_id = message.chat.id
    url = message.text.strip()

    # Simple URL validation
    if not url.startswith(('http://', 'https://')):
        bot.send_message(chat_id, "Please enter a valid URL starting with http:// or https://")
        return

    # Store the URL and update the user's state
    user_data[chat_id] = {'url': url}
    user_states[chat_id] = 'awaiting_domain'
    bot.send_message(
        chat_id,
        "Thanks! Now, please send me the domain you want to search for (e.g., example.com)."
    )

@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'awaiting_domain')
def handle_domain(message):
    """
    Handles the user's domain input, performs the search, and sends the results.
    """
    chat_id = message.chat.id
    target_domain = message.text.strip()
    url = user_data[chat_id].get('url')

    # Reset state immediately to prevent re-processing during file generation
    user_states[chat_id] = None

    if not url:
        bot.send_message(chat_id, "An error occurred. Please start again with /start.")
        return

    bot.send_message(
        chat_id,
        f"Searching for lines containing '{target_domain}' in the file. This may take a moment for large files..."
    )

    try:
        # Use an in-memory byte stream instead of a temporary file for better performance
        # and to avoid filesystem issues on some platforms like Koyeb.
        found_lines_stream = io.BytesIO()
        
        # Use streaming to handle large files efficiently
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status() # Raise an HTTPError for bad responses

        found_lines_count = 0
        for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
            # The search is on a line-by-line basis
            for line in chunk.splitlines():
                if re.search(r'\b' + re.escape(target_domain) + r'\b', line, re.IGNORECASE):
                    found_lines_stream.write((line + '\n').encode('utf-8'))
                    found_lines_count += 1
        
        if found_lines_count > 0:
            found_lines_stream.seek(0)  # Rewind the stream to the beginning
            
            # Send the document with an explicit filename
            bot.send_message(chat_id, f"Found {found_lines_count} matching lines! Sending the file now.")
            bot.send_document(chat_id, found_lines_stream, visible_file_name=f"search_results_{target_domain}.txt", caption=f"Results for '{target_domain}'.")
        else:
            bot.send_message(chat_id, f"No lines containing '{target_domain}' were found in the file.")

    except requests.exceptions.RequestException as e:
        bot.send_message(chat_id, f"An error occurred while fetching the URL: {e}")
    except Exception as e:
        bot.send_message(chat_id, f"An unexpected error occurred: {e}")
    finally:
        # Close the in-memory stream
        found_lines_stream.close()

# Start the bot
if __name__ == '__main__':
    print("Bot is running...")
    bot.polling(none_stop=True)
