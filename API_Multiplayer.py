
from Game import *
from Level import *
import Spells
import Upgrades
import Consumables

import mods.API_Multiplayer.Client as Client
import mods.API_Universal.Modred as Modred
import mods.API_Multiplayer.Chat as Chat


# NOTE: the working server is in server_v2

# networked multiplayer
# https://github.com/philippj/SteamworksPy/blob/master/steamworks/interfaces/matchmaking.py
#
# p2p architecture
# at the start of a game, the host claims p1, the guest claims p2, and the host sends the game seed to the guest
# then, whenever set_player_action() is called on either the host or the guest, that info is sent to the other player
# and that's it! (TURN_MODE_DEFAULT only)
#
# to get other turn modes working, have guests only set player actions when told by the host. the timer also only 'ends' 
# once it has recieved a message from the host saying that it has. when the guest user takes an action, it skips
# setting the player action locally and instead sends it directly to the host. the host then sends that action back to the guest
#
# notes:
# don't start the game until all players have joined
# before joining a game, check to make sure you have the exact same modlist as the host
# select player characters before joining
# on game start, host sends the seed, and all players send their character select index
# end the game if any player disconnects
# no support for continuing saved game


#
# TODO: send timer (t) and process it when it's recieved
# TODO: handle settings changes (s) midgame
# TODO: make sure multiplayer works when both players have different settings
# TODO: test shrines
# TODO: fix mutators' seeds
#
# TODO: clean up the lobby menu - make it clear when you're inputting text and when you're not, enter makes it impossible to edit, maybe add a spinner

# TODO: add a server connection menu - for inputting server url and port num
# to run the matchmaking server locally with ngrok - 
#	first run the server using $ node app.js
#	then run ngrok using $ ./ngrok.exe tcp 3000
#



# BUG:
#   if you wait too long, the port closes
#   online: p2 can't click to set path
#   online: casting friend's spells crashes game
#   online: p2 can't hover over p1 with mouse
#   Tile overlay is SUUUUPER broken, PLUS it needs to be updated to use the new version of get_image
#   bestiary doesn't open

# TODO: fast player with timer 2: works like regular fast player, but with timer, AND if p1 moved first on a given turn, p1 must wait for half the turn timer to pass to move again (action queuing allowed)



# TODO: make SP distribution non-dispellable


# Latest Release: 
# fixed crash caused by right clicking while deploying
# fixed rebind menu (it was very buggy and crash-y)
# added option to have mana potions affect both players when either drinks one
# reimplemented cast select
# made left menu border green if the player's movement keys will navigate this menu instead of moving the player
# fixed crash when trying to deploy when either player was dead
# fixed bug causing players' movement input to get dropped


####################################################
# Importing RiftWizard.py                          |
# Credit to trung on discord                       |
#                                                  |
#----------------------------------------------    |
import inspect #                                   |
def get_RiftWizard(): #                            |
    # Returns the RiftWizard.py module object      |
    for f in inspect.stack()[::-1]: #              |
        if "file 'RiftWizard.py'" in str(f): #     |
            return inspect.getmodule(f[0]) #       |
	 #                                             |
    return inspect.getmodule(f[0]) #               |
#                                                  |
RiftWizard = get_RiftWizard() #                    |
#                                                  |
#                                                  |
####################################################

import pygame
import SteamAdapter



# ######################################### 
#
# Settings
#
# #########################################

# ^def.*\n(?!\tif.*\n\t\treturn)


TURN_MODE_DEFAULT = 0                        # turn advances once both players have moved
TURN_MODE_FAST_PLAYER = 1                    # turn advances once a total of 2 moves have been made by players
TURN_MODE_DEFAULT_WITH_TIMER = 2             # turn advances once both players have moved or a timer runs out
TURN_MODE_HYPERSPEED_PLAYERS_WITH_TIMER = 3  # turn advances only once a timer runs out - players can move as much as they want in the meantime
TURN_MODE_ONE_PLAYER_AT_A_TIME = 4           # turn advances once one player has moved
TURN_MODE_FAST_PLAYER_WITH_TIMER = 5         # turn advances once a total of 2 moves have been made by players or a timer has run out


RiftWizard.turn_mode_from_settings = TURN_MODE_FAST_PLAYER
RiftWizard.turn_mode = RiftWizard.turn_mode_from_settings

TURN_TIMER = 1



SP_DISTRIBUTION_STRATEGY_DEFAULT = 0
SP_DISTRIBUTION_STRATEGY_ONE_FOR_ALL = 1
SP_DISTRIBUTION_STRATEGY_ROUND_ROBIN = 2
SP_DISTRIBUTION_STRATEGY_HALF_FOR_ALL = 3

RiftWizard.sp_distribution_strategy = SP_DISTRIBUTION_STRATEGY_HALF_FOR_ALL
	


BOTH_PLAYERS = 0
EITHER_PLAYER = 1
GAMEOVER_CONDITION = BOTH_PLAYERS


CLAY_IS_DEBUGGING_ONLINE_MULTIPLAYER_ON_HIS_ONE_COMPUTER = True

# try:
if True:
	Modred.add_tile_option_line('Multiplayer Settings:')

	def turn_mode_string(self, cur_value):
		if self.game and not self.in_multiplayer_mode:
			return None

		if cur_value == TURN_MODE_DEFAULT:
			turn_mode_fmt = 'default'
		elif cur_value == TURN_MODE_FAST_PLAYER:
			turn_mode_fmt = 'fast player'
		elif cur_value == TURN_MODE_DEFAULT_WITH_TIMER:
			turn_mode_fmt = 'default (with timer)'
		elif cur_value == TURN_MODE_HYPERSPEED_PLAYERS_WITH_TIMER:
			turn_mode_fmt = 'turnless (with timer)'
		elif cur_value == TURN_MODE_ONE_PLAYER_AT_A_TIME:
			turn_mode_fmt = 'one at a time'
		elif cur_value == TURN_MODE_FAST_PLAYER_WITH_TIMER:
			turn_mode_fmt = 'fast player (with timer)'

		return ("Turn Mode: %6s" % turn_mode_fmt)

	def set_turn_mode(self, new_value):
		self.options['multiplayer_turn_mode'] = new_value
		RiftWizard.turn_mode_from_settings = self.options['multiplayer_turn_mode']
	
	def initialize_turn_mode(self):
		if not 'multiplayer_turn_mode' in self.options:
			self.options['multiplayer_turn_mode'] = TURN_MODE_FAST_PLAYER
		RiftWizard.turn_mode_from_settings = self.options['multiplayer_turn_mode']

	Modred.add_option( \
		turn_mode_string, \
		lambda self: self.options['multiplayer_turn_mode'], \
		[
			TURN_MODE_DEFAULT,
			TURN_MODE_FAST_PLAYER,
			TURN_MODE_DEFAULT_WITH_TIMER,
			TURN_MODE_FAST_PLAYER_WITH_TIMER,
			TURN_MODE_HYPERSPEED_PLAYERS_WITH_TIMER,
			TURN_MODE_ONE_PLAYER_AT_A_TIME,
		], \
		23, 
		set_turn_mode, \
		option_wraps=True, \
		initialize_option=initialize_turn_mode
	)

	def turn_timer_string(self, cur_value):
		if self.game and not self.in_multiplayer_mode:
			return None
		return 'Turn Timer: %.1f seconds' % cur_value

	def set_turn_timer(self, new_value):
		self.options['turn_timer_length'] = new_value
		TURN_TIMER = self.options['turn_timer_length']

	def initialize_turn_timer(self):
		if not 'turn_timer_length' in self.options:
			self.options['turn_timer_length'] = 1
		TURN_TIMER = self.options['turn_timer_length']
		
	Modred.add_option( \
		turn_timer_string, \
		lambda self: self.options['turn_timer_length'], \
		[i / 10 for i in range(5, 21)], \
		24, 
		set_turn_timer, \
		option_wraps=False, \
		initialize_option=initialize_turn_timer
	)



	
	def sp_distribution_strategy_string(self, cur_value):
		if self.game and not self.in_multiplayer_mode:
			return None
			
		if cur_value == SP_DISTRIBUTION_STRATEGY_DEFAULT:
			sp_dist_fmt = 'Default'
		elif cur_value == SP_DISTRIBUTION_STRATEGY_ONE_FOR_ALL:
			sp_dist_fmt = 'One for All'
		elif cur_value == SP_DISTRIBUTION_STRATEGY_ROUND_ROBIN:
			sp_dist_fmt = 'Round Robin'
		elif cur_value == SP_DISTRIBUTION_STRATEGY_HALF_FOR_ALL:
			sp_dist_fmt = 'Half for All'

		return ("SP Distribution: %6s" % sp_dist_fmt)

	def set_sp_distribution_strategy(self, new_value):
		self.options['sp_distribution_strategy'] = new_value
		RiftWizard.sp_distribution_strategy = self.options['sp_distribution_strategy']
	
	def initialize_sp_distribution_strategy(self):
		if not 'sp_distribution_strategy' in self.options:
			self.options['sp_distribution_strategy'] = SP_DISTRIBUTION_STRATEGY_HALF_FOR_ALL
		RiftWizard.sp_distribution_strategy = self.options['sp_distribution_strategy']

	Modred.add_option( \
		sp_distribution_strategy_string, \
		lambda self: self.options['sp_distribution_strategy'], \
		[
			SP_DISTRIBUTION_STRATEGY_HALF_FOR_ALL,
			SP_DISTRIBUTION_STRATEGY_ONE_FOR_ALL,
			SP_DISTRIBUTION_STRATEGY_DEFAULT,
			SP_DISTRIBUTION_STRATEGY_ROUND_ROBIN,
		], \
		'sp_distribution_strategy_option', 
		set_sp_distribution_strategy, \
		option_wraps=True, \
		initialize_option=initialize_sp_distribution_strategy
	)

	
	def universal_mana_potion_enabled_string(self, cur_value):
		if self.game and not self.in_multiplayer_mode:
			return None
		return ("Mana Potions: %6s" % ('Shared Effect' if self.options['universal_mana_potion_enabled'] else 'Individual'))
	def set_universal_mana_potion_enabled(self, new_value):
		self.options['universal_mana_potion_enabled'] = new_value
		RiftWizard.universal_mana_potion_enabled = self.options['universal_mana_potion_enabled']
	def initialize_universal_mana_potion_enabled(self):
		if not 'universal_mana_potion_enabled' in self.options:
			self.options['universal_mana_potion_enabled'] = True
		RiftWizard.universal_mana_potion_enabled = self.options['universal_mana_potion_enabled']
	Modred.add_option( \
		universal_mana_potion_enabled_string, \
		lambda self: self.options['universal_mana_potion_enabled'], \
		[ True, False ], \
		'universal_mana_potion_enabled_option', 
		set_universal_mana_potion_enabled, \
		option_wraps=True, \
		initialize_option=initialize_universal_mana_potion_enabled
	)

	Modred.add_blank_option_line()
# except Exception as e:
# 	print('\tAPI Multiplayer error: settings failed to load')
# 	print(e)


# ######################################### 
#
# SP Distribution
#
# #########################################

# level.event_manager.register_global_trigger(EventOnItemPickup, myCoolHandlerFunction)
class SPDistributionBuff(Buff):
	def __init__(self, starts, other_player):
		Buff.__init__(self)
		self.name = "SP Distribution"
		self.owner_triggers[EventOnItemPickup] = self.on_pickup
		self.stack_type = STACK_NONE
		self.buff_type = BUFF_TYPE_NONE
		self.starts = starts

		self.other_player = other_player

	def on_applied(self, owner):
		pass

	def on_advance(self):
		pass

	def on_pickup(self, evt):
		if not isinstance(evt.item, ManaDot):
			return

		if RiftWizard.sp_distribution_strategy == SP_DISTRIBUTION_STRATEGY_DEFAULT:
			return
		if RiftWizard.sp_distribution_strategy == SP_DISTRIBUTION_STRATEGY_ONE_FOR_ALL:
			self.other_player.xp += 1
			return
		if RiftWizard.sp_distribution_strategy == SP_DISTRIBUTION_STRATEGY_HALF_FOR_ALL:
			self.other_player.xp += 0.5
			self.owner.xp -= 0.5
			return
		if RiftWizard.sp_distribution_strategy == SP_DISTRIBUTION_STRATEGY_ROUND_ROBIN:
			if not hasattr(self.owner, 'sp_turn_toggle'):
				self.owner.sp_turn_toggle = starts
				self.other_player.sp_turn_toggle = not starts
			
			if self.owner.sp_turn_toggle:
				self.owner.sp_turn_toggle = False
				self.other_player.sp_turn_toggle = True
			else:
				self.owner.sp_turn_toggle = True
				self.other_player.sp_turn_toggle = False

				self.owner.xp -= 1
				self.other_player.xp += 1


class ShareManaPotionEffectBuff(Buff):
	def __init__(self, starts, other_player):
		Buff.__init__(self)
		self.name = "Share Mana Potions"
		self.owner_triggers[EventOnSpellCast] = self.on_cast
		self.stack_type = STACK_NONE
		self.buff_type = BUFF_TYPE_NONE
		self.starts = starts

		self.other_player = other_player

	def on_cast(self, event):
		if isinstance(event.spell, Consumables.SpellCouponSpell):
			for spell in self.other_player.spells:
				spell.cur_charges = spell.get_stat('max_charges')


# ######################################### 
#
# Disable Steam stats during multiplayer
#
# #########################################
		
global_in_multiplayer_mode = False

# import SteamAdapter as SteamAdapter

# old_SteamAdapter_set_stat = SteamAdapter.set_stat
# def SteamAdapter_set_stat(stat, val):
# 	global global_in_multiplayer_mode
# 	if global_in_multiplayer_mode:
# 		return

# 	old_SteamAdapter_set_stat(stat, val)
# SteamAdapter.set_stat = SteamAdapter_set_stat

# old_SteamAdapter_set_presence_level = SteamAdapter.set_presence_level
# def SteamAdapter_set_presence_level(level):
# 	global global_in_multiplayer_mode
# 	if global_in_multiplayer_mode:
# 		return
# 	old_SteamAdapter_set_presence_level(level)
# SteamAdapter.set_presence_level = SteamAdapter_set_presence_level

# old_SteamAdapter_set_trial_complete = SteamAdapter.set_trial_complete
# def SteamAdapter_set_trial_complete(trial_name):
# 	global global_in_multiplayer_mode
# 	if global_in_multiplayer_mode:
# 		return
# 	old_SteamAdapter_set_trial_complete(trial_name)
# SteamAdapter.set_trial_complete = SteamAdapter_set_trial_complete


# old_SteamAdapter_unlock_bestiary = SteamAdapter.unlock_bestiary
# def SteamAdapter_unlock_bestiary(monster_name):
# 	global global_in_multiplayer_mode
# 	if global_in_multiplayer_mode:
# 		return
# 	old_SteamAdapter_unlock_bestiary(monster_name)
# SteamAdapter.unlock_bestiary = SteamAdapter_unlock_bestiary


# TODO: this
# import mods.API_Universal.Modred as Modred
# Modred.add_steam_blocker('multiplayer')



# ######################################### 
#
# Title Screen
#
# #########################################

TITLE_SELECTION_NEW_MULTIPLAYER = RiftWizard.TITLE_SELECTION_NEW+1
TITLE_SELECTION_NEW_MULTIPLAYER_ONLINE = RiftWizard.TITLE_SELECTION_NEW+2
TITLE_SELECTION_JOIN_MULTIPLAYER_ONLINE = RiftWizard.TITLE_SELECTION_NEW+3
RiftWizard.TITLE_SELECTION_OPTIONS += 3
RiftWizard.TITLE_SELECTION_BESTIARY += 3
RiftWizard.TITLE_SELECTION_DISCORD += 3
RiftWizard.TITLE_SELECTION_EXIT += 3
RiftWizard.TITLE_SELECTION_MAX += 3


COLOR_SCHEME_MAIN_TARGET = 0
COLOR_SCHEME_CURR_IMPACTED = 1
COLOR_SCHEME_TARGETABLE = 2
COLOR_SCHEME_UNTARGETABLE_IN_RANGE = 3
COLOR_SCHEME_MAIN_TARGET_UNTARGETABLE = 4
COLOR_SCHEME_NAME = 5

global_player_characters_asset_names = []
global_player_characters_names = []
global_player_characters_color_schemes = []
global_player_characters_blurbs = []
global_player_characters_add_quirks_functions = []
global_player_characters_quirks_descriptions = []
def add_character_to_char_select(character_asset_path, character_name, character_color_scheme, blurb, add_quirks, quirks_description):
	global_player_characters_asset_names.append(character_asset_path)
	global_player_characters_names.append(character_name)
	global_player_characters_color_schemes.append(character_color_scheme)
	global_player_characters_blurbs.append(blurb)
	global_player_characters_add_quirks_functions.append(add_quirks)
	global_player_characters_quirks_descriptions.append(quirks_description)

# add the two default characters
add_character_to_char_select(["API_Multiplayer","player_1"], 'The Wizard', \
	{
		COLOR_SCHEME_MAIN_TARGET: (0, 0, 255, 150),
		COLOR_SCHEME_CURR_IMPACTED: (100, 100, 200, 150),
		COLOR_SCHEME_TARGETABLE: (150, 150, 200, 150),
		COLOR_SCHEME_UNTARGETABLE_IN_RANGE: (255, 80, 80, 100),
		COLOR_SCHEME_MAIN_TARGET_UNTARGETABLE: (100, 0, 0, 150),
		COLOR_SCHEME_NAME: (75, 127, 200)
	}, \
	'The orignial wizard',
	None,
	'The Wizard has no Quirks. The vanilla experience.'
)
add_character_to_char_select(["API_Multiplayer","shmerlin_by_fartfish"], 'Shmerlin', \
	{
		COLOR_SCHEME_MAIN_TARGET: (0, 255, 0, 150),
		COLOR_SCHEME_CURR_IMPACTED: (100, 200, 100, 150),
		COLOR_SCHEME_TARGETABLE: (150, 200, 150, 150),
		COLOR_SCHEME_UNTARGETABLE_IN_RANGE: (255, 80, 80, 100),
		COLOR_SCHEME_MAIN_TARGET_UNTARGETABLE: (100, 0, 0, 150),
		COLOR_SCHEME_NAME: (43, 175, 43)
	}, \
	'Created by FartFish on the Discord.',
	None,
	'Shmerlin has no Quirks. The vanilla experience.'
)

def try_init_char_select(self):
	if not hasattr(self, 'p1_char_select_index')   \
		or not hasattr(self, 'p2_char_select_index')   \
		or not hasattr(self, 'player_characters_asset_names') \
		or not hasattr(self, 'player_characters_names') \
		or not hasattr(self, 'player_characters_color_schemes') \
		or not hasattr(self, 'player_characters_blurbs') \
		or not hasattr(self, 'player_characters_add_quirks_functions') \
		or not hasattr(self, 'player_characters_quirks_descriptions'):
		# self.in_char_select = False
		self.p1_char_select_index = 0
		self.p2_char_select_index = 1
		self.player_characters_asset_names = global_player_characters_asset_names
		self.player_characters_names = global_player_characters_names
		self.player_characters_color_schemes = global_player_characters_color_schemes
		self.player_characters_blurbs = global_player_characters_blurbs
		self.player_characters_add_quirks_functions = global_player_characters_add_quirks_functions
		self.player_characters_quirks_descriptions = global_player_characters_quirks_descriptions

		self.add_character_quirks_p1 = True
		self.add_character_quirks_p2 = True

		font_path = os.path.join("rl_data", "PrintChar21.ttf")
		self.font_large_line_size = 40
		self.font_large = pygame.font.Font(font_path, self.font_large_line_size)


