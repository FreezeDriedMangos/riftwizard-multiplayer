CRASH ON CHAT 


C:\Program Files (x86)\Steam\steamapps\common\Rift Wizard\RiftWizard>RiftWizard.exe windowed
Setting breakpad minidump AppID = 1271280
SteamInternal_SetMinidumpSteamID:  Caching Steam ID:  76561198045268775 [API loaded no]
API Options Menu Loaded
Multiplayer API Loaded
API_Boss Loaded
overriding stuff
NEW GAME WITH TRIAL None
connect to dragon
<<< b'h{"name": "dragon", "trial": -1, "mods": ["API_Multiplayer", "API_Universal"]}'
>>> y
inbox size: 1
Callback for message type y
>>> c
inbox size: 1
>>> r21,True
inbox size: 2
Callback for message type c
player joined lobby!
<<< b'r10,True'
Callback for message type r
NEW GAME WITH TRIAL None
<<< b's1,3,998450,-1'
>>> y
inbox size: 1
>>> y
inbox size: 2
Callback for message type y
Callback for message type y
<<< b'a1Move18,11'
>>> y
inbox size: 1
Callback for message type y
>>> b2Spell1
inbox size: 1
Callback for message type b
player made a purchase
<<< b'b2Spell1'
>>> y
inbox size: 1
Callback for message type y
game buy upgrade
<class 'Spells.DeathBolt'>
<<< b'b1Spell0'
>>> y
inbox size: 1
Callback for message type y
<<< b'm/hello'
Traceback (most recent call last):
  File "RiftWizard.py", line 5547, in <module>
    main_view.run()
  File "C:\Program Files (x86)\Steam\steamapps\common\Rift Wizard\RiftWizard\mods\API_Universal\RiftWizardOverrides.py", line 246, in run
    API_TitleMenus.on_run_draw(self)
  File "C:\Program Files (x86)\Steam\steamapps\common\Rift Wizard\RiftWizard\mods\API_Universal\API_TitleMenus\API_TitleMenus.py", line 49, in on_run_draw
    cur_menu.draw_function(self)
  File "C:\Program Files (x86)\Steam\steamapps\common\Rift Wizard\RiftWizard\mods\API_Multiplayer\API_Multiplayer.py", line 3088, in draw_level
    image = get_tile_overlay(self, p1_colors[p1_category])
  File "C:\Program Files (x86)\Steam\steamapps\common\Rift Wizard\RiftWizard\mods\API_Multiplayer\API_Multiplayer.py", line 2964, in get_tile_overlay
    if not TILE_OVERLAY_FILE_NAME in self.images:
AttributeError: 'PyGameView' object has no attribute 'images'

Loaded mods:
API_Multiplayer
API_Universal
>>> y
inbox size: 1

C:\Program Files (x86)\Steam\steamapps\common\Rift Wizard\RiftWizard>pause
Press any key to continue . . .