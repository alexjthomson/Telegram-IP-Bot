import os
import io
import sys
import json
import time
import telepot
import requests
from telepot.loop import MessageLoop
import logging
import logging.handlers

#####################################################################################################################################################
# CONSTANTS                                                                                                                                         #
#####################################################################################################################################################

CONFIGURATION_FILE_PATH = "configuration.json"                      # Configuration file name.

LOG_LEVEL               = logging.INFO                              # Logging level.
LOG_DATE_FORMAT         = "%Y-%m-%d %H:%M:%S"                       # Date-time format used in all log files.
LOG_FILE_NAME           = "ipbot.log"                               # Bot log file name.
LOG_FILE_ENCODING       = "utf-8"                                   # Encoding used for log files.
LOG_FILE_MAX_BYTES      = 32 * 1024 * 1024                          # Maximum number of bytes a single log file can take up.
LOG_FILE_BACKUP_COUNT   = 5                                         # Number of log file backups to maintain.

#####################################################################################################################################################
# LOGGING                                                                                                                                           #
#####################################################################################################################################################

# Create basic configuration for logging. This will make the root logger write to stdout:
logging.basicConfig()

# Create the log formatter:
LOG_FORMATTER = logging.Formatter("[{asctime}] [{levelname}] {name}: {message}", LOG_DATE_FORMAT, style='{')

# Create the log stream handler:
LOG_STREAM_HANDLER = logging.StreamHandler()
LOG_STREAM_HANDLER.setLevel(LOG_LEVEL)
LOG_STREAM_HANDLER.setFormatter(LOG_FORMATTER)

# Create the log file handler:
LOG_FILE_HANDLER = logging.handlers.RotatingFileHandler(
    filename    = LOG_FILE_NAME,
    encoding    = LOG_FILE_ENCODING,
    maxBytes    = LOG_FILE_MAX_BYTES,
    backupCount = LOG_FILE_BACKUP_COUNT
)
LOG_FILE_HANDLER.setFormatter(LOG_FORMATTER)

# configure_logger
# logger_name: Name of the logger.
# This method creates and configures a logger, then finally returns it. 
def configure_logger(logger_name):
    logger = logging.getLogger(logger_name)
    logger.setLevel(LOG_LEVEL)
    for handler in logger.handlers:
        logger.removeHandler(handler)
    logger.addHandler(LOG_STREAM_HANDLER)
    logger.addHandler(LOG_FILE_HANDLER)
    return logger

# Configure the root logger:
LOGGER = configure_logger("root")

#####################################################################################################################################################
# FILESYSTEM LOGIC                                                                                                                                  #
#####################################################################################################################################################

# file_exists
# path: Path to the target file.
# This method returns true if the file path specified is a readable file that exists.
def file_exists(path):
    return os.path.isfile(path) and os.access(path, os.R_OK)

# read_json
# path: Path to the JSON file.
# This method returns the JSON object read from the target file path. None is returned if the read operation failed.
def read_json(path):
    # Try to read the JSON data from the specified path:
    try:
        # Open the file in read mode:
        with open(path, "r") as file:
            # Try load the JSON data from the target file:
            data = json.load(file)
            # Log the read operation to the root logger:
            LOGGER.info(f"Read JSON data at `{path}`.")
            # Return the read JSON object:
            return data
    # Catch any exception that occurs during the read operation:
    except Exception as exception:
        # Log the exception with an error message:
        LOGGER.exception(exception)
        LOGGER.error(f"Failed to read JSON data from `{path}`.")
        # Return None because nothing was read:
        return None

# write_json
# path: Path to write the JSON file to.
# data: JSON file data to write to the file.
# Writes JSON data to a JSON file and returns either true or false depending on if the operation was successful.
def write_json(path, data):
    # Try to write the JSON data to the specified path:
    try:
        # Opent the target file in write mode:
        with open(path, "w") as file:
            # Dump the JSON data to the target file:
            json.dump(file, data, indent = 4)
            # Log the write operation to the root logger:
            LOGGER.info(f"Wrote JSON data to `{path}`.")
            # Return True since the write operation was successful:
            return True
    # Catch any exception that occurs during the write operation:
    except Exception as exception:
        # Log the exception with an error message:
        LOGGER.exception(exception)
        LOGGER.error(f"Failed to write JSON data to `{path}`")
        # Return False since the write operation was unsuccessful:
        return False

#####################################################################################################################################################
# JSON CONFIGURATION                                                                                                                                #
#####################################################################################################################################################

# read_field
# key: Name of the key within the dictionary.
# dictionary: Dictionary to read from.
# Reads and returns the value of a field. If the value cannot be read, None is returned.
def read_field(key, dictionary):
    try:
        value = configuration[key]
        if value != None:
            return value
        LOGGER.info(f"Read value of `{key}`.")
    except Exception as exception:
        LOGGER.exception(exception)
    LOGGER.error(f"Failed to read value of `{key}`.")
    return None

# Try read configuration file:
if file_exists(CONFIGURATION_FILE_PATH):
    # Read JSON configuration:
    configuration = read_json(CONFIGURATION_FILE_PATH)
    # Check if configuration file was read successfully:
    if configuration != None:
        # Read configuration fields:
        bot_token       = read_field("bot_token",      configuration)
        admin_username  = read_field("admin_username", configuration)
        admin_chat_id   = read_field("admin_chat_id",  configuration)
        if bot_token == None or admin_username == None or admin_chat_id == None:
            LOGGER.error("Failed to read JSON configuration.")
            print("Either repair the existing JSON configuration, or delete it and re-run this script.")
            sys.exit(1)
        # Log read successful operation:
        LOGGER.info("Successfully read JSON configuration.")
    # Read operation was not successful:
    else:
        LOGGER.error("Failed to read JSON configuration file.")
        sys.exit(1)

