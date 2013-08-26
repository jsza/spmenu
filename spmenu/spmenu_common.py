'''
Common (game-independent) classes defined here.
'''
import pprint
import weakref

import es
import gamethread
import langlib
import playerlib


class PopuplibError(RuntimeError):
    '''
    Error in performing spmenu functions.
    '''
    pass


class PopupSet(set):
    '''
    A set of related popups.
    The objects of this set are GroupedPopup objects.
    '''
    def __init__(self, iterable=None):
        '''
        Initialize the set, optionally with contents from iterable.
        '''
        super(PopupSet, self).__init__()
        if iterable:
            for x in iterable:
                self.add(x)

    def add(self, item):
        '''Add a new popup to this set.'''
        if not isinstance(item, GroupedPopup):
            item = GroupedPopup(self, item)
        else:
            item.group = weakref.proxy(self)
        super(PopupSet, self).add(item)
        return item


class GroupedPopup(object):
    '''
    A wrapper for Popup objects that supports grouping them together.
    Main purpose is to allow a script to group multiple popups together so that
    when one is sent to a user, all other popups in the group are automatically
    removed from the user's queue.
    '''
    def __init__(self, group, popup_object):
        '''
        Initialize.

        Parameters:
        group -- an object of type set to which this popup
        '''
        self._GP_popup = popup_object
        self._GP_group = weakref.proxy(group)
        group.add(self)

    def send(self, userid, *args, **kw):
        '''
        Send the popup. Unsend all others in group.
        '''
        self._GP_popup.send(userid, *args, **kw)
        for popup in self._GP_group:
            if popup is not self:
                popup.unsend(userid)

    def __getattr__(self, attr):
        if attr == 'send' or attr.startswith(('_GP_','__')):
            return vars(self)[attr]
        else:
            return getattr(self._GP_popup, attr)

    def __setattr__(self, attr, value):
        if attr.startswith(('_GP_',)):
            vars(self)[attr] = value
        else:
            return setattr(self._GP_popup, attr, value)


class PopupGroup(dict):
    '''
    Group multiple popups by languages.
    Any attributes specified for a PopupGroup will be relayed to popups in the
    group. Sending popups using the send method chooses the most suitable language
    version of popups to send.

    Usage from scripts (example):

    pg = spmenu.PopupGroup()
    english_popup = spmenu.Popup()
    ...
    pg['en'] = english_popup
    ...
    pg.send(userid)

    '''
    '''
    self = {'en': Popup instance,
            'de': Popup instance,
           }
    '''
    def __init__(self):
        '''Initialize a new PopupGroup.'''
        self._users = {}
        ''' self._users = {userid: UserPopup instance,} '''

    def _getlang(self, user):
        '''
        Return the language to use for the user.

        Parameters:
        user -- the user for the language is to be chosen, a _User instance

        '''
        if len(self) == 0:
            raise PopuplibError('Trying to handle popup group with no popups.')
        lang = user.language
        if lang not in self:
            lang = langlib.getDefaultLang()
            if lang not in self:
                lang = self.iterkeys().next()
        return lang

    def __setitem__(self, language, popup):
        '''popup_group[language] = popup'''
        dict.__setitem__(self, language, popup)
        popup.language = language
        # Copy extra attributes, but do not overwrite.
        for attribute, value in vars(self).iteritems():
            if attribute[0] != '_':
                if (not hasattr(popup, attribute) or
                    not getattr(popup, attribute)):
                    setattr(popup, attribute, value)

    def __setattr__(self, attribute, value):
        '''popup_group.attribute = value'''
        vars(self)[attribute] = value
        if attribute[0] != '_':
            for popup in self.itervalues():
                if (not hasattr(popup, attribute) or
                    not getattr(popup, attribute)):
                    setattr(popup, attribute, value)

    def send(self, userid, *args, **kw):
        '''Send a popup from this group to the user specified by userid.'''
        user = _usermanager[userid]
        lang = self._getlang(user)
        popup = self[lang]
        userpopup = popup._send(user, *args, **kw)

    def unsend(self, userid):
        '''
        Removes a popup of this group from user.

        Return True if the popup was removed.
        Return False if the popup was not in queue.
        '''
        if userid in self._users:
            user = _usermanager[userid]
            userpopup = self._get_userpopup(user)
            return userpopup.unsend()
        return False

    def __del__(self):
        '''
        No references to this group.

        Normally this means an addon which created this group was unloaded.
        For that we are going to clear all the popups in here.
        '''
        dbgmsg(1, 'Popuplib2: Deleting popup group')
        dbgmsg_repr(2, self)
        # the references for popups and userpopups will be gone along with this

    def _get_userpopup(self, user):
        '''Return the userpopup for the user.'''
        lang = self._getlang(user)
        userpopup = self[lang]._get_userpopup(user)
        return userpopup

    def get_queue_index(self, userid):
        """
        Return the position this popup has in the specified user's queue.

        If the popup is currently visible, the returned index is 0.
        If the popup is next to be displayed, the returned index is 1,
        and so on.
        If the popup is not in user's queue, None is returned.
        """
        user = _usermanager[userid]
        userpopup = self._get_userpopup(user)
        try:
            return user.queue.index(userpopup)
        except ValueError:
            return None

    # TODO: more actions, relay to specific popups


