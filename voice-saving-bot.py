"""
Bot that saves voices and attaching it to command that users
sets and then it can be acquired via this command with "-" prefix
"""
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler

import bot
import os
import string
from command_filter import filter_command

COMMAND, WRONG_COMMAND = range(2)


class VoiceSavingBot(bot.Bot):
	"""
	Voice Saving Bot encapsulates Bot class
	"""

	def __init__(self):
		"""
		Construct a new 'VoiceSavingBot' object.

		:return: nothing
		"""
		super().__init__()

		# Allowed characters for command
		self.allowed_characters = set(string.ascii_lowercase + string.digits + '_')
		self.voice_file_name = None
		self.add_handlers(self.dispatcher)

	def add_handlers(self, dispatcher):
		"""
		Register handlers

		:param dispatcher: Updater.dispatcher
		:return: nothing
		"""
		# Command Handlers
		dispatcher.add_handler(CommandHandler('start', self.start))

		# Conversation Handlers
		dispatcher.add_handler(ConversationHandler(
			entry_points=[MessageHandler(Filters.voice, self.voice)],

			states={
				COMMAND: [MessageHandler(Filters.text, self.command)],

				WRONG_COMMAND: [MessageHandler(Filters.text, self.wrong_command)]
			},

			fallbacks=[CommandHandler('cancel', self.cancel)],
		))  # Voice Saving

		# Message Handlers
		dispatcher.add_handler(MessageHandler(filter_command, self.retrieve))  # Retrieve command starting with -
		dispatcher.add_handler(MessageHandler(Filters.command, self.unknown))  # Unknown Command

	def start(self, update: Update, context: CallbackContext):
		"""
		Bot /start command

		:param update: Update object
		:param context: CallbackContext object
		:return: nothing
		"""
		self.logger.info("User %s %s with id: %d started bot", update.effective_user.first_name,
						 update.effective_user.last_name,
						 update.effective_user.id)

		context.bot.send_message(chat_id=update.effective_chat.id,
								 text="I'm a bot, please talk to me!")

	def voice(self, update: Update, context: CallbackContext):
		"""
		Downloads voice message and goes to command func

		:param update: Update object
		:param context: CallbackContext object
		:return: to command func
		"""
		voice_id = update.message.voice.file_id
		user_id = update.effective_user.id

		file = context.bot.getFile(update.message.voice.file_id)
		self.voice_file_name = str(user_id) + '__' + voice_id
		file_name = self.voice_file_name + '.ogg'
		file_path = 'voice_messages/' + file_name
		file.download(file_path)

		self.logger_message(update, 'sent voice stored as ' + file_name)

		update.message.reply_text(
			'Voice saved! Please send me a command which you want it to refer to! Just write down the word (without /?! or ~).'
			'Or just send /cancel if you changed your mind.')

		return COMMAND

	def command(self, update: Update, context: CallbackContext):
		"""
		Sets command for voice and saves it to DB

		:param update: Update object
		:param context: CallbackContext object
		:return: ends Conversation or to wrong_command func
		"""
		command = update.message.text

		check = self.is_proper_command_check(update, command)

		if check is True:
			self.logger_message(update, 'set command for ' + self.voice_file_name + ' named ' + command)

			if self.insert_voice_message(update, command):
				return ConversationHandler.END
		else:
			return WRONG_COMMAND

	def wrong_command(self, update: Update, context: CallbackContext):
		"""
		Sets command for voice and saves it to DB

		:param update: Update object
		:param context: CallbackContext object
		:return: ends Conversation or to wrong_command func
		"""
		self.command(update, context)

	def cancel(self, update: Update, context: CallbackContext):
		"""
		Cancel conversation

		:param update: Update object
		:param context: CallbackContext object
		:return: ends Conversation
		"""
		self.logger_message(update,
							'cancelled voice saving conversation. File ' + self.voice_file_name + 'will be deleted.')

		update.message.reply_text("Bye! Don't be afraid, voice message is going to be deleted right now!")

		os.remove('voice_messages/' + self.voice_file_name + '.ogg')

		return ConversationHandler.END

	def retrieve(self, update: Update, context: CallbackContext):
		"""
		Gets voice message via command

		:param update: Update object
		:param context: CallbackContext object
		:return: voice message or text message
		"""
		message = update.message.text

		self.db_cursor.execute("SELECT filename FROM voice_messages WHERE command =%s", (message,))

		result = self.db_cursor.fetchone()
		filename = result[0]

		if result is not None:
			self.logger_message(update, 'retrieved message ' + filename + ' with ' + message + ' command')

			file_path = 'voice_messages/' + filename + '.ogg'
			file = open(file_path, 'rb')

			context.bot.send_voice(chat_id=update.effective_chat.id, voice=file)
		else:
			context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, nothing found for this command")

	def unknown(self, update: Update, context: CallbackContext):
		"""
		Responds to unknown command with '/'

		:param update: Update object
		:param context: CallbackContext object
		:return: text message
		"""
		self.logger_message(update, 'tried unknown command: ' + update.message.text)

		context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")

	def insert_voice_message(self, update: Update, command: str):
		"""
		Inserts voice message and command attached to it by user to DB

		:param update: Update object
		:param command: string attached to voice by user
		:return: ends Conversation or to wrong_command func
		"""
		sql = "INSERT INTO voice_messages (user_id, filename, command) VALUES (%s, %s, %s)"
		val = (update.effective_user.id, self.voice_file_name, '-' + command)
		self.db_cursor.execute(sql, val)
		self.db.commit()

		update.message.reply_text(
			'Voice message is saved! You can access it by sending it with "-" prefix, check it out!')

		return True

	def is_proper_command_check(self, update: Update, command: str):
		"""
		Checks command entered by user if its suits filter

		:param update: Update object
		:param command: string attached to voice by user
		:return: bool
		"""
		check = set(command) <= self.allowed_characters

		if check is False:
			self.logger_message(update, 'entered wrong command ' + command)
			update.message.reply_text(
				'Sry, your message contains something beside characters and underscore, please enter another one!')

			return False
		else:
			return True


bot = VoiceSavingBot()
bot.enable()