def try_init_online_menu(self):
	if not hasattr(self, 'online__lobby_name_input'):
		self.online__lobby_name_input = Modred.TextInput()
		# self.online__lobby_name_input.give_focus()
		self.online__lobby_name_input.font = self.font_large
		self.online__lobby_name_input.linesize = self.font_large_line_size
		self.online__lobby_name_input.placeholder_text = "lobby name"

		self.online__waiting_in_lobby = False
		def on_confirm_callback():
			if not self.online__waiting_in_lobby:
				lobby_name = self.online__lobby_name_input.text

				print('connect to ' + lobby_name)
				if not hasattr(self, 'trial_index_selected'):
					self.trial_index_selected = -1

				if self.online__is_host:
					Client.host_lobby(lobby_name, self.trial_index_selected, RiftWizard.loaded_mods)
				else:
					Client.join_lobby(lobby_name, RiftWizard.loaded_mods)
					Client.send_game_ready(2, self.p2_char_select_index, self.add_character_quirks_p2)

				join_button.set_text("Abandon Lobby")
				Chat.add_chat_message('>>> Now waiting in lobby ' + lobby_name + ". Game will begin when player 2 connects.")
				self.online__waiting_in_lobby = True
			else:
				Client.disconnect()

				join_button.set_text("Create/Join Lobby")
				self.online__waiting_in_lobby = False
			

		# self.online__lobby_name_input.confirm_callback = on_confirm_callback

		def menu_draw_text_input(pygameview, draw_pane, x, y):
			self.online__lobby_name_input.draw(pygameview, self.screen.get_width()//2, y, draw_pane, center=True)



		menu_width = self.screen.get_width() * 2/3
		menu_height = self.screen.get_height() * 99/100

		join_button = Modred.row_from_text("Create/Join Lobby", self.font, self.linesize, selectable=True, on_confirm_callback=on_confirm_callback, center=True)
		headers = [
			Modred.row_from_text("Enter Lobby Name", self.font_large, self.font_large_line_size, center=True),
			Modred.row_from_size(menu_width, self.font_large_line_size, custom_draw_function=menu_draw_text_input, selectable=True, on_confirm_callback=self.online__lobby_name_input.give_focus, mouse_content=self.online__lobby_name_input),
			join_button,
			Modred.row_from_text(" ", self.font, self.linesize, selectable=False, center=True),
			
			Modred.row_from_text("-------------------------------------------", self.font_large, self.font_large_line_size, center=True),
			Modred.row_from_text("Existing Lobbies", self.font_large, self.font_large_line_size, center=True),
			Modred.row_from_text("Refresh", self.font, self.linesize, selectable=True, on_confirm_callback=None, center=True)
		]

		# main_rows = [
		# 	Modred.row_from_text(lobby.name, color=(255, 255, 255) if lobby.can_join else (50, 50, 50), selectable=True, on_confirm_callback=lambda row: on_confirm_callback(lobby.name))
		# 	for lobby in Client.request_lobby_list()
		# ]
		main_rows = []

		# self.online__lobby_menu = Modred.create_menu(headers, main_rows, screen.height)
		self.online__lobby_menu = Modred.make_menu_from_rows(main_rows, menu_height, self.font, self.linesize, header_rows=headers, footer_rows=[], add_page_count_footer=True, loopable=True)






def draw_lobby_menu(self):
	try_init_online_menu(self)

	# char_select_title_string = 'Enter Lobby Name'
	# cur_x = self.screen.get_width()//2 - self.font_large.size(char_select_title_string)[0]//2
	# cur_y = self.screen.get_height()//2
	# self.draw_string(char_select_title_string, self.screen, cur_x, cur_y, font=self.font_large)
	
	# cur_x = self.screen.get_width()//2
	# cur_y += self.font_large_line_size

	# self.online__lobby_name_input.draw(self, cur_x, cur_y, self.screen, center=True)


	self.online__lobby_menu.draw(self, self.screen, self.screen.get_width()//3, 0)

	Chat.draw_chat_messages(self, self.screen, 5)




def process_lobby_menu_input(self):
	try_init_online_menu(self)

	if self.online__lobby_name_input.has_focus:
		self.online__lobby_name_input.process_input(self, RiftWizard.KEY_BIND_CONFIRM, RiftWizard.KEY_BIND_ABORT)
	else:
		# pygameview, up_keys, down_keys, left_keys, right_keys, confirm_keys
		self.online__lobby_menu.process_input(self, self.key_binds[RiftWizard.KEY_BIND_UP], self.key_binds[RiftWizard.KEY_BIND_DOWN], self.key_binds[RiftWizard.KEY_BIND_LEFT], self.key_binds[RiftWizard.KEY_BIND_RIGHT], self.key_binds[RiftWizard.KEY_BIND_CONFIRM])

	# for evt in self.events:
	# 	if evt.type != pygame.KEYDOWN:
	# 		continue
		
	# 	# if not self.lobby_name_input_active:
	# 	# 	break

	# 	if evt.key in self.key_binds[RiftWizard.KEY_BIND_CONFIRM]:
	# 		print('connect to ' + self.online__loby_name)
	# 		if not hasattr(self, 'trial_index_selected'):
	# 			self.trial_index_selected = -1

	# 		if self.online__is_host:
	# 			Client.host_lobby(self.online__loby_name, self.trial_index_selected, RiftWizard.loaded_mods)
	# 		else:
	# 			Client.join_lobby(self.online__loby_name, RiftWizard.loaded_mods)
	# 			Client.send_game_ready(2, self.p2_char_select_index, self.add_character_quirks_p2)
		
	# 	elif evt.key in self.key_binds[RiftWizard.KEY_BIND_ABORT]:
	# 		Client.disconnect()
	# 		self.state = RiftWizard.STATE_TITLE
	# 	elif evt.key == pygame.K_BACKSPACE:
	# 		self.online__loby_name = self.online__loby_name[:-1]
	# 	elif hasattr(evt, 'unicode'):
	# 		self.online__loby_name += evt.unicode


STATE_LOBBY_MENU = Modred.add_menu(draw_lobby_menu, process_lobby_menu_input)


def draw_char_select(self):
	try_init_char_select(self)

	title_disp_frame = self.title_frame // 16 % 2
	self.title_frame += 1


	char_select_title_string = 'Select Your Character'
	cur_x = self.screen.get_width()//2 - self.font_large.size(char_select_title_string)[0]//2
	cur_y = 0
	self.draw_string(char_select_title_string, self.screen, cur_x, cur_y, font=self.font_large)

	# 		
	# draw animated character sprites
	# 

	big_scale = 16#32
	blit_area = (title_disp_frame * RiftWizard.SPRITE_SIZE, 2*RiftWizard.SPRITE_SIZE, RiftWizard.SPRITE_SIZE, RiftWizard.SPRITE_SIZE)


	half_screen_width = self.screen.get_width() // 2
	third_screen_width = self.screen.get_width() // 3
	p1_center_x = half_screen_width*0.5
	p2_center_x = half_screen_width*1.5

	if not self.in_multiplayer_mode or self.online_mode:
		p1_center_x = half_screen_width
	
	cur_y = 60

	p1_char_x = p1_center_x - RiftWizard.SPRITE_SIZE*big_scale // 2
	spritesheet_p1 = RiftWizard.get_image(self.player_characters_asset_names[self.p1_char_select_index])
	image_p1 = spritesheet_p1.subsurface((\
		(self.title_frame // 16 % (spritesheet_p1.get_width()/RiftWizard.SPRITE_SIZE)) * RiftWizard.SPRITE_SIZE, \
		2*RiftWizard.SPRITE_SIZE, \
		RiftWizard.SPRITE_SIZE, \
		RiftWizard.SPRITE_SIZE\
	))
	big_char_p1 = pygame.transform.scale(image_p1, (RiftWizard.SPRITE_SIZE*big_scale, RiftWizard.SPRITE_SIZE*big_scale))
	self.screen.blit(big_char_p1, (p1_char_x, cur_y))
	
	if self.in_multiplayer_mode and not self.online_mode:
		p2_char_x = p2_center_x - RiftWizard.SPRITE_SIZE*big_scale // 2
		spritesheet_p2 = RiftWizard.get_image(self.player_characters_asset_names[self.p2_char_select_index])
		image_p2 = spritesheet_p2.subsurface((\
			(self.title_frame // 16 % (spritesheet_p2.get_width()/RiftWizard.SPRITE_SIZE)) * RiftWizard.SPRITE_SIZE, \
			2*RiftWizard.SPRITE_SIZE, \
			RiftWizard.SPRITE_SIZE, \
			RiftWizard.SPRITE_SIZE\
		))
		big_char_p2 = pygame.transform.scale(image_p2, (RiftWizard.SPRITE_SIZE*big_scale, RiftWizard.SPRITE_SIZE*big_scale))
		self.screen.blit(big_char_p2, (p2_char_x, cur_y))

	
	# 		
	# draw character names
	# 

	cur_y += RiftWizard.SPRITE_SIZE*big_scale
	cur_y += self.linesize // 2

	# draw_string(self, string, surface, x, y, color=(255, 255, 255))
	p1_char_name = self.player_characters_names[self.p1_char_select_index]
	p1_char_name_color = self.player_characters_color_schemes[self.p1_char_select_index][COLOR_SCHEME_NAME]
	cur_x = p1_center_x - self.font_large.size(p1_char_name)[0] // 2
	self.draw_string(p1_char_name, self.screen, cur_x, cur_y, color=p1_char_name_color, font=self.font_large, content_width=RiftWizard.SPRITE_SIZE*big_scale)
	
	if self.in_multiplayer_mode and not self.online_mode:
		p2_char_name = self.player_characters_names[self.p2_char_select_index]
		p2_char_name_color = self.player_characters_color_schemes[self.p2_char_select_index][COLOR_SCHEME_NAME]
		cur_x = p2_center_x - self.font_large.size(p2_char_name)[0] // 2
		self.draw_string(p2_char_name, self.screen, cur_x, cur_y,  color=p2_char_name_color, font=self.font_large, content_width=RiftWizard.SPRITE_SIZE*big_scale)

	cur_y += self.font_large_line_size
	cur_y += self.linesize // 2

	#
	# draw character descriptions
	#

	if self.in_multiplayer_mode and not self.online_mode:
		p1_text_x = p1_center_x - third_screen_width/2
		p2_text_x = p2_center_x - third_screen_width/2

		lines_p1 = self.draw_wrapped_string(self.player_characters_blurbs[self.p1_char_select_index], self.screen, p1_text_x, cur_y, third_screen_width, extra_space=True, center=True)
		lines_p2 = self.draw_wrapped_string(self.player_characters_blurbs[self.p2_char_select_index], self.screen, p2_text_x, cur_y, third_screen_width, extra_space=True, center=True)
	else:
		p1_text_x = p1_center_x - third_screen_width/2
		lines_p1 = self.draw_wrapped_string(self.player_characters_blurbs[self.p1_char_select_index], self.screen, p1_text_x, cur_y, third_screen_width, extra_space=True, center=True)
		lines_p2 = 0

	
	cur_y += self.linesize * max(lines_p1, lines_p2)
	cur_y += self.font_large_line_size
	

	#
	# draw character quirk descriptions
	#

	if self.in_multiplayer_mode and not self.online_mode:
		self.draw_string("Quirks ", self.screen, p1_text_x, cur_y,  color=RiftWizard.COLOR_XP, font=self.font_large, content_width=third_screen_width)
		self.draw_string("Quirks ", self.screen, p2_text_x, cur_y,  color=RiftWizard.COLOR_XP, font=self.font_large, content_width=third_screen_width)
		quirks_string_width = self.font_large.size("Quirks.")[0]
		line_height_diff = self.font_large_line_size - self.linesize
		self.draw_string(("(Enabled)" if self.add_character_quirks_p1 else "(Disabled)"), self.screen, p1_text_x+quirks_string_width, cur_y+line_height_diff, color=(RiftWizard.tooltip_colors["heal"] if self.add_character_quirks_p1 else RiftWizard.tooltip_colors["damage"]).to_tup(), font=self.font)
		self.draw_string(("(Enabled)" if self.add_character_quirks_p2 else "(Disabled)"), self.screen, p2_text_x+quirks_string_width, cur_y+line_height_diff, color=(RiftWizard.tooltip_colors["heal"] if self.add_character_quirks_p2 else RiftWizard.tooltip_colors["damage"]).to_tup(), font=self.font)
	else:
		self.draw_string("Quirks ", self.screen, p1_text_x, cur_y,  color=RiftWizard.COLOR_XP, font=self.font_large, content_width=third_screen_width)
		quirks_string_width = self.font_large.size("Quirks.")[0]
		line_height_diff = self.font_large_line_size - self.linesize
		self.draw_string(("(Enabled)" if self.add_character_quirks_p1 else "(Disabled)"), self.screen, p1_text_x+quirks_string_width, cur_y+line_height_diff, color=(RiftWizard.tooltip_colors["heal"] if self.add_character_quirks_p1 else RiftWizard.tooltip_colors["damage"]).to_tup(), font=self.font)


	cur_y += self.font_large_line_size
	cur_y += self.linesize

	if self.in_multiplayer_mode and not self.online_mode:
		lines_p1 = self.draw_wrapped_string(self.player_characters_quirks_descriptions[self.p1_char_select_index], self.screen, p1_text_x, cur_y, third_screen_width, extra_space=True, center=True)
		lines_p2 = self.draw_wrapped_string(self.player_characters_quirks_descriptions[self.p2_char_select_index], self.screen, p2_text_x, cur_y, third_screen_width, extra_space=True, center=True)
	else:
		lines_p1 = self.draw_wrapped_string(self.player_characters_quirks_descriptions[self.p1_char_select_index], self.screen, p1_text_x, cur_y, third_screen_width, extra_space=True, center=True)


	
	cur_y += self.linesize * max(lines_p1, lines_p2)
	cur_y += self.font_large_line_size

	#
	# Page Numbers
	#

	
	page_num_string = '<<<   '+str(self.p1_char_select_index+1)+'/'+str(len(self.player_characters_names))+'   >>>'
	string_width = self.font.size(page_num_string)[0]
	self.draw_string(page_num_string, self.screen, p1_center_x-string_width//2, cur_y, content_width=third_screen_width)
	
	if self.in_multiplayer_mode and not self.online_mode:
		page_num_string = '<<<   '+str(self.p2_char_select_index+1)+'/'+str(len(self.player_characters_names))+'   >>>'
		string_width = self.font.size(page_num_string)[0]
		self.draw_string(page_num_string, self.screen, p2_center_x-string_width//2, cur_y, content_width=third_screen_width)



def process_char_select_input(self):
	try_init_char_select(self)

	title_disp_frame = self.title_frame // 16 % 2

	for evt in self.events:
		if evt.type != pygame.KEYDOWN:
			continue
			
		if evt.key in self.key_binds[RiftWizard.KEY_BIND_CONFIRM]:
			self.play_sound('menu_confirm')
			self.state = RiftWizard.STATE_PICK_MODE
			self.examine_target = 0

			# if self.online_mode:
			# 	# self.in_lobby_menu = True
			# 	# self.in_char_select = False
			# 	self.state = STATE_LOBBY_MENU
			# else:
			# 	self.state = RiftWizard.STATE_PICK_MODE
			# 	self.examine_target = 0
			# 	# self.in_multiplayer_mode = True
			# 	# global global_in_multiplayer_mode
			# 	# global_in_multiplayer_mode = True 

			# 	# self.in_char_select = False


			
		if evt.key in self.key_binds[RiftWizard.KEY_BIND_ABORT]:
			self.play_sound('menu_abort')
			# self.in_char_select = False
			self.state = RiftWizard.STATE_TITLE

		
		if evt.key in self.key_binds[RiftWizard.KEY_BIND_RIGHT]:
			self.play_sound('menu_confirm')
			self.p1_char_select_index += 1
			self.p1_char_select_index = self.p1_char_select_index % len(self.player_characters_asset_names)
			if self.p1_char_select_index == self.p2_char_select_index:
				self.p1_char_select_index += 1
				self.p1_char_select_index = self.p1_char_select_index % len(self.player_characters_asset_names)
		if evt.key in self.key_binds[RiftWizard.KEY_BIND_LEFT]:
			self.play_sound('menu_confirm')
			self.p1_char_select_index -= 1
			self.p1_char_select_index = (self.p1_char_select_index + len(self.player_characters_asset_names)) % len(self.player_characters_asset_names)
			if self.p1_char_select_index == self.p2_char_select_index:
				self.p1_char_select_index -= 1
				self.p1_char_select_index = (self.p1_char_select_index + len(self.player_characters_asset_names)) % len(self.player_characters_asset_names)
		if evt.key in self.key_binds[RiftWizard.KEY_BIND_UP] or evt.key in self.key_binds[RiftWizard.KEY_BIND_DOWN]:
			self.play_sound('menu_confirm')
			self.add_character_quirks_p1 = not self.add_character_quirks_p1

		if evt.key in self.key_binds[KEY_BIND_RIGHT_P2]:
			self.play_sound('menu_confirm')
			self.p2_char_select_index += 1
			self.p2_char_select_index = self.p2_char_select_index % len(self.player_characters_asset_names)
			if self.p2_char_select_index == self.p1_char_select_index:
				self.p2_char_select_index += 1
				self.p2_char_select_index = self.p2_char_select_index % len(self.player_characters_asset_names)
		if evt.key in self.key_binds[KEY_BIND_LEFT_P2]:
			self.play_sound('menu_confirm')
			self.p2_char_select_index -= 1
			self.p2_char_select_index = (self.p2_char_select_index + len(self.player_characters_asset_names)) % len(self.player_characters_asset_names)
			if self.p2_char_select_index == self.p1_char_select_index:
				self.p2_char_select_index -= 1
				self.p2_char_select_index = (self.p2_char_select_index + len(self.player_characters_asset_names)) % len(self.player_characters_asset_names)
		if evt.key in self.key_binds[KEY_BIND_UP_P2] or evt.key in self.key_binds[KEY_BIND_DOWN_P2]:
			self.play_sound('menu_confirm')
			self.add_character_quirks_p2 = not self.add_character_quirks_p2

	# online mode stuff
	if self.online_mode and not self.online__is_host:
		self.add_character_quirks_p2 = self.add_character_quirks_p1
		self.p2_char_select_index = self.p1_char_select_index
		

STATE_CHAR_SELECT = Modred.add_menu(draw_char_select, process_char_select_input)



Modred.override_menu_transition(STATE_CHAR_SELECT, RiftWizard.STATE_PICK_MODE, STATE_LOBBY_MENU, lambda pygameview: pygameview.online_mode and not pygameview.online__is_host)
Modred.override_menu_transition(RiftWizard.STATE_PICK_MODE, RiftWizard.STATE_LEVEL, STATE_LOBBY_MENU, lambda pygameview: pygameview.online_mode)
Modred.override_menu_transition(RiftWizard.STATE_PICK_TRIAL, RiftWizard.STATE_LEVEL, STATE_LOBBY_MENU, lambda pygameview: pygameview.online_mode)




def draw_title(self):

	title_disp_frame = self.title_frame // 16 % 2
	self.screen.blit(self.title_image, (0, 0, 1600, 900), (title_disp_frame*1600, 0, 1600, 900))

	m_loc = self.get_mouse_pos()

	self.title_frame += 1

	cur_x = 629
	cur_y = 535

	rect_w = self.font.size("NEW MULTIPLAYER GAME")[0]

	opts = []
	if can_continue_game():
		opts.append((RiftWizard.TITLE_SELECTION_LOAD, "CONTINUE RUN"))
		opts.append((RiftWizard.TITLE_SELECTION_ABANDON, "ABANDON RUN"))
	else:
		opts.append((RiftWizard.TITLE_SELECTION_NEW, "NEW GAME"))
		opts.append((TITLE_SELECTION_NEW_MULTIPLAYER, "NEW MULTIPLAYER GAME"))
		opts.append((TITLE_SELECTION_NEW_MULTIPLAYER_ONLINE, "HOST ONLINE GAME"))
		opts.append((TITLE_SELECTION_JOIN_MULTIPLAYER_ONLINE, "JOIN ONLINE GAME"))

	opts.extend([(RiftWizard.TITLE_SELECTION_OPTIONS, "OPTIONS"),
					(RiftWizard.TITLE_SELECTION_BESTIARY, "BESTIARY"),
					(RiftWizard.TITLE_SELECTION_DISCORD, "DISCORD"),
					(RiftWizard.TITLE_SELECTION_EXIT, "QUIT")])

	for o, w in opts:

		cur_color = (255, 255, 255)
		self.draw_string(w, self.screen, cur_x, cur_y, cur_color, mouse_content=o, content_width=rect_w)
		cur_y += self.linesize + 2

	cur_y += 3*self.linesize

	#self.draw_string("Wins:   %d" % SteamAdapter.get_stat('w'), self.screen, cur_x, cur_y)
	cur_y += self.linesize
	#self.draw_string("Loses:  %d" % SteamAdapter.get_stat('l'), self.screen, cur_x, cur_y)
	cur_y += self.linesize
	#self.draw_string("Streak: %d" % SteamAdapter.get_stat('s'), self.screen, cur_x, cur_y)

# RiftWizard.PyGameView.draw_title = draw_title



old_process_title_input = RiftWizard.PyGameView.process_title_input
def process_title_input(self):
	# regular title

	# old_process_title_input(self)

	# self.in_multiplayer_mode = False
	# selection = None
	# for evt in self.events:
	# 	if evt.type == pygame.KEYDOWN:
			
	# 		if evt.key in self.key_binds[RiftWizard.KEY_BIND_CONFIRM]:
	# 			self.play_sound('menu_confirm')
	# 			selection = self.examine_target

	# if selection == TITLE_SELECTION_NEW_MULTIPLAYER:
	# 	# self.state = RiftWizard.STATE_PICK_MODE
	# 	# self.examine_target = 0
	# 	self.in_multiplayer_mode = True
	# 	self.in_char_select = True

	selection = None
	m_loc = self.get_mouse_pos()

	self.in_multiplayer_mode = False
	# global global_in_multiplayer_mode
	global_in_multiplayer_mode = False 
	for evt in self.events:
		if evt.type == pygame.KEYDOWN:
			
			if evt.key in self.key_binds[RiftWizard.KEY_BIND_CONFIRM]:
				self.play_sound('menu_confirm')
				selection = self.examine_target
				
			direction = 0
			if evt.key in self.key_binds[RiftWizard.KEY_BIND_UP] or evt.key in self.key_binds[RiftWizard.KEY_BIND_LEFT]:
				direction = -1

			elif evt.key in self.key_binds[RiftWizard.KEY_BIND_DOWN] or evt.key in self.key_binds[RiftWizard.KEY_BIND_RIGHT]:
				direction = 1

			if direction:
				self.play_sound('menu_confirm')
				self.examine_target += direction
				self.examine_target = min(self.examine_target, RiftWizard.TITLE_SELECTION_MAX)

				min_selection = RiftWizard.TITLE_SELECTION_LOAD if can_continue_game() else RiftWizard.TITLE_SELECTION_NEW
				self.examine_target = max(min_selection, self.examine_target)

				# do not allow selection of new game no savegame exists
				if can_continue_game():
					while \
					self.examine_target == RiftWizard.TITLE_SELECTION_NEW or \
					self.examine_target == TITLE_SELECTION_NEW_MULTIPLAYER or \
					self.examine_target == TITLE_SELECTION_JOIN_MULTIPLAYER_ONLINE or \
					self.examine_target == TITLE_SELECTION_NEW_MULTIPLAYER_ONLINE:
						self.examine_target += direction
					

		if evt.type == pygame.MOUSEBUTTONDOWN:

			if evt.button == pygame.BUTTON_LEFT:
				for r, o in self.ui_rects:
					if r.collidepoint(m_loc):
						self.play_sound('menu_confirm')
						selection = o
						break
				else:
					self.play_sound('menu_abort')

	dx, dy = self.get_mouse_rel()
	if dx or dy:
		for r, o in self.ui_rects:
			if r.collidepoint(m_loc):
				if self.examine_target != o:
					self.play_sound('menu_confirm')
				self.examine_target = o

	# if selection == RiftWizard.TITLE_SELECTION_NEW:
	# 	self.state = RiftWizard.STATE_PICK_MODE
	# 	self.examine_target = 0
	if selection == RiftWizard.TITLE_SELECTION_ABANDON:
		self.open_abandon_prompt()
	if selection == RiftWizard.TITLE_SELECTION_OPTIONS:
		self.open_options()
	if selection == RiftWizard.TITLE_SELECTION_LOAD:
		if can_continue_game():
			self.load_game()
	if selection == RiftWizard.TITLE_SELECTION_DISCORD:
		import webbrowser
		webbrowser.open("https://discord.gg/NngFZ7B")
	if selection == RiftWizard.TITLE_SELECTION_EXIT:
		self.running = False
	if selection == RiftWizard.TITLE_SELECTION_BESTIARY:
		self.open_shop(RiftWizard.SHOP_TYPE_BESTIARY)


	#
	# if the selection was to start a new game,
	#

	# set the mode
	self.online_mode = False
	self.in_multiplayer_mode = False
	if selection == RiftWizard.TITLE_SELECTION_NEW:
		self.in_multiplayer_mode = False
	if selection in [TITLE_SELECTION_NEW_MULTIPLAYER, TITLE_SELECTION_NEW_MULTIPLAYER_ONLINE, TITLE_SELECTION_JOIN_MULTIPLAYER_ONLINE]:
		self.in_multiplayer_mode = True
		global_in_multiplayer_mode = False
	if selection in [TITLE_SELECTION_NEW_MULTIPLAYER_ONLINE, TITLE_SELECTION_JOIN_MULTIPLAYER_ONLINE]:
		self.online_mode = True
		Client.create_socket()
		# Client.set_message_recieved_callback(multiplayer_socket_callback(self))
	
	self.online__is_host = (selection == TITLE_SELECTION_NEW_MULTIPLAYER_ONLINE)

	# open the character select screen
	if selection in [RiftWizard.TITLE_SELECTION_NEW, TITLE_SELECTION_NEW_MULTIPLAYER, TITLE_SELECTION_NEW_MULTIPLAYER_ONLINE, TITLE_SELECTION_JOIN_MULTIPLAYER_ONLINE]:
		# self.state = RiftWizard.STATE_PICK_MODE
		# self.examine_target = 0
		if not hasattr(self, 'add_character_quirks_p1'):
			self.add_character_quirks_p1 = True
		if not hasattr(self, 'add_character_quirks_p2'):
			self.add_character_quirks_p2 = True
		
		# self.in_char_select = True
		self.state = STATE_CHAR_SELECT


# RiftWizard.PyGameView.process_title_input = process_title_input
Modred.override_menu(RiftWizard.STATE_TITLE, draw_title, process_title_input)







def get_repeatable_keys(self):
	repeatable_keybinds = [
		RiftWizard.KEY_BIND_UP,
		RiftWizard.KEY_BIND_DOWN,
		RiftWizard.KEY_BIND_LEFT,
		RiftWizard.KEY_BIND_RIGHT,
		RiftWizard.KEY_BIND_UP_RIGHT,
		RiftWizard.KEY_BIND_UP_LEFT,
		RiftWizard.KEY_BIND_DOWN_RIGHT,
		RiftWizard.KEY_BIND_DOWN_LEFT
	]
	
	if hasattr(self, 'in_multiplayer_mode') and self.in_multiplayer_mode:
		return [key for kb in repeatable_keybinds for key in self.key_binds[p1_key_binds_map[kb]]] \
			+ [key for kb in repeatable_keybinds for key in self.key_binds[p2_key_binds_map[kb]]]
	else:
		return [key for kb in repeatable_keybinds for key in self.key_binds[p1_key_binds_map[kb]]]
		
# RiftWizard.PyGameView.get_repeatable_keys = get_repeatable_keys


# for RiftWizard.PyGameView.run
def on_run_frame_start(self): 
	Client.listen(multiplayer_socket_callback(self))


import gc
import time


# ######################################### 
#
# Keybinds
#
# ######################################### 

# TODO: new keybinds:
# +KEY_BIND_NEXT_EXAMINE_TARGET = 36^M
# +KEY_BIND_PREV_EXAMINE_TARGET = 37^M
# +KEY_BIND_MAX = KEY_BIND_PREV_EXAMINE_TARGET

# make new keybind related constants
KEY_BIND_TOGGLE_SPELL_SELECT = RiftWizard.KEY_BIND_MAX+1
KEY_BIND_OPEN_CHAT = RiftWizard.KEY_BIND_MAX+2
KEY_BIND_PAUSE = RiftWizard.KEY_BIND_MAX+3

KEY_BIND_UP_P2 = RiftWizard.KEY_BIND_MAX+4 + 0
KEY_BIND_DOWN_P2 = RiftWizard.KEY_BIND_MAX+4 + 1
KEY_BIND_LEFT_P2 = RiftWizard.KEY_BIND_MAX+4 + 2
KEY_BIND_RIGHT_P2 = RiftWizard.KEY_BIND_MAX+4 + 3
KEY_BIND_UP_RIGHT_P2 = RiftWizard.KEY_BIND_MAX+4 + 4
KEY_BIND_UP_LEFT_P2 = RiftWizard.KEY_BIND_MAX+4 + 5
KEY_BIND_DOWN_RIGHT_P2 = RiftWizard.KEY_BIND_MAX+4 + 6
KEY_BIND_DOWN_LEFT_P2 = RiftWizard.KEY_BIND_MAX+4 + 7
KEY_BIND_PASS_P2 = RiftWizard.KEY_BIND_MAX+4 + 8
KEY_BIND_CONFIRM_P2 = RiftWizard.KEY_BIND_MAX+4 + 9
KEY_BIND_ABORT_P2 = RiftWizard.KEY_BIND_MAX+4 + 10
KEY_BIND_SPELL_1_P2 = RiftWizard.KEY_BIND_MAX+4 + 11
KEY_BIND_SPELL_2_P2 = RiftWizard.KEY_BIND_MAX+4 + 12
KEY_BIND_SPELL_3_P2 = RiftWizard.KEY_BIND_MAX+4 + 13
KEY_BIND_SPELL_4_P2 = RiftWizard.KEY_BIND_MAX+4 + 14
KEY_BIND_SPELL_5_P2 = RiftWizard.KEY_BIND_MAX+4 + 15
KEY_BIND_SPELL_6_P2 = RiftWizard.KEY_BIND_MAX+4 + 16
KEY_BIND_SPELL_7_P2 = RiftWizard.KEY_BIND_MAX+4 + 17
KEY_BIND_SPELL_8_P2 = RiftWizard.KEY_BIND_MAX+4 + 18
KEY_BIND_SPELL_9_P2 = RiftWizard.KEY_BIND_MAX+4 + 19
KEY_BIND_SPELL_10_P2 = RiftWizard.KEY_BIND_MAX+4 + 20
KEY_BIND_MODIFIER_1_P2 = RiftWizard.KEY_BIND_MAX+4 + 21
KEY_BIND_MODIFIER_2_P2 = RiftWizard.KEY_BIND_MAX+4 + 22
KEY_BIND_TAB_P2 = RiftWizard.KEY_BIND_MAX+4 + 23
KEY_BIND_CTRL_P2 = RiftWizard.KEY_BIND_MAX+4 + 24
KEY_BIND_VIEW_P2 = RiftWizard.KEY_BIND_MAX+4 + 25
KEY_BIND_WALK_P2 = RiftWizard.KEY_BIND_MAX+4 + 26
KEY_BIND_AUTOPICKUP_P2 = RiftWizard.KEY_BIND_MAX+4 + 27
KEY_BIND_CHAR_P2 = RiftWizard.KEY_BIND_MAX+4 + 28
KEY_BIND_SPELLS_P2 = RiftWizard.KEY_BIND_MAX+4 + 29
KEY_BIND_SKILLS_P2 = RiftWizard.KEY_BIND_MAX+4 + 30
KEY_BIND_HELP_P2 = RiftWizard.KEY_BIND_MAX+4 + 31
KEY_BIND_INTERACT_P2 = RiftWizard.KEY_BIND_MAX+4 + 32
KEY_BIND_MESSAGE_LOG_P2 = RiftWizard.KEY_BIND_MAX+4 + 33
KEY_BIND_THREAT_P2 = RiftWizard.KEY_BIND_MAX+4 + 34
KEY_BIND_LOS_P2 = RiftWizard.KEY_BIND_MAX+4 + 35
KEY_BIND_TOGGLE_SPELL_SELECT_P2 = RiftWizard.KEY_BIND_MAX+4 + 36


# update existing keybind related constants
RiftWizard.KEY_BIND_MAX = KEY_BIND_TOGGLE_SPELL_SELECT_P2

RiftWizard.KEY_BIND_OPTION_ACCEPT = RiftWizard.KEY_BIND_MAX + 1
RiftWizard.KEY_BIND_OPTION_ABORT = RiftWizard.KEY_BIND_MAX + 2
RiftWizard.KEY_BIND_OPTION_RESET = RiftWizard.KEY_BIND_MAX + 3


RiftWizard.default_key_binds[RiftWizard.KEY_BIND_HELP] = [pygame.K_h, None]
RiftWizard.default_key_binds = {	 
	**RiftWizard.default_key_binds,
	KEY_BIND_TOGGLE_SPELL_SELECT : [None, None],
	KEY_BIND_PAUSE : [None, None],
	KEY_BIND_OPEN_CHAT : [pygame.K_SLASH, None],

	KEY_BIND_UP_P2 : [None, None],
	KEY_BIND_DOWN_P2 : [None, None],
	KEY_BIND_LEFT_P2 : [None, None],
	KEY_BIND_RIGHT_P2 : [None, None],
	KEY_BIND_UP_RIGHT_P2 : [None, None],
	KEY_BIND_UP_LEFT_P2: [None, None],
	KEY_BIND_DOWN_RIGHT_P2: [None, None],
	KEY_BIND_DOWN_LEFT_P2: [None, None],
	KEY_BIND_PASS_P2 : [None, None],
	KEY_BIND_CONFIRM_P2 : [None, None],
	KEY_BIND_ABORT_P2 : [None, None],
	KEY_BIND_SPELL_1_P2 : [None, None],
	KEY_BIND_SPELL_2_P2 : [None, None],
	KEY_BIND_SPELL_3_P2 : [None, None], 
	KEY_BIND_SPELL_4_P2 : [None, None], 
	KEY_BIND_SPELL_5_P2 : [None, None], 
	KEY_BIND_SPELL_6_P2 : [None, None], 
	KEY_BIND_SPELL_7_P2 : [None, None], 
	KEY_BIND_SPELL_8_P2 : [None, None], 
	KEY_BIND_SPELL_9_P2 : [None, None], 
	KEY_BIND_SPELL_10_P2 : [None, None], 
	KEY_BIND_MODIFIER_1_P2 : [None, None], 
	KEY_BIND_MODIFIER_2_P2 : [None, None],
	KEY_BIND_TAB_P2 : [None, None], 
	KEY_BIND_CTRL_P2 : [None, None], 
	KEY_BIND_VIEW_P2 : [None, None], 
	KEY_BIND_WALK_P2 : [None, None], 
	KEY_BIND_AUTOPICKUP_P2 : [None, None], 
	KEY_BIND_CHAR_P2 : [None, None], 
	KEY_BIND_SPELLS_P2 : [None, None], 
	KEY_BIND_SKILLS_P2 : [None, None], 
	KEY_BIND_HELP_P2 : [None, None],
	KEY_BIND_INTERACT_P2 : [None, None],
	KEY_BIND_MESSAGE_LOG_P2 : [None, None],
	KEY_BIND_THREAT_P2: [None, None],
	KEY_BIND_LOS_P2: [None, None],
	KEY_BIND_TOGGLE_SPELL_SELECT_P2 : [None, None]
}

default_key_binds_multiplayer_scheme = {	 # TODO: Set these default values ----------------------------------------------------------------------------
	KEY_BIND_PAUSE : [pygame.K_ESCAPE, None],

	RiftWizard.KEY_BIND_UP : [pygame.K_w, pygame.K_UP],   # [pygame.K_UP, pygame.K_KP8],
	RiftWizard.KEY_BIND_DOWN : [pygame.K_s, pygame.K_DOWN],     # [pygame.K_DOWN, pygame.K_KP2],
	RiftWizard.KEY_BIND_LEFT : [pygame.K_a, pygame.K_LEFT],     # [pygame.K_LEFT, pygame.K_KP4],
	RiftWizard.KEY_BIND_RIGHT : [pygame.K_d, pygame.K_RIGHT],      # [pygame.K_RIGHT, pygame.K_KP6],
	RiftWizard.KEY_BIND_UP_RIGHT : [pygame.K_e, None],         # [pygame.K_KP9, None],
	RiftWizard.KEY_BIND_UP_LEFT: [pygame.K_q, None],       # [pygame.K_KP7, None],
	RiftWizard.KEY_BIND_DOWN_RIGHT: [pygame.K_c, None],          # [pygame.K_KP3, None],
	RiftWizard.KEY_BIND_DOWN_LEFT: [pygame.K_z, None],         # [pygame.K_KP1, None],
	RiftWizard.KEY_BIND_PASS : [pygame.K_x, None],     # [pygame.K_SPACE, pygame.K_KP5],
	RiftWizard.KEY_BIND_CONFIRM : [pygame.K_r, pygame.K_RETURN],        # [pygame.K_RETURN, pygame.K_KP_ENTER],
	RiftWizard.KEY_BIND_ABORT : [pygame.K_v, pygame.K_ESCAPE],      # [pygame.K_ESCAPE, None],
	RiftWizard.KEY_BIND_SPELL_1 : [None, None],        # [pygame.K_1, None],
	RiftWizard.KEY_BIND_SPELL_2 : [None, None],        # [pygame.K_2, None],
	RiftWizard.KEY_BIND_SPELL_3 : [None, None],        # [pygame.K_3, None], 
	RiftWizard.KEY_BIND_SPELL_4 : [None, None],        # [pygame.K_4, None], 
	RiftWizard.KEY_BIND_SPELL_5 : [None, None],        # [pygame.K_5, None], 
	RiftWizard.KEY_BIND_SPELL_6 : [None, None],        # [pygame.K_6, None], 
	RiftWizard.KEY_BIND_SPELL_7 : [None, None],        # [pygame.K_7, None], 
	RiftWizard.KEY_BIND_SPELL_8 : [None, None],        # [pygame.K_8, None], 
	RiftWizard.KEY_BIND_SPELL_9 : [None, None],        # [pygame.K_9, None], 
	RiftWizard.KEY_BIND_SPELL_10 : [None, None],         # [pygame.K_0, None], 
	RiftWizard.KEY_BIND_MODIFIER_1 : [None, None],           # [pygame.K_LSHIFT, pygame.K_RSHIFT], 
	RiftWizard.KEY_BIND_MODIFIER_2 : [None, None],           # [pygame.K_LALT, pygame.K_RALT],
	RiftWizard.KEY_BIND_TAB : [pygame.K_TAB, None],    # [pygame.K_TAB, None], 
	RiftWizard.KEY_BIND_CTRL : [None, None],     # [pygame.K_LCTRL, pygame.K_RCTRL], 
	RiftWizard.KEY_BIND_VIEW : [None, None],     # [pygame.K_v, None], 
	RiftWizard.KEY_BIND_WALK : [None, None],     # [pygame.K_w, None], 
	RiftWizard.KEY_BIND_AUTOPICKUP : [None, None],           # [pygame.K_a, None], 
	RiftWizard.KEY_BIND_CHAR : [pygame.K_g, None],     # [pygame.K_c, pygame.K_BACKQUOTE], 
	RiftWizard.KEY_BIND_SPELLS : [None, None],       # [pygame.K_s, None], 
	RiftWizard.KEY_BIND_SKILLS : [None, None],       # [pygame.K_k, None], 
	RiftWizard.KEY_BIND_HELP : [None, None],     # [pygame.K_h, pygame.K_SLASH],
	RiftWizard.KEY_BIND_INTERACT : [None, None],         # [pygame.K_i, pygame.K_PERIOD],
	RiftWizard.KEY_BIND_MESSAGE_LOG : [None, None],            # [pygame.K_m, None],
	RiftWizard.KEY_BIND_THREAT : [None, None],      # [pygame.K_t, None],
	RiftWizard.KEY_BIND_LOS : [None, None],    # [pygame.K_l, None],
	KEY_BIND_TOGGLE_SPELL_SELECT : [pygame.K_f, None],

	KEY_BIND_UP_P2 : [pygame.K_o, None],   # [pygame.K_UP, pygame.K_KP8],
	KEY_BIND_DOWN_P2 : [pygame.K_l, None],     # [pygame.K_DOWN, pygame.K_KP2],
	KEY_BIND_LEFT_P2 : [pygame.K_k, None],     # [pygame.K_LEFT, pygame.K_KP4],
	KEY_BIND_RIGHT_P2 : [pygame.K_SEMICOLON, None],      # [pygame.K_RIGHT, pygame.K_KP6],
	KEY_BIND_UP_RIGHT_P2 : [pygame.K_p, None],         # [pygame.K_KP9, None],
	KEY_BIND_UP_LEFT_P2: [pygame.K_i, None],       # [pygame.K_KP7, None],
	KEY_BIND_DOWN_RIGHT_P2: [pygame.K_SLASH, None],          # [pygame.K_KP3, None],
	KEY_BIND_DOWN_LEFT_P2: [pygame.K_COMMA, None],         # [pygame.K_KP1, None],
	KEY_BIND_PASS_P2 : [pygame.K_PERIOD, None],     # [pygame.K_SPACE, pygame.K_KP5],
	KEY_BIND_CONFIRM_P2 : [pygame.K_u, None],        # [pygame.K_RETURN, pygame.K_KP_ENTER],
	KEY_BIND_ABORT_P2 : [pygame.K_m, None],      # [pygame.K_ESCAPE, None],
	KEY_BIND_SPELL_1_P2 : [None, None],        # [pygame.K_1, None],
	KEY_BIND_SPELL_2_P2 : [None, None],        # [pygame.K_2, None],
	KEY_BIND_SPELL_3_P2 : [None, None],        # [pygame.K_3, None], 
	KEY_BIND_SPELL_4_P2 : [None, None],        # [pygame.K_4, None], 
	KEY_BIND_SPELL_5_P2 : [None, None],        # [pygame.K_5, None], 
	KEY_BIND_SPELL_6_P2 : [None, None],        # [pygame.K_6, None], 
	KEY_BIND_SPELL_7_P2 : [None, None],        # [pygame.K_7, None], 
	KEY_BIND_SPELL_8_P2 : [None, None],        # [pygame.K_8, None], 
	KEY_BIND_SPELL_9_P2 : [None, None],        # [pygame.K_9, None], 
	KEY_BIND_SPELL_10_P2 : [None, None],         # [pygame.K_0, None], 
	KEY_BIND_MODIFIER_1_P2 : [None, None],           # [pygame.K_LSHIFT, pygame.K_RSHIFT], 
	KEY_BIND_MODIFIER_2_P2 : [None, None],           # [pygame.K_LALT, pygame.K_RALT],
	KEY_BIND_TAB_P2 : [pygame.K_LEFTBRACKET, None],    # [pygame.K_TAB, None], 
	KEY_BIND_CTRL_P2 : [None, None],     # [pygame.K_LCTRL, pygame.K_RCTRL], 
	KEY_BIND_VIEW_P2 : [None, None],     # [pygame.K_v, None], 
	KEY_BIND_WALK_P2 : [None, None],     # [pygame.K_w, None], 
	KEY_BIND_AUTOPICKUP_P2 : [None, None],           # [pygame.K_a, None], 
	KEY_BIND_CHAR_P2 : [pygame.K_h, None],     # [pygame.K_c, pygame.K_BACKQUOTE], 
	KEY_BIND_SPELLS_P2 : [None, None],       # [pygame.K_s, None], 
	KEY_BIND_SKILLS_P2 : [None, None],       # [pygame.K_k, None], 
	KEY_BIND_HELP_P2 : [None, None],     # [pygame.K_h, pygame.K_SLASH],
	KEY_BIND_INTERACT_P2 : [None, None],         # [pygame.K_i, pygame.K_PERIOD],
	KEY_BIND_MESSAGE_LOG_P2 : [None, None],            # [pygame.K_m, None],
	KEY_BIND_THREAT_P2 : [None, None],      # [pygame.K_t, None],
	KEY_BIND_LOS_P2 : [None, None],    # [pygame.K_l, None],
	KEY_BIND_TOGGLE_SPELL_SELECT_P2 : [pygame.K_j, None]
}

RiftWizard.key_names = {
	**RiftWizard.key_names,
	KEY_BIND_TOGGLE_SPELL_SELECT : "Toggle Cast Spell Select",
	KEY_BIND_PAUSE : "Open Pause Menu",
	KEY_BIND_OPEN_CHAT : "Open Chat (online mode)",

	KEY_BIND_UP_P2 : "(P2) up",
	KEY_BIND_DOWN_P2 : "(P2) down",
	KEY_BIND_LEFT_P2 : "(P2) left",
	KEY_BIND_RIGHT_P2 : "(P2) right",
	KEY_BIND_UP_RIGHT_P2 : "(P2) up-right",
	KEY_BIND_UP_LEFT_P2: "(P2) up-left",
	KEY_BIND_DOWN_RIGHT_P2: "(P2) down-right",
	KEY_BIND_DOWN_LEFT_P2: "(P2) down-left",
	KEY_BIND_PASS_P2 : "(P2) pass/channel",
	KEY_BIND_CONFIRM_P2 : "(P2) confirm/cast",
	KEY_BIND_ABORT_P2 : "(P2) abort/cast",
	KEY_BIND_SPELL_1_P2 : "(P2) Spell 1",
	KEY_BIND_SPELL_2_P2 : "(P2) Spell 2",
	KEY_BIND_SPELL_3_P2 : "(P2) Spell 3",
	KEY_BIND_SPELL_4_P2 : "(P2) Spell 4",
	KEY_BIND_SPELL_5_P2 : "(P2) Spell 5",
	KEY_BIND_SPELL_6_P2 : "(P2) Spell 6",
	KEY_BIND_SPELL_7_P2 : "(P2) Spell 7",
	KEY_BIND_SPELL_8_P2 : "(P2) Spell 8",
	KEY_BIND_SPELL_9_P2 : "(P2) Spell 9",
	KEY_BIND_SPELL_10_P2 : "(P2) Spell 10",
	KEY_BIND_MODIFIER_1_P2 : "(P2) Spell Modifier Key",
	KEY_BIND_MODIFIER_2_P2 : "(P2) Item Modifier Key",
	KEY_BIND_TAB_P2 : "(P2) Next Target",
	KEY_BIND_CTRL_P2 : "(P2) Show Line of Sight",
	KEY_BIND_VIEW_P2 : "(P2) Look",
	KEY_BIND_WALK_P2 : "(P2) Walk",
	KEY_BIND_AUTOPICKUP_P2 : "(P2) Autopickup",
	KEY_BIND_CHAR_P2 : "(P2) Character Sheet",
	KEY_BIND_SPELLS_P2 : "(P2) Spells",
	KEY_BIND_SKILLS_P2 : "(P2) Skills",
	KEY_BIND_HELP_P2 : "(P2) Help",
	KEY_BIND_INTERACT_P2 : "(P2) Interact",
	KEY_BIND_MESSAGE_LOG_P2 : "(P2) Message Log",
	KEY_BIND_THREAT_P2 : "(P2) Show Threat Zone",
	KEY_BIND_LOS_P2 : "(P2) Show Line of Sight",
	KEY_BIND_TOGGLE_SPELL_SELECT_P2 : "(P2) Toggle Cast Spell Select"
}

SHOP_TYPE_SPELLS_P2 = 5
SHOP_TYPE_UPGRADES_P2 = 6
SHOP_TYPE_SPELL_UPGRADES_P2 = 7
SHOP_TYPE_SHOP_P2 = 8
SHOP_TYPE_BESTIARY_P2 = 9

p1_key_binds_map = {
	RiftWizard.KEY_BIND_UP : RiftWizard.KEY_BIND_UP,
	RiftWizard.KEY_BIND_DOWN : RiftWizard.KEY_BIND_DOWN,
	RiftWizard.KEY_BIND_LEFT : RiftWizard.KEY_BIND_LEFT,
	RiftWizard.KEY_BIND_RIGHT : RiftWizard.KEY_BIND_RIGHT,
	RiftWizard.KEY_BIND_UP_RIGHT : RiftWizard.KEY_BIND_UP_RIGHT,
	RiftWizard.KEY_BIND_UP_LEFT: RiftWizard.KEY_BIND_UP_LEFT,
	RiftWizard.KEY_BIND_DOWN_RIGHT: RiftWizard.KEY_BIND_DOWN_RIGHT,
	RiftWizard.KEY_BIND_DOWN_LEFT: RiftWizard.KEY_BIND_DOWN_LEFT,
	RiftWizard.KEY_BIND_PASS : RiftWizard.KEY_BIND_PASS,
	RiftWizard.KEY_BIND_CONFIRM : RiftWizard.KEY_BIND_CONFIRM,
	RiftWizard.KEY_BIND_ABORT : RiftWizard.KEY_BIND_ABORT,
	RiftWizard.KEY_BIND_SPELL_1 : RiftWizard.KEY_BIND_SPELL_1,
	RiftWizard.KEY_BIND_SPELL_2 : RiftWizard.KEY_BIND_SPELL_2,
	RiftWizard.KEY_BIND_SPELL_3 : RiftWizard.KEY_BIND_SPELL_3,
	RiftWizard.KEY_BIND_SPELL_4 : RiftWizard.KEY_BIND_SPELL_4,
	RiftWizard.KEY_BIND_SPELL_5 : RiftWizard.KEY_BIND_SPELL_5,
	RiftWizard.KEY_BIND_SPELL_6 : RiftWizard.KEY_BIND_SPELL_6,
	RiftWizard.KEY_BIND_SPELL_7 : RiftWizard.KEY_BIND_SPELL_7,
	RiftWizard.KEY_BIND_SPELL_8 : RiftWizard.KEY_BIND_SPELL_8,
	RiftWizard.KEY_BIND_SPELL_9 : RiftWizard.KEY_BIND_SPELL_9,
	RiftWizard.KEY_BIND_SPELL_10 : RiftWizard.KEY_BIND_SPELL_10,
	RiftWizard.KEY_BIND_MODIFIER_1 : RiftWizard.KEY_BIND_MODIFIER_1,
	RiftWizard.KEY_BIND_MODIFIER_2 : RiftWizard.KEY_BIND_MODIFIER_2,
	RiftWizard.KEY_BIND_TAB : RiftWizard.KEY_BIND_TAB,
	RiftWizard.KEY_BIND_CTRL : RiftWizard.KEY_BIND_CTRL,
	RiftWizard.KEY_BIND_VIEW : RiftWizard.KEY_BIND_VIEW,
	RiftWizard.KEY_BIND_WALK : RiftWizard.KEY_BIND_WALK,
	RiftWizard.KEY_BIND_AUTOPICKUP : RiftWizard.KEY_BIND_AUTOPICKUP,
	RiftWizard.KEY_BIND_CHAR : RiftWizard.KEY_BIND_CHAR,
	RiftWizard.KEY_BIND_SPELLS : RiftWizard.KEY_BIND_SPELLS,
	RiftWizard.KEY_BIND_SKILLS : RiftWizard.KEY_BIND_SKILLS,
	RiftWizard.KEY_BIND_HELP : RiftWizard.KEY_BIND_HELP,
	RiftWizard.KEY_BIND_INTERACT : RiftWizard.KEY_BIND_INTERACT,
	RiftWizard.KEY_BIND_MESSAGE_LOG : RiftWizard.KEY_BIND_MESSAGE_LOG,
	RiftWizard.KEY_BIND_THREAT: RiftWizard.KEY_BIND_THREAT,
	RiftWizard.KEY_BIND_LOS: RiftWizard.KEY_BIND_LOS,
	KEY_BIND_TOGGLE_SPELL_SELECT: KEY_BIND_TOGGLE_SPELL_SELECT
}


p2_key_binds_map = {
	RiftWizard.KEY_BIND_UP : KEY_BIND_UP_P2,
	RiftWizard.KEY_BIND_DOWN : KEY_BIND_DOWN_P2,
	RiftWizard.KEY_BIND_LEFT : KEY_BIND_LEFT_P2,
	RiftWizard.KEY_BIND_RIGHT : KEY_BIND_RIGHT_P2,
	RiftWizard.KEY_BIND_UP_RIGHT : KEY_BIND_UP_RIGHT_P2,
	RiftWizard.KEY_BIND_UP_LEFT: KEY_BIND_UP_LEFT_P2,
	RiftWizard.KEY_BIND_DOWN_RIGHT: KEY_BIND_DOWN_RIGHT_P2,
	RiftWizard.KEY_BIND_DOWN_LEFT: KEY_BIND_DOWN_LEFT_P2,
	RiftWizard.KEY_BIND_PASS : KEY_BIND_PASS_P2,
	RiftWizard.KEY_BIND_CONFIRM : KEY_BIND_CONFIRM_P2,
	RiftWizard.KEY_BIND_ABORT : KEY_BIND_ABORT_P2,
	RiftWizard.KEY_BIND_SPELL_1 : KEY_BIND_SPELL_1_P2,
	RiftWizard.KEY_BIND_SPELL_2 : KEY_BIND_SPELL_2_P2,
	RiftWizard.KEY_BIND_SPELL_3 : KEY_BIND_SPELL_3_P2,
	RiftWizard.KEY_BIND_SPELL_4 : KEY_BIND_SPELL_4_P2,
	RiftWizard.KEY_BIND_SPELL_5 : KEY_BIND_SPELL_5_P2,
	RiftWizard.KEY_BIND_SPELL_6 : KEY_BIND_SPELL_6_P2,
	RiftWizard.KEY_BIND_SPELL_7 : KEY_BIND_SPELL_7_P2,
	RiftWizard.KEY_BIND_SPELL_8 : KEY_BIND_SPELL_8_P2,
	RiftWizard.KEY_BIND_SPELL_9 : KEY_BIND_SPELL_9_P2,
	RiftWizard.KEY_BIND_SPELL_10 : KEY_BIND_SPELL_10_P2,
	RiftWizard.KEY_BIND_MODIFIER_1 : KEY_BIND_MODIFIER_1_P2,
	RiftWizard.KEY_BIND_MODIFIER_2 : KEY_BIND_MODIFIER_2_P2,
	RiftWizard.KEY_BIND_TAB : KEY_BIND_TAB_P2,
	RiftWizard.KEY_BIND_CTRL : KEY_BIND_CTRL_P2,
	RiftWizard.KEY_BIND_VIEW : KEY_BIND_VIEW_P2,
	RiftWizard.KEY_BIND_WALK : KEY_BIND_WALK_P2,
	RiftWizard.KEY_BIND_AUTOPICKUP : KEY_BIND_AUTOPICKUP_P2,
	RiftWizard.KEY_BIND_CHAR : KEY_BIND_CHAR_P2,
	RiftWizard.KEY_BIND_SPELLS : KEY_BIND_SPELLS_P2,
	RiftWizard.KEY_BIND_SKILLS : KEY_BIND_SKILLS_P2,
	RiftWizard.KEY_BIND_HELP : KEY_BIND_HELP_P2,
	RiftWizard.KEY_BIND_INTERACT : KEY_BIND_INTERACT_P2,
	RiftWizard.KEY_BIND_MESSAGE_LOG : KEY_BIND_MESSAGE_LOG_P2,
	RiftWizard.KEY_BIND_THREAT: KEY_BIND_THREAT_P2,
	RiftWizard.KEY_BIND_LOS: KEY_BIND_LOS_P2,
	KEY_BIND_TOGGLE_SPELL_SELECT: KEY_BIND_TOGGLE_SPELL_SELECT_P2
}


# ######################################### 
#
# Draw String
#
# ######################################### 

def get_surface_pos(self, surf):
	if surf == self.middle_menu_display:
		return (self.h_margin, 0)
	elif surf == self.examine_display:
		return (self.screen.get_width() - self.h_margin, 0) 
	elif surf == self.character_display:
		return (0, 0)
	elif hasattr(self, 'character_display_p2') and surf == self.character_display_p2:
		return (0, self.character_display.get_height())
	else:
		return (0, 0)
# RiftWizard.PyGameView.get_surface_pos = get_surface_pos

old_draw_string = RiftWizard.PyGameView.draw_string
def draw_string(self, string, surface, x, y, color=(255, 255, 255), mouse_content=None, content_width=None, center=False, char_panel=False, font=None, player=None):
	# if not self.game or not hasattr(self, 'in_multiplayer_mode') or not self.in_multiplayer_mode:
	# 	return old_draw_string(self, string, surface, x, y, color=color, mouse_content=mouse_content, content_width=content_width, center=center, char_panel=char_panel, font=font)
	if not self.game:
		return old_draw_string(self, string, surface, x, y, color=color, mouse_content=mouse_content, content_width=content_width, center=center, char_panel=char_panel, font=font)

	if not font:
		font = self.font

	width = content_width if content_width else font.size(string)[0]
	if center:		
		line_size = self.font.size(string)[0]
		x = x + (width - line_size) // 2
		width = line_size
	
	if mouse_content is not None:
		surf_pos = self.get_surface_pos(surface)

		rect_y = y - 2
		rel_rect = pygame.Rect(x, rect_y, width, self.linesize)
		abs_rect = pygame.Rect(x + surf_pos[0], rect_y + surf_pos[1], width, self.linesize)

		self.ui_rects.append((abs_rect, mouse_content))
		
		# If the mouse moved, and is over this text, set this mouse content as examine target
		dx, dy = self.get_mouse_rel()
		if (dx or dy) and abs_rect.collidepoint(self.get_mouse_pos()):
			self.examine_target = mouse_content

		# If, for whatever reason, this content is the examine target, draw the highlight rect
		is_examined_by_player = False
		try:
			if player:
				is_examined_by_player = player.menu__examine_target == mouse_content
			else:
				is_examined_by_player = self.game.p1.menu__examine_target == mouse_content or self.game.p2.menu__examine_target == mouse_content or self.examine_target == mouse_content
		except Exception as e:
			# print(e)
			is_examined_by_player = self.game.p1.menu__examine_target == mouse_content or self.examine_target == mouse_content
			pass

		if is_examined_by_player:
			should_highlight = True

			# if char_panel:
			# 	if not abs_rect.collidepoint(self.get_mouse_pos()):
			# 		should_highlight = False
			if should_highlight:
				pygame.draw.rect(surface, RiftWizard.HIGHLIGHT_COLOR, rel_rect)

	string_surface = font.render(string, True, color)
	surface.blit(string_surface, (int(x), int(y)))

# RiftWizard.PyGameView.draw_string = draw_string

# ######################################### 
#
# Input
#
# ######################################### 


old_process_char_sheet_input = RiftWizard.PyGameView.process_char_sheet_input
def process_char_sheet_input(self):
	# if not self.in_multiplayer_mode:
	# 	return old_process_char_sheet_input(self)
	unified_process_input(self)
# RiftWizard.PyGameView.process_char_sheet_input = process_char_sheet_input

old_process_shop_input = RiftWizard.PyGameView.process_shop_input
def process_shop_input(self):
	# if not self.in_multiplayer_mode:
	# 	return old_process_shop_input(self)
	unified_process_input(self)
# RiftWizard.PyGameView.process_shop_input = process_shop_input

old_process_confirm_input = RiftWizard.PyGameView.process_confirm_input
def process_confirm_input(self):
	# if not self.in_multiplayer_mode:
	# 	return old_process_confirm_input(self)
	if not self.game:
		return old_process_confirm_input(self)
	unified_process_input(self)
# RiftWizard.PyGameView.process_confirm_input = process_confirm_input

old_process_combat_log_input = RiftWizard.PyGameView.process_combat_log_input
def process_combat_log_input(self):
	# if not self.in_multiplayer_mode:
	# 	return old_process_combat_log_input(self)
	unified_process_input(self)
# RiftWizard.PyGameView.process_combat_log_input = process_combat_log_input


# ######################################### 
#
# Input - Cast Selection
#
# ######################################### 

STATE_CAST_SELECTION = RiftWizard.STATE_SETUP_CUSTOM + 20

# def temp(self, other):
# 	if isinstance(other, Spell):
# 		print('comparing ' + self.spell.name + ' to ' + other.name + ' = ' + str(self.spell == other))
# 		return self.spell == other
# 	if not isinstance(other, RiftWizard.SpellCharacterWrapper):
# 		return False
# 	print('comparing ' + self.spell.name + ' to ' + other.spell.name + ' = ' + str(self.spell == other.spell))
# 	return self.spell == other.spell
# RiftWizard.SpellCharacterWrapper.__eq__ = temp

def update_cast_selection(self, player):
	player_inventory_size = len(player.spells)+len(player.items)
	# respect bounds
	if player.menu__cast_selection__index >= player_inventory_size + 3:
		player.menu__cast_selection__index = player_inventory_size + 3 - 1
	if player.menu__cast_selection__index < 0:
		player.menu__cast_selection__index = 0

	# update examine target
	if player.menu__cast_selection__index >= len(player.spells) and player.menu__cast_selection__index < player_inventory_size:
		player.menu__examine_target = player.items[player.menu__cast_selection__index - len(player.spells)]
	elif player.menu__cast_selection__index < player_inventory_size:
		player.menu__examine_target = RiftWizard.SpellCharacterWrapper(player.spells[player.menu__cast_selection__index])
	elif player.menu__cast_selection__index == player_inventory_size+0:
		player.menu__examine_target = RiftWizard.OPTIONS_TARGET
	elif player.menu__cast_selection__index == player_inventory_size+1:
		player.menu__examine_target = RiftWizard.INSTRUCTIONS_TARGET
	elif player.menu__cast_selection__index == player_inventory_size+2:
		player.menu__examine_target = RiftWizard.CHAR_SHEET_TARGET


def handle_cast_selection(self, evt, key_binds_map, player):
	if evt.type != pygame.KEYDOWN:
		return


	# if event is one of the number keys or the chat key (and we're in online multiplayer mode) exit cast select state and pass the event to handle_event_level
	instantly_exit_to_state_level = False
	if KEY_BIND_OPEN_CHAT in self.key_binds and evt.key in self.key_binds[KEY_BIND_OPEN_CHAT]:
		instantly_exit_to_state_level = True
	for bind in range(key_binds_map[RiftWizard.KEY_BIND_SPELL_1], key_binds_map[RiftWizard.KEY_BIND_SPELL_10]+1):
		if evt.key in self.key_binds[bind] and not self.game.deploying:
			instantly_exit_to_state_level = True
			break
	if instantly_exit_to_state_level:
		player.menu__state = RiftWizard.STATE_LEVEL
		# self.tag_filter.clear()
		# player.menu__examine_target = None
		# self.examine_target = None
		return handle_event_level(self, evt, key_binds_map, player)



	if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_ABORT]] or evt.key in self.key_binds[key_binds_map[KEY_BIND_TOGGLE_SPELL_SELECT]] or (len(player.spells) == 0 and len(player.items) == 0):
		self.play_sound("menu_confirm")
		player.menu__state = RiftWizard.STATE_LEVEL
		self.tag_filter.clear()
		player.menu__examine_target = None
		self.examine_target = None
		return

	if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_CHAR]]:
		open_char_sheet(player)
		return


	update_cast_selection(self, player)

	if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_DOWN]]:
		player.menu__cast_selection__index += 1
		update_cast_selection(self, player)
	
	if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_UP]]:
		player.menu__cast_selection__index -= 1
		update_cast_selection(self, player)

	
	if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_CONFIRM]]:
		player_inventory_size = len(player.spells)+len(player.items)
			
		if player.menu__cast_selection__index < len(player.spells):
			# player is highlighting a spell
			self.choose_spell(player.spells[player.menu__cast_selection__index], player)
		elif player.menu__cast_selection__index < player_inventory_size:
			#player is highlighting an item
			self.choose_spell(player.items[player.menu__cast_selection__index - len(player.spells)].spell, player) 
		else:
			# player is highlighting a menu option
			if player.menu__cast_selection__index == player_inventory_size+0:
				self.open_options()
				return
			elif player.menu__cast_selection__index == player_inventory_size+1:
				pass # do not open the help menu, it'll disrupt the other player
			elif player.menu__cast_selection__index == player_inventory_size+2:
				open_char_sheet(player)
				return

		player.menu__state = RiftWizard.STATE_LEVEL



