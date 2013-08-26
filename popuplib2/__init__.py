'''
More Pythonic and object oriented way to handle tasks previously
handled by popuplib
'''
__version__ = '20120916_053411'
import popuplib2_radio as radio
import popuplib2_vgui as vgui
import popuplib2_resources
import popuplib2_common


_language_data = popuplib2_resources.load_language_data(popuplib2_resources)
_game_data = popuplib2_resources.get_game_data(popuplib2_resources)

_usermanager = popuplib2_common._usermanager
# distribute common information
radio._usermanager = _usermanager
radio._language_data = _language_data
vgui._usermanager = _usermanager
vgui._language_data = _language_data

popuplib2_common._game_data = _game_data

PopupSet = popuplib2_common.PopupSet
GroupedPopup = popuplib2_common.GroupedPopup
PopupGroup = popuplib2_common.PopupGroup
PopuplibError = popuplib2_common.PopuplibError

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
