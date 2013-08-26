'''
Resource loading module for popuplib2.
'''
import os

import es

import langlib
from configobj import ConfigObj

from popuplib2_common import dbgmsg, dbgmsg_repr

def load_language_data(module):
    global lang_data
    mypath = os.path.split(module.__file__)[0]
    filename = os.path.join(mypath, 'language_data.ini')
    lang_data = langlib.Strings(filename)
    return lang_data

def load_game_data(module):
    mypath = os.path.split(module.__file__)[0]
    filename = os.path.join(mypath, 'game_data.ini')
    data = ConfigObj(filename)
    return data

def get_game_data(module):
    global game_data
    data = load_game_data(module)
    # GJ HAX:
    gamename = str(es.ServerVar('eventscripts_gamedir')).replace('\\', '/').rpartition('/')[2].lower()
    dbgmsg(1, 'popuplib2: game name is %s'%repr(gamename))
    if gamename not in data:
        dbgmsg(1, 'popuplib2: game not found, going default')
        gamename = 'default'
    this_game = data[gamename]
    game_data = {
        'type': this_game['type'],
        'refresh': this_game.as_int('refresh') if this_game['type'] == 'radio' else 0,
        }
    dbgmsg_repr(2, game_data)
    return game_data

def get_string(identifier, language):
    return lang_data.expand(identifier, lang=language)