# ######################################### 
#
# Casting
#
# ######################################### 

old_choose_spell = RiftWizard.PyGameView.choose_spell
def choose_spell(self, spell, player=None):
	# if player == None:
	# 	return old_choose_spell(self, spell)

	if spell.show_tt:
		player.menu__examine_target = spell

	if player.menu__deploy_target:
		self.play_sound("menu_abort")
		return

	if spell.max_charges and not spell.cur_charges:
		self.play_sound("menu_abort")
		self.cast_fail_frames = RiftWizard.SPELL_FAIL_LOCKOUT_FRAMES
		return

	prev_spell = player.cur_spell
	player.cur_spell = spell

	def can_tab_target(t):
		unit = self.game.cur_level.get_unit_at(t.x, t.y)
		if unit is None:
			return False
		return are_hostile(player, unit)	

	self.play_sound("menu_confirm")
	#p = self.get_mouse_level_point()
	#if p and spell.can_cast(*p):
	#	self.cur_spell_target = p
	player.spell__targetable_tiles = spell.get_targetable_tiles()
	if hasattr(spell, 'get_tab_targets'):
		player.spell__tab_targets = spell.get_tab_targets()
	else:
		player.spell__tab_targets = [t for t in player.cur_spell.get_targetable_tiles() if can_tab_target(t)]
		player.spell__tab_targets.sort(key=lambda t: distance(t, self.game.p1))

	player.spell__tab_targets = [Point(t.x, t.y) if not isinstance(t, Point) else t for t in player.spell__tab_targets]

	if self.options['smart_targeting']:
		# If the unit we last targeted is dead, dont target the empty space where it died
		if isinstance(player.cur_spell_target, Unit):
			if not player.cur_spell_target.is_alive():
				player.prev_spell_target = player.cur_spell_target
				player.cur_spell_target = None

		# If we dont have a target, target the first tab target option if it exists
		if not player.cur_spell_target:
			if player.spell__tab_targets:
				player.cur_spell_target = player.spell__tab_targets[0]
			else:
				player.cur_spell_target = Point(player.x, player.y)
	else:
		if not prev_spell:
			if player.cur_spell_target != None:
				player.prev_spell_target = player.cur_spell_target
			if player.prev_spell_target == None:
				player.prev_spell_target = Point(player.x, player.y)
			
			old_target_in_range = distance(player.prev_spell_target, Point(spell.caster.x, spell.caster.y), diag=spell.melee or spell.diag_range) <= spell.get_stat('range')
			player.cur_spell_target = player.prev_spell_target if old_target_in_range else Point(player.x, player.y)

