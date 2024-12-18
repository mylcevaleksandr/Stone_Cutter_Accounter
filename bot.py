from multiprocessing.reduction import duplicate
from typing import List, Dict
from messages import *

from config import telegram_token
import telebot
import threading
import json

from utils import create_slabs, get_current_saw_number

# Initialize the bot
bot = telebot.TeleBot(telegram_token)
# Global variable to store temporary message data for user confirmation
temporary_data: Dict[str, str] = {}
user_data: Dict


# Get user data from json file if it exists
def get_user_data() -> dict:
    """
    Get saved user data.

    :return:
        {
            user_id:
            {
                "available_saws":
                {
                     saw_number:
                     {
                        "blocks_decommissioned":
                        {
                            block_number:str,
                            block_cubic_meters:"int"
                        }
                    },
                    "new_slabs":
                    {
                        slab_number:
                        {
                            "width":int,
                            "length":int,
                            "thickness":int.
                            "square_meters":int
                        }
                    },
                    "tech_cuts":
                    {
                        "block_number":str,
                        "width":int,
                        "length":int
                        "square_meters":int
                    },
                    "new_blocks":
                    {
                        block_number:str,
                        "width":int,
                        "length":int,
                        "height":int,
                        "block_cubic_meters":int
                    }
                },
            }
        }
    """

    file = open('user_data.json', 'r')
    try:
        user_data_from_json = json.load(file)
    except FileNotFoundError:
        user_data_from_json = {}
    except json.decoder.JSONDecodeError:
        user_data_from_json = {}
    finally:
        file.close()
    return user_data_from_json


# Dictionary to store user data
user_data = get_user_data()


# Save user data to a json file
def save_user_data():
    with open('user_data.json', 'w') as file:
        json.dump(user_data, file, indent=4)


@bot.message_handler(commands=['start'])
def process_start_message(message):
    reply_message = start_message()
    user_id = str(message.chat.id)
    bot.send_message(user_id, reply_message, parse_mode='Markdown')


# Handler to process user input for saw number
@bot.message_handler(commands=['saw'])
def process_saw_number(message):
    user_id: str = str(message.chat.id)
    split_message = message.text.split()
    saw_data = {
        "blocks_decommissioned": {},
        "new_slabs": {},
        "tech_cuts": {},
        "new_blocks": {}
    }
    if len(split_message) > 1:
        saw_number = split_message[-1]
        if saw_number.isdigit():
            if user_id not in user_data:
                user_data[user_id] = {'available_saws': {saw_number: saw_data}, 'current_saw_number': saw_number}
            elif saw_number not in user_data[user_id]['available_saws']:
                user_data[user_id]['available_saws'][saw_number] = saw_data
                user_data[user_id]['current_saw_number'] = saw_number
            else:
                saw_data = user_data[user_id]['available_saws'][saw_number]
                user_data[user_id]['current_saw_number'] = saw_number
            save_user_data()
            saw_message = ""
            for key, value in saw_data.items():
                if not value:
                    empty_message = empty_entry_message(key=key, saw_number=saw_number)
                    saw_message += empty_message
                else:
                    if key == "blocks_decommissioned":
                        saw_message += blocks_decommissioned_message(key, value, saw_number)
                        saw_message += block_all_commands_message()
                    if key == "new_slabs":
                        saw_message += new_slabs_message(key, value, saw_number)
                    if key == "tech_cuts":
                        saw_message += tech_cuts_message(key, value, saw_number)
                    if key == "new_blocks":
                        saw_message += new_blocks_message(key, value, saw_number)
            bot.send_message(user_id, saw_message, parse_mode='Markdown')
        else:
            reply_message = bad_value_entered(message.text)
            bot.send_message(user_id, reply_message)

    else:
        reply_message = bad_value_entered(message.text)
        bot.send_message(user_id, reply_message)


