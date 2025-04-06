import requests  # Import requests for API calls
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import os
import time  # Import time module to track timestamps
import json

# File to store data
DATA_FILE = "bot_data.json"

# Load data from the JSON file
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as file:
            return json.load(file)
    return {"user_coins": {}, "user_referrals": {}}

# Save data to the JSON file
def save_data(data):
    with open(DATA_FILE, "w") as file:
        json.dump(data, file)

# Replace with your SMM panel API key
API_KEY = "70e4f31e660d5a448d32753563cbdfb5"

# Replace with your channel username (without @)
CHANNEL_USERNAME = "jdsmm11"

# Define conversation state
LINK = 0

# Dictionary to store the last order time for each user
user_last_order_time = {}

# Load data from the file
data = load_data()
user_coins = data.get("user_coins", {})
user_referrals = data.get("user_referrals", {})

# Debugging: Print the referrals dictionary
print(f"User Referrals: {user_referrals}")

# Function to check if the user is a member of the channel
async def is_user_in_channel(user_id: int, bot_token: str) -> bool:
    url = f"https://api.telegram.org/bot{bot_token}/getChatMember"
    params = {
        "chat_id": f"@{CHANNEL_USERNAME}",
        "user_id": user_id
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        result = response.json()
        status = result.get("result", {}).get("status", "")
        # Check if the user is a member or an administrator
        return status in ["member", "administrator", "creator"]
    return False

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    bot_token = context.bot.token

    # Check if the user is in the channel
    if not await is_user_in_channel(user_id, bot_token):
        await update.message.reply_text(
            f"You must join our channel first to use this bot: https://t.me/{CHANNEL_USERNAME}"
        )
        return

    # Initialize coins for new users
    if user_id not in user_coins:
        user_coins[user_id] = 0

    # Check for referral
    args = context.args
    if args:
        try:
            referrer_id = int(args[0])
            if referrer_id != user_id:  # Prevent self-referral
                # Update the user_referrals dictionary
                if referrer_id in user_referrals:
                    if user_id not in user_referrals[referrer_id]:  # Avoid duplicate entries
                        user_referrals[referrer_id].append(user_id)

                        # Reward the referrer
                        if referrer_id in user_coins:
                            user_coins[referrer_id] += 300
                        else:
                            user_coins[referrer_id] = 300

                        # Save data to the file
                        save_data({"user_coins": user_coins, "user_referrals": user_referrals})

                        await update.message.reply_text(
                            f"Thank you for joining! You were referred by user {referrer_id}."
                        )
                        await context.bot.send_message(
                            chat_id=referrer_id,
                            text=f"Congratulations! You earned 300 coins for referring user {user_id}."
                        )
                else:
                    user_referrals[referrer_id] = [user_id]

                    # Reward the referrer
                    if referrer_id in user_coins:
                        user_coins[referrer_id] += 300
                    else:
                        user_coins[referrer_id] = 300

                    # Save data to the file
                    save_data({"user_coins": user_coins, "user_referrals": user_referrals})

                    await update.message.reply_text(
                        f"Thank you for joining! You were referred by user {referrer_id}."
                    )
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"Congratulations! You earned 300 coins for referring user {user_id}."
                    )
        except ValueError:
            pass  # Ignore invalid referral IDs

    # Provide the referral link
    referral_link = f"https://t.me/{context.bot.username}?start={user_id}"
    await update.message.reply_text(
        f"Welcome! You can now use the bot. Here are the commands:\n"
        f"/start - Start the bot\n"
        f"/help - Get help\n"
        f"/order - Place an order\n"
        f"/coins - Check your coin balance\n"
        f"/referrals - Check your referrals\n\n"
        f"Your referral link: {referral_link}"
    )

# Help command handler
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Here are the commands you can use:\n"
        "/start - Start the bot\n"
        "/help - Get help\n"
        "/order - Place an order\n"
        "/referrals - Check your referrals"
    )

# Referrals command handler
async def referrals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    referral_count = len(user_referrals.get(user_id, []))
    referral_link = f"https://t.me/{context.bot.username}?start={user_id}"
    await update.message.reply_text(
        f"You have referred {referral_count} users to the bot.\n"
        f"Your referral link: {referral_link}"
    )

# Coins command handler
async def coins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    total_coins = user_coins.get(user_id, 0)
    await update.message.reply_text(
        f"You have a total of {total_coins} coins."
    )

# Order conversation: Ask for link
async def order_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    bot_token = context.bot.token

    # Check if the user is in the channel
    if not await is_user_in_channel(user_id, bot_token):
        await update.message.reply_text(
            f"You must join our channel first to use this bot: https://t.me/{CHANNEL_USERNAME}"
        )
        return ConversationHandler.END

    # Check if the user has enough coins
    if user_coins.get(user_id, 0) < 1000:
        await update.message.reply_text(
            "You need at least 1000 coins to place an order. Use your referral link to earn more coins."
        )
        return ConversationHandler.END

    current_time = time.time()

    # Check if the user has placed an order within the last 90 seconds
    if user_id in user_last_order_time:
        last_order_time = user_last_order_time[user_id]
        if current_time - last_order_time < 90:
            remaining_time = int(90 - (current_time - last_order_time))
            await update.message.reply_text(
                f"You can only place an order every 90 seconds. Please wait {remaining_time} seconds before trying again."
            )
            return ConversationHandler.END

    # Update the last order time for the user
    user_last_order_time[user_id] = current_time

    await update.message.reply_text("Please provide the link for your order:")
    return LINK

# Order conversation: Place the order
async def order_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    link = update.message.text

    # Predefined service ID and quantity
    service_id = 459
    quantity = 1000

    # Prepare API request data
    data = {
        'key': API_KEY,
        'action': 'add',
        'service': service_id,
        'link': link,
        'quantity': quantity
    }

    try:
        # Send request to SMM panel API
        response = requests.post("https://jdsmm.in/api/v2", data=data)
        result = response.json()

        # Handle API response
        if response.status_code == 200 and result.get("order"):
            order_id = result["order"]

            # Deduct 1000 coins
            user_coins[user_id] -= 1000

            # Save updated data
            save_data({"user_coins": user_coins, "user_referrals": user_referrals})

            await update.message.reply_text(
                f"Order placed successfully! Your order ID is: {order_id}\n"
                f"Views: {quantity}\n"
                f"Link: {link}\n"
                f"Remaining coins: {user_coins[user_id]}"
            )
        else:
            error_message = result.get("error", "Unknown error occurred.")
            await update.message.reply_text(
                f"Failed to place the order. Error: {error_message}"
            )
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {str(e)}")

    return ConversationHandler.END

# Cancel the order process
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Order process has been canceled.")
    return ConversationHandler.END

# Main function to run the bot
def main():
    # Retrieve the bot token from the environment variable
    bot_token=("7628473825:AAH1Imf2ByYqDsdEv3ymnEieeKdGkIrW8mM")

   

    # Create the bot application
    app = ApplicationBuilder().token(bot_token).build()

    # Define conversation handler for the /order command
    order_handler = ConversationHandler(
        entry_points=[CommandHandler("order", order_start)],
        states={
            LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_link)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("coins", coins))
    app.add_handler(order_handler)  # Add conversation handler for /order

    # Start the bot
    print("Bot is up and running!")
    app.run_polling()

if __name__ == "__main__":
    main()