# RiftWizard.PyGameView.choose_spell = choose_spell


old_abort_cur_spell = RiftWizard.PyGameView.abort_cur_spell
def abort_cur_spell(self, player=None):
	# if player == None:
	# 	return old_abort_cur_spell(self)

	player.cur_spell = None
	self.play_sound("menu_abort")
# RiftWizard.PyGameView.abort_cur_spell = abort_cur_spell


old_Game_try_cast = Game.try_cast
def Game_try_cast(self, spell, x, y, player=None):
	# if player == None:
	# 	return old_Game_try_cast(self, spell, x, y)

	if spell.can_cast(x, y):
		set_player_action(self, player, CastAction(spell, x, y))
		return True
	else:
		return False
# Game.try_cast = Game_try_cast

old_cast_cur_spell = RiftWizard.PyGameView.cast_cur_spell
def cast_cur_spell(self, player=None):
	# if player == None:
	# 	return old_cast_cur_spell(self)

	success = self.game.try_cast(player.cur_spell, player.cur_spell_target.x, player.cur_spell_target.y, player)
	if not success:
		self.play_sound('menu_abort')
	player.cur_spell = None
	unit = self.game.cur_level.get_unit_at(player.cur_spell_target.x, player.cur_spell_target.y)
	if unit:
		player.cur_spell_target = unit
# RiftWizard.PyGameView.cast_cur_spell = cast_cur_spell


old_cycle_tab_targets = RiftWizard.PyGameView.cycle_tab_targets
def cycle_tab_targets(self, player=None):
	# if player == None:
	# 	return old_cycle_tab_targets(self)

	target = player.menu__deploy_target or player.cur_spell_target
	if not player.spell__tab_targets:
		return

	if target in player.spell__tab_targets:
		index = player.spell__tab_targets.index(target)
		new_index = (index + 1) % len(player.spell__tab_targets)
	else:
		new_index = 0
	
	target = player.spell__tab_targets[new_index]

	if player.menu__deploy_target:
		player.menu__deploy_target = target
	if player.cur_spell_target:
		player.cur_spell_target = target

	self.try_examine_tile(target) ## TODO: update this for multiplayer -----------------------------------------------
# RiftWizard.PyGameView.cycle_tab_targets = cycle_tab_targets

# ######################################### 
#
# Input - Shop
#
# ######################################### 	

old_close_shop = RiftWizard.PyGameView.close_shop
def close_shop(self, player=None):
	# if player == None or not self.in_multiplayer_mode:
	# 	return old_close_shop(self)

	if player.menu__abort_to_spell_shop:
		self.play_sound("menu_abort")
		player.menu__abort_to_spell_shop = False
		self.open_shop(RiftWizard.SHOP_TYPE_SPELLS, player=player)
		return

	self.game.try_shop(None, player)

	if player.menu__shop_type == RiftWizard.SHOP_TYPE_SHOP or player.menu__prev_state == RiftWizard.STATE_LEVEL:
		self.play_sound("menu_confirm")
		player.menu__state = RiftWizard.STATE_LEVEL

	elif player.menu__shop_type != RiftWizard.SHOP_TYPE_SHOP:
		open_char_sheet(player)

		player.menu__examine_target = player.menu__shop_open_examine_target

# RiftWizard.PyGameView.close_shop = close_shop



def shop_page_adjust(self, inc, player, max_shop_pages, max_shop_objects, shop_options):
	if max_shop_pages < 1:
		return

	if max_shop_pages > 1:
		self.play_sound("menu_confirm")
	else:
		self.play_sound("menu_abort")

	player.menu__shop_page += inc
	player.menu__shop_page = player.menu__shop_page	% max_shop_pages
	shop_selection_index = player.menu__shop_page * max_shop_objects

	player.menu__examine_target = shop_options[int(shop_selection_index)]

def inc_shop_index(self, inc, player, max_shop_pages, max_shop_objects, shop_options):
	# Bump examine target up by inc, roll over if it goes over the shop page
	if not shop_options:
		return
	self.play_sound("menu_confirm")
	
	if player.menu__examine_target in shop_options:
		shop_selection_index = shop_options.index(player.menu__examine_target)
	else:
		shop_selection_index = max_shop_pages * player.menu__shop_page
		inc = 0

	shop_selection_index += inc

	shop_selection_index = max(player.menu__shop_page * max_shop_objects, shop_selection_index)
	shop_selection_index = min((player.menu__shop_page + 1) * max_shop_objects - 1, shop_selection_index)
	shop_selection_index = min(len(shop_options) - 1, shop_selection_index)

	player.menu__examine_target = shop_options[int(shop_selection_index)]


old_Game_has_upgrade = Game.has_upgrade
def Game_has_upgrade(self, upgrade, player=None):
	# if player == None:
	# 	return old_Game_has_upgrade(self, upgrade)
	if player == None:
		return False

	# Spells you can have only one of
	if any(s.name == upgrade.name for s in player.spells):
		return True

	# General upgrades (non spell upgrades) are like spells
	if any(s.name == upgrade.name for s in player.get_skills()):
		return True

	# Shrine upgrades are infinitely stackable
	if getattr(upgrade, 'shrine_name', None):
		return False

	# Non shrine upgrades- check name, prereq pair
	if any(isinstance(b, Upgrade) and b.name == upgrade.name and b.prereq == upgrade.prereq and not b.shrine_name for b in player.buffs):
		return True
	return False
# Game.has_upgrade = Game_has_upgrade

old_Game_get_upgrade_cost = Game.get_upgrade_cost
def Game_get_upgrade_cost(self, upgrade, player=None):
	# if player == None:
	# 	return old_Game_get_upgrade_cost(self, upgrade)

	level = upgrade.level
	if level == 0:
		return 0
		
	if player.discount_tag in upgrade.tags:
		level = level - 1

	# stuff for character quirks
	
	if hasattr(player, 'tag_purchase_cost_bonus'):
		total_bonus = sum([player.tag_purchase_cost_bonus[tag] for tag in upgrade.tags if tag in player.tag_purchase_cost_bonus])
		level += total_bonus
	if hasattr(player, 'tag_purchase_cost_multiplier'):
		total_multiplier = 1 
		for multiplier in (player.tag_purchase_cost_multiplier[tag] for tag in upgrade.tags if tag in player.tag_purchase_cost_multiplier):
			total_multiplier *= multiplier
		level *= total_multiplier
		level = int(level)
	
	# end character quirks

	level -= player.scroll_discounts.get(upgrade.name, 0)
	level = max(level, 1)
	return level
# Game.get_upgrade_cost = Game_get_upgrade_cost

old_Game_can_buy_upgrade = Game.can_buy_upgrade
def Game_can_buy_upgrade(self, upgrade, player=None):
	# if player == None:
	# 	return old_Game_can_buy_upgrade(self, upgrade)

	# Limit 20 spells
	if isinstance(upgrade, Spell) and len(player.spells) >= 20:
		return False

	if self.has_upgrade(upgrade, player):
		return False

	if isinstance(upgrade, Upgrade) and upgrade.prereq:
		if not self.has_upgrade(upgrade.prereq, player):
			return False

	if player.xp < self.get_upgrade_cost(upgrade, player):
		return False

	if hasattr(upgrade, 'exc_class') and upgrade.exc_class:
		# Non shrine upgrades- check name, prereq pair
		if any(isinstance(b, Upgrade) and getattr(b, 'exc_class', None) == upgrade.exc_class and b.prereq == upgrade.prereq for b in player.buffs):
			return False

	# adding in for character quirks
	if hasattr(player, 'banned_spell_types'):
		matching = [tag for tag in upgrade.tags if tag in player.banned_spell_types]
		if len(matching) > 0:
			return False
	if hasattr(player, 'banned_purchaces'):
		if upgrade in player.banned_purchaces:
			return False

	#if self.get_upgrade_distance(upgrade) > 0:
	#	return False

	return True
# Game.can_buy_upgrade = Game_can_buy_upgrade


old_Game_can_shop = Game.can_shop
def Game_can_shop(self, item, player=None):
	# if player == None:
	# 	return old_Game_can_shop(self, item)

	if self.cur_level.cur_shop:

		if isinstance(item, Upgrade) and self.has_upgrade(item, player):
			return False

		if self.cur_level.cur_shop.can_shop(player, item):
			return True
		return False

	elif isinstance(item, Upgrade) or isinstance(item, Spell):
		if self.can_buy_upgrade(item, player):
			return True
		return False

	return False
# Game.can_shop = Game_can_shop


old_Game_buy_upgrade = Game.buy_upgrade
def Game_buy_upgrade(self, upgrade, player=None):
	# if player == None:
	# 	return old_Game_buy_upgrade(self, upgrade)

	print('game buy upgrade') # shrines do not go through here
	print(type(upgrade))
	if self.online_mode:
		player_num = '1' if player == self.p1 else '2'
		if isinstance(upgrade, SpellUpgrade):
			Client.send_purchase(player_num + "SUpgd" + str(player.spells.index(upgrade.prereq)) + ',' + str(upgrade.prereq.spell_upgrades.index(upgrade))) # spell upgrade buy
		elif isinstance(upgrade, Upgrade):
			Client.send_purchase(player_num + "Skill" + str(player.all_player_skills.index(upgrade)))
		elif isinstance(upgrade, Spell):
			Client.send_purchase(player_num + "Spell" + str(player.all_player_spells.index(upgrade)))

		if not self.online__is_host:
			return

	player.xp -= self.get_upgrade_cost(upgrade, player)
	if isinstance(upgrade, Upgrade):
		player.apply_buff(upgrade)
	elif isinstance(upgrade, Spell):
		player.add_spell(upgrade)
# Game.buy_upgrade = Game_buy_upgrade

old_Game_try_shop = Game.try_shop
def Game_try_shop(self, item, player=None):
	# if player == None:
	# 	return old_Game_try_shop(self, item)

	if not self.can_shop(item, player):
		return False

	if self.cur_level.cur_shop: # shrines go through here
		if self.online_mode:
			player_num = '1' if player == self.p1 else '2'
			Client.send_purchase(player_num + "Shop " + int(self.cur_level.cur_shop.index(item))) # make sure this works

			if not self.online__is_host:
				return

		self.cur_level.act_shop(player, item) 

	elif isinstance(item, Upgrade) or isinstance(item, Spell):
		self.buy_upgrade(item, player) 

	if item:
		self.recent_upgrades.append(item) 

	return True
# Game.try_shop = Game_try_shop


old_confirm_buy = RiftWizard.PyGameView.confirm_buy
def confirm_buy(self, player=None):
	# if player == None:
	# 	return old_confirm_buy(self)

	success = self.game.try_shop(player.menu__chosen_purchase, player)
	# Shouldnt get into the screen if we cannot buy
	assert(success)

	if player.menu__shop_type in [RiftWizard.SHOP_TYPE_SPELLS, RiftWizard.SHOP_TYPE_UPGRADES]:
		player.menu__char_sheet_select_index += 1

	player.menu__abort_to_spell_shop = False
	self.close_shop(player)
# RiftWizard.PyGameView.confirm_buy = confirm_buy

old_abort_buy = RiftWizard.PyGameView.abort_buy
def abort_buy(self, player=None):
	# if player == None:
	# 	return old_abort_buy(self)

	player.menu__state = RiftWizard.STATE_SHOP
	player.menu__chosen_purchase = None
	self.play_sound("menu_abort")
# RiftWizard.PyGameView.abort_buy = abort_buy

old_open_buy_prompt = RiftWizard.PyGameView.open_buy_prompt
def open_buy_prompt(self, item, player=None):
	# if player == None:
	# 	return old_open_buy_prompt(self, item)

	self.play_sound("menu_confirm")
	player.menu__state = RiftWizard.STATE_CONFIRM

	# player.menu__confirm_yes = lambda: self.confirm_buy(player)
	# player.menu__confirm_no = lambda: self.abort_buy(player)
	func_type = type(self.confirm_buy)
	player.menu__confirm_yes = func_type(self.confirm_buy, player)
	func_type = type(self.abort_buy)
	player.menu__confirm_no = func_type(self.abort_buy, player)

	player.menu__chosen_purchase = item

	if player.menu__shop_type == RiftWizard.SHOP_TYPE_SHOP:
		attr = player.menu__chosen_purchase.name.replace(player.menu__chosen_purchase.shrine_name + ' ', '').lower()
		player.menu__confirm_text = "Use %s on %s?" % (self.game.cur_level.cur_shop.name, player.menu__chosen_purchase.prereq.name)
	else:
		cost = self.game.get_upgrade_cost(player.menu__chosen_purchase, player)
		player.menu__confirm_text = "Learn %s for %s SP?" % (player.menu__chosen_purchase.name, cost)

	# Default to no (?)
	player.menu__examine_target = False
# RiftWizard.PyGameView.open_buy_prompt = open_buy_prompt

old_try_buy_shop_selection = RiftWizard.PyGameView.try_buy_shop_selection
def try_buy_shop_selection(self, prompt=True, player=None):
	# if player == None or not self.in_multiplayer_mode:
	# 	return old_try_buy_shop_selection(self, prompt=prompt)

	if player.menu__shop_type == RiftWizard.SHOP_TYPE_BESTIARY:
		return

	if player.menu__examine_target == None:
		return

	# If its an owned spell, open upgrades shop for that spell
	if player.menu__examine_target in player.spells:
		self.play_sound("menu_confirm")
		self.open_shop(RiftWizard.SHOP_TYPE_SPELL_UPGRADES, spell=player.menu__examine_target, player=player)
		player.menu__abort_to_spell_shop = True
		return

	success = self.game.can_shop(player.menu__examine_target, player)
	if not success:
		self.play_sound("menu_abort")
		return

	self.open_buy_prompt(player.menu__examine_target, player)

	if not prompt:
		self.confirm_buy(player)
# RiftWizard.PyGameView.try_buy_shop_selection = try_buy_shop_selection


def handle_shop_event(self, evt, key_binds_map, player):
	if evt.type != pygame.KEYDOWN:
		return

	shop_options = self.get_shop_options(player)
	num_options = len(shop_options)
	max_shop_objects = self.max_shop_objects/2 - 3 if self.in_multiplayer_mode else self.max_shop_objects

	max_shop_pages = math.ceil(num_options / max_shop_objects)
	
	if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_DOWN]]:
		inc_shop_index(self, 1, player, max_shop_pages, max_shop_objects, shop_options)

	if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_UP]]:
		inc_shop_index(self, -1, player, max_shop_pages, max_shop_objects, shop_options)

	if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_LEFT]]:
		shop_page_adjust(self, -1, player, max_shop_pages, max_shop_objects, shop_options)

	if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_RIGHT]]:
		shop_page_adjust(self, 1, player, max_shop_pages, max_shop_objects, shop_options)

	# TODO: update this for 2p ----------------------------------------------------------
	# if (pygame.K_a <= evt.key <= pygame.K_z) and chr(evt.key) in self.tag_keys:
	# 	tag = self.tag_keys[chr(evt.key)]
	# 	self.toggle_shop_filter(tag) # TODO: update this for 2p ----------------------------------------------------------

	if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_CONFIRM]]:
		self.try_buy_shop_selection(prompt=False, player=player)
		return

	if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_ABORT]]:
		self.close_shop(player)


def handle_event_chat(self, evt, key_binds_map, player):
	if evt.type != pygame.KEYDOWN:
		return

	retval = Chat.process_chat_input_event(self, evt, [pygame.K_RETURN, pygame.K_KP_ENTER], [pygame.K_ESCAPE], [pygame.K_UP], [pygame.K_DOWN], pygame.K_BACKSPACE)
	if not retval[1]:
		self.chat_open = False
		if retval[0]:
			Client.send_chat(retval[0])


def handle_any_event(self, evt, key_binds_map, player):
	if player.menu__state == RiftWizard.STATE_LEVEL:
		if self.online_mode and self.chat_open:
			return handle_event_chat(self, evt, key_binds_map, player)
		else:
			return handle_event_level(self, evt, key_binds_map, player)
	elif player.menu__state == RiftWizard.STATE_CHAR_SHEET:
		handle_event_char_sheet(self, evt, key_binds_map, player)
	elif player.menu__state == STATE_CAST_SELECTION:
		handle_cast_selection(self, evt, key_binds_map, player)
	elif player.menu__state == RiftWizard.STATE_SHOP:
		handle_shop_event(self, evt, key_binds_map, player)
	else:
		# set_player_action(self, player, PassAction())
		pass


def process_click_character(self, button, x, y):
	target = None
	for (r, c) in self.ui_rects: 
		if r.collidepoint((x, y)):
			target = c 

	if not target:
		return

	# TODO: include what to do when the char sheet is open
	# TODO: include what to do when a shop is open
	if target == RiftWizard.CHAR_SHEET_TARGET:
		open_char_sheet(self.main_player)
		# self.char_sheet_select_index = 0
	elif target == RiftWizard.INSTRUCTIONS_TARGET:
		self.show_help()
	elif target == RiftWizard.OPTIONS_TARGET:
		self.open_options()
	elif button == pygame.BUTTON_LEFT:
		if isinstance(target, RiftWizard.SpellCharacterWrapper):
			self.choose_spell(target.spell, self.main_player)
		if isinstance(target, Item):
			self.choose_spell(target.spell, self.main_player)
	elif button == pygame.BUTTON_RIGHT:
		self.examine_target = target