# Configuration file does not exist:
else:
    LOGGER.warning("No configuration file found, creating one...")
    write_json(
        CONFIGURATION_FILE_PATH,
        {
            "bot_token": "bot token here",
            "admin_username": "Telegram username here",
            "admin_chat_id": 12345
        }
    )
    print("Please edit the configuration file and re-run this script.")
    sys.exit(0)

#####################################################################################################################################################
# GLOBAL VARIABLES                                                                                                                                  #
#####################################################################################################################################################

last_ip = None                                                      # Last public IP address recorded for the host machine.

#####################################################################################################################################################
# IP FEATURES                                                                                                                                       #
#####################################################################################################################################################

# get_ip
# Gets and returns the public ip address of the host machine. If this method fails to get the host machine IP address, None is returned; otherwise,
# the body of the response is returned as a UTF-8 string.
def get_ip():
    try:
        # Query the public IP address of the host machine:
        response = requests.get("https://api.ipify.org", verify=False, timeout=10.0)
        # Validate the response status code is "200 OK":
        if response.status_code == 200:
            # Decode the response body:
            response_body = response.content.decode("utf8")
            # Log response:
            LOGGER.info(f"Response from `https://api.ipify.org`: `{response_body}`.")
            # Return the response body:
            return response_body
        # The response code is not "200 OK":
        else:
            # Log that something has gone wrong:
            LOGGER.error(f"Failed to get IP address (response.status_code: `{response.status_code}`).")
            # Return None:
            return None
    except Exception as exception:
        # Log that an unexpected exception occurred while trying to obtain the host machine public IP address:
        LOGGER.exception(exception)
        LOGGER.error("An unexpected exception occurred while trying to obtain the public IP address of the host machine.")
        # Return None:
        return None

# check_ip
# Checks the public IP address of the host machine and attempts to send the new IP address into the admin_chat_id
def check_ip():
    global last_ip
    # Get the current public IP address of the host machine:
    current_ip = get_ip()
    # Check if IP address is None:
    if current_ip == None:
        LOGGER.error("Failed to update IP address.")
    # Check if the current IP of the host machine has changed:
    elif current_ip != last_ip:
        # Construct a message containing the new IP addresses:
        message = f"New public IP address detected: `{current_ip}`."
        # Print the message to the console:
        LOGGER.info(message)
        # Send the new IP address to the target chat ID:
        update_ip = True
        if admin_chat_id != None:
            update_ip = send_message(admin_chat_id, message)
        # Update last IP address:
        if update_ip:
            last_ip = current_ip

# Get the current IP address:
#last_ip = get_ip()

#####################################################################################################################################################
# TELEGRAM BOT                                                                                                                                      #
#####################################################################################################################################################

# send_message
# Sends a message from the Telegram bot.
def send_message(chat_id, message):
    global bot
    try:
        bot.sendMessage(chat_id, message)
        LOGGER.info(f"Sent message: `{message}` to chat ID: `{chat_id}`.")
        return True
    except Exception as exception:
        LOGGER.exception(exception)
        LOGGER.error("An unexpected exception occurred while trying to send a message.")
        return False

# telepot_handle
# Telepot message loop handle.
def telepot_handle(msg):
    try:
        # Get basic information about the incoming message:
        content_type, chat_type, chat_id = telepot.glance(msg)
        chat_username = msg["from"]["username"]
        LOGGER.info(f"Received `{chat_type} {content_type}` message from `{chat_username}` (chat_id: `{chat_id}`): `{msg.text}`.")
        # must be text, private chat, and by specified user
        if (content_type == 'text') and (chat_type == 'private') and (chat_username == admin_username) and (chat_id == admin_chat_id):
            # Get public ip address:
            ip = get_ip()
            # Check if IP is none:
            if ip == None:
                send_message("Failed to obtain IP address.")
            # Send IP address to user:
            else:
                send_message(chat_id, f"IP: `{ip}`.")
            #bot.sendMessage(chat_id, str(chat_id))
        else: # Assume anyone else who is communicating with the bot is not authorized
            # Log this:
            LOGGER.warning(f"Received message from unauthorized user: `{chat_username}` (chat_id: `{chat_id}`).")
            # Send message:
            send_message(chat_id, "You are not authorized to interact with this bot.")
    except Exception as exception:
        # Log exception:
        LOGGER.exception(exception)
        LOGGER.error("An unexpected exception occurred while responding to a chat callback.")

# Start Telegram bot:
bot = telepot.Bot(bot_token)
MessageLoop(bot, telepot_handle).run_as_thread()
LOGGER.info("Telegram bot started and is listening for messages.")

#####################################################################################################################################################
# MAIN LOOP                                                                                                                                         #
#####################################################################################################################################################

# Check for change in IP address:
while True:
    try:
        check_ip()
    except Exception as exception:
        LOGGER.exception(exception)
        LOGGER.error("An unexpected exception occurred while checking the public IP address of the host machine.")
    time.sleep(60)