# Handler to process user input for block number
@bot.message_handler(commands=['block'])
def process_block_number(message):
    user_id = str(message.chat.id)
    if user_id in user_data and 'available_saws' in user_data[user_id]:
        available_saws = user_data[user_id]['available_saws']
        current_saw_number = user_data[user_id].get('current_saw_number')
        if len(message.text.split()) > 2 and message.text[0] != "/block":
            block_number = message.text.split()[-2]
            new_block_value = message.text.split()[-1]
            if current_saw_number and current_saw_number in available_saws:
                blocks_decommissioned: Dict = available_saws[current_saw_number]['blocks_decommissioned']
                if block_number not in blocks_decommissioned:
                    blocks_decommissioned[block_number] = new_block_value
                    reply_message = block_decommissioned_message(block_number=block_number,
                                                                 saw_number=current_saw_number)
                    bot.send_message(user_id, reply_message)
                    save_user_data()
                else:
                    reply_message = bad_value_entered(data=message.text) + block_all_commands_message(
                        saw_number=current_saw_number)
                    bot.send_message(user_id, reply_message, parse_mode="Markdown")
            else:
                reply_message: str = select_saw_message()
                bot.send_message(user_id, reply_message)
        else:
            reply_message = bad_value_entered(data=message.text) + block_all_commands_message(
                saw_number=current_saw_number)
            bot.send_message(user_id, reply_message, parse_mode="Markdown")
    else:
        bot.send_message(user_id, "No user data found")


@bot.message_handler(commands=["slab"])
def process_slab_number(message):
    user_id: str = str(message.chat.id)
    split_message: str = message.text.split()
    block_number = split_message[1]
    slab_number: str = split_message[2]
    slab_width: int = int(split_message[3])
    slab_length: int = int(split_message[4])
    slab_thickness: int = int(split_message[5])
    if not block_number or not slab_number or not slab_width or not slab_length or not slab_thickness:
        reply_message = bad_value_entered(message.text)
        bot.send_message(user_id, reply_message)
    else:
        bot.send_message(user_id,
                         f"block:Ok {block_number}, #: {slab_number}, w: {slab_width}, l: {slab_length}, th: {slab_thickness}")
        current_saw_number = get_current_saw_number(user_id=user_id, block_number=block_number,
                                                    user_data=user_data)
        if current_saw_number:
            new_slabs = user_data[user_id]['available_saws'][current_saw_number].get('new_slabs', {})
            slab_range_start = int(slab_number)
            slab_range_end = int(slab_number)+1
            if not new_slabs:
                new_slabs = {}
            if "-" in slab_number:
                slab_range_start = int(slab_number.split("-")[0])
                slab_range_end = int(slab_number.split("-")[-1])+1
            slabs_to_append = create_slabs(block_number=block_number, start=slab_range_start,
                                           end=slab_range_end, width=slab_width, length=slab_length,
                                           thickness=slab_thickness)
            duplicate_key = None
            for key, value in slabs_to_append.items():
                if key in new_slabs:
                    duplicate_key = key
                    break
                new_slabs[key] = value
            if duplicate_key:
                reply_message = entry_already_exists_message()
                bot.send_message(user_id, reply_message)
            else:
                user_data[user_id]['available_saws'][current_saw_number]['new_slabs'].update(new_slabs)
                save_user_data()
                reply_message = slabs_added_message()
                bot.send_message(user_id, reply_message)
            # else:
            #     slab_to_append = create_slabs(block_number=block_number, start=int(slab_number),
            #                                   end=int(slab_number), width=slab_width, length=slab_length,
            #                                   thickness=slab_thickness)
            #     if not slab_to_append in new_slabs:
            #         new_slabs.update(slab_to_append)
            #         reply_message = slabs_added_message()
            #         bot.send_message(user_id, reply_message)
            #     else:
            #         reply_message = entry_already_exists_message()
            #         bot.send_message(user_id, reply_message)
        else:
            reply_message = no_data_found_message()
            bot.send_message(user_id, reply_message)


@bot.message_handler(commands=['update'])
def process_update_entry(message): ...