# RiftWizard.PyGameView.process_click_character = process_click_character


def handle_mouse_level(self):
	no_menus_open = self.main_player.menu__state == RiftWizard.STATE_LEVEL or self.main_player.menu__state == STATE_CAST_SELECTION
	char_sheet_open = self.main_player.menu__state == RiftWizard.STATE_CHAR_SHEET
	shop_open = self.main_player.menu__state == RiftWizard.STATE_SHOP
	
	if no_menus_open:
		level_point = self.get_mouse_level_point()

		mouse_dx, mouse_dy = self.get_mouse_rel()
		if mouse_dx or mouse_dy:
			if level_point:	
				if self.main_player.cur_spell:
					self.main_player.cur_spell_target = level_point
				if self.game.deploying and not self.online_mode:
					self.main_player.menu__deploy_target = level_point
					self.deploy_target = level_point

				self.try_examine_tile(level_point)
				
			self.main_player.menu__examine_target = None

			mouse_pos = self.get_mouse_pos()
			for r, c in self.ui_rects:
				if r.collidepoint(mouse_pos):
					self.main_player.menu__examine_target = c

		for click in self.events:
			if click.type != pygame.MOUSEBUTTONDOWN:
				continue

			# Cancel click to move on subsequent clicks
			self.path = []
			
			if self.gameover_frames > 8 and not self.gameover_tiles:
				self.enter_reminisce()
				return

			mx, my = self.get_mouse_pos()
			if mx < self.h_margin:
				self.process_click_character(click.button, mx, my)

			if click.button == pygame.BUTTON_LEFT and self.can_execute_inputs():
				if self.main_player.cur_spell and click.button == pygame.BUTTON_LEFT and level_point:
					self.main_player.cur_spell_target = level_point
					self.cast_cur_spell(self.main_player)
				elif self.game.deploying and level_point:
					deploy_overlaps_other_player = self.other_player and (level_point.x == self.other_player.x and level_point.y == self.other_player.y)
					if self.game.next_level.is_point_in_bounds(level_point) and not deploy_overlaps_other_player:
						self.main_player.menu__deploy_target = level_point
						self.deploy_target = level_point
						self.try_examine_tile(level_point)
						
						self.deploy(True)
				elif level_point and all(u.team == RiftWizard.TEAM_PLAYER for u in self.game.cur_level.units):
					self.path = self.game.cur_level.find_path(self.main_player, level_point, self.main_player, pythonize=True)
				elif level_point and distance(level_point, self.main_player, diag=True) >= 1:
					path = self.game.cur_level.find_path(self.main_player, level_point, self.main_player, pythonize=True)
					if path:
						movedir = Point(path[0].x - self.main_player.x, path[0].y - self.main_player.y)
						handle_move_dir(self, movedir, self.main_player, self.other_player, force_no_repeats=True)
				elif level_point and distance(level_point, self.main_player) == 0:
					if not hasattr(self.main_player, 'cur_spell') or not self.main_player.cur_spell:
						set_player_action(self.game, self.main_player, PassAction())
			if click.button == pygame.BUTTON_RIGHT:
				if self.main_player.cur_spell:
					self.abort_cur_spell(self.main_player)
				if self.game.deploying:
					self.main_player.menu__deploy_target = None
					self.main_player.examine_target = None
					self.examine_target = None
					self.game.try_abort_deploy()
					self.play_sound("menu_abort")

			# Only process one mouse evt per frame
			break
	elif char_sheet_open:
		mouse_pos = self.get_mouse_pos()
		mx, my = mouse_pos
		
		mouse_dx, mouse_dy = pygame.mouse.get_rel()
		if self.mouse_dy or self.mouse_dx:
			for r, c in self.ui_rects:
				if r.collidepoint(mouse_pos):
					self.main_player.menu__examine_target = c
					
		for evt in self.events:
			if evt.type !=pygame.MOUSEBUTTONDOWN:
				continue
			
			if evt.button == pygame.BUTTON_LEFT:
				if self.examine_target == RiftWizard.LEARN_SPELL_TARGET:
					self.open_shop(RiftWizard.SHOP_TYPE_SPELLS, player=self.main_player)
				elif self.examine_target == RiftWizard.LEARN_SKILL_TARGET:
					self.open_shop(RiftWizard.SHOP_TYPE_UPGRADES, player=self.main_player)
				elif isinstance(self.examine_target, Spell):		
					self.open_shop(RiftWizard.SHOP_TYPE_SPELL_UPGRADES, self.examine_target, player=self.main_player)
				elif isinstance(self.examine_target, Upgrade) and self.examine_target.prereq is None:
					self.open_shop(RiftWizard.SHOP_TYPE_UPGRADES, player=self.main_player)
				elif isinstance(self.examine_target, Upgrade) and self.examine_target is not None:
					self.open_shop(RiftWizard.SHOP_TYPE_SPELL_UPGRADES, self.examine_target.prereq, player=self.main_player)
	
			if evt.button == pygame.BUTTON_RIGHT:
				self.main_player.menu__state = RiftWizard.STATE_LEVEL
				self.play_sound("menu_abort")
	elif shop_open:
		mouse_pos = self.get_mouse_pos()

		
		shop_options = self.get_shop_options(self.main_player)
		num_options = len(shop_options)
		max_shop_objects = self.max_shop_objects/2 - 3 if self.in_multiplayer_mode else self.max_shop_objects
		max_shop_pages = math.ceil(num_options / max_shop_objects)
		
		# start_index = int(self.main_player.menu__shop_page * max_shop_objects)
		# end_index = int(start_index + max_shop_objects)

		mouse_dx, mouse_dy = pygame.mouse.get_rel()
		if self.mouse_dy or self.mouse_dx:
			for r, c in self.ui_rects:
				if r.collidepoint(mouse_pos):
					self.main_player.menu__examine_target = c

		# shop_start_index = start_index
		for click in self.events:
			if click.type != pygame.MOUSEBUTTONDOWN:
				continue

			# shop_page_adjust(self, -1, player, max_shop_pages, max_shop_objects, shop_options)
			if click.button == pygame.BUTTON_WHEELDOWN:
				self.play_sound("menu_confirm")
				shop_page_adjust(self, 1, self.main_player, max_shop_pages, max_shop_objects, shop_options)

			if click.button == pygame.BUTTON_WHEELUP:
				self.play_sound("menu_confirm")
				shop_page_adjust(self, -1, self.main_player, max_shop_pages, max_shop_objects, shop_options)

			if click.button == pygame.BUTTON_LEFT:

				for r, c in self.ui_rects:
					if r.collidepoint(mouse_pos):
						if c == RiftWizard.TOOLTIP_NEXT:
							shop_page_adjust(self, 1, self.main_player, max_shop_pages, max_shop_objects, shop_options)
						elif c == RiftWizard.TOOLTIP_PREV:
							shop_page_adjust(self, -1, self.main_player, max_shop_pages, max_shop_objects, shop_options)
						elif c == RiftWizard.TOOLTIP_EXIT:
							self.close_shop(player=self.main_player)
						elif isinstance(c, Tag):
							# self.toggle_shop_filter(c) # TODO: this
							break
						else:
							# prompt's supposed to be True, but for some reason that softlocks the game and does not buy the item
							# self.try_buy_shop_selection(prompt=True, player=self.main_player) 
							self.try_buy_shop_selection(prompt=False, player=self.main_player)
							break

			elif click.button == pygame.BUTTON_RIGHT:
				self.close_shop(player=self.main_player)
				self.play_sound("menu_abort")


def unified_process_input(self):
	
	# self.game.cur_level.is_awaiting_input = False #self.game.p1.requested_action == None or self.game.p2.requested_action == None

	if self.cast_fail_frames:
		self.cast_fail_frames -= 1

	if any(evt.type == pygame.KEYDOWN for evt in self.events) and self.gameover_frames > 8 and not self.gameover_tiles:
		self.enter_reminisce()
		return

	# exclusive self.main_player stuff ------------------------------------------------------------------------ 
	if self.can_execute_inputs() and self.path:
		if not self.path_delay:
			next_point = self.path[0]
			self.path = self.path[1:]
			movedir = Point(next_point.x - self.main_player.x, next_point.y - self.main_player.y)
			self.try_move(movedir, self.main_player)
			self.main_player.prev_spell_target = self.main_player.cur_spell_target
			self.main_player.cur_spell_target = None
			self.path_delay = RiftWizard.MAX_PATH_DELAY
		else:
			self.path_delay -= 1
	# --------------------------------------------------------------------------------------------------

	movedir_pMain = None
	movedir_pOther = None
	for evt in self.events:
		if self.in_multiplayer_mode:
			new_movedir_pMain = handle_any_event(self, evt, p1_key_binds_map, self.main_player)
			new_movedir_pOther = handle_any_event(self, evt, p2_key_binds_map, self.other_player)

			movedir_pMain = new_movedir_pMain if new_movedir_pMain != None else movedir_pMain
			movedir_pOther = new_movedir_pOther if new_movedir_pOther != None else movedir_pOther
		else:
			new_movedir_pMain = handle_any_event(self, evt, p1_key_binds_map, self.main_player)
			movedir_pMain = new_movedir_pMain if new_movedir_pMain != None else movedir_pMain
			

	if self.in_multiplayer_mode:
		handle_move_dir(self, movedir_pMain, self.main_player, self.other_player.menu__deploy_target)
		handle_move_dir(self, movedir_pOther, self.other_player, self.main_player.menu__deploy_target)
	else:
		handle_move_dir(self, movedir_pMain, self.main_player, None)



	# more exclusive main_player stuff ------------------------------------------------------------------------ 
	handle_mouse_level(self)
	

old_get_shop_options = RiftWizard.PyGameView.get_shop_options
def get_shop_options(self, player=None):
	# if not self.in_multiplayer_mode or player == None:
	# 	return old_get_shop_options(self)

	if player.menu__shop_type == RiftWizard.SHOP_TYPE_SPELLS:
		return [s for s in player.all_player_spells if all(t in s.tags for t in self.tag_filter)]
	if player.menu__shop_type == RiftWizard.SHOP_TYPE_UPGRADES:
		return [u for u in player.all_player_skills if all(t in u.tags for t in self.tag_filter)]
	if player.menu__shop_type == RiftWizard.SHOP_TYPE_SPELL_UPGRADES:
		return [u for u in player.menu__shop_upgrade_spell.spell_upgrades]
	if player.menu__shop_type == RiftWizard.SHOP_TYPE_SHOP:
		if self.game.cur_level.cur_shop:
			return self.game.cur_level.cur_shop.items
	if player.menu__shop_type == RiftWizard.SHOP_TYPE_BESTIARY:
		return all_monsters
	else:
		return []
# RiftWizard.PyGameView.get_shop_options = get_shop_options


class DummyObject(object):
    pass

old_open_shop = RiftWizard.PyGameView.open_shop
def open_shop(self, shop_type, spell=None, player=None):
	# if not self.in_multiplayer_mode:
	# 	return old_open_shop(self, shop_type, spell=spell)

	if player == None:
		player = DummyObject()
		player.menu__state = self.state
		player.menu__examine_target = self.examine_target
		
	player.menu__prev_state = player.menu__state

	self.play_sound("menu_confirm")

	player.menu__shop_open_examine_target = player.menu__examine_target

	player.menu__shop_type = shop_type
	if spell:
		player.menu__shop_upgrade_spell = spell

	player.menu__state = RiftWizard.STATE_SHOP
	player.menu__shop_page = 0
	
	shoptions = self.get_shop_options(player)
	if shoptions:
		player.menu__examine_target = shoptions[0]

	self.tag_filter.clear()
# RiftWizard.PyGameView.open_shop = open_shop


# ######################################### 
#
# Input - Char Sheet
#
# ######################################### 

def handle_event_char_sheet(self, evt, key_binds_map, player):
	if evt.type != pygame.KEYDOWN:
		return

	if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_DOWN]]:
		self.adjust_char_sheet_selection(1, player)
		self.play_sound("menu_confirm")

	if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_UP]]:
		self.adjust_char_sheet_selection(-1, player)
		self.play_sound("menu_confirm")
		
	if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_LEFT]] or evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_RIGHT]]:
		# self.toggle_char_sheet_selection_type()
		player.menu__char_sheet__is_on_spells = not player.menu__char_sheet__is_on_spells
		if player.menu__char_sheet__is_on_spells:
			player.menu__examine_target = RiftWizard.LEARN_SPELL_TARGET
		else:
			player.menu__examine_target = RiftWizard.LEARN_SKILL_TARGET
		
	if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_ABORT]]:
		self.play_sound("menu_confirm")
		# player.menu__state = RiftWizard.STATE_LEVEL
		player.menu__state = STATE_CAST_SELECTION
		update_cast_selection(self, player)
		self.tag_filter.clear()

	if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_CONFIRM]]:
		if player.menu__examine_target == RiftWizard.LEARN_SKILL_TARGET:
			self.open_shop(RiftWizard.SHOP_TYPE_UPGRADES, player=player)

		elif player.menu__examine_target == RiftWizard.LEARN_SPELL_TARGET:
			self.open_shop(RiftWizard.SHOP_TYPE_SPELLS, player=player)

		elif player.menu__examine_target in player.spells:
			self.open_shop(RiftWizard.SHOP_TYPE_SPELL_UPGRADES, player.menu__examine_target, player=player)

		elif player.menu__examine_target in player.get_skills():
			self.open_shop(RiftWizard.SHOP_TYPE_UPGRADES, player=player)

		elif hasattr(player.menu__examine_target, "prereq") and player.menu__examine_target.prereq in player.spells:
			self.open_shop(RiftWizard.SHOP_TYPE_SPELL_UPGRADES, self.examine_target.prereq, player=player)

	if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_SPELLS]]:
		self.open_shop(RiftWizard.SHOP_TYPE_SPELLS, player=player)

	if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_SKILLS]]:
			self.open_shop(RiftWizard.SHOP_TYPE_UPGRADES, player=player)

	for bind in range(key_binds_map[RiftWizard.KEY_BIND_SPELL_1], key_binds_map[RiftWizard.KEY_BIND_SPELL_10]):
		if not bind in key_binds_map or not key_binds_map[bind] in self.key_binds:
			continue

		if evt.key in self.key_binds[key_binds_map[bind]]:
			index = bind - RiftWizard.KEY_BIND_SPELL_1

			for key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_MODIFIER_1]]:
				if key and keys[key]:
					index += 10
		
			if len(player.spells) > index:
				self.examine_target = player.spells[index]

	char_sheet_selection_max = len(player.spells) if self.char_sheet_select_type == RiftWizard.CHAR_SHEET_SELECT_TYPE_SPELLS else len(player.get_skills())

	if player.menu__char_sheet__select_index < 0:
		player.menu__char_sheet__select_index = char_sheet_selection_max
	if player.menu__char_sheet__select_index > char_sheet_selection_max:
		player.menu__char_sheet__select_index = 0

old_adjust_char_sheet_selection = RiftWizard.PyGameView.adjust_char_sheet_selection
def adjust_char_sheet_selection(self, diff, player=None):
	# if player == None:
	# 	old_adjust_char_sheet_selection(self, diff)

	assert(diff in [1, -1, 0])
	
	skills = player.get_skills()

	# Looking at known spell
	if isinstance(player.menu__examine_target, Spell) and player.menu__examine_target in player.spells:
		
		spell_index = player.spells.index(player.menu__examine_target)
		new_index = spell_index + diff	# Pressing up at top of spell list

		if new_index < 0:
			self.play_sound("menu_abort")
		if 0 <= new_index < len(player.spells):
			self.play_sound("menu_confirm")
			player.menu__examine_target = player.spells[new_index]
		if new_index >= len(player.spells):
			self.play_sound("menu_confirm")
			player.menu__examine_target = RiftWizard.LEARN_SPELL_TARGET

	# Looking at known skill
	elif isinstance(player.menu__examine_target, Upgrade) and player.menu__examine_target.prereq == None:

		skill_index = skills.index(player.menu__examine_target)
		new_index = skill_index + diff
		
		if new_index < 0:
			self.play_sound("menu_abort")
		if 0 <= new_index < len(skills):
			self.play_sound("menu_confirm")
			player.menu__examine_target = skills[new_index]
		if new_index >= len(skills):
			self.play_sound("menu_confirm")
			player.menu__examine_target = RiftWizard.LEARN_SKILL_TARGET

	# Looking at spell upgrade for known spell
	elif isinstance(player.menu__examine_target, Upgrade) and player.menu__examine_target.prereq in player.spells:

		prereq_index = player.spells.index(player.menu__examine_target.prereq)
		new_index = prereq_index + diff

		if new_index < 0:
			self.play_sound("menu_abort")
		if 0 <= new_index <= len(player.spells) - 1:
			self.play_sound("menu_confirm")
			player.menu__examine_target = player.spells[new_index]
		if new_index == len(player.spells):
			self.play_sound("menu_confirm")
			player.menu__examine_target = RiftWizard.LEARN_SPELL_TARGET
		else:
			self.play_sound("menu_abort")

	# Looking at 'Learn Skill'
	elif player.menu__examine_target == RiftWizard.LEARN_SPELL_TARGET:

		if diff < 0 and player.spells:
			self.play_sound("menu_confirm")
			player.menu__examine_target = player.spells[-1]
		else:
			self.play_sound("menu_abort")
	# Looking at 'Learn Spell'
	elif player.menu__examine_target == RiftWizard.LEARN_SKILL_TARGET:

		if diff < 0 and skills:
			self.play_sound("menu_confirm")
			player.menu__examine_target = skills[-1]
		else:
			self.play_sound("menu_abort")

	# other random exmaine targets
	else:
		self.play_sound("menu_confirm")
		player.menu__examine_target = player.spells[0] if player.spells else RiftWizard.LEARN_SPELL_TARGET

# RiftWizard.PyGameView.adjust_char_sheet_selection = adjust_char_sheet_selection 


# ######################################### 
#
# Input - Level
#
# ######################################### 

def open_char_sheet(player):
	player.menu__char_sheet__is_open = True
	player.menu__char_sheet__char_sheet_select_index = 0
	player.menu__state = RiftWizard.STATE_CHAR_SHEET
	player.menu__char_sheet__select_index = 0

	if player.menu__char_sheet__is_on_spells:
		player.menu__examine_target = RiftWizard.LEARN_SPELL_TARGET
	else:
		player.menu__examine_target = RiftWizard.LEARN_SKILL_TARGET


def autopickup(self):
	props = [tile.prop for tile in self.game.cur_level.iter_tiles() if tile.prop]
	pickups = [p for p in props if isinstance(p, ManaDot) or isinstance(p, ItemPickup) or isinstance(p, HeartDot) or isinstance(p, SpellScroll)]
	destinations = [p for p in pickups if self.game.cur_level.find_path(self.main_player, p, self.main_player, pythonize=True)]
	

	full_path = []
	prev_dest = self.main_player
	while destinations:
		destinations.sort(key=lambda d: distance(prev_dest, d), reverse=True)
		d = destinations.pop()
		path = self.game.cur_level.find_path(prev_dest, d, self.main_player, pythonize=True)
		if path:
			full_path += path
			prev_dest = d

	self.path = full_path
# RiftWizard.PyGameView.autopickup = autopickup

def handle_event_level(self, evt, key_binds_map, player):
	if not evt.type == pygame.KEYDOWN:
		return


	# Cancel path on key down
	# do this here instead of by checking pressed keys to deal with pygame alt tab bug
	self.path = []

	movedir = None
	
	if self.can_execute_inputs():
		if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_UP]]:
			movedir = Point(0, -1)
		if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_DOWN]]:
			movedir = Point(0, 1)
		if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_LEFT]]:
			movedir = Point(-1, 0)
		if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_RIGHT]]:
			movedir = Point(1, 0)
		if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_DOWN_RIGHT]]:
			movedir = Point(1, 1)
		if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_DOWN_LEFT]]:
			movedir = Point(-1, 1)
		if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_UP_LEFT]]:
			movedir = Point(-1, -1)
		if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_UP_RIGHT]]:
			movedir = Point(1, -1)

		if evt.key in self.key_binds[key_binds_map[KEY_BIND_TOGGLE_SPELL_SELECT]]:
			player.menu__state = STATE_CAST_SELECTION
			update_cast_selection(self, player)


		if KEY_BIND_OPEN_CHAT in self.key_binds and evt.key in self.key_binds[KEY_BIND_OPEN_CHAT]:
			self.chat_open = True
			

		if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_CONFIRM]]:
			if player.cur_spell:
				self.cast_cur_spell(player)
			elif self.game.deploying:
				if self.online_mode:
					player_num = '1' if player == self.game.p1 else '2'
					Client.send_purchase(player_num + 'Dploy' + 'Confirm')

					if not self.online__is_host:
						return

				self.deploy(True)


		if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_PASS]]:
			if not hasattr(player, 'cur_spell') or not player.cur_spell:
				set_player_action(self.game, player, PassAction())


		# TODO: update this for 2p ------------------------------------------------------------------------ 
		keys = pygame.key.get_pressed()
		for bind in range(key_binds_map[RiftWizard.KEY_BIND_SPELL_1], key_binds_map[RiftWizard.KEY_BIND_SPELL_10]+1):
			if evt.key in self.key_binds[bind] and not self.game.deploying:
				index = bind - key_binds_map[RiftWizard.KEY_BIND_SPELL_1]

				for modifier in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_MODIFIER_1]]:
					if modifier and keys[modifier]:
						index += 10
				
				# Item
				is_item = False
				for modifier in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_MODIFIER_2]]:
					if modifier and keys[modifier]:
						is_item = True
				
				if is_item:
					if len(player.items) > index:
						# TODO: set on cast selection false here
						player.menu__state = STATE_CAST_SELECTION # RiftWizard.STATE_LEVEL
						self.choose_spell(player.items[index].spell, player=player)
				else:
					if len(player.spells) > index:
						player.menu__state = STATE_CAST_SELECTION # RiftWizard.STATE_LEVEL
						self.choose_spell(player.spells[index], player=player)

		# TODO: check this works for 2p ------------------------------------------------------------------------ 
		if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_WALK]]:
			if not any(are_hostile(u, player) for u in self.game.cur_level.units):
				spell = RiftWizard.WalkSpell()
				spell.caster = player
				self.choose_spell(spell, player)

		# TODO: check this works for 2p ------------------------------------------------------------------------ 
		if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_VIEW]]:
			spell = RiftWizard.LookSpell()
			spell.caster = player
			self.choose_spell(spell, player)

		
		if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_CHAR]]:
			open_char_sheet(player)


		# TODO: check this works for 2p ------------------------------------------------------------------------ 
		if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_SPELLS]]:
			self.open_shop(RiftWizard.SHOP_TYPE_SPELLS, player=player)

		# TODO: check this works for 2p ------------------------------------------------------------------------ 
		if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_SKILLS]]:
			self.open_shop(RiftWizard.SHOP_TYPE_UPGRADES, player=player)

		# TODO: update this for 2p ------------------------------------------------------------------------ 
		if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_TAB]] and (self.cur_spell or self.deploy_target):
			self.cycle_tab_targets(player=player)

		# TODO: update this for 2p ------------------------------------------------------------------------ 
		if evt.key in self.key_binds[RiftWizard.KEY_BIND_HELP]:
			self.show_help()

		# TODO: update this for 2p ------------------------------------------------------------------------ 
		if not self.in_multiplayer_mode:
			if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_AUTOPICKUP]] and all(not are_hostile(player, u) for u in self.game.cur_level.units):
				self.autopickup()

		# TODO: update this for 2p ------------------------------------------------------------------------ 
		if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_INTERACT]] and self.game.cur_level.tiles[player.x][player.y].prop:
			if self.online_mode:
				return # TODO: implement interact for online mode

			self.game.cur_level.tiles[player.x][player.y].prop.on_player_enter(player)

			if self.game.cur_level.cur_shop:
				self.open_shop(RiftWizard.SHOP_TYPE_SHOP, player=player)

			if self.game.cur_level.cur_portal and not self.game.deploying:
				self.game.enter_portal()


		
		if evt.key in self.key_binds[key_binds_map[RiftWizard.KEY_BIND_ABORT]]:
			if player.cur_spell:
				self.abort_cur_spell(player)
			elif self.game.deploying:
				if self.online_mode:
					player_num = '1' if player == self.game.p1 else '2'
					Client.send_purchase(player_num + 'Dploy' + 'Cancel')

					if not self.online__is_host:
						return

				player.menu__deploy_target = None
				player.examine_target = None
				self.examine_target = None
				self.game.try_abort_deploy()
				self.play_sound("menu_abort")
			else:
				self.open_options()
			# elif evt.key in self.key_binds[KEY_BIND_PAUSE]:
			# 	self.open_options()
		elif evt.key not in self.key_binds[p1_key_binds_map[RiftWizard.KEY_BIND_ABORT]] and \
			 evt.key not in self.key_binds[p2_key_binds_map[RiftWizard.KEY_BIND_ABORT]] and \
			 evt.key in self.key_binds[KEY_BIND_PAUSE]:
			self.open_options()
		

		# TODO: update this for 2p ------------------------------------------------------------------------ 
		# if evt.key in self.key_binds[KEY_BIND_MESSAGE_LOG]:
		# 	self.open_combat_log()

	if movedir:
		return movedir


