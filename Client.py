# installing dependencies locally: https://stackoverflow.com/a/53925671/9643841

#
# used for online multiplayer
#
import socket # for socket
import sys


import urllib.parse
import urllib.request


import mods.API_Multiplayer.lib.websocket as websocket_client

import threading
def on_open(ws):
	sendThread = threading.Thread(target=send, args=[ws])
	sendThread.daemon = True
	sendThread.start()

def on_message(ws, message):
    print(message)

def on_error(ws, error):
    print(error)

def on_close(ws, close_status_code, close_msg):
    print("### closed ###")

# def on_open(ws):
#     def run(*args):
#         for i in range(3):
#             time.sleep(1)
#             ws.send("Hello %d" % i)
#         time.sleep(1)
#         ws.close()
#         print("thread terminating...")
#     _thread.start_new_thread(run, ())








def init_socket():
	# try:
	# 	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	# 	print ("Socket successfully created")
	# except socket.error as err:
	# 	print ("socket creation failed with error %s" %(err))
	
	# default port for socket
	port = 3000
	
	try:
		# server_ip = socket.gethostbyname('www.google.com')
		# server_ip = 'localhost'
		f = open('mods/API_Multiplayer/server_url.txt')
		server_info = f.read()
		f.close()

		# server_info = server_info.split(':')
		# server_ip = server_info[0]
		# port = int(server_info[1])
		server_info
	except socket.gaierror:
	
		# this means could not resolve the server host
		print ("there was an error resolving the server host")
		# sys.exit()
		return None
	
	
	# websocket_client.enableTrace(True)
	ws = websocket_client.WebSocketApp(
							server_info,
							on_open=on_open,
							on_message=recieve,
							on_error=on_error,
							on_close=on_close
							)

	# ws.run_forever()
	wst = threading.Thread(target=ws.run_forever)
	wst.daemon = True
	wst.start()

	# # connecting to the server
	# s.connect((server_ip, port))

	# # s.setblocking(False)

	# return s
	return None


import mods.API_Multiplayer.lib.websocket as websocket_client

import threading
import time
import queue
outgoing_messages = queue.Queue()
inbox = queue.Queue()

# playerID = None

closed = False
def recieve(ws, msg):
	if msg == '':
		msg = None

	if msg != None:
		print('>>> ' + str(msg))
		inbox.put(msg)
		print('inbox size: ' + str(inbox.qsize()))

def send(ws):
	global closed
	while not closed:
		msg = outgoing_messages.get()
		try:
			ws.send(msg)
			print('<<< ' + str(msg))
		except:
			closed = True
			ws.close()


server_url = None
recieveThread = None
sendThread = None
def create_socket(): # call this function to create the socket
	global server_url
	# global playerID
	global recieveThread
	global sendThread

	server_url = init_socket()
	# recieveThread = threading.Thread(target=recieve, args=[server_url, playerID])
	# recieveThread.daemon = True
	# recieveThread.start()
	# sendThread = threading.Thread(target=send, args=[server_url, playerID])
	# sendThread.daemon = True
	# sendThread.start()

def disconnect():
	try:
		s.close()
	except:
		pass # s probably either isn't initialized or has already been closed. don't worry about it


def client_send_message(message, encode=True):
	if encode:
		message = message.encode()
	outgoing_messages.put(message, block=False)

# def client_get_message():
# 	if inbox.empty():
# 		return None
# 	print('polling next message')
# 	return inbox.get(block=False)




# def __get_message_for_callback(callback):
# 	global closed
# 	while not closed:
# 		message = inbox.get(block=True)
# 		callback(message)

# def set_message_recieved_callback(callback): # expected to use this one
# 	threading.Thread(target=__get_message_for_callback, args=[callback]).start()


def listen(callback):
	if inbox.empty():
		return
		
	message = inbox.get(block=False)
	if message != None:
		callback(message)


#
# End low-level functions
#

#
# function specific to my RiftWizard Online protocol
#


import json

# host_lobby(name, self.game.trial_name, RiftWizard.loaded_mods)
def host_lobby(lobby_name, trial, mods):
	message_body = json.dumps({'name': lobby_name, 'trial': trial, 'mods':mods})
	client_send_message('h'+message_body)

def join_lobby(lobby_name, mods):
	message_body = json.dumps({'name': lobby_name, 'mods':mods})
	client_send_message('j'+message_body)

def send_game_ready(player_num, char_select_index, quirks_enabled):
	client_send_message('r'+ str(player_num) + str(char_select_index) + ',' + str(quirks_enabled))

def send_game_start(seed=None, turn_mode=None, sp_mode=None, trial_index_selected=-1):
	# host only
	client_send_message('s' + str(turn_mode) + ',' + str(sp_mode) + "," + str(seed) + ',' + str(trial_index_selected))

def send_action(action_string):
	client_send_message('a'+action_string)

def send_purchase(purchase_string):
	client_send_message('b'+purchase_string)

def send_chat(chat_message):
	client_send_message('m'+chat_message)

def disconnect():
	client_send_message('d')