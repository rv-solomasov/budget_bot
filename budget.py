import os
import datetime
import threading
import json
import telebot
import gspread
from google.oauth2.service_account import Credentials

CURRENT_SHEET = "test"

"""
Create a file .env containing your bot token and authorized users:
---
export BOT_TOKEN=abcdefghijklmnop12345
export AUTHORIZED_USERS='{"Username1":111111111,"Username2":222222222}'
---
Then source those variables: ~ source .env
---
Remember to deactivate your virtual environment to source those variables otherwise Python won't see them
"""

BOT_TOKEN = os.environ.get("BOT_TOKEN")
USERS_DICT = json.loads(os.environ.get("AUTHORIZED_USERS"))
AUTHORIZED_USERS = {value: key for key, value in USERS_DICT.items()}

"""
AUTHORIZED_USERS = {
    111111111 : "Username1",
    222222222 : "Username2",
}
"""


CATEGORIES = sorted(
    [
        "\U0001F6D2 Groceries",
        "\U0001F6DE Car Service",
        "\U0001F3E0 Home",
        "\U0001F444 Beauty",
        "\U0001F35F Cafe",
        "\U0001F455 Clothes",
        "\U0001F3CB Sport",
        "\U000026FD Car Fuel",
        "\U0001FAA9 Entertainment",
        "\U0001F4F1 Mobile",
        "\U0001F47E Internet",
        "\U0001F4C3 Rent",
        "\U0001F4A7 Water Fee",
        "\U0001F4A1 Electricity Fee",
        "\U0001F48A Medicine",
    ],
    key=lambda x: x[2:],
)

bot = telebot.TeleBot(BOT_TOKEN)

empty_keyboard = telebot.types.ReplyKeyboardRemove()


# set up a variable to track the last time the date check was performed
def check_date(chat_ids=AUTHORIZED_USERS.keys()):
    global CURRENT_SHEET
    print("check_date")
    # get current date and time
    now = datetime.datetime.now()

    # check if it's the first day of the month
    G_OUT = google_initial_login()
    if (now.day == 1) & G_OUT[0]:
        # send a message to the user(s)
        for chat_id in chat_ids:
            bot.send_message(
                chat_id,
                "It's the first day of the month! Your export will be there soon.",
            )
            sh = G_OUT[1].worksheet(CURRENT_SHEET)
            get_export(sh, chat_id)
        CURRENT_SHEET = str(datetime.datetime.now().date())
        try:
            G_OUT[1].add_worksheet(title=CURRENT_SHEET, rows=100, cols=20)
            sh = G_OUT[1].worksheet(CURRENT_SHEET)
            for i in range(1, len(CATEGORIES) + 1):
                sh.update_cell(i, 1, CATEGORIES[i - 1])
                sh.update_cell(i, 2, 0)
            bot.send_message(
                chat_id,
                f"Created a new sheet titled: {CURRENT_SHEET}",
            )
        except Exception as exc:
            bot.send_message(chat_id, f"Got a error when creating a new sheet: {exc}")

    elif not G_OUT[0]:
        for chat_id in chat_ids:
            bot.send_message(
                chat_id,
                f"I have trouble connecting to GSheet: {G_OUT[1]}",
            )
    else:
        pass

    # set the timer to run the function again in 24 hours
    threading.Timer(86400, check_date).start()


def google_initial_login(success=False):
    print("google-login")
    try:
        # set up credentials
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets",
        ]
        creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
        client = gspread.authorize(creds)
        # open the spreadsheet and select the first worksheet
        sheet = client.open("Budget Tracker")
        success = True
    except Exception as exc:
        return [success, exc]
    return [success, sheet]


G_OUT = google_initial_login()


def sync_test(sh=G_OUT[1].worksheet("test")):
    for i in range(1, len(CATEGORIES) + 1):
        sh.update_cell(i, 1, CATEGORIES[i - 1])


def get_export(sheet, chat_id):
    global CATEGORIES
    n_cats = len(CATEGORIES)
    data_cats = [
        elem.value for elem in sheet.range(1, 1, n_cats, 1) if elem.value != ""
    ]
    data_costs = [
        float(elem.value) if len(elem.value) > 0 else 0
        for elem in sheet.range(1, 2, len(data_cats), 2)
    ]
    export = dict(zip(data_cats, data_costs))
    export["\U0001F7F0	Total"] = sum(export.values())
    msg_export = "\n".join([f"{key}: {value}" for key, value in export.items()])
    bot.send_message(chat_id, msg_export)


def create_new_category(cat_name, g_out=G_OUT):
    global CATEGORIES
    CATEGORIES.append(cat_name)
    CATEGORIES = sorted(CATEGORIES, key=lambda x: x[2:])
    insert_index = CATEGORIES.index(cat_name)
    sh = g_out[1].worksheet(CURRENT_SHEET)
    for i in range(len(CATEGORIES), insert_index + 1, -1):
        sh.update_cell(i, 1, sh.cell(i - 1, 1).value)
        sh.update_cell(i, 2, sh.cell(i - 1, 2).value)
    sh.update_cell(insert_index + 1, 1, cat_name)
    sh.update_cell(insert_index + 1, 2, 0)


def remove_category(cat_name, g_out=G_OUT):
    global CATEGORIES
    insert_index = CATEGORIES.index(cat_name)
    sh = g_out[1].worksheet(CURRENT_SHEET)
    for i in range(insert_index + 1, len(CATEGORIES)):
        sh.update_cell(i, 1, sh.cell(i + 1, 1).value)
        sh.update_cell(i, 2, sh.cell(i + 1, 2).value)
    sh.update_cell(len(CATEGORIES), 1, "")
    sh.update_cell(len(CATEGORIES), 2, "")
    CATEGORIES.remove(cat_name)
    CATEGORIES = sorted(CATEGORIES, key=lambda x: x[2:])


def edit_category(cat_name_old, cat_name_new, g_out=G_OUT):
    global CATEGORIES
    sh = g_out[1].worksheet(CURRENT_SHEET)
    insert_index_old = CATEGORIES.index(cat_name_old)
    cat_val_old = sh.cell(insert_index_old, 2).value
    CATEGORIES.remove(cat_name_old)
    CATEGORIES.append(cat_name_new)
    CATEGORIES = sorted(CATEGORIES, key=lambda x: x[2:])
    insert_index_new = CATEGORIES.index(cat_name_new)
    if insert_index_new > insert_index_old:
        for i in range(insert_index_old + 1, insert_index_new + 1):
            sh.update_cell(i, 1, sh.cell(i + 1, 1).value)
            sh.update_cell(i, 2, sh.cell(i + 1, 2).value)
    elif insert_index_new < insert_index_old:
        for i in range(insert_index_old + 1, insert_index_new + 1, -1):
            sh.update_cell(i, 1, sh.cell(i - 1, 1).value)
            sh.update_cell(i, 2, sh.cell(i - 1, 2).value)
    sh.update_cell(insert_index_new + 1, 1, cat_name_new)
    sh.update_cell(insert_index_new + 1, 2, cat_val_old)


@bot.message_handler(commands=["sync"])
def sync_test_handler(message):
    chat_id = message.chat.id
    if chat_id in AUTHORIZED_USERS.keys():
        sync_test()
        bot.send_message(chat_id, "Synced")


@bot.message_handler(commands=["start"])
def start(message, g_out=G_OUT):
    global CURRENT_SHEET
    print("start")
    chat_id = message.chat.id
    if chat_id in AUTHORIZED_USERS.keys():
        msg = f"Hi {AUTHORIZED_USERS[chat_id]}! Type '/help' for help :)"
        bot.send_message(chat_id, msg)
        print("test")
        bot.send_message(chat_id, f"Testing Gsheet Integration")
        # write data to the spreadsheet
        if g_out[0]:
            sh = g_out[1].worksheet(CURRENT_SHEET)
            sh.update_cell(100, 20, "Test")
            bot.send_message(chat_id, f'Success. Tested "{CURRENT_SHEET}"')
            sh.update_cell(100, 20, "")
        else:
            bot.send_message(chat_id, f"Got an error: {g_out[1]}")
    else:
        bot.send_message(chat_id, f"Sorry, you are not authorized to use this bot.")