def handle_move_dir(self, movedir, player, other_player, force_no_repeats=False):
	if movedir == None: 
		return

	keys = pygame.key.get_pressed()

	if movedir:
		repeats = 1
		if not force_no_repeats and keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
			repeats = 4

		if player.cur_spell:
			for _ in range(repeats):
				new_spell_target = Point(player.cur_spell_target.x + movedir.x, player.cur_spell_target.y + movedir.y)
				if self.game.cur_level.is_point_in_bounds(new_spell_target):
					player.cur_spell_target = new_spell_target
					self.try_examine_tile(new_spell_target)
		elif self.game.deploying and player.menu__deploy_target:
			for _ in range(repeats): 
				new_point = Point(player.menu__deploy_target.x + movedir.x, player.menu__deploy_target.y + movedir.y)

				if other_player != None:
					new_point_is_valid = self.game.next_level.is_point_in_bounds(new_point) and not (new_point.x == other_player.x and new_point.y == other_player.y)
				else:
					new_point_is_valid = self.game.next_level.is_point_in_bounds(new_point)

				if new_point_is_valid:
					if self.online_mode:		
						Client.send_action(encode_action(player, MoveAction(new_point.x, new_point.y)))
						if not self.online__is_host:
							return

					player.menu__deploy_target = new_point
					self.deploy_target = new_point
					self.try_examine_tile(new_point)
		else:
			self.try_move(movedir, player)
			player.prev_spell_target = player.cur_spell_target
			player.cur_spell_target = None


# new process level input
process_level_input_for_p1 = False 
old_process_level_input = RiftWizard.PyGameView.process_level_input
def process_level_input(self):
	# if not self.in_multiplayer_mode:
	# 	old_process_level_input(self)
	# 	self.game.p1.requested_action = self.game.cur_level.requested_action
	# 	return
	unified_process_input(self)

# RiftWizard.PyGameView.process_level_input = process_level_input


# PyGameView
old_PyGameView_try_move = RiftWizard.PyGameView.try_move 
def PyGameView_try_move(self, movedir, player=None):
	# if not self.in_multiplayer_mode:
	# 	return old_PyGameView_try_move(self, movedir)

	result = self.game.try_move(*movedir, player)
	if result:
		self.play_sound("step_player")
		self.second_step = 1 - self.second_step
	return result
# RiftWizard.PyGameView.try_move = PyGameView_try_move

# game
old_Game_try_move = Game.try_move 
def Game_try_move(self, xdir, ydir, player=None):
	# if not self.in_multiplayer_mode:
	# 	return old_Game_try_move(self, xdir, ydir)

	# TODO: Uncomment the below ---------------------------------------------------------
	# if not self.cur_level.is_awaiting_input:
	# 	return False
	
	new_x = player.x + xdir
	new_y = player.y + ydir

	if self.cur_level.can_move(player, new_x, new_y):
		set_player_action(self, player, MoveAction(new_x, new_y))
		return True

# Game.try_move = Game_try_move


def set_player_action(self, player, action, from_server=False):
	if not allow_turn_queuing(self, player, action, RiftWizard.turn_mode) and self.cur_level.turn_no <= player.last_turn_acted:
		return

	# TODO: this
	if self.online_mode and not self.online__is_host and not from_server:
		if not player == self.p2:
			return # guest cannot set p1's action
		Client.send_action(encode_action(player, action))
		return
	if self.online_mode and not self.online__is_host and from_server:
		pass # if I'm a guest and this came from the server, continue setting the player action like normal
	
	if self.online_mode and self.online__is_host:
		Client.send_action(encode_action(player, action)) # host is the master copy, so it sends all 

	player.requested_action = action
	self.cur_level.requested_action = None #MoveAction(new_x, new_y)
	self.cur_level.is_awaiting_input = False #self.p1.requested_action == None or self.p2.requested_action == None
	self.cur_level.cur_chatter = None


# level
# def set_order_move(self, x, y):
# 	self.requested_action = MoveAction(x, y)
# 	self.is_awaiting_input = False
# 	self.cur_chatter = None


# make ALL units use ai - aka force player units to read actions from their ai, rather than using specially tracked actions
old_Unit_advance = Unit.advance
def Unit_advance(self, orders=None):
	# global global_in_multiplayer_mode
	# if not global_in_multiplayer_mode:
	# 	old_Unit_advance(self, orders=orders)
	# 	return

	can_act = True
	for b in self.buffs:
		if not b.on_attempt_advance():
			can_act = False

	if can_act:
		# Take an action
		action = self.get_ai_action() # player's ai tracks the human's input
			
		logging.debug("%s will %s" % (self, action))
		assert(action is not None)

		if isinstance(action, MoveAction):
			self.level.act_move(self, action.x, action.y, force_swap=self.is_coward)
		elif isinstance(action, CastAction):
			self.level.act_cast(self, action.spell, action.x, action.y)
			if action.spell.quick_cast:
				return False
		elif isinstance(action, PassAction):
			self.level.event_manager.raise_event(EventOnPass(self), self)


	self.try_dismiss_ally()

	# TODO- post turn effects
	# TODO- return False if a non turn consuming action was taken
	return True

# Unit.advance = Unit_advance

# def set_order_move(self, x, y):
# 	self.requested_action = MoveAction(x, y)
# 	self.is_awaiting_input = False
# 	self.cur_chatter = None

# def set_order_cast(self, spell, x, y):
# 	self.requested_action = CastAction(spell, x, y)
# 	self.is_awaiting_input = False
# 	self.cur_chatter = None

# def set_order_pass(self):
# 	self.requested_action = PassAction()
# 	self.is_awaiting_input = False
# 	self.cur_chatter = None

# TODO: implement this update for 2p ------------------------------------------------------------------------------------------------------ 
# Level.is_awaiting_input = not (self.game.p1.requested_action and self.game.p2.requested_action)



# ######################################### 
#
# Deploying
#
# #########################################

old_try_deploy = Game.try_deploy
def try_deploy(self, x, y, x2=None, y2=None):
	# TODO: I probably shouldn't ever be calling old_try_deploy - make sure this works
	if (x2 == None): ######################################################################################################################################
		return old_try_deploy(self, x, y)

	# make sure deploying is possible
	assert(self.deploying)

	if not self.next_level.can_stand(x, y, self.p1) or not self.next_level.can_stand(x2, y2, self.p2):
		return False

	# player setup
	self.p1.Anim = None

	if self.p1.cur_hp > 0:
		self.cur_level.remove_obj(self.p1)
		self.next_level.start_pos = Point(x, y)
		self.next_level.spawn_player(self.p1)
	self.next_level.player_unit = self.p1

	self.p2.Anim = None

	if self.p2.cur_hp > 0:
		self.cur_level.remove_obj(self.p2)
		self.next_level.start_pos = Point(x2, y2)
		# self.next_level.spawn_player(self.p2)
		spawn_p2(self.next_level, self.p2)
	self.next_level.player_unit_2 = self.p2


	# other setup (from Game.try_deploy)
	self.cur_level = self.next_level
	self.next_level = None
	self.deploying = False

	self.level_num += 1
	self.has_granted_xp = False
	
	self.cur_level.setup_logging(logdir=self.logdir, level_num=self.level_num)

	import gc
	gc.collect()

	self.subscribe_mutators()
	self.save_game()

	if self.cur_level.gen_params:
		logging.getLogger("Level").debug("\nEntering level %d, id=%d" % (self.level_num, self.cur_level.gen_params.level_id))

	return True
# Game.try_deploy = try_deploy


old_deploy = RiftWizard.PyGameView.deploy
def deploy(self, p):
	# if (p2 == None):
	# 	return old_deploy(self, p)

	if self.in_multiplayer_mode:
		p2 = self.game.p2
		deploy_success = self.game.try_deploy(self.game.p1.menu__deploy_target.x, self.game.p1.menu__deploy_target.y, self.game.p2.menu__deploy_target.x, self.game.p2.menu__deploy_target.y)
	else:
		p2 = None
		deploy_success = self.game.try_deploy(self.game.p1.menu__deploy_target.x, self.game.p1.menu__deploy_target.y, None, None)

	if deploy_success:	
	
		self.deploy_anim_frames = 0
		self.make_level_screenshot()

		self.effects = []

		if self.game.level_num < LAST_LEVEL:
			self.play_sound("victory_new")
		else:
			self.play_sound("victory_bell")
			self.play_music("mordred_theme")

		self.deploy_target = None

		if self.in_multiplayer_mode:
			self.game.p1.Anim = None
			self.game.p2.Anim = None

			self.game.p1.menu__deploy_target = None
			self.game.p2.menu__deploy_target = None

			self.game.p1.last_turn_acted = -1
			self.game.p2.last_turn_acted = -1
			self.game.p1.times_moved_this_turn = 0
			self.game.p2.times_moved_this_turn = 0
		else:
			self.game.p1.Anim = None
			self.game.p1.menu__deploy_target = None
			self.game.p1.last_turn_acted = -1
			self.game.p1.times_moved_this_turn = 0

		
		

		# SteamAdapter.set_presence_level(self.game.level_num)

		# prev_max = SteamAdapter.get_stat('r')
		# if self.game.level_num > prev_max:
			# Set reached level
			# SteamAdapter.set_stat('r', self.game.level_num)

	else:
		self.play_sound("menu_abort")
# RiftWizard.PyGameView.deploy = deploy



# ######################################### 
#
# Game Over Condition
#
# #########################################

def gameover_condition(self):
	if not hasattr(self, 'p2'):
		return self.p1.cur_hp <= 0

	if GAMEOVER_CONDITION == BOTH_PLAYERS:
		return self.p1.cur_hp <= 0 and self.p2.cur_hp <= 0
	if GAMEOVER_CONDITION == EITHER_PLAYER:
		return self.p1.cur_hp <= 0 or self.p2.cur_hp <= 0

old_check_triggers = Game.check_triggers
def check_triggers(self):
	# if not self.in_multiplayer_mode:
	# 	return old_check_triggers(self)


	if self.cur_level.cur_portal and not self.deploying:
		self.enter_portal()
		
	if all([u.team == RiftWizard.TEAM_PLAYER for u in self.cur_level.units]):
			
		if not self.has_granted_xp:
			#self.p1.xp += 3
			self.has_granted_xp = True
			self.victory_evt = True
			self.finalize_level(victory=True)

	if gameover_condition(self): # this is the only line I changed
		self.gameover = True
		self.finalize_save(victory=False)

	if self.level_num == LAST_LEVEL and not any(u.name == "Mordred" for u in self.cur_level.units):
		self.victory = True
		self.victory_evt = True
		self.finalize_save(victory=True)
# Game.check_triggers = check_triggers

# ######################################### 
#
# Draw Spell Targeting and deploying
#
# #########################################

TILE_OVERLAY_FILE_NAME = 'tile_overlay_colorless_bright'
def get_tile_overlay(self, color):
	self.images = dict()
	if not hasattr(self, 'tile_overlay_image'): #not TILE_OVERLAY_FILE_NAME in self.images:
		img = pygame.image.load(os.path.join('mods', 'API_Multiplayer', TILE_OVERLAY_FILE_NAME) + '.png')
		# self.images[TILE_OVERLAY_FILE_NAME] = img
		self.tile_overlay_image = img
	# img = self.images[TILE_OVERLAY_FILE_NAME]
	img = self.tile_overlay_image

	if (TILE_OVERLAY_FILE_NAME, color) in self.images:
		return self.images[(TILE_OVERLAY_FILE_NAME, color)]
	
	if len(color) == 3:
		color = (color[0], color[1], color[2], 100)

	alpha = color[3]
	color = (color[0], color[1], color[2])

	img = img.copy()
	img.fill(color, special_flags=pygame.BLEND_RGB_MULT)
	img.set_alpha(alpha)
	self.images[(TILE_OVERLAY_FILE_NAME, color)] = img

	return img
	
def get_tile_categories(self, player):
	# Current main target
	if player.cur_spell.can_cast(player.cur_spell_target.x, player.cur_spell_target.y):
		main_target = set()
		main_target.add(player.cur_spell_target)
		main_target_untargetable = set()
	else:
		main_target = set()
		main_target_untargetable = set()
		main_target_untargetable.add(player.cur_spell_target)


	used_tiles = set()
	used_tiles.add(Point(player.cur_spell_target.x, player.cur_spell_target.y))

	# Currently impacted squares
	curr_impacted = set()
	if player.cur_spell.can_cast(player.cur_spell_target.x, player.cur_spell_target.y):
		for p in player.cur_spell.get_impacted_tiles(player.cur_spell_target.x, player.cur_spell_target.y):
			if p in used_tiles:
				continue
			curr_impacted.add(p)
			used_tiles.add(Point(p.x, p.y))


	targetable = set()
	untargetable_in_range = set()
	if player.cur_spell.show_tt:
		# Targetable squares
		for p in player.spell__targetable_tiles: 
			if p in used_tiles:
				continue
			targetable.add(p)
			used_tiles.add(Point(p.x, p.y))

		# Untargetable but in range squares
		aoe = player.cur_spell.get_targetable_tiles()
		if player.cur_spell.melee:
			aoe = self.game.cur_level.get_points_in_ball(player.x, player.y, 1, diag=True)

		for p in aoe:
			if p in used_tiles:
				continue
			if p.x == player.x and p.y == player.y and not player.cur_spell.can_target_self:
				continue
			if player.cur_spell.get_stat('requires_los') and not self.game.cur_level.can_see(player.x, player.y, p.x, p.y):
				continue

			untargetable_in_range.add(p)

	return [main_target, curr_impacted, targetable, untargetable_in_range, main_target_untargetable]

old_draw_level = RiftWizard.PyGameView.draw_level
def draw_level(self):
	old_draw_level(self)

	if self.gameover_frames >= 8:
		return

	# if not self.in_multiplayer_mode:
	# 	return

	#
	# spell targeting
	#

	if hasattr(self.game.p1, 'cur_spell') and self.game.p1.cur_spell:
		p1_tiles = get_tile_categories(self, self.game.p1)
	else:
		p1_tiles = [set(), set(), set(), set(), set()]
		
	if hasattr(self.game, 'p2') and hasattr(self.game.p2, 'cur_spell') and self.game.p2.cur_spell:
		p2_tiles = get_tile_categories(self, self.game.p2)
	else:
		p2_tiles = [set(), set(), set(), set(), set()]
		
	def tile_category(categories, tile):
		for i in range(5):
			if tile in categories[i]:
				return i
		return -1
		

	idle_frame = RiftWizard.idle_frame
	cur_frame = idle_frame % 2
	blit_area = (cur_frame * RiftWizard.SPRITE_SIZE, 0, RiftWizard.SPRITE_SIZE, RiftWizard.SPRITE_SIZE)

	# [main_target, curr_impacted, targetable, untargetable_in_range, main_target_untargetable]
	p1_colors = self.player_characters_color_schemes[self.p1_char_select_index] # [(0, 0, 100), (30, 30, 60), (30, 30, 50), (255, 80, 80), (100, 0, 0)]
	p2_colors = self.player_characters_color_schemes[self.p2_char_select_index] # [(0, 255, 0), (30, 150, 30), (10, 50, 10), (255, 80, 80), (100, 0, 0)]

	all_tiles = [tile for category in p1_tiles for tile in category] + [tile for category in p2_tiles for tile in category]
	for tile in all_tiles:
		p1_category = tile_category(p1_tiles, tile)
		p2_category = tile_category(p2_tiles, tile)

		image = None

		if p1_category == -1 and p2_category == -1:
			print('warning! tile snuck in without a category!')
			continue
		
		if (p2_category == -1 or p2_category == COLOR_SCHEME_UNTARGETABLE_IN_RANGE) and not p1_category == -1:
			image = get_tile_overlay(self, p1_colors[p1_category])
		elif (p1_category == -1 or p1_category == COLOR_SCHEME_UNTARGETABLE_IN_RANGE) and not p2_category == -1:
			image = get_tile_overlay(self, p2_colors[p2_category])
		
		# if we don't have an image yet
		if not image:
			# alpha blend the two colors
			alphaSum = p1_colors[p1_category][3] + p2_colors[p2_category][3]
			p1_prop = p1_colors[p1_category][3]/alphaSum
			p2_prop = p2_colors[p2_category][3]/alphaSum
			
			color = tuple(int(p1c*p1_prop + p2c*p2_prop) for (p1c, p2c) in zip(p1_colors[p1_category], p2_colors[p2_category]))
			color = (color[0], color[1], color[2], max(p1_colors[p1_category][3], p2_colors[p2_category][3]))
			image = get_tile_overlay(self, color)

		if not image:
			print('error! tile uncolored!')
			continue

		x = tile.x * RiftWizard.SPRITE_SIZE
		y = tile.y * RiftWizard.SPRITE_SIZE
		self.level_display.blit(image, (x, y), blit_area)


	#
	# Deploying
	#
	level = self.get_display_level()

	# Draw deploy
	if self.game.deploying and self.game.p1.menu__deploy_target:
		image = RiftWizard.get_image(["UI", "deploy_ok_animated"]) if level.can_stand(self.game.p1.menu__deploy_target.x, self.game.p1.menu__deploy_target.y, self.game.p1) else RiftWizard.get_image(["UI", "deploy_no_animated"])
		deploy_frames = image.get_width() // RiftWizard.SPRITE_SIZE
		deploy_frame = idle_frame % deploy_frames
		self.level_display.blit(image, (self.game.p1.menu__deploy_target.x * RiftWizard.SPRITE_SIZE, self.game.p1.menu__deploy_target.y * RiftWizard.SPRITE_SIZE), (deploy_frame * RiftWizard.SPRITE_SIZE, 0, RiftWizard.SPRITE_SIZE, RiftWizard.SPRITE_SIZE))

	if self.in_multiplayer_mode and self.game.deploying and self.game.p2.menu__deploy_target:
		image = RiftWizard.get_image(["UI", "deploy_ok_animated"]) if level.can_stand(self.game.p2.menu__deploy_target.x, self.game.p2.menu__deploy_target.y, self.game.p2) else RiftWizard.get_image(["UI", "deploy_no_animated"])
		deploy_frames = image.get_width() // RiftWizard.SPRITE_SIZE
		deploy_frame = idle_frame % deploy_frames
		self.level_display.blit(image, (self.game.p2.menu__deploy_target.x * RiftWizard.SPRITE_SIZE, self.game.p2.menu__deploy_target.y * RiftWizard.SPRITE_SIZE), (deploy_frame * RiftWizard.SPRITE_SIZE, 0, RiftWizard.SPRITE_SIZE, RiftWizard.SPRITE_SIZE))


	#
	# Blit to main screen
	#
	pygame.transform.scale(self.whole_level_display, (self.screen.get_width(), self.screen.get_height()), self.screen)

	#
	# chat menu
	#
	if self.online_mode:
		Chat.draw_chat_messages(self, self.screen, cur_x=self.h_margin)

# RiftWizard.PyGameView.draw_level = draw_level


Modred.override_menu(RiftWizard.STATE_LEVEL, draw_level, lambda pygameview: None)
		

	


# ######################################### 
#
# Char sheet
#
# #########################################


def draw_single_char_sheet(self, character_display, player):
	if not hasattr(player, 'menu__char_sheet__is_on_spells'):
		player.menu__char_sheet__is_on_spells = True

	character_display.fill((0, 0, 0))
	self.draw_panel(character_display)
	# make the borders of the menu green to indicate the player's movement keys will affect this menu, not the playspace
	character_display.fill((100, 255, 100, 90), special_flags=pygame.BLEND_RGBA_MULT)

	# Spells
	spell_x_offset = self.border_margin # + 18
	cur_x = spell_x_offset
	cur_y = self.linesize
	col_width = character_display.get_width() - 2*self.border_margin

	if player.menu__char_sheet__is_on_spells:
		self.draw_string("Spells", character_display, cur_x, cur_y)

		m_loc = self.get_mouse_pos()

		cur_y += self.linesize
		cur_y += self.linesize
		spell_index = 0

		for spell in player.spells:
			#Spells
			self.draw_string(spell.name, character_display, cur_x, cur_y, mouse_content=spell, content_width=col_width)
			cur_y += self.linesize

			# Upgrades
			for upgrade in sorted((b for b in player.buffs if isinstance(b, Upgrade) and b.prereq == spell), key=lambda b: b.shrine_name is None):
				fmt = upgrade.name
				if upgrade.shrine_name:
					color = RiftWizard.COLOR_XP
					fmt = upgrade.name.replace('(%s)' % spell.name, '')
				else:
					color = (255, 255, 255)
				self.draw_string(' ' + fmt, character_display, cur_x, cur_y, mouse_content=upgrade, content_width=col_width, color=color)

				cur_y += self.linesize

			available_upgrades = len([b for b in spell.spell_upgrades if not b.applied])
			if available_upgrades:
				self.draw_string(' %d Upgrades Available' % available_upgrades, character_display, cur_x, cur_y)
				cur_y += self.linesize



			spell_index += 1


		learn_color = (255, 255, 255) if len(player.spells) < 20 else (170, 170, 170)

		self.draw_string("Learn New Spell (S)", character_display, cur_x, cur_y, learn_color, mouse_content=RiftWizard.LEARN_SPELL_TARGET, content_width=col_width, player=player)

		page_num_string = '<<<   Page 1/2   >>>'
		string_height = self.font.size(page_num_string)[1]
		self.draw_string(page_num_string, character_display, cur_x, character_display.get_height()-self.border_margin-string_height, content_width=col_width, player=player)

	else:
		# Skills
		self.draw_string("Skills", character_display, cur_x, cur_y)
		
		cur_y += self.linesize
		cur_y += self.linesize

		for skill in player.get_skills():
			self.draw_string(skill.name, character_display, cur_x, cur_y, mouse_content=skill, content_width=col_width)
			cur_y += self.linesize
		self.draw_string("Learn New Skill (K)", character_display, cur_x, cur_y, mouse_content=RiftWizard.LEARN_SKILL_TARGET,  content_width=col_width, player=player)
		
		page_num_string = '<<<   Page 2/2   >>>'
		string_height = self.font.size(page_num_string)[1]
		self.draw_string(page_num_string, character_display, cur_x, character_display.get_height()-self.border_margin-string_height, content_width=col_width)

	# self.screen.blit(character_display, (0, 0))

old_draw_char_sheet = RiftWizard.PyGameView.draw_char_sheet
def draw_char_sheet(self):
	# if not self.in_multiplayer_mode:
	# 	return old_draw_char_sheet(self)
	
	self.draw_level()

# RiftWizard.PyGameView.draw_char_sheet = draw_char_sheet


# ######################################### 
#
# patch the key rebind menu to be scrollable, and add a 'reset to Multiplayer default' option
#
# #########################################

def try_init_key_rebind(self):
	if not hasattr(self, 'key_rebind_menu'):
		self.rebinding = False

		rows_by_keybind = dict()
		def reset_keybind_names():
			keybinds = list(RiftWizard.key_names.keys())

			for keybind in keybinds:
				row = rows_by_keybind[keybind]
				if keybind in self.new_key_binds:
					key1 = self.new_key_binds[keybind][0]
					key2 = self.new_key_binds[keybind][1]
					
					keyname_1 = pygame.key.name(key1) if key1 else "Unbound"
					keyname_2 = pygame.key.name(key2) if key2 else "Unbound"

					row.subrows[1].set_text(keyname_1)
					row.subrows[2].set_text(keyname_2)
			
		def make_callback_for_key_rebind(key_bind, is_primary):
			def callback():
				self.rebinding = True
				self.rebinding_key = [key_bind, 0 if is_primary else 1]
				pass
			return callback
		def reset_keybinds_to_default():
			self.play_sound("menu_confirm")
			self.new_key_binds = dict(RiftWizard.default_key_binds)
			reset_keybind_names()
		def reset_keybinds_to_multiplayer_default():
			self.play_sound("menu_confirm")
			self.new_key_binds = dict(default_key_binds_multiplayer_scheme)
			reset_keybind_names()
		def leave_key_rebind_screen():
			self.play_sound("menu_confirm")
			self.key_binds = dict(self.new_key_binds)
			self.open_options() 

		
		menu_width = self.screen.get_width() * 2/3
		menu_height = self.screen.get_height() * 99/100

		col_widths = [
			int(menu_width/3),
			int(menu_width/3),
			int(menu_width/3)
		]
		self.key_rebind_menu_main_rows = [
			Modred.make_multirow(
				Modred.row_from_text("FUNCTION", self.font, self.linesize, selectable=False, width=col_widths[0]),
				Modred.row_from_text("MAIN KEY", self.font, self.linesize, selectable=False, width=col_widths[1]),
				Modred.row_from_text("SECONDARY KEY", self.font, self.linesize, selectable=False, width=col_widths[2])
			),
			Modred.row_from_text(" ", self.font, self.linesize, selectable=False),
			Modred.row_from_text(" ", self.font, self.linesize, selectable=False)
		]

		for (key_bind, name) in RiftWizard.key_names.items():
			key1, key2 = self.new_key_binds[key_bind]
			keyname_1 = pygame.key.name(key1) if key1 else "Unbound"
			keyname_2 = pygame.key.name(key2) if key2 else "Unbound"


			self.key_rebind_menu_main_rows.append(
				Modred.make_multirow(
					Modred.row_from_text(name+":", self.font, self.linesize, selectable=False, width=col_widths[0]),
					Modred.row_from_text(keyname_1+(' '*(10-len(keyname_1))), self.font, self.linesize, selectable=True, on_confirm_callback=make_callback_for_key_rebind(key_bind, True), width=col_widths[1]),
					Modred.row_from_text(keyname_2+(' '*(10-len(keyname_2))), self.font, self.linesize, selectable=True, on_confirm_callback=make_callback_for_key_rebind(key_bind, False), width=col_widths[2]),
				)
			)
			rows_by_keybind[key_bind] = self.key_rebind_menu_main_rows[-1]
		
		self.key_rebind_menu_main_rows.append(Modred.row_from_size(menu_width, self.linesize)) # blank space
		self.key_rebind_menu_main_rows.append(Modred.row_from_size(menu_width, self.linesize)) # blank space
		self.key_rebind_menu_main_rows.append(Modred.row_from_text("Reset to Default", self.font, self.linesize, selectable=True, on_confirm_callback=reset_keybinds_to_default, width=menu_width))
		self.key_rebind_menu_main_rows.append(Modred.row_from_text("Reset to Multiplayer Default", self.font, self.linesize, selectable=True, on_confirm_callback=reset_keybinds_to_multiplayer_default, width=menu_width))
		self.key_rebind_menu_main_rows.append(Modred.row_from_text("Done", self.font, self.linesize, selectable=True, on_confirm_callback=leave_key_rebind_screen, width=menu_width))
		self.key_rebind_menu_main_rows.append(Modred.row_from_size(menu_width, self.linesize)) # blank space
		self.key_rebind_menu_main_rows.append(Modred.row_from_size(menu_width, self.linesize)) # blank space

		# self.key_rebind_menu = Modred.make_menu_from_rows(self.key_rebind_menu_main_rows, menu_height, self.font, self.linesize, header_rows=[], footer_rows=[], add_page_count_footer=False, loopable=False)
		self.key_rebind_menu = Modred.make_single_page_menu_from_rows(self.key_rebind_menu_main_rows, menu_height)


