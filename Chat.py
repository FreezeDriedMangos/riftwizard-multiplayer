

scroll_index = 0
chat_messsages = []
NUM_MESSAGES_DISPLAYED_AT_ONCE = 5

def draw_chat_messages(self, draw_pane, num_messages=None, cur_x=0):
	if num_messages == None:
		num_messages = NUM_MESSAGES_DISPLAYED_AT_ONCE if chat_string != None else 1

	end_index = len(chat_messsages)-scroll_index
	start_index = max(0, end_index-num_messages)
	messages = chat_messsages[start_index:end_index]
	messages = messages[::-1]

	if chat_string != None:
		messages.insert(0, chat_string)

	cur_y = draw_pane.get_height() - self.linesize
	for message in messages:
		self.draw_string(message, draw_pane, cur_x, cur_y)
		cur_y -= self.linesize




chat_string = None
# def open_chat_typing(self):
# 	global chat_string
# 	chat_string = ''

def process_chat_input_event(self, event, confirm_keys, abort_keys, up_keys, down_keys, backspace):
	global chat_string
	if chat_string == None:
		chat_string = ''

	if event.key in confirm_keys:
		return (chat_string, False)
	if event.key in abort_keys:
		chat_string = None
		return (None, False)

	if event.key in up_keys:
		scroll_index

	if event.key == backspace:
		chat_string = chat_string[:-1]
	else:
		chat_string += event.unicode
	return (chat_string, True)


def add_chat_message(message):
	global chat_messsages
	chat_messsages.append(message)