@bot.message_handler(commands=['delete'])
def process_delete_entry(message):
    user_id: str = str(message.chat.id)
    command = message.text.split()[0].lstrip('/')
    entry_type: str = message.text.split()[1]
    target_key: str = message.text.split()[2]
    saw_number = user_data[user_id]['current_saw_number']
    all_saws = user_data[user_id]['available_saws']
    global temporary_data
    if entry_type and target_key:
        if entry_type == 'block':
            blocks: dict = all_saws[saw_number]['blocks_decommissioned']
            if target_key in blocks:
                temporary_data = {
                    'target_key': target_key,
                    'entry_type': 'block',
                    'command': command,
                }
                reply_message = confirm_block_delete_message(saw_number=saw_number, block_number=target_key,
                                                             block_value=blocks[target_key])

                bot.send_message(user_id, reply_message)


@bot.message_handler(commands=['yes'])
def process_submit_changes(message):
    user_id = str(message.chat.id)
    global temporary_data
    key = temporary_data['target_key']
    entry_type = temporary_data['entry_type']
    command = temporary_data['command']
    saw_number = user_data[user_id]['current_saw_number']
    selected_saw = user_data[user_id]['available_saws'][saw_number]

    if entry_type == 'block':
        target_dict = selected_saw['blocks_decommissioned']
        if key in target_dict:
            bot.send_message(user_id, command)
            if command == 'update':
                new_value = temporary_data['new_value']
                target_dict[key] = new_value
                bot.send_message(user_id, f"Block {key} updated with new value {new_value} m3.")
            elif command == 'delete':
                del target_dict[key]
                bot.send_message(user_id, f"Block {key} deleted.")
    save_user_data()
    temporary_data = {}


@bot.message_handler(commands=['no'])
def process_discard_changes(message):
    global temporary_data
    temporary_data = {}


# Handler to process user input for cubic meters and calculate square
@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    print(message.text)
    bot.reply_to(message, message.text)


def start_bot_polling():
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"An error occurred: {e}")


polling_thread = threading.Thread(target=start_bot_polling)
polling_thread.start()

# my_saw_number = 7
# my_saw_data = {
#     "blocks_decommissioned": [
#         {
#             "block_number": "123E/1",
#             "block_m3": 3
#         },
#         {
#             "block_number": "123E/2",
#             "block_m3": 1
#         },
#     ],
#     "new_slabs": [
#         {
#             "123E/1-1":
#                 {
#                     "width": 1100,
#                     "length": 550,
#                     "thickness": 50,
#                     "square_meters": .60
#                 }
#         },
#         {
#             "123E/1-3":
#                 {
#                     "width": 1200,
#                     "length": 650,
#                     "thickness": 50,
#                     "square_meters": .75
#                 }
#         }
#     ],
#     "tech_cuts": [
#         {
#             "123/1":
#                 {
#                     "width": 1200,
#                     "length": 650,
#                     "square_meters": .75
#                 }
#         }
#     ],
#     "new_blocks": [
#         {
#             "123/2":
#                 {
#                     "width": 1200,
#                     "length": 650,
#                     "height": 500,
#                     "square_meters": .75
#                 }
#         }
#     ]
# }
# my_saw_message = ""
# for my_key, my_value in my_saw_data.items():
#     if not my_value:
#         my_empty_message = create_pretty_table(field_names=[my_key], rows=[["This entry is currently empty"]],
#                                                title=f"Saw number: {my_saw_number} selected")
#         my_saw_message += my_empty_message
#     else:
#         if my_key == "blocks_decommissioned":
#             my_saw_message += blocks_decommissioned_message(my_key, my_value, my_saw_number)
#         if my_key == "new_slabs":
#             my_saw_message += new_slabs_message(my_key, my_value, my_saw_number)
#         if my_key == "tech_cuts":
#             my_saw_message += tech_cuts_message(my_key, my_value, my_saw_number)
#         if my_key == "new_blocks":
#             my_saw_message += new_blocks_message(my_key, my_value, my_saw_number)

# print(my_saw_message)
print("Bot started successfully without errors!")