KEY_BIND_OPTION_RESET_MULTIPLAYER = RiftWizard.KEY_BIND_MAX + 4

old_draw_key_rebind = RiftWizard.PyGameView.draw_key_rebind
def draw_key_rebind(self):
	try_init_key_rebind(self)

	self.key_rebind_menu.draw(self, self.screen, self.screen.get_width()//6, 0)

# RiftWizard.PyGameView.draw_key_rebind = draw_key_rebind


old_process_key_rebind = RiftWizard.PyGameView.process_key_rebind
def process_key_rebind(self):
	if self.rebinding:
		for evt in self.events:
			if evt.type == pygame.KEYDOWN:
				if evt.key in self.key_binds[RiftWizard.KEY_BIND_ABORT]:
					self.rebinding = False
					continue
				
				key = evt.key
				if evt.key == pygame.K_BACKSPACE and self.rebinding_key[1] > 0:
					key = None

				# Check for dual keybinds
				for f, (k1, k2) in self.new_key_binds.items():
					if k1 == evt.key:
						self.new_key_binds[f] = (k2, None)
					if k2 == evt.key:
						self.new_key_binds[f] = (k1, None)

				cur_controls = self.new_key_binds[self.rebinding_key[0]]
				new_control = list(cur_controls)
				new_control[self.rebinding_key[1]] = key
				self.new_key_binds[self.rebinding_key[0]] = new_control
				self.rebinding = False

				rebind_page = self.key_rebind_menu.pages[0]
				rebind_page.rows[rebind_page.selected_row_index].subrows[self.rebinding_key[1]+1].set_text(pygame.key.name(key) if key else "Unbound")
	else:
		for evt in self.events:
			if evt.type == pygame.KEYDOWN:
				if evt.key in self.key_binds[RiftWizard.KEY_BIND_ABORT]:
					self.play_sound("menu_confirm")
					self.key_binds = dict(self.new_key_binds)
					self.open_options() 
			if evt.type == pygame.MOUSEBUTTONDOWN:
				if evt.button == pygame.BUTTON_RIGHT:
					self.play_sound("menu_abort")
					self.open_options()
		
		self.key_rebind_menu.process_input(self, self.key_binds[RiftWizard.KEY_BIND_UP], self.key_binds[RiftWizard.KEY_BIND_DOWN], self.key_binds[RiftWizard.KEY_BIND_LEFT], self.key_binds[RiftWizard.KEY_BIND_RIGHT], self.key_binds[RiftWizard.KEY_BIND_CONFIRM])

# RiftWizard.PyGameView.process_key_rebind = process_key_rebind


old_key_bind_select_option = RiftWizard.PyGameView.key_bind_select_option
def key_bind_select_option(self, option):
	old_key_bind_select_option(self, option)
	
	if isinstance(option, list):
		pass
	elif option == KEY_BIND_OPTION_RESET_MULTIPLAYER:
		self.play_sound("menu_confirm")
		self.new_key_binds = dict(default_key_binds_multiplayer_scheme)
	elif option == RiftWizard.KEY_BIND_OPTION_ABORT:
		self.cur_top_row_of_rebind_controls_menu = 0

# RiftWizard.PyGameView.key_bind_select_option = key_bind_select_option
Modred.override_menu(RiftWizard.STATE_REBIND, draw_key_rebind, process_key_rebind)



# ######################################### 
#
# Set Multiplayer
#
# #########################################


# ######################################### 
#
# Draw menus
#
# #########################################

old_draw_shop = RiftWizard.PyGameView.draw_shop
def draw_shop(self, character_display=None, player=None):
	# if not self.in_multiplayer_mode or player == None:
	# 	return old_draw_shop(self)

	# Spells: show spells show filters
	# Upgrades: show upgrades
	# Spell Upgrades: show upgrades for spell
	# Bestary: show all monsters (cannot purchase)

	self.shop_rects = []
	character_display.fill((0, 0, 0))
	self.draw_panel(character_display)
	
	# Draw Shrine Background
	if player.menu__shop_type == RiftWizard.SHOP_TYPE_SHOP:
		cur_shop = self.game.cur_level.tiles[player.x][player.y].prop
		if cur_shop:
			# from original source: TODO- draw the sprite onto a surface so that animation works and blit THAT surface
			image = RiftWizard.get_image(cur_shop.asset).subsurface((0, 0, RiftWizard.SPRITE_SIZE, RiftWizard.SPRITE_SIZE))
			shop_sprite_scale = 16 #32
			big_shop = pygame.transform.scale(image, (RiftWizard.SPRITE_SIZE*shop_sprite_scale, RiftWizard.SPRITE_SIZE*shop_sprite_scale))
			dx = (character_display.get_width() - big_shop.get_width()) // 2
			dy = (character_display.get_height() - big_shop.get_height()) // 2
			big_shop.fill((255, 255, 255, 90), special_flags=pygame.BLEND_RGBA_MULT)
			character_display.blit(big_shop, (dx, dy))

	mx, my = self.get_mouse_pos()
	options = self.get_shop_options(player)

	spell_x_offset = self.border_margin # + 18
	cur_x = spell_x_offset
	cur_y = self.linesize

	level_x = (character_display.get_width() - 2 * self.border_margin) * (4/5) + 2
	sp_x = level_x - self.font.size('X')[0]
	tag_x = level_x + self.font.size('XX')[0]
	spell_column_width = sp_x - spell_x_offset

	shoptions = self.get_shop_options(player)
	num_options = len(shoptions)

	max_shop_objects = self.max_shop_objects/2 - 3 if self.in_multiplayer_mode else self.max_shop_objects

	if player.menu__shop_type == RiftWizard.SHOP_TYPE_SPELLS:
		self.draw_string("Learn Spell:", character_display, cur_x, cur_y)
		self.draw_string("SP", character_display, sp_x, cur_y, RiftWizard.COLOR_XP)
		self.draw_string("Type", character_display, tag_x, cur_y)
	if player.menu__shop_type == RiftWizard.SHOP_TYPE_UPGRADES:
		self.draw_string("Learn Skill:", character_display, cur_x, cur_y)
		self.draw_string("SP", character_display, sp_x, cur_y, RiftWizard.COLOR_XP)
		self.draw_string("Type", character_display, tag_x, cur_y)
	if player.menu__shop_type == RiftWizard.SHOP_TYPE_SPELL_UPGRADES:
		self.draw_string("Upgrade %s:" % player.menu__shop_upgrade_spell.name, character_display, cur_x, cur_y)
	if player.menu__shop_type == RiftWizard.SHOP_TYPE_SHOP:
		self.draw_string(self.get_display_level().cur_shop.name, character_display, 0, cur_y, content_width=character_display.get_width(), center=True)
	if player.menu__shop_type == RiftWizard.SHOP_TYPE_BESTIARY:
		self.draw_string("Bestiary: %d of %d Monsters Slain" % (SteamAdapter.get_num_slain(), len(all_monsters)), character_display, cur_x, cur_y)


	cur_y += self.linesize
	cur_y += self.linesize
	
	if not shoptions:
		if player.menu__shop_type == RiftWizard.SHOP_TYPE_SHOP:
			self.draw_string("None of your spells", character_display, 0, cur_y, content_width=character_display.get_width(), center=True)
			cur_y += self.linesize
			self.draw_string("can be improved at", character_display, 0, cur_y, content_width=character_display.get_width(), center=True)
			cur_y += self.linesize
			self.draw_string("this shrine", character_display, 0, cur_y, content_width=character_display.get_width(), center=True)
		elif player.menu__shop_type in [RiftWizard.SHOP_TYPE_SPELLS, RiftWizard.SHOP_TYPE_SPELLS]:
			self.draw_string("No spells fit these filters", character_display, cur_x, cur_y, RiftWizard.HIGHLIGHT_COLOR)

	start_index = int(player.menu__shop_page * max_shop_objects)
	end_index = int(start_index + max_shop_objects)

	for opt in shoptions[start_index:end_index]:

		cur_x = spell_x_offset
		if self.shop_type in [RiftWizard.SHOP_TYPE_SPELLS, RiftWizard.SHOP_TYPE_UPGRADES]:
			self.draw_spell_icon(opt, character_display, cur_x, cur_y)
			cur_x += 20

		fmt = opt.name			
		cur_color = (255, 255, 255)

		if player.menu__shop_type == RiftWizard.SHOP_TYPE_BESTIARY and not SteamAdapter.has_slain(opt.name):
			fmt = "?????????????????????"
			cur_color = (100, 100, 100)
		
		
		if player.menu__shop_type != RiftWizard.SHOP_TYPE_BESTIARY:
			cost = self.game.get_upgrade_cost(opt, player)
			if self.game.has_upgrade(opt, player): 
				cur_color = (0, 255, 0)
			elif self.game.can_buy_upgrade(opt, player):
				cur_color = player.discount_tag.color.to_tup() if player.discount_tag in opt.tags else (255, 255, 255)
			else:
				cur_color = (100, 100, 100)

		if player.menu__shop_type == RiftWizard.SHOP_TYPE_SHOP:
			self.draw_string(fmt, character_display, 0, cur_y, cur_color, mouse_content=opt, content_width=character_display.get_width(), center=True)
		else:
			self.draw_string(fmt, character_display, cur_x, cur_y, cur_color, mouse_content=opt, content_width=spell_column_width)

		if hasattr(opt, 'level') and isinstance(opt.level, int) and opt.level > 0:
			fmt = str(cost)
			if opt.name in player.scroll_discounts:
				fmt += '*'
			self.draw_string(fmt, character_display, level_x, cur_y, cur_color)

		if player.menu__shop_type != RiftWizard.SHOP_TYPE_BESTIARY and hasattr(opt, 'tags'):
			# tag_x = cur_x + tag_offset
			cur_tag_x = tag_x
			for tag in Tags:
				if tag not in opt.tags:
					continue
				self.draw_string(self.reverse_tag_keys[tag], character_display, cur_tag_x, cur_y, tag.color.to_tup())
				cur_tag_x += self.font.size(tag.name[0])[0]


		cur_y += self.linesize


	# TODO: update all below for 2p --------------------------------------------------------------------------------------------------------------------------------------------
	# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------

	if player.menu__shop_type in [RiftWizard.SHOP_TYPE_UPGRADES, RiftWizard.SHOP_TYPE_SPELLS]:
		# Draw filters
		cur_x = 16 * 40
		cur_y = self.linesize

		tag_width = character_display.get_width() - cur_x - self.border_margin
		self.draw_string("Filter:", character_display, cur_x, cur_y)
		cur_y += 2*self.linesize
		
		for tag in self.game.spell_tags:

			color = tag.color.to_tup() if tag in self.tag_filter else (150, 150, 150)
			self.draw_string(tag.name, character_display, cur_x, cur_y, color, mouse_content=tag, content_width=tag_width)

			idx = 0

			for c in tag.name:
				if self.tag_keys.get(c.lower(), None) == tag:
					self.draw_string(c, character_display, cur_x + self.font.size(tag.name[:idx])[0], cur_y, tag.color.to_tup())
					break
				idx += 1
	
			cur_y += self.linesize


	cur_x = spell_x_offset
	cur_y = self.linesize * (max_shop_objects+4)
	max_shop_pages = math.ceil(len(self.get_shop_options(player)) / max_shop_objects)
	
	if max_shop_pages > 1:

		can_prev = player.menu__shop_page > 0
		prev_fmt = "<<<<"
		cur_color = (255, 255, 255) if can_prev else RiftWizard.HIGHLIGHT_COLOR
		self.draw_string(prev_fmt, character_display, cur_x, cur_y, cur_color, mouse_content=RiftWizard.TOOLTIP_PREV if can_prev else None)
	
		cur_x += self.font.size(prev_fmt + '   ')[0]
		fmt = "Page %d/%d" % (player.menu__shop_page + 1, math.ceil(len(self.get_shop_options(player)) / max_shop_objects))
		self.draw_string(fmt, character_display, cur_x, cur_y)

		cur_x += self.font.size(fmt + '   ')[0]
		#cur_x = spell_x_offset + spell_column_width - self.font.size(prev_fmt)[0]

		can_next = player.menu__shop_page < max_shop_pages - 1
		next_fmt = ">>>>"
		cur_color = (255, 255, 255) if can_next else RiftWizard.HIGHLIGHT_COLOR
		self.draw_string(next_fmt, character_display, cur_x, cur_y, cur_color, mouse_content=RiftWizard.TOOLTIP_NEXT if can_next else None)


	# self.screen.blit(self.middle_menu_display, (self.h_margin, 0))
# RiftWizard.PyGameView.draw_shop = draw_shop


def draw_single_character(self, character_display, player, key_binds_map):


	# if player_should_indicate_waiting(self, player):
	#   draw panel with greys
	self.draw_panel(character_display)
	if player.menu__state == STATE_CAST_SELECTION:
		# make the borders of the menu green if the player's in cast select state
		character_display.fill((100, 255, 100, 90), special_flags=pygame.BLEND_RGBA_MULT)
	
	self.char_panel_examine_lines = {}

	cur_x = self.border_margin
	cur_y = self.border_margin
	linesize = self.linesize

	# draw hp

	hpcolor = (255, 255, 255)
	if player.cur_hp <= 25:
		hpcolor = (255, 0, 0)

	hp_string_full = "%s %d/%d" % (RiftWizard.CHAR_HEART, player.cur_hp, player.max_hp)
	hp_string_label_only = "%s" % RiftWizard.CHAR_HEART

	self.draw_string(hp_string_full, character_display, cur_x, cur_y, color=hpcolor)
	self.draw_string(hp_string_label_only, character_display, cur_x, cur_y, (255, 0, 0))
	cur_x += self.font.size(hp_string_full + " ")[0]

	# draw shields

	if True or player.shields:
		self.draw_string("%s %d" % (RiftWizard.CHAR_SHIELD, player.shields), character_display, cur_x, cur_y)
		self.draw_string("%s" % (RiftWizard.CHAR_SHIELD), character_display, cur_x, cur_y, color=RiftWizard.COLOR_SHIELD.to_tup())

	# draw sp (right aligned)
	sp_string = "SP %d" % player.xp
	cur_x = character_display.get_width() - self.border_margin - self.font.size(sp_string)[0]
	self.draw_string(sp_string, character_display, cur_x, cur_y, color=RiftWizard.COLOR_XP)
	
	cur_x = self.border_margin
	cur_y += linesize

	# draw the rest

	self.draw_string("Realm %d" % self.game.level_num, character_display, cur_x, cur_y)
	cur_y += linesize

	# from original code: TODO- buffs here

	cur_y += linesize

	# from here on, 21 lines fit max
	TOTAL_NUM_LINES = 20
	if not self.in_multiplayer_mode:
		TOTAL_NUM_LINES = 40

	if not hasattr(player, 'menu__char_pane_scroll_index'):
		player.menu__char_pane_scroll_index = 0

	effective_cast_selection_index = player.menu__cast_selection__index + 1 + (2 if player.menu__cast_selection__index >= len(player.spells) else 0)
	if player.menu__cast_selection__index >= len(player.spells) + len(player.items):
		player_skills = [skill for skill in player.buffs if isinstance(skill, Upgrade)]
		player_buffs = [skill for skill in player.buffs if not isinstance(skill, Upgrade)]
		
		if len(player_skills) > 0:
			effective_cast_selection_index += 3
		if len(player_buffs) > 0:
			effective_cast_selection_index += 2 + len(player_buffs)

	if effective_cast_selection_index > TOTAL_NUM_LINES + player.menu__char_pane_scroll_index - 1:
		player.menu__char_pane_scroll_index = effective_cast_selection_index - TOTAL_NUM_LINES + 1
		print(str(player.menu__char_pane_scroll_index) + "     " + str(effective_cast_selection_index))
	if effective_cast_selection_index < player.menu__char_pane_scroll_index+1:
		player.menu__char_pane_scroll_index = effective_cast_selection_index-1
		print(str(player.menu__char_pane_scroll_index) + "     " + str(effective_cast_selection_index))
	
	if player.menu__char_pane_scroll_index <= 0:
		self.draw_string("Spells:", character_display, cur_x, cur_y)
		cur_y += linesize

	# Spells
	index = player.menu__char_pane_scroll_index+1
	for spell in player.spells[player.menu__char_pane_scroll_index + (-1 if player.menu__char_pane_scroll_index > 0 else 0) :  player.menu__char_pane_scroll_index+TOTAL_NUM_LINES]:
		
		# spell_number = (index) % 10
		# mod_key = 'C' if index > 20 else 'S' if index > 10 else ''
		# hotkey_str = "%s%d" % (mod_key, spell_number)
		hotkey_str = str(index)

		if spell == player.cur_spell:
			cur_color = (0, 255, 0)
		elif spell.can_pay_costs():
			cur_color = (255, 255, 255)
		else:
			cur_color = (128, 128, 128)
		
		fmt = "%2s  %-17s%2d" % (hotkey_str, spell.name, spell.cur_charges)

		self.draw_string(fmt, character_display, cur_x, cur_y, cur_color, mouse_content=RiftWizard.SpellCharacterWrapper(spell), char_panel=True)
		self.draw_spell_icon(spell, character_display, cur_x + 38, cur_y)

		cur_y += linesize
		index += 1

	cur_y += linesize
	# Items


	if player.menu__char_pane_scroll_index <= 1 + len(player.spells) + 1:
		# this will be line 1 + len(player.spells)
		self.draw_string("Items:", character_display, cur_x, cur_y)
		cur_y += linesize

	first_item_is_on_line = 2 + len(player.spells)

	index = max(0, player.menu__char_pane_scroll_index-first_item_is_on_line-1)+1
	for item in player.items[max(0, player.menu__char_pane_scroll_index-first_item_is_on_line-1)  :  player.menu__char_pane_scroll_index-first_item_is_on_line+TOTAL_NUM_LINES]:

		# hotkey_str = "A%d" % (index % 10)
		hotkey_str = str(index)

		cur_color = (255, 255, 255)
		if item.spell == player.cur_spell:
			cur_color = (0, 255, 0)
		fmt = "%2s  %-17s%2d" % (hotkey_str, item.name, item.quantity)			

		self.draw_string(fmt, character_display, cur_x, cur_y, cur_color, mouse_content=item)
		self.draw_spell_icon(item, character_display, cur_x + 38, cur_y)

		cur_y += linesize
		index += 1

	# Buffs
	status_effects = [b for b in player.buffs if b.buff_type != BUFF_TYPE_PASSIVE]
	counts = {}
	for effect in status_effects:
		if effect.name not in counts:
			counts[effect.name] = (effect, 0, 0, None)
		_, stacks, duration, color = counts[effect.name]
		stacks += 1
		duration = max(duration, effect.turns_left)

		counts[effect.name] = (effect, stacks, duration, effect.get_tooltip_color().to_tup())

	if status_effects:
		cur_y += linesize
		self.draw_string("Status Effects:", character_display, cur_x, cur_y)
		cur_y += linesize
		for buff_name, (buff, stacks, duration, color) in counts.items():

			fmt = buff_name

			if stacks > 1:
				fmt += ' x%d' % stacks

			if duration:
				fmt += ' (%d)' % duration

			self.draw_string(fmt, character_display, cur_x, cur_y, color, mouse_content=buff)
			cur_y += linesize
		cur_y += linesize

	skills = [b for b in player.buffs if b.buff_type == RiftWizard.BUFF_TYPE_PASSIVE and not b.prereq]
	if skills:
		cur_y += linesize

		self.draw_string("Skills:", character_display, cur_x, cur_y)
		cur_y += linesize

		skill_x_max = character_display.get_width() - self.border_margin - 16
		for skill in skills:
			self.draw_spell_icon(skill, character_display, cur_x, cur_y)
			cur_x += 18
			if cur_x > skill_x_max:
				cur_x = self.border_margin
				cur_y += self.linesize

	cur_x = self.border_margin
	cur_y = max(cur_y, character_display.get_height() - self.border_margin - 3*self.linesize)
	
	k = self.key_binds[key_binds_map[RiftWizard.KEY_BIND_ABORT]][0]
	fmt = pygame.key.name(k) if k else "Unbound" 
	self.draw_string("Menu ("+fmt+")", character_display, cur_x, cur_y, mouse_content=RiftWizard.OPTIONS_TARGET, player=player)
	cur_y += linesize

	k = self.key_binds[key_binds_map[RiftWizard.KEY_BIND_HELP]][0]
	fmt = pygame.key.name(k) if k else "Unbound" 
	self.draw_string("How to Play ("+fmt+")", character_display, cur_x, cur_y, mouse_content=RiftWizard.INSTRUCTIONS_TARGET, player=player)
	cur_y += linesize

	k = self.key_binds[key_binds_map[RiftWizard.KEY_BIND_CHAR]][0]
	fmt = pygame.key.name(k) if k else "Unbound" 
	color = player.discount_tag.color.to_tup() if player.discount_tag else (255, 255, 255)
	self.draw_string("Character Sheet ("+fmt+")", character_display, cur_x, cur_y, color=color, mouse_content=RiftWizard.CHAR_SHEET_TARGET, player=player)


	
	if player_should_indicate_waiting(player, RiftWizard.turn_mode): # make the player's pane grey if they've moved this turn
		character_display.fill((127, 127, 127), special_flags=pygame.BLEND_RGBA_MULT)
	#self.screen.blit(character_display, (0, 0))


old_draw_character = RiftWizard.PyGameView.draw_character
def draw_character(self):
	# if self.in_multiplayer_mode and hasattr(self, 'character_display_p2') and hasattr(self.game, 'p2') and hasattr(self.game.p1, 'menu__state'):

	if hasattr(self.main_player, 'menu__state'):
		if self.main_player.menu__state == RiftWizard.STATE_CHAR_SHEET: 
			draw_single_char_sheet(self, self.character_display, self.main_player)
		elif self.main_player.menu__state == RiftWizard.STATE_SHOP:
			draw_shop(self, self.character_display, self.main_player)
		else:
			draw_single_character(self, self.character_display, self.main_player, p1_key_binds_map)
		self.screen.blit(self.character_display, (0, 0))

	if self.in_multiplayer_mode and hasattr(self, 'character_display_p2') and hasattr(self.game, 'p2'):
		if self.other_player.menu__state == RiftWizard.STATE_CHAR_SHEET: 
			draw_single_char_sheet(self, self.character_display_p2, self.other_player)
		elif self.other_player.menu__state == RiftWizard.STATE_SHOP:
			draw_shop(self, self.character_display_p2, self.other_player)
		else:
			draw_single_character(self, self.character_display_p2, self.other_player, p2_key_binds_map)
		self.screen.blit(self.character_display_p2, (0, self.character_display.get_height()))
	# else:
	# 	old_draw_character(self)

# RiftWizard.PyGameView.draw_character = draw_character










# ######################################### 
#
# Turn Order
#
# #########################################

def unit_turn(self, unit):
	if not unit.is_alive():
		return

	unit.pre_advance()

	# finished_advance = False
	# while not finished_advance:
	# 	# if unit.is_player_controlled and not unit.is_stunned() and not self.requested_action:
	# 	# 	self.is_awaiting_input = True
	# 	# 	yield
	# 	finished_advance = unit.advance()
	finished_advance = unit.advance()

	#yield
	while self.can_advance_spells():
		yield self.advance_spells()

	# Advance buffs after advancing spells
	unit.advance_buffs()

	while self.can_advance_spells():
		yield self.advance_spells()

	self.frame_units_moved += 1
	
	# Yield if the current advance frame is aboive the advance time budget
	if time.time() - self.frame_start_time > MAX_ADVANCE_TIME:
		yield


old_Level_iter_frame = Level.iter_frame
def Level_iter_frame(self, mark_turn_end=False):
	# global global_in_multiplayer_mode
	# if not global_in_multiplayer_mode:
	# 	yield from old_Level_iter_frame(self, mark_turn_end=mark_turn_end)
	# 	return

	# An iterator representing the order of turns for all game objects
	while True:

		# Yield once per iteration if there are no units to prevent infinite loop
		if not self.units:
			yield

		self.turn_no += 1
		turn_mode = RiftWizard.turn_mode

		if any(u.team != TEAM_PLAYER for u in self.units):
			self.next_log_turn()
			self.combat_log.debug("Level %d, Turn %d begins." % (self.level_no, self.turn_no))
			turn_mode = RiftWizard.turn_mode_from_settings
		else:
			turn_mode = TURN_MODE_ONE_PLAYER_AT_A_TIME


		# Cache unit list here to enforce summoning delay
		turn_units = list(self.units)
		for is_player_turn in [True, False]:
			clouds = [cloud for cloud in self.clouds if cloud.owner.is_player_controlled == is_player_turn]
			if clouds:
				for cloud in clouds:
					if cloud.is_alive:
						cloud.advance()
				while self.can_advance_spells():
					yield self.advance_spells()

			# self.is_awaiting_input = False

			if is_player_turn:

				units = [unit for unit in turn_units if unit.is_player_controlled == is_player_turn]
				
				p1 = self.player_unit
				p2 = self.player_unit_2 if hasattr(self, 'player_unit_2') else None


				while not should_advance_turn_to_ai_action(self, p1, p2, turn_mode):
					p1_is_ready = player_is_ready(p1, turn_mode)
					p2_is_ready = player_is_ready(p2, turn_mode) if p2 else False

					if p1_is_ready:
						yield from unit_turn(self, p1)
					if p2_is_ready:
						yield from unit_turn(self, p2)

					if player_should_indicate_waiting(p1, turn_mode):
						p1.Anim = RiftWizard.ANIM_FLINCH # TODO: this doesn't work, I don't know why. this whole if block is safe to remove
					if p2 and player_should_indicate_waiting(p2, turn_mode):
						p2.Anim = RiftWizard.ANIM_FLINCH # TODO: this doesn't work, I don't know why. this whole if block is safe to remove
					

					if not should_advance_turn_to_ai_action(self, p1, p2, turn_mode):
						self.is_awaiting_input = True
						yield
				
				# self.is_awaiting_input = False
				

			if not is_player_turn:
				units = [unit for unit in turn_units if unit.is_player_controlled == is_player_turn]
				random.shuffle(units)

				for unit in units:
					yield from unit_turn(self, unit)
				
				if not allow_turn_queuing(self, p1, p1.requested_action, turn_mode):
					p1.requested_action = None
				if p2 and not allow_turn_queuing(self, p2, p2.requested_action, turn_mode):
					p2.requested_action = None
					

		# Advance all props similtaneously
		for prop in list(self.props):
			prop.advance()

		# In the unlikely event that that created effects, advance them
		while self.can_advance_spells():
			yield self.advance_spells()

		if not visual_mode:
			yield True
# Level.iter_frame = Level_iter_frame


def player_ai(self):
	self.level.requested_action = None
	self.times_moved_this_turn = self.times_moved_this_turn+1 if self.last_turn_acted == self.level.turn_no else 0
	self.last_turn_acted = self.level.turn_no

	try:
		action = self.requested_action
		self.requested_action = None

		# handle cases like this:
		# +----+----+----+
		# | p1 | p2 |    |
		# +----+----+----+
		# both players move right, but p1 moves first
		# without the below if statement, the game crashes because p1 switches places with p2, then p2 tries to switch places with p1
		if isinstance(action, MoveAction) and not self.level.can_move(self, action.x, action.y):
			return PassAction()

		return action
	except Exception as e:
		print(e)
		return PassAction()

#
# simple "when should turn advance" logic
# override or edit here to change turn advancing logic
#

# TURN_MODE_DEFAULT = 0
# TURN_MODE_FAST_PLAYER = 1
# TURN_MODE_DEFAULT_WITH_TIMER = 2
# TURN_MODE_HYPERSPEED_PLAYERS_WITH_TIMER = 3
# TURN_MODE_ONE_PLAYER_AT_A_TIME = 4


# RiftWizard.turn_mode = TURN_MODE_ONE_PLAYER_AT_A_TIME
# TURN_TIMER = 1

old_Game_is_awaiting_input = Game.is_awaiting_input
def Game_is_awaiting_input(self, turn_mode=RiftWizard.turn_mode):
	# if not hasattr(self, 'in_multiplayer_mode') or not self.in_multiplayer_mode:
	# 	return old_Game_is_awaiting_input(self)

	cases = {
		TURN_MODE_DEFAULT: 0,
		TURN_MODE_FAST_PLAYER: 0,
		TURN_MODE_DEFAULT_WITH_TIMER: 1,
		TURN_MODE_HYPERSPEED_PLAYERS_WITH_TIMER: 1,
		TURN_MODE_ONE_PLAYER_AT_A_TIME: 0,
		TURN_MODE_FAST_PLAYER_WITH_TIMER: 1
	}

	# if the current mode has a timer, we're going to skip both players' turns
	if cases[turn_mode] == 1:
		if not hasattr(self, 'timer'):
			self.timer = time.time() + TURN_TIMER
		if not hasattr(self.cur_level, 'timer_has_run'):
			self.cur_level.timer_has_run = False
		if  self.timer < time.time():
			self.timer = time.time() + TURN_TIMER
			self.cur_level.timer_has_run = True
			return False
	
	return old_Game_is_awaiting_input(self)
	
# Game.is_awaiting_input = Game_is_awaiting_input


# pretty self exaplanatory
def should_advance_turn_to_ai_action(self, p1, p2, turn_mode):
	if p2 == None:
		return p1.last_turn_acted == self.turn_no

	cases = {
		TURN_MODE_DEFAULT: 0,
		TURN_MODE_FAST_PLAYER: 1,
		TURN_MODE_DEFAULT_WITH_TIMER: 2,
		TURN_MODE_HYPERSPEED_PLAYERS_WITH_TIMER: 3,
		TURN_MODE_ONE_PLAYER_AT_A_TIME: 4,
		TURN_MODE_FAST_PLAYER_WITH_TIMER: 5, 
	}

	if cases[turn_mode] == 0:
		# advance when both players have moved
		live_players = [player for player in [p1, p2] if player.is_alive()]
		return all(player.last_turn_acted >= self.turn_no for player in live_players)
		# return p1.last_turn_acted == self.turn_no and \
		# 	   p2.last_turn_acted == self.turn_no

	if cases[turn_mode] == 1:
		# advance when one player has tried to move twice or both players have moved
		live_players = [player for player in [p1, p2] if player.is_alive()]
		if len(live_players) >= 2:
			return (p1.last_turn_acted >= self.turn_no and p1.times_moved_this_turn >= 1) or \
					(p2.last_turn_acted >= self.turn_no and p2.times_moved_this_turn >= 1) or \
					(p1.last_turn_acted >= self.turn_no and p2.last_turn_acted >= self.turn_no)
		else:
			return live_players[0].last_turn_acted >= self.turn_no

	if cases[turn_mode] == 2:
		# advance when both players have acted or a timer runs out
		live_players = [player for player in [p1, p2] if player.is_alive()]
		if all(player.last_turn_acted >= self.turn_no for player in live_players):
			return True
		# if p1.last_turn_acted == self.turn_no and \
		#    p2.last_turn_acted == self.turn_no:
		# 	return True
		
		if not hasattr(self, 'timer_has_run'):
			self.timer_has_run = False

		retval = self.timer_has_run
		self.timer_has_run = False
		return retval

	if cases[turn_mode] == 5:
		# advance when one player has tried to move twice or both players have moved, or a timer has run
		retval = False
		live_players = [player for player in [p1, p2] if player.is_alive()]
		if len(live_players) >= 2:
			retval = (p1.last_turn_acted >= self.turn_no and p1.times_moved_this_turn >= 1) or \
					 (p2.last_turn_acted >= self.turn_no and p2.times_moved_this_turn >= 1) or \
					 (p1.last_turn_acted >= self.turn_no and p2.last_turn_acted >= self.turn_no)
		else:
			retval = live_players[0].last_turn_acted >= self.turn_no

		if retval:
			return retval


		if not hasattr(self, 'timer_has_run'):
			self.timer_has_run = False

		retval = self.timer_has_run
		self.timer_has_run = False
		return retval

	if cases[turn_mode] == 3:
		if not hasattr(self, 'timer_has_run'):
			self.timer_has_run = False

		# advance only when a timer has run
		retval = self.timer_has_run
		self.timer_has_run = False
		return retval

	if cases[turn_mode] == 4:
		# advance when either player has moved
		return p1.last_turn_acted == self.turn_no or \
			   p2.last_turn_acted == self.turn_no

# is the player ready to perform its action for this turn
def player_is_ready(player, turn_mode):
	cases = {
		TURN_MODE_DEFAULT: 0,
		TURN_MODE_FAST_PLAYER: 1,
		TURN_MODE_DEFAULT_WITH_TIMER: 0,
		TURN_MODE_HYPERSPEED_PLAYERS_WITH_TIMER: 1,
		TURN_MODE_ONE_PLAYER_AT_A_TIME: 0,
		TURN_MODE_FAST_PLAYER_WITH_TIMER: 1,
	}

	if cases[turn_mode] == 0:
		# allow players to move only once per turn - players are ready when they have a requested action AND haven't moved this turn yet
		return player.requested_action != None and player.last_turn_acted < player.level.turn_no
		
	if cases[turn_mode] == 1:
		# let players move many times per turn - players are always ready as long as they have a requested action set up
		return player.requested_action != None

# should the player show that they've already taken their action for the turn?
def player_should_indicate_waiting(player, turn_mode):
	cases = {
		TURN_MODE_DEFAULT: 0,
		TURN_MODE_FAST_PLAYER: 0, #1,
		TURN_MODE_DEFAULT_WITH_TIMER: 0,
		TURN_MODE_HYPERSPEED_PLAYERS_WITH_TIMER: 1,
		TURN_MODE_ONE_PLAYER_AT_A_TIME: 1,
		TURN_MODE_FAST_PLAYER_WITH_TIMER: 0 #1
	}

	if not player.is_alive():
		return True

	if cases[turn_mode] == 0:
		return  player.last_turn_acted >= player.level.turn_no
		
	if cases[turn_mode] == 1:
		return False

# should players be able to queue up their next action before their next turn?
# eg: if this returns True,  and p1 hits up twice, then p2 hits up - p1 moves up, p2 moves up, p1 moves up, game waits for input
#     if this returns False, and p1 hits up twice, then p2 hits up - p1 moves up, p2 moves up, game waits for input
def allow_turn_queuing(self, player, action, turn_mode):
	cases = {
		TURN_MODE_DEFAULT: 0,
		TURN_MODE_FAST_PLAYER: 1,
		TURN_MODE_DEFAULT_WITH_TIMER: 0,
		TURN_MODE_HYPERSPEED_PLAYERS_WITH_TIMER: 1,
		TURN_MODE_ONE_PLAYER_AT_A_TIME: 0,
		TURN_MODE_FAST_PLAYER_WITH_TIMER: 0,
	}

	if cases[turn_mode] == 0:
		return False
	if cases[turn_mode] == 1:
		# must be true if you want players to move more than once per turn
		return True

# ######################################### 
#
# Initialize p2
#
# #########################################

def spawn_p2(self, player_unit):
	frontier = [(self.start_pos.x, self.start_pos.y)]
	visited = set()
	player2_start = None
	while len(frontier) > 0:
		(x, y) = frontier.pop(0)
		visited.add((x, y))

		new_points = [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]
		new_points = list(set(new_points) - visited)
		frontier = frontier + new_points

		tile = self.tiles[x][y]
		if not tile.can_walk:
			continue
		if self.get_unit_at(x, y):
			continue
		
		player2_start = Point(x, y)
		break

	self.add_obj(player_unit, player2_start.x, player2_start.y)

	prop = self.tiles[player2_start.x][player2_start.y].prop
	if prop:
		prop.on_player_enter(player_unit)

def init_player(self, player, char_select_index):
	player.all_player_spells = Spells.make_player_spells()
	player.all_player_skills = Upgrades.make_player_skills()
	
	player.transform_asset_name = self.player_characters_asset_names[char_select_index]
	player.asset = self.player_characters_asset_names[char_select_index]

	player.requested_action = None

	func_type = type(player.get_ai_action)
	player.get_ai_action = func_type(player_ai, player)

	player.last_turn_acted = -1
	player.times_moved_this_turn = 0
	player.max_num_items = 5
	player.cur_spell = None
	player.cur_spell_target = None
	player.prev_spell_target = None
	player.menu__deploy_target = None

	# menu stuff
	player.menu__char_sheet__is_open = False
	player.menu__char_sheet__is_on_spells = True
	player.menu__state = RiftWizard.STATE_LEVEL
	player.menu__examine_target = None 
	player.menu__cast_selection__index = 0
	player.menu__shop_page = 0
	player.menu__abort_to_spell_shop = False
	player.menu__char_sheet_select_index = 0
	player.menu__deploy_target = None


import Mutators

old_new_game = RiftWizard.PyGameView.new_game
def new_game(self, mutators=None, trial_name=None, seed=None, from_online_code=False):
	#
	# old_new_game:
	#

	print("NEW GAME WITH TRIAL " + str(trial_name))

	if self.online_mode and not from_online_code:
		# hijack trial select / mode select input
		self.trial_index_selected = -1 if trial_name == None else RiftWizard.all_trials.index([trial for trial in RiftWizard.all_trials if trial.name == trial_name][0])
		
		if trial_name == Mutators.get_weekly_name():
			self.trial_index_selected = -2
		
		self.state = STATE_LOBBY_MENU
		return

	# If you are overwriting an old game, break streak
	if can_continue_game():
		SteamAdapter.set_stat('s', 0)
		SteamAdapter.set_stat('l', SteamAdapter.get_stat('l') + 1)


	self.game = Game(save_enabled=(not self.online_mode), mutators=mutators, trial_name=trial_name, seed=seed)
	self.message = text.intro_text

	if mutators:
		self.message += "\n\n\n\nChallenge Modifiers:"
		for mutator in mutators:
			self.message += "\n" + mutator.description

	self.center_message = True
	self.state = RiftWizard.STATE_MESSAGE
	self.play_music('battle_2')
	global CLAY_IS_DEBUGGING_ONLINE_MULTIPLAYER_ON_HIS_ONE_COMPUTER
	if not CLAY_IS_DEBUGGING_ONLINE_MULTIPLAYER_ON_HIS_ONE_COMPUTER:
		self.make_level_screenshot()
	SteamAdapter.set_presence_level(1)

	#
	# new code
	#
	self.chat_open = False

	self.game.in_multiplayer_mode = self.in_multiplayer_mode
	self.game.online_mode = self.online_mode
	self.game.online__is_host = self.online__is_host

	if self.in_multiplayer_mode:
		#
		# initialize game objects
		#


		


		# p2 only stuff
		self.game.p2 = self.game.make_player_character()
		self.game.p2.name = "Player 2"
		 
		# cheating
		# if CLAY_IS_DEBUGGING_ONLINE_MULTIPLAYER_ON_HIS_ONE_COMPUTER:
		# 	self.game.p1.xp = 30
		# 	self.game.p2.xp = 30

		self.main_player = self.game.p1
		self.other_player = self.game.p2

		if self.online_mode and not self.online__is_host:
			self.other_player = self.game.p1
			self.main_player = self.game.p2

		# p1 AND p2 stuff
		self.game.p1.ally_player = self.game.p2
		self.game.p2.ally_player = self.game.p1

		init_player(self, self.game.p1, self.p1_char_select_index)
		init_player(self, self.game.p2, self.p2_char_select_index)
		

		# Spawn p2
		spawn_p2(self.game.cur_level, self.game.p2)
		self.game.cur_level.player_unit_2 = self.game.p2
	

		
		self.game.p1.apply_buff(SPDistributionBuff(True, self.game.p2))
		self.game.p2.apply_buff(SPDistributionBuff(False, self.game.p1))

		if RiftWizard.universal_mana_potion_enabled:
			self.game.p1.apply_buff(ShareManaPotionEffectBuff(True, self.game.p2))
			self.game.p2.apply_buff(ShareManaPotionEffectBuff(False, self.game.p1))

		if self.player_characters_add_quirks_functions[self.p1_char_select_index] != None and self.add_character_quirks_p1:
			self.player_characters_add_quirks_functions[self.p1_char_select_index](self.game.p1)
		if self.player_characters_add_quirks_functions[self.p2_char_select_index] != None and self.add_character_quirks_p2:
			self.player_characters_add_quirks_functions[self.p2_char_select_index](self.game.p2)


		# apply mutators 
		if mutators != None:
			for mutator in mutators:
				# mutator.set_seed(seed) # shouldn't be necessary

				mutator.on_generate_spells(self.game.p1.all_player_spells)
				mutator.on_generate_skills(self.game.p1.all_player_skills)

				mutator.on_generate_spells(self.game.p2.all_player_spells)
				mutator.on_generate_skills(self.game.p2.all_player_skills)

		#
		# initialize draw resources
		#

		self.character_display = pygame.Surface((self.h_margin, 900/2))
		self.character_display_p2 = pygame.Surface((self.h_margin, 900/2))
	else:	
		#
		# reset game objects
		#

		# self.game.p1.requested_action = None
		# self.game.p1.is_player_controlled = False

		# self.game.p1.get_ai_action = player_ai
		# self.game.p1.max_num_items = 10

		RiftWizard.turn_mode_from_settings = TURN_MODE_ONE_PLAYER_AT_A_TIME
		RiftWizard.turn_mode = TURN_MODE_ONE_PLAYER_AT_A_TIME

		self.main_player = self.game.p1
		self.other_player = None

		init_player(self, self.game.p1, self.p1_char_select_index)

		if self.player_characters_add_quirks_functions[self.p1_char_select_index] != None and self.add_character_quirks_p1:
			self.player_characters_add_quirks_functions[self.p1_char_select_index](self.game.p1)


		# apply mutators 
		if mutators != None:
			for mutator in mutators:
				# mutator.set_seed(seed) # shouldn't be necessary

				mutator.on_generate_spells(self.game.p1.all_player_spells)
				mutator.on_generate_skills(self.game.p1.all_player_skills)

		#
		# reset draw resources	
		#
		self.character_display = pygame.Surface((self.h_margin, 900))

# RiftWizard.PyGameView.new_game = new_game

old_load_game = RiftWizard.PyGameView.load_game
def load_game(self, filename=None):
	old_load_game(self, filename)

	if self.game.in_multiplayer_mode:
		self.in_multiplayer_mode = True

		global global_in_multiplayer_mode
		global_in_multiplayer_mode = True

		self.character_display = pygame.Surface((self.h_margin, 900/2))
		self.character_display_p2 = pygame.Surface((self.h_margin, 900/2))


# RiftWizard.PyGameView.load_game = load_game



# ######################################### 
#
# Items, required to limit player inventory
#
# #########################################

old_on_player_enter = ItemPickup.on_player_enter
def on_player_enter(self, player):
	try:
		if len(player.items) >= player.max_num_items and self.item.name not in [i.name for i in player.items]:
			return
		
		existing = [i for i in player.items if i.name == self.name]
		if existing:
			if player.stack_max is not None and existing[0].quantity >= player.stack_max:
				return

		player.add_item(self.item)
		self.level.remove_prop(self)
		self.level.event_manager.raise_event(EventOnItemPickup(self.item), player)
	except:
		old_on_player_enter(self, player)

# ItemPickup.on_player_enter = on_player_enter

# TODO: player drop item

# ##################
# 
# Patch save game
#
# ################### 

save_game = Game.save_game
def save_game_wrapper(self, filename=None):
	# remove un-pickleable stuff
	self.p1.menu__confirm_yes = None
	self.p1.menu__confirm_no = None
	if hasattr(self, 'p2'):
		self.p2.menu__confirm_yes = None
		self.p2.menu__confirm_no = None

	# save the game
	try:
		save_game(self, filename)
		
	except Exception as e:
		print('savegame error!')
		print(e)
	
# Game.save_game = save_game_wrapper


# ###########################
# 
# deploy
#
# ##########################

old_enter_portal = Game.enter_portal
def enter_portal(self):
	old_enter_portal(self)

	if hasattr(self, 'p2'):
		self.p1.menu__deploy_target = Point(self.p1.x, self.p1.y)
		self.p2.menu__deploy_target = Point(self.p2.x, self.p2.y)
	else:
		self.p1.menu__deploy_target = Point(self.p1.x, self.p1.y)

# Game.enter_portal = enter_portal



# ######################################### 
#
# Online multiplayer
#
# #########################################

def encode_action(player, action):
	playerNum = '1' if player.name == "Player" else '2'
	if isinstance(action, PassAction):
		return playerNum+'Pass'
	if isinstance(action, MoveAction):
		return playerNum+'Move'+str(action.x)+","+str(action.y)
	if isinstance(action, CastAction):
		print(action.spell)
		return playerNum+'Cast'+str(action.x)+','+str(action.y)+','+str(player.spells.index(action.spell))
	print('ERROR: unknown action type')
	return playerNum+'Pass'

def decode_action(action, p1, p2):
	player_num = action[0]
	action_type = action[1:5]
	data = action[5:]

	print('action: ' + player_num + '    ' + action_type + '    ' + data)

	player = p1 if player_num == '1' else p2

	if action_type == 'Pass':
		action = RiftWizard.PassAction()
		return (player, action)
	if action_type == 'Move':
		data = data.split(',')
		action = RiftWizard.MoveAction(int(data[0]), int(data[1]))
		return (player, action)
	if action_type == 'Cast':
		data = data.split(',')
		spell = player.spells[int(data[2])]
		action = RiftWizard.CastAction(spell, int(data[0]), int(data[1]))
		return (player, action)

	print('ERROR: unknown action type')
	action = RiftWizard.PassAction()
	return (player, action)


def multiplayer_socket_callback(self):
	# self is the pygame view

	def callback_response(message):
		message_type = message[0]
		message = message[1:]
		print('Callback for message type ' + message_type)

		if message_type == 'y':
			if message:
				Chat.add_chat_message('>>> ' + message)
			return
		if message_type == 'n':
			print('Recieved Error message! - ' + message)
			Chat.add_chat_message('>>> Error: ' + message)
			return
		if message_type == 'c':
			print('player joined lobby!')
			Chat.add_chat_message('>>> Player joined the lobby')
			Client.send_game_ready(1, self.p1_char_select_index, self.add_character_quirks_p1)
			return
		if message_type == 'd':
			print('player disconnected')
			Chat.add_chat_message('>>> Player disconnected')
			Client.disconnect()
			self.examine_target = 0
			self.state = RiftWizard.STATE_TITLE

		if message_type == 'r':
			# self.online__player_ready_count += 1
			player_num = message[0]
			message = message[1:]
			message = message.split(',')

			Chat.add_chat_message('>>> Player ' + player_num + ' is ready to start')

			if player_num == '2':
				self.p2_char_select_index = int(message[0])
				self.add_character_quirks_p2 = message[1] == "True"
			else:
				self.p1_char_select_index = int(message[0])
				self.add_character_quirks_p1 = message[1] == "True"

			if self.online__is_host:
				# now that everyone's ready, start the game
				seed = random.randrange(999999)
				sp_mode = RiftWizard.sp_distribution_strategy
				Client.send_game_start(seed, RiftWizard.turn_mode_from_settings, sp_mode, self.trial_index_selected)

				if self.trial_index_selected == -1:
					trial_name = None 
					mutators = None
				elif self.trial_index_selected == -2:
					trial_name = Mutators.get_weekly_name() 
					mutators = Mutators.get_weekly_mutators()
					seed = Mutators.get_weekly_seed()
				else:
					trial = RiftWizard.all_trials[self.trial_index_selected]
					trial_name = trial.name
					mutators = trial.mutators

				self.new_game(seed=seed, trial_name=trial_name, mutators=mutators, from_online_code=True)
			
			return
		if message_type == 's':
			print('start game!')
			
			Chat.add_chat_message('>>> Starting the game')

			# set turn mode
			# set sp mode
			# set game seed
			message = message.split(',')
			RiftWizard.turn_mode_from_settings = int(message[0])
			RiftWizard.turn_mode = RiftWizard.turn_mode_from_settings
			self.sp_mode = int(message[1])
			seed = int(message[2])
			self.trial_index_selected = int(message[3])

			if self.trial_index_selected == -1:
				trial_name = None 
				mutators = None
			elif self.trial_index_selected == -2:
				trial_name = Mutators.get_weekly_name() 
				mutators = Mutators.get_weekly_mutators()
				seed = Mutators.get_weekly_seed()
			else:
				trial = RiftWizard.all_trials[self.trial_index_selected]
				trial_name = trial.name
				mutators = trial.mutators


			self.new_game(seed=seed, trial_name=trial_name, mutators=mutators, from_online_code=True)
			return

		if message_type == 'a':
			(player, action) = decode_action(message, self.game.p1, self.game.p2)
			print(str(player) + '   ' + str(action))
			if isinstance(action, MoveAction) and self.game.deploying:
				new_point = Point(action.x, action.y)
				
				player.menu__deploy_target = new_point
				self.deploy_target = new_point
				self.try_examine_tile(new_point)

				if self.online__is_host:
					Client.send_action(message)
			else:
				set_player_action(self.game, player, action, from_server=True)
				# if self.online__is_host: # don't send here - all actions are sent from set_player_action
				# 	Client.send_action(message)

			print('set action for ' + player.name)
			return

		if message_type == 'b':
			print('player made a purchase')

			if self.online__is_host:
				Client.send_purchase(message)
			
			player_num = message[0]
			purchase_type = message[1:6]
			data = message[6:]
			player = self.game.p1 if player_num == '1' else self.game.p2

			if purchase_type == 'Spell':
				player.xp -= self.game.get_upgrade_cost(player.all_player_spells[int(data)], player)
				player.add_spell(player.all_player_spells[int(data)])
			elif purchase_type == 'Skill':
				player.xp -= self.game.get_upgrade_cost(player.all_player_skills[int(data)], player)
				player.apply_buff(player.all_player_skills[int(data)])
			elif purchase_type == 'Shop ':
				shop_item = self.game.cur_level.cur_shop.items[int(data)]
				# player.xp -= self.game.get_upgrade_cost(shop_item, player)
				# player.apply_buff(shop_item)
				self.cur_level.act_shop(player, shop_item)
				pass # TODO: this - find out where shrine purchases happen in base code
			elif purchase_type == 'SUpgd':
				data = data.split(',')
				upgrade = player.spells[int(data[0])].spell_upgrades[int(data[1])]
				player.xp -= self.game.get_upgrade_cost(upgrade, player)
				player.apply_buff(upgrade)
			elif purchase_type == 'Dploy':
				if data == 'Cancel':
					player.menu__deploy_target = None
					player.examine_target = None
					self.examine_target = None
					self.game.try_abort_deploy()
					self.play_sound("menu_abort")
				elif data == 'Confirm':
					self.deploy(True)
				

			return
		if message_type == 'm':
			print('chat message: ' + message)
			Chat.add_chat_message(message)
			return


	return callback_response


if CLAY_IS_DEBUGGING_ONLINE_MULTIPLAYER_ON_HIS_ONE_COMPUTER:
	RiftWizard.PyGameView.make_level_end_screenshot = lambda self: None 
	RiftWizard.PyGameView.make_level_screenshot = lambda self: None

# ######################################### 
#
# Done!
#
# #########################################

print('Multiplayer API Loaded')