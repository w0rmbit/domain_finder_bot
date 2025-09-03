# This script creates a Telegram bot with a streamlined conversational flow:
# 1. User starts the bot and is prompted for a file URL.
# 2. User sends the URL, and the bot stores it, then prompts for a domain to search.
# 3. The bot remains in this "ready for search" state. The user can now send multiple
#    domains to search on the same file without needing to re-upload it.
# 4. The bot searches the file for each domain and sends a .txt file with the results.
#
# To run this script, you must set the BOT_TOKEN environment variable.

import telebot
import requests
import os
import re
import sys
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
# A dictionary to store user data (like the URL)
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
        "Welcome! Please send me the URL of the large file you want to search. This will be the file for all subsequent searches until you type /start again."
    )

@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'awaiting_url')
def handle_url(message):
    """
    Handles the user's file URL input and sets the 'url_received' state.
    """
    chat_id = message.chat.id
    url = message.text.strip()

    # Simple URL validation
    if not url.startswith(('http://', 'https://')):
        bot.send_message(chat_id, "Please enter a valid URL starting with http:// or https://")
        return

    # Store the URL and update the user's state
    user_data[chat_id]['url'] = url
    user_states[chat_id] = 'url_received'
    bot.send_message(
        chat_id,
        "Thanks! I have the file URL. Now, you can send me any domain you want to search for (e.g., example.com).\n\n"
        "You can send multiple domains one after another to search the same file. To start a new search on a different file, use the /start command."
    )

@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'url_received')
def handle_domain_and_search(message):
    """
    Handles subsequent domain search requests on the stored URL.
    """
    chat_id = message.chat.id
    target_domain = message.text.strip()
    url = user_data[chat_id].get('url')

    if not url:
        bot.send_message(chat_id, "An error occurred. Please use /start to begin a new session.")
        return

    bot.send_message(
        chat_id,
        f"Searching for lines containing '{target_domain}' in the file. This may take a moment for large files..."
    )

    try:
        found_lines_stream = io.BytesIO()
        
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()

        found_lines_count = 0
        for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
            if chunk:
                # The search is on a line-by-line basis
                for line in chunk.splitlines():
                    if re.search(r'\b' + re.escape(target_domain) + r'\b', line, re.IGNORECASE):
                        found_lines_stream.write((line + '\n').encode('utf-8'))
                        found_lines_count += 1
        
        if found_lines_count > 0:
            found_lines_stream.seek(0)
            bot.send_message(chat_id, f"Found {found_lines_count} matching lines! Sending the file now.")
            bot.send_document(
                chat_id, 
                found_lines_stream, 
                visible_file_name=f"search_results_{target_domain}.txt", 
                caption=f"Results for '{target_domain}'.\n\nSend another domain to search this file."
            )
        else:
            bot.send_message(chat_id, f"No lines containing '{target_domain}' were found in the file. You can send another domain to search the same file.")

    except requests.exceptions.RequestException as e:
        bot.send_message(chat_id, f"An error occurred while fetching the URL: {e}")
    except Exception as e:
        bot.send_message(chat_id, f"An unexpected error occurred: {e}")
    finally:
        found_lines_stream.close()

# Start the bot
if __name__ == '__main__':
    print("Bot is running...")
    bot.polling(none_stop=True)