@bot.message_handler(commands=["link"])
def get_link(message, g_out=G_OUT):
    print("link")
    chat_id = message.chat.id
    if chat_id in AUTHORIZED_USERS.keys():
        if g_out[0]:
            link_text = f"Sure, here is your link: {g_out[1].url}"
            bot.send_message(chat_id, link_text)
        else:
            bot.send_message(
                chat_id,
                f"I have trouble connecting to GSheet: {g_out[1]}",
                reply_markup=empty_keyboard,
            )


@bot.message_handler(commands=["export"])
def send_export(message, g_out=G_OUT):
    print("export")
    chat_id = message.chat.id
    if chat_id in AUTHORIZED_USERS.keys():
        if g_out[0]:
            sh = g_out[1].worksheet(CURRENT_SHEET)
            get_export(sh, chat_id)
        else:
            bot.send_message(chat_id, f"Got an error: {g_out[1]}")


@bot.message_handler(commands=["help"])
def send_help(message):
    print("help")
    chat_id = message.chat.id
    if chat_id in AUTHORIZED_USERS.keys():
        text = "Hey!\nYou can add, edit and remove categories with\n/settings\nYou can add payments with\n/add\nYou can export budget for the current month manually via\n/export\nYou can get a link to the cloud spreadsheet with\n/link"
        bot.reply_to(
            message,
            text,
        )


@bot.message_handler(commands=["list"])
def send_list(message):
    global CATEGORIES
    print("list")
    chat_id = message.chat.id
    if chat_id in AUTHORIZED_USERS.keys():
        bot.reply_to(message, "Here is a list of available categories: ")
        bot.send_message(chat_id, "\n".join(CATEGORIES))


category_choice = {}


@bot.message_handler(commands=["settings"])
def get_action_category(message, g_out=G_OUT):
    print("action_category")
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.row("Add", "Remove", "Edit", "Cancel")
    chat_id = message.chat.id
    if chat_id in AUTHORIZED_USERS.keys():
        if g_out[0]:
            bot.send_message(chat_id, "What do you want to do?", reply_markup=markup)
            bot.register_next_step_handler(message, choice_handler)
        else:
            bot.send_message(
                chat_id,
                f"I have trouble connecting to GSheet: {g_out[1]}",
                reply_markup=empty_keyboard,
            )


def choice_handler(message):
    chat_id = message.chat.id
    category_choice["action"] = message.text.upper()
    if message.text.upper() == "ADD":
        keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_text = telebot.types.KeyboardButton(text="Cancel")
        keyboard.add(button_text)
        bot.send_message(
            chat_id=chat_id,
            text=f"Enter name for the new category:",
            reply_markup=keyboard,
        )
        bot.register_next_step_handler(message, category_action_add)
    elif message.text.upper() in ["REMOVE", "EDIT"]:
        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        for cat in CATEGORIES:
            markup.add(
                telebot.types.InlineKeyboardButton(
                    f"{cat}", callback_data=f"category_{cat}"
                )
            )
        markup.add(
            telebot.types.InlineKeyboardButton(f"CANCEL", callback_data=f"Cancel")
        )
        bot.send_message(
            message.chat.id,
            f"Choose the category to {message.text.lower()}:",
            reply_markup=markup,
        )
    elif message.text.upper() == "CANCEL":
        bot.send_message(chat_id, "Action cancelled", reply_markup=empty_keyboard)
    else:
        bot.send_message(chat_id, f"Your option is incorrect. Please try again.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("category_"))
def category_action_edit_remove(call, g_out=G_OUT):
    chat_id = call.message.chat.id
    call.data = call.data.lstrip("category_")
    if call.data != "Cancel":
        if g_out[0]:
            if category_choice["action"] == "EDIT":
                category_choice["to_edit"] = call.data
                keyboard = telebot.types.ReplyKeyboardMarkup(
                    row_width=1, resize_keyboard=True
                )
                button_text = telebot.types.KeyboardButton(text="Cancel")
                keyboard.add(button_text)
                bot.send_message(
                    chat_id=chat_id,
                    text=f"Enter new name for '{call.data}':",
                    reply_markup=keyboard,
                )
                bot.register_next_step_handler(call.message, category_action_edit_emoji)
            elif category_choice["action"] == "REMOVE":
                category_choice["to_remove"] = call.data
                keyboard = telebot.types.ReplyKeyboardMarkup(
                    row_width=2, resize_keyboard=True
                )
                button_yes = telebot.types.KeyboardButton(text="Yes")
                button_cancel = telebot.types.KeyboardButton(text="Cancel")
                keyboard.add(button_yes)
                keyboard.add(button_cancel)
                bot.send_message(
                    chat_id=chat_id,
                    text=f"Are you sure you want to remove '{call.data}'?",
                    reply_markup=keyboard,
                )
                bot.register_next_step_handler(
                    call.message, category_action_remove_perform
                )
        else:
            bot.send_message(
                chat_id,
                f"I have trouble connecting to GSheet: {g_out[1]}",
                reply_markup=empty_keyboard,
            )
    else:
        bot.send_message(chat_id, "Action cancelled", reply_markup=empty_keyboard)


def category_action_add(message):
    chat_id = message.chat.id
    if message.text != "Cancel":
        category_choice["add_name"] = message.text
        keyboard = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        button_cancel = telebot.types.KeyboardButton(text="Cancel")
        button_no = telebot.types.KeyboardButton(text="No emoji")
        keyboard.add(button_cancel)
        keyboard.add(button_no)
        bot.send_message(
            chat_id=chat_id,
            text=f"Choose emoji for the new category:",
            reply_markup=keyboard,
        )
        bot.register_next_step_handler(message, category_action_add_perform)
    else:
        bot.send_message(chat_id, "Action cancelled", reply_markup=empty_keyboard)


def category_action_edit_emoji(message):
    chat_id = message.chat.id
    category_choice["new_name"] = message.text
    if message.text != "Cancel":
        keyboard = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        button_cancel = telebot.types.KeyboardButton(text="Cancel")
        button_no = telebot.types.KeyboardButton(text="No emoji")
        keyboard.add(button_cancel)
        keyboard.add(button_no)
        bot.send_message(
            chat_id=chat_id,
            text=f"Enter new emoji for '{message.text}':",
            reply_markup=keyboard,
        )
        bot.register_next_step_handler(message, category_action_edit_perform)
    else:
        bot.send_message(chat_id, "Action cancelled", reply_markup=empty_keyboard)


def category_action_edit_perform(message, g_out=G_OUT):
    chat_id = message.chat.id
    cat_name_old = category_choice["to_edit"]
    if message.text != "Cancel":
        if message.text == "No emoji":
            cat_name_new = "  " + category_choice["new_name"]
        else:
            cat_name_new = message.text + " " + category_choice["new_name"]
        if g_out[0]:
            bot.send_message(chat_id, f"Working on '{cat_name_new}'!")
            edit_category(cat_name_old, cat_name_new, g_out=g_out)
            bot.send_message(
                chat_id,
                f"'{cat_name_old}' is now '{cat_name_new}'!",
                reply_markup=empty_keyboard,
            )
        else:
            bot.send_message(
                chat_id,
                f"I have trouble connecting to GSheet: {g_out[1]}",
                reply_markup=empty_keyboard,
            )
    else:
        bot.send_message(
            chat_id,
            "Action cancelled",
            reply_markup=empty_keyboard,
        )


def category_action_remove_perform(message, g_out=G_OUT):
    chat_id = message.chat.id
    if message.text == "Yes":
        if g_out[0]:
            bot.send_message(
                chat_id,
                f"Removing {category_choice['to_remove']}",
                reply_markup=empty_keyboard,
            )
            remove_category(cat_name=category_choice["to_remove"], g_out=g_out)
            bot.send_message(
                chat_id,
                f"Successfully removed {category_choice['to_remove']}",
                reply_markup=empty_keyboard,
            )
        else:
            bot.send_message(
                chat_id,
                f"I have trouble connecting to GSheet: {g_out[1]}",
                reply_markup=empty_keyboard,
            )
    elif message.text == "Cancel":
        bot.send_message(chat_id, "Action cancelled", reply_markup=empty_keyboard)


def category_action_add_perform(message, g_out=G_OUT):
    chat_id = message.chat.id
    if message.text != "Cancel":
        if message.text == "No emoji":
            new_cat_name = "  " + category_choice["add_name"]
        else:
            new_cat_name = message.text + " " + category_choice["add_name"]
        if g_out[0]:
            bot.send_message(chat_id, f"Working on '{new_cat_name}'!")
            create_new_category(cat_name=new_cat_name, g_out=g_out)
            bot.send_message(
                chat_id,
                f"New category '{new_cat_name}' is created!",
                reply_markup=empty_keyboard,
            )
        else:
            bot.send_message(
                chat_id,
                f"I have trouble connecting to GSheet: {g_out[1]}",
                reply_markup=empty_keyboard,
            )
    else:
        bot.send_message(chat_id, "Action cancelled", reply_markup=empty_keyboard)


payment_dict = {}


@bot.message_handler(commands=["add"])
def add_payment(message):
    if message.chat.id in AUTHORIZED_USERS.keys():
        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        for cat in CATEGORIES:
            markup.add(
                telebot.types.InlineKeyboardButton(
                    f"{cat}", callback_data=f"payment_{cat}"
                )
            )
        markup.add(
            telebot.types.InlineKeyboardButton(f"CANCEL", callback_data=f"Cancel")
        )
        bot.send_message(
            message.chat.id,
            f"Choose a category to add a payment:",
            reply_markup=markup,
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("payment_"))
def add_payment_handler(call):
    call.data = call.data.lstrip("payment_")
    chat_id = call.message.chat.id
    payment_dict["category"] = call.data
    if call.data != "Cancel":
        keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_text = telebot.types.KeyboardButton(text="Cancel")
        keyboard.add(button_text)
        bot.send_message(
            chat_id, f"Enter the amount for '{call.data}':", reply_markup=keyboard
        )
        bot.register_next_step_handler(call.message, process_payment)
    else:
        bot.send_message(chat_id, "Action cancelled", reply_markup=empty_keyboard)


def process_payment(message, g_out=G_OUT):
    chat_id = message.chat.id
    cat_payment = payment_dict["category"]
    if message.text != "Cancel":
        if g_out[0]:
            try:
                sh = g_out[1].worksheet(CURRENT_SHEET)
                payment_index = CATEGORIES.index(cat_payment) + 1
                payment_amount = float(sh.cell(payment_index, 2).value)
                payment_amount += float(message.text)
                sh.update_cell(payment_index, 2, payment_amount)
                bot.send_message(
                    chat_id,
                    f"Added {message.text} to '{cat_payment}'!",
                    reply_markup=empty_keyboard,
                )
            except Exception as exp:
                bot.send_message(
                    chat_id,
                    f"Got an error: {exp}",
                    reply_markup=empty_keyboard,
                )
        else:
            bot.send_message(
                chat_id,
                f"I have trouble connecting to GSheet: {g_out[1]}",
                reply_markup=empty_keyboard,
            )
    else:
        bot.send_message(chat_id, "Action cancelled", reply_markup=empty_keyboard)


# start the timer for the first time
check_date()
bot.infinity_polling()
