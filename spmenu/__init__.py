'''
More Pythonic and object oriented way to handle tasks previously
handled by popuplib
'''
__version__ = '20120916_053411'
import spmenu_radio as radio
import spmenu_vgui as vgui
import spmenu_resources
import spmenu_common


_language_data = spmenu_resources.load_language_data(spmenu_resources)
_game_data = spmenu_resources.get_game_data(spmenu_resources)

_usermanager = spmenu_common._usermanager
# distribute common information
radio._usermanager = _usermanager
radio._language_data = _language_data
vgui._usermanager = _usermanager
vgui._language_data = _language_data

spmenu_common._game_data = _game_data

PopupSet = spmenu_common.PopupSet
GroupedPopup = spmenu_common.GroupedPopup
PopupGroup = spmenu_common.PopupGroup
PopuplibError = spmenu_common.PopuplibError

# get default type dependent popup classes
if _game_data['type'] == 'radio':
    default_module = radio
elif _game_data['type'] == 'vgui':
    default_module = vgui

Popup = default_module.Popup
TemplatePopup = default_module.TemplatePopup
PersonalPopup = default_module.PersonalPopup
PagedMenu = default_module.PagedMenu
PagedList = default_module.PagedList
PersonalMenu = default_module.PersonalMenu
MenuOption = default_module.MenuOption