class _UserManager(object):
    '''The class that manages users and interaction with them.'''
    def __init__(self):
        '''Initialize the class.'''
        self.users = {} # {userid: _User instance,}
        self.active_users = set() # users who have active popups
        # for optimization, listen for es_map_start and player_disconnect
        es.addons.registerForEvent(self, 'es_map_start', self.es_map_start)
        es.addons.registerForEvent(
            self, 'player_disconnect', self.player_disconnect
        )

    def __getitem__(self, userid):
        '''user = _usermanager[userid]'''
        if not isinstance(userid, int):
            raise TypeError(
                "userid must be integer, got %s"%(
                    repr(type(userid)),
                )
            )
        if userid in self.users:
            return self.users[userid]
        else:
            user = _User(userid)
            self.users[userid] = user
            return user

    def activate(self, user):
        '''Mark user to have active popups, start listening to menuselect.'''
        if not self.active_users:
            es.addons.registerClientCommandFilter(self.ccf)
        self.active_users.add(user.userid)

    def inactivate(self, user):
        '''
        Mark user to not have active popups.

        Stop listening to menuselect if no active users left.
        '''
        if user.userid in self.active_users:
            self.active_users.remove(user.userid)
            if not self.active_users:
                self.active = False
                es.addons.unregisterClientCommandFilter(self.ccf)

    def ccf(self, userid, args):
        '''
        Monitor for menuselect client command and call got_response method
        for the user.
        '''
        if args[0] == 'menuselect':
            # This could be for us
            if userid in self.active_users:
                try:
                    choice = int(args[1])
                except ValueError:
                    return True
                user = self.users[userid] #no indirect reference here for debug
                user.got_response(choice)
                return False
        return True

    # EVENT HANDLERS

    def es_map_start(self, event_var):
        '''
        Handle map changing by emptying the queues of all users.

        This method is called by EventScripts automatically.
        '''
        for userid, user in self.users.iteritems():
            user.clear_queue()
        self.active_users.clear()

    def player_disconnect(self, event_var):
        '''
        Handle disconnected players by deleting their user instances.

        This is to save memory since long running servers could have up to
        65534 users in them but only maximum of 64 can be active at a time,
        so it is not good to have a huge dict with the user history but to
        only have the users that are on currently.
        '''
        userid = int(event_var['userid'])
        if userid in self.users:
            self.users[userid]._delete()
            del self.users[userid]

    # TODO: more _Usermanager actions


class _User(object):
    '''User object containing user's popup queue and settings.'''
    def __init__(self, userid):
        ''' Initializes a new _User,
raises playerlib.UseridError if user not found. '''
        self.userid = userid
        player = playerlib.getPlayer(userid)
        self.language = player.get('lang')
        self.bot = bool(player.get('isbot'))
        self.queue = []
        self.navstack = []
        ''' self.queue = [Userpopup instance, Userpopup instance, ] '''
        self._delete_handlers = set()
        self.__delayed_refresh = 0
        self.__handling_response = False

    def inactivate(self):
        '''Mark this user having no popup activity.'''
        self.navstack = [] # make sure the navstack is empty
        self.queue = [] # make sure the queue is empty
        _usermanager.inactivate(self)

    def activate(self):
        '''Mark this user having popup activity.'''
        _usermanager.activate(self)

    def clear_queue(self):
        '''Clear the queue, called on map start.'''
        self.queue = []
        self._delete_handlers = set()

    def get_popup_index(self, popup):
        '''Return the queue index if in queue or None if not.'''
        if popup not in self.queue:
            return None
        else:
            return self.queue.index(popup)

    def add_deleter(self, delfunc):
        '''
        Add a deletion handler function which is called when
        the user disconnects.
        '''
        self._delete_handlers.add(delfunc)

    def _delete(self):
        '''Call the deletion handler functions.'''
        for delfunc in self._delete_handlers:
            delfunc()
        del self._delete_handlers

    def __del__(self):
        '''Mark this user not being active when no references are left.'''
        dbgmsg(1, 'Popuplib2: Deleting user %s'%(self.userid,))
        self.inactivate()

    def want_popup(self, userpopup):
        '''
        Add popup to queue if it is not in there already.

        If this is the first popup, display it.
        '''
        if self.bot:
            dbgmsg(1, 'Popuplib2: Trying to send to bot (id %s), ignoring'%(
                self.userid,))
            return False

        if userpopup not in self.queue or (
            self.__handling_response and self.queue[0] is userpopup
        ):
            self.queue.append(userpopup)
        index = self.queue.index(userpopup)
        dbgmsg(1, 'Popuplib2: User %s wants popup, index %s'%(
            self.userid, index))
        self.refresh() # make sure the current popup is visible
        return True

    def remove_popup(self, userpopup):
        '''
        Remove popup from queue if it is there.

        If it was the first popup, update display.

        Return True if the popup was removed.
        Return False if the popup was not in queue.
        '''
        if userpopup in self.queue:
            index = self.queue.index(userpopup)
            if index == 0:
                # This was the first popup, needs updating!
                if not self.next_popup():
                    # No more popups to display, goodbye!
                    self.inactivate()
                    userpopup.hide_display()
            else:
                del self.queue[index]

    def refresh(self):
        '''Display the popup first in queue.'''
        if self.__handling_response:
            return False
        if not self.queue:
            self.inactivate()
            return False
        userpopup = self.queue[0]
        if userpopup in self.navstack:
            self.navstack.remove(userpopup)
        dbgmsg(1, 'Popuplib2: Displaying popup')
        userpopup.display()
        dbgmsg(2, 'Popuplib2: Activating user listening')
        self.activate()
        refresh_time = _game_data.get('refresh', 0)
        if self.__delayed_refresh == 0 and refresh_time > 0:
            self.__delayed_refresh += 1
            gamethread.delayed(refresh_time, self.__delayed_refresh_call)
        return True

    def __delayed_refresh_call(self):
        self.__delayed_refresh -= 1
        self.refresh()

    def next_popup(self):
        '''Remove the first popup from queue, display next if possible.'''
        return self.pop(0)

    def get_previous_popup(self):
        '''Return the popup from the top of the navigation stack.'''
        if self.navstack:
            return self.navstack[-1]
        else:
            return None

    def go_previous_popup(self):
        '''Go to previous menu in navstack.'''
        if self.navstack:
            self.queue.insert(1, self.navstack.pop())
        return True # for got_response that queue should be checked

    def pop(self, index):
        '''Remove specified popup index from queue.'''
        self.queue.pop(index)
        if index == 0 and len(self.queue) > 0:
            self.refresh()
            return True
        return False

    def got_response(self, choice):
        '''
        Handle response given to a popup by this user.

        Will display the next popup.
        '''
        dbgmsg(1, 'Popuplib2: User %s got response %s'%(self.userid, choice))
        userpopup = self.queue[0]
        self.__handling_response = True # prevent circular calls messing up
        response = userpopup.response(choice)
        self.__handling_response = False
        if response:
            # Method is allowed to display the next popup.
            dbgmsg(1, 'Popuplib2: Result: Send next popup')
            if not self.next_popup():
                # There are no more popups, mark user inactive.
                dbgmsg(1, 'Popuplib2: No more popups, inactivate self')
                self.inactivate()
        else:
            # Do not edit the queue, just make sure the popup is visible.
            dbgmsg(1, 'Popuplib2: Result: Refresh current popup')
            if self.navstack and self.queue[0] is self.navstack[-1]:
                # submenu choice was to go back to previous menu
                dbgmsg(1, 'Going back in navigation history.')
            else:
                dbgmsg(1, 'New submenu, adding previous popup to history.')
                self.navstack.append(userpopup)
            self.refresh()
        dbgmsg(2, 'Popuplib2: Queue is')
        dbgmsg_repr(2, self.queue)

    # TODO: more _User actions

_usermanager = _UserManager()


def dbgmsg(level, text):
    return es.dbgmsg(level, text) # fixed in build 169 or so

    for s in xrange(0, len(text), 240):
        es.dbgmsg(level, text[s:s+240])

def dbgmsg_repr(level, obj):
    return es.dbgmsg(level, repr(obj)) # fixed in build 169 or so

    if level <= int(es.ServerVar('eventscripts_debug')):
        for line in pprint.pformat(obj).splitlines():
            es.dbgmsg(level, line)

