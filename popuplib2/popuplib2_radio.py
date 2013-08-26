'''
More Pythonic and object oriented way to handle tasks previously
handled by popuplib, in-game radio menu type popups
'''
import string
import sys
import warnings

import es
import gamethread
import langlib

from popuplib2_common import dbgmsg, dbgmsg_repr
import popuplib2_resources


# UserPopup classes

class UserPopup(object):
    '''
    A basic userpopup class, other userpopups subclass this.

    A userpopup is a view to specific Popup, specific to a single user.
    Each user for each popup have their own userpopup instances.
    '''
    def __init__(self, user, popup):
        '''Initialize a new Userpopup '''
        # self._user is the _User instance for this userpopup.
        self._user = user
        user.add_deleter(self._user_deleted)
        self._userid = self._user.userid # Copy it to be able to delete refs.
        # self._popup is the Popup instance in which this userpopup appears.
        self._popup = popup
        self._send_args = None
        self._send_kw = None
        self._being_hidden = False
    
    def __del__(self):
        '''
        No references to this userpopup.
        '''
        dbgmsg(1, 'Popuplib2: Deleting userpopup')
        dbgmsg_repr(2, self)
        
    def _send(self, *args, **kw):
        '''Send this popup to queue of the user.'''
        self._send_args = args or ()
        self._send_kw = kw or {}
        self._user.want_popup(self)
    
    def get_language(self):
        '''Get the language for this user popup.'''
        if self._popup.language:
            return self._popup.language
        return self._user.language
    
    def generate_text(self):
        '''
        Generate the string that is to be displayed in the popup.
        '''
        dbgmsg(1, 'Popuplib2: Userpopup building self')
        return '\n'.join(self._popup)
    
    def display(self):
        '''Create a GUI panel and display it for the user.'''
        self._being_hidden = False
        text = self.generate_text()
        if isinstance(text, unicode):
            text = text.encode('utf-8')
        dbgmsg(2, 'Popuplib2: Calling es.menu(%s, %s, textlen=%s, %s)'%(
            0, self._user.userid, len(text), self._popup.enable_keys))
        es.menu(0, self._user.userid, text, self._popup.enable_keys)
    
    def response(self, choice):
        '''
        Handle the user input given to this popup.
        
        Returns True if next popup may be shown;
        Returns False otherwise.
        '''
        if not self._being_hidden:
            self._popup._menuselect_special = {}
            return self._popup._response(self._user, choice)
        else:
            return True
    
    def unsend(self):
        '''Remove this popup from user queue.'''
        return self._user.remove_popup(self)
    
    def hide_display(self):
        '''Remove this popup type from display.'''
        self._being_hidden = True
        # FIXME: FIX ME!
        es.menu(1, self._user.userid, 'Closing...')
    
    def _user_deleted(self):
        '''The user is no longer in game, this popup is not needed anymore.'''
        del self._popup._users[self._userid]
        
    # TODO: more basic userpopup actions


class UserTemplatePopup(UserPopup):
    '''
    A template userpopup class for TemplatePopup

    A userpopup is a view to specific Popup, specific to a single user.
    Each user for each popup have their own userpopup instances.
    '''
    def display(self):
        '''Create a GUI panel and display it for the user.'''
        dbgmsg(1, 'Popuplib2: Template Userpopup building self')
        text_template = string.Template('\n'.join(self._popup))
        text = text_template.substitute(*self._send_args, **self._send_kw)
        dbgmsg(2, 'Popuplib2: Calling es.menu(%f, %d, textlen=%d, %s)'%(
            0, self._user.userid, len(text), self._popup.enable_keys))
        es.menu(0, self._user.userid, text, self._popup.enable_keys)


class UserPersonalPopup(UserPopup):
    '''
    A userpopup class for PersonalPopup.
    
    A userpopup is a view to specific Popup, specific to a single user.
    Each user for each popup have their own userpopup instances.
    
    When a PersonalPopup is sent, the assigned callback function is called
    with the userid and an instance of this class as parameters. Editing
    the contents of the instance determines the contents of the popup
    sent to the user. Use the common list methods to edit the contents.
    When the callback is called, the personal contents are always empty.
    
    Attributes:
    menuselect_args -- a dictionary containing extra information that is put
      to the menuselect callback dict
    '''
    def __init__(self, *args, **kw):
        '''Initialize a new Userpopup '''
        super(UserPersonalPopup, self).__init__(*args, **kw)
        self._contents = []
        self._final_contents = ['No content due to errors.']
        self.menuselect_args = {}

    def __setitem__(self, *args):
        return self._contents.__setitem__(*args)
    
    def __getitem__(self, *args):
        return self._contents.__getitem__(*args)

    def __delitem__(self, *args):
        return self._contents.__delitem__(*args)
    
    def append(self, line):
        return self._contents.append(line)
    
    def extend(self, lines):
        return self._contents.extend(lines)
    
    def index(self, *args, **kw):
        return self._contents.index(*args, **kw)
    
    def insert(self, index, line):
        return self._contents.insert(index, line)
    
    def pop(self, *args, **kw):
        return self._contents.pop(*args, **kw)
    
    def remove(self, line):
        return self._contents.remove(line)
    
    def display(self):
        self._contents = []
        try:
            self._popup.build_callback(self._user.userid, self)
        except TypeError, e:
            warnings.warn('TypeError when calling build_callback: %s'%e)
        else:
            self._final_contents = list(self._popup) + self._contents
        self._being_hidden = False
        dbgmsg(1, 'Popuplib2: Userpopup building self')
        text = '\n'.join(self._final_contents)
        dbgmsg(2, 'Popuplib2: Calling es.menu(%s, %s, textlen=%s, %s)'%(
            0, self._user.userid, len(text), self._popup.enable_keys))
        es.menu(0, self._user.userid, text, self._popup.enable_keys)
        

class UserPagedMenu(UserPopup):
    '''
    A userpopup class for PagedMenu.

    A userpopup is a view to specific Popup, specific to a single user.
    Each user for each popup have their own userpopup instances.
    '''
    def __init__(self, *args, **kw):
        '''Initialize a new Userpopup '''
        super(UserPagedMenu, self).__init__(*args, **kw)
        self.pagenum = 1

    def pages(self):
        '''Count the number of pages in this popup.'''
        return self._popup.pages()
    
    def _add_options(self, tb):
        '''Add options to builder block tb.'''
        minopt = (self.pagenum-1)*self._popup.options_per_page
        maxopt = self.pagenum*self._popup.options_per_page
        index = 0
        for index, option in enumerate(self._popup[minopt:maxopt]):
            tb.append(str(option)%(index+1))
        for i in xrange(self._popup.options_per_page-index-1):
            tb.append(' ')
    
    def _send(self, page=1, *args, **kw):
        '''Send this popup to queue of the user (override for page control).'''
        self.pagenum = self._popup.isvalidpage(page) and page or 1
        self._send_args = args or ()
        self._send_kw = kw or {}
        self._user.want_popup(self)
    
    def display(self):
        '''Create a GUI panel and display it for the user.'''
        pages = self.pages() or 1
        language = self.get_language()
        tb = []
        # add title
        tb.append('%-25s'%(self._popup.title))
        # add description
        if self._popup.description:
            tb.append('%s\n'%self._popup.description)
        # add separating slashes
        if pages == 0:
            # empty menu
            tb.append(popuplib2_resources.get_string('empty', language))
        else:
            # add options
            self._add_options(tb)
            # add separating slashes
            tb.append(' ')
            # add page navigation links
            if pages > 1:
                s_prev = popuplib2_resources.get_string('prev', language)
                s_next = popuplib2_resources.get_string('next', language)
                if self.pagenum == 1:
                    # tb.append('8. %s'%s_prev)
                    tb.append(' ')
                else:
                    tb.append('->8. %s\n'%s_prev)
                if self.pagenum == pages:
                    # tb.append('9. %s\n'%s_next)
                    tb.append(' ')
                else:
                    tb.append('->9. %s\n'%s_next)
            else:
                tb.append(' ')
                tb.append(' ')
        
        # add exit button
        tb.append('0. %s'%popuplib2_resources.get_string('cancel', language))
        #display it
        text = '\n'.join(tb)
        dbgmsg(2, 'es.menu(%d, %d, textlen=%d, %s'%(
            0, self._user.userid, len(text), self._popup.enable_keys))
        es.menu(0, self._user.userid, text, self._popup.enable_keys)
    
    def response(self, choice):
        '''
        Handle the user input given to this popup.
        
        Returns True if next popup may be shown;
        Returns False otherwise.
        '''
        self._popup._menuselect_special = {}
        self._popup._menuselect_special['raw_choice'] = choice
        self._popup._menuselect_special['page'] = self.pagenum
        self._popup._menuselect_special['option'] = None
        achoice = None
        if choice < 8:
            nopt = (self.pagenum-1)*self._popup.options_per_page + choice - 1
            try:
                nchoice = self._popup[nopt]
                achoice = nchoice.choice
                self._popup._menuselect_special['option'] = nchoice
                if nchoice.selectable:
                    # valid option, handle it
                    self._popup._menuselect_special['special'] = False
                    return self._popup._response(self._user, achoice)
            except IndexError:
                # invalid option, go on...
                pass
        # the choice was either special or non-existing option
        result = True
        if self._popup.call_special:
            self._popup._menuselect_special['special'] = True
            result = self._popup._response(self._user, achoice)
        if result:
            if choice == 8:
                # previous!
                if self.pagenum > 1:
                    self.pagenum -= 1
            elif choice == 9:
                # next!
                if self.pagenum < self.pages():
                    self.pagenum += 1
            if choice == 10:
                return self._user.go_previous_popup()
            # resend current
            self._user.queue[0] = self
        return False


class UserPagedList(UserPagedMenu):
    '''
    A userpopup class for PagedList.

    A userpopup is a view to specific Popup, specific to a single user.
    Each user for each popup have their own userpopup instances.
    '''
    def _generate_line(self, index, index_on_page, text):
        if isinstance(text, MenuOption):
            text = text.text
        return '%s. %s'%(index, text)
    
    def _add_options(self, tb):
        '''Add list items to builder block tb.'''
        minopt = (self.pagenum-1)*self._popup.options_per_page
        maxopt = self.pagenum*self._popup.options_per_page
        index = 0
        for index, text in enumerate(self._popup[minopt:maxopt]):
            tb.append(self._generate_line(index+minopt+1, index, text))
        if self.pagenum > 1:
            for i in xrange(self._popup.options_per_page-index-1):
                tb.append(' ')
    
    def response(self, choice):
        '''
        Handle the user input given to this popup.
        
        Returns True if next popup may be shown;
        Returns False otherwise.
        '''
        self._popup._menuselect_special = {}
        self._popup._menuselect_special['raw_choice'] = choice
        self._popup._menuselect_special['page'] = self.pagenum
        result = True
        if self._popup.call_special:
            self._popup._menuselect_special['special'] = True
            result = self._popup._response(self._user, choice)
        if result:
            if choice == 8:
                # previous!
                if self.pagenum > 1:
                    self.pagenum -= 1
            elif choice == 9:
                # next!
                if self.pagenum < self.pages():
                    self.pagenum += 1
            if choice == 10:
                return self._user.go_previous_popup()
            # resend current
            self._user.queue[0] = self
        return False


class UserPersonalMenu(UserPagedMenu):
    '''
    A userpopup class for PersonalMenu.
    
    A userpopup is a view to specific Popup, specific to a single user.
    Each user for each popup have their own userpopup instances.
    
    When a PersonalMenu is sent, the assigned callback function is called
    with the userid and an instance of this class as parameters. Editing
    the contents of the instance determines the contents of the menu
    sent to the user. Use the methods add, find and remove.
    When the callback is called, the personal contents are always empty.
    
    Attributes:
    title -- the title of the menu
    description -- the description of the menu
    menuselect_args -- a dictionary containing extra information that is put
      to the menuselect callback dict
    '''
    def __init__(self, *args, **kw):
        '''Initialize a new Userpopup '''
        super(UserPersonalMenu, self).__init__(*args, **kw)
        self._contents = []
        self._final_contents = []
        self.menuselect_args = {}
        self.title = ''
        self.description = ''

    def __setitem__(self, *args):
        return self._contents.__setitem__(*args)
    
    def __getitem__(self, *args):
        return self._contents.__getitem__(*args)

    def __delitem__(self, *args):
        return self._contents.__delitem__(*args)
    
    def add(self, choice, text, selectable=True):
        '''
        Add a new menu option.
    
        Parameters:
        choice -- the value for choice in menuselect dictionary when this
            option is chosen
        text -- the text to show in the menu for this option
        selectable -- (optional) boolean specifying if this option can be
            selected
        
        Return value:
        the MenuOption instance added to the menu
        '''
        opt = MenuOption(choice, text, selectable)
        self._contents.append(opt)
        return opt
    
    def find(self, choice):
        '''
        Find added menu option and return it or None if not found.
        '''
        for opt in self._contents:
            if opt.choice == choice:
                return opt
        return None
    
    def remove(self, choice):
        '''
        Find added menu option and remove it, returning it.
        '''
        for index, opt in enumerate(self._contents):
            if opt.choice == choice:
                return self._contents.pop(index)
        return None
    
    def pages(self):
        '''Count the number of pages in this popup.'''
        full_pages, left_over_options = divmod(
            len(self._popup)+len(self._contents), self._popup.options_per_page
        )
        return full_pages + (1 if left_over_options else 0)
    
    def display(self):
        '''Create a GUI panel and display it for the user.'''
        self._contents = []
        try:
            self._popup.build_callback(self._user.userid, self)
        except TypeError, e:
            warnings.warn('TypeError when calling build_callback: %s'%e)
        else:
            self._final_contents = list(self._popup) + self._contents
        pages = self.pages()
        language = self.get_language()
        tb = []
        # add title
        tb.append('%-25s(%d/%d)'%(self.title or self._popup.title,
            self.pagenum, pages or 1))
        # add description
        if self.description:
            tb.append('%s\n'%self.description or self._popup.description)
        # add separating slashes
        tb.append('-'*30)
        if pages == 0:
            # empty menu
            tb.append(popuplib2_resources.get_string('empty', language))
        else:
            # add options
            minopt = (self.pagenum-1)*self._popup.options_per_page
            maxopt = self.pagenum*self._popup.options_per_page
            index = 0
            for index, option in enumerate(self._final_contents[minopt:maxopt]):
                tb.append(str(option)%(index+1))
            for i in xrange(self._popup.options_per_page-index-1):
                tb.append(' ')
            # add separating slashes
            tb.append('-'*30)
            # add page navigation links
            if pages > 1:
                s_prev = popuplib2_resources.get_string('prev', language)
                s_next = popuplib2_resources.get_string('next', language)
                if self.pagenum == 1:
                    tb.append('8. %s'%s_prev)
                else:
                    tb.append('->8. %s\n'%s_prev)
                if self.pagenum == pages:
                    tb.append('9. %s\n'%s_next)
                else:
                    tb.append('->9. %s\n'%s_next)
            else:
                tb.append(' ')
                tb.append(' ')
        # add exit button
        tb.append('0. %s'%popuplib2_resources.get_string('cancel', language))
        #display it
        text = '\n'.join(tb)
        dbgmsg(2, 'es.menu(%d, %d, textlen=%d, %s'%(
            0, self._user.userid, len(text), self._popup.enable_keys))
        es.menu(0, self._user.userid, text, self._popup.enable_keys)
    
    def response(self, choice):
        '''
        Handle the user input given to this popup.
        
        Returns True if next popup may be shown;
        Returns False otherwise.
        '''
        # this is very similar to UserPagedMenu's response method (diff marked)
        # TODO: Combine the two?
        self._popup._menuselect_special = dict(self.menuselect_args) #new
        self._popup._menuselect_special['raw_choice'] = choice
        self._popup._menuselect_special['page'] = self.pagenum
        self._popup._menuselect_special['option'] = None
        achoice = None
        if choice < 8:
            nopt = (self.pagenum-1)*self._popup.options_per_page + choice - 1
            try:
                nchoice = self._final_contents[nopt] #edited
                achoice = nchoice.choice
                self._popup._menuselect_special['option'] = nchoice
                if nchoice.selectable:
                    # valid option, handle it
                    self._popup._menuselect_special['special'] = False
                    return self._popup._response(self._user, achoice)
            except IndexError:
                # invalid option, go on...
                pass
        # the choice was either special or non-existing option
        result = True
        if self._popup.call_special:
            self._popup._menuselect_special['special'] = True
            result = self._popup._response(self._user, achoice)
        if result:
            if choice == 8:
                # previous!
                if self.pagenum > 1:
                    self.pagenum -= 1
            elif choice == 9:
                # next!
                if self.pagenum < self.pages():
                    self.pagenum += 1
            if choice == 10:
                return self._user.go_previous_popup()
            # resend current
            self._user.queue[0] = self
        return False


# Option classes


class MenuOption(object):
    '''
    A menu option for PagedMenu.

    Attributes:
    choice -- the value to put in menuselect dictionary and the value that is
        used to identify the option
    text -- the text to show in the menu
    selectable -- if this option can be selected
    '''
    def __init__(self, choice, text, selectable=True):
        '''Initialize a new MenuOption.'''
        self.choice = choice
        self.text = text
        self.selectable = selectable

    def __str__(self):
        # this method needs to be optimized and unfortunately
        # ('%s'%d) is faster than ('%d'%d) which would be more explicit
        if self.selectable:
            return "->%%s. %s"%(self.text.replace('%', '%%'))
        else:
            return "%%s. %s"%(self.text.replace('%', '%%'))


# Popup classes


class Popup(list):
    '''
    A basic popup class, other popups subclass this.

    Attributes:
    language -- the abbreviated language for automatically created content,
      filled automatically if added to PopupGroup
    enable_keys -- a string of accepted input keys, defaults to "0123456789"
    menuselect -- callback function that is called when user gives response
      to this popup; the callback function must accept one parameter, a dict
      that contains at least keys "popup", "userid" and "choice". The callback
      function may return a popup or popupgroup object which will be used as a
      submenu and displayed immediately after processing the resonse.
    menuselect_args -- a dictionary containing extra information that is put
      to the menuselect callback dict
    '''
    
    _user_popup_class = UserPopup
    
    # FIXME: add max queue time and max visibility times
    def __init__(self, *args, **kw):
        '''Initialize a new Popup.'''
        super(Popup, self).__init__(*args, **kw)
        self._users = {}
        ''' self._users = {userid: Userpopup instance,} '''
        self._menuselect_special = {}
        self.language = None
        self.enable_keys = "0123456789"
        self.menuselect = None
        self.menuselect_args = {}
    
    def _delete(self):
        '''Deletes this popup user information.'''
        self.menuselect = None
        self.menuselect_args = {}
    
    def __del__(self):
        '''
        No references to this popup.
        '''
        dbgmsg(1, 'Popuplib2: Deleting popup')
        dbgmsg_repr(2, self)
    
    def _get_userpopup(self, user):
        '''Return userpopup and create one if necessary.'''
        if user.userid not in self._users:
            userpopup = self._user_popup_class(user, self)
            self._users[user.userid] = userpopup
        else:
            userpopup = self._users[user.userid]
        return userpopup
    
    def _send(self, user, *args, **kw):
        '''Send this popup to _User object.'''
        userpopup = self._get_userpopup(user)
        userpopup._send(*args, **kw)
        return userpopup
    
    def _unsend(self, user):
        '''Remove this popup from _User queue.'''
        if user.userid in self._users:
            userpopup = self._users[user.userid]
            return userpopup.unsend()
        return False
    
    def _response(self, user, choice):
        '''Handle response from a user.'''
        if callable(self.menuselect):
            params = {
                'userid': user.userid,
                'choice': choice,
                'popup': self,
                'previous': user.get_previous_popup(),
            }
            params.update(self.menuselect_args)
            params.update(self._menuselect_special)
            try:
                submenu = self.menuselect(params)
            except Exception:
                # print the exception as normal, but pretend nothing happened
                dbgmsg(1, 'Popuplib2: Called menuselect function raised:')
                sys.excepthook(*sys.exc_info())
                sys.exc_clear()
                submenu = None
            if submenu is not None:
                try:
                    user.queue[0] = submenu._get_userpopup(user)
                    return False
                except AttributeError:
                    dbgmsg(0, 'Popuplib2: got non-popup return value from callback function')
                    dbgmsg_repr(0, submenu)
        return True
    
    def send(self, userid, *args, **kw):
        '''Send this popup to user specified by userid.'''
        user = _usermanager[userid]
        return self._send(user, *args, **kw)
    
    def unsend(self, userid):
        '''
        Remove this popup from user queue.

        Return True if the popup was removed.
        Return False if the popup was not in queue.
        '''
        user = _usermanager[userid]
        return self._unsend(user)

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
    
    # TODO: more basic popup actions


class TemplatePopup(Popup):
    '''
    A template popup class, popup supporting run-time replacements.

    Attributes:
    language -- the abbreviated language for automatically created content,
      filled automatically if added to PopupGroup
    enable_keys -- a string of accepted input keys, defaults to "0123456789"
    menuselect -- callback function that is called when user gives response
      to this popup; the callback function must accept one parameter, a dict
      that contains at least keys "popup", "userid" and "choice". The callback
      function may return a popup or popupgroup object which will be used as a
      submenu and displayed immediately after processing the resonse.
    menuselect_args -- a dictionary containing extra information that is put
      to the menuselect callback dict
    '''
    
    _user_popup_class = UserTemplatePopup


class PersonalPopup(Popup):
    '''
    Callback-based dynamically created popup.
    
    The constructor parameter build_callback must be a function that accepts
    two parameters: (userid, userpopup)
    The userid parameter will contain the userid for which the popup is being
    sent, the userpopup is an instance of UserPersonalPopup that can be
    modified to make the content correct. Additional parameters and keywords
    are as given to the send() method. See UserPersonalPopup documentation
    for further information.
    
    Attributes:
    language -- the abbreviated language for automatically created content,
      filled automatically if added to PopupGroup
    enable_keys -- a string of accepted input keys, defaults to "0123456789"
    menuselect -- callback function that is called when user gives response
      to this popup; the callback function must accept one parameter, a dict
      that contains at least keys "popup", "userid" and "choice". The callback
      function may return a popup or popupgroup object which will be used as a
      submenu and displayed immediately after processing the resonse.
    menuselect_args -- a dictionary containing extra information that is put
      to the menuselect callback dict
    '''

    _user_popup_class = UserPersonalPopup
    
    def __init__(self, build_callback, *args, **kw):
        '''Initialize a new PersonalPopup.'''
        super(PersonalPopup, self).__init__(*args, **kw)
        self.build_callback = build_callback
    
    def _send(self, user, *args, **kw):
        '''Send this popup to _User object.'''
        userpopup = self._get_userpopup(user)
        userpopup._contents = []
        self.build_callback(user.userid, userpopup, *args, **kw)
        userpopup._send()
        return userpopup


class PagedMenu(Popup):
    '''
    A paged menu popup.
    
    Attributes:
    language -- the abbreviated language for automatically created content,
      filled automatically if added to PopupGroup
    menuselect -- callback function that is called when user gives response
      to this popup; the callback function must accept one parameter, a dict
      that contains at least keys "popup", "userid" and "choice". The callback
      function may return a popup or popupgroup object which will be used as a
      submenu and displayed immediately after processing the resonse.
    menuselect_args -- a dictionary containing extra information that is put
      to the menuselect callback dict
    title -- the title of the menu
    description -- the description of the menu
    call_special -- bool, will menuselect be called with non-choice inputs too
    '''
    
    _user_popup_class = UserPagedMenu
    
    def __init__(self, *args, **kw):
        '''Initialize a new PagedMenu.'''
        super(PagedMenu, self).__init__(*args, **kw)
        self._menuselect_special = {
            'raw_choice': None,
            'page': None,
        } # maybe needed for Popup._response with custom userpopups
        self.title = ''
        self.description = ''
        self.call_special = False
        self.options_per_page = 7 # do not change, or at least don't increase
        
        self.enable_keys = "0123456789"
    
    def add(self, choice, text, selectable=True):
        '''
        Add a new menu option.
    
        Parameters:
        choice -- the value for choice in menuselect dictionary when this
            option is chosen
        text -- the text to show in the menu for this option
        selectable -- (optional) boolean specifying if this option can be
            selected
        
        Return value:
        the MenuOption instance added to the menu
        '''
        opt = MenuOption(choice, text, selectable)
        self.append(opt)
        return opt
    
    def find(self, choice):
        '''
        Find added menu option and return it or None if not found.
        '''
        for opt in self:
            if opt.choice == choice:
                return opt
        return None
    
    def remove(self, choice):
        '''
        Find added menu option and remove it, returning it.
        '''
        for index, opt in enumerate(self):
            if opt.choice == choice:
                return self.pop(index)
        return None
    
    def pages(self):
        '''Count the number of pages in this popup.'''
        full_pages, left_over_options = divmod(len(self), self.options_per_page)
        return full_pages + (1 if left_over_options else 0)
    
    def isvalidpage(self, pagenum):
        '''Check if specified page number is currently valid for this popup.'''
        if not isinstance(pagenum, int):
            return False # sorry guys, coerce to int yourselves
        if 1 <= pagenum <= self.pages():
            return True
        return False



class PersonalMenu(PagedMenu):
    '''
    A paged menu popup that displays personal information to users.

    The constructor parameter build_callback must be a function that accepts
    two parameters: (userid, userpopup)
    The userid parameter will contain the userid for which the popup is being
    sent, the userpopup is an instance of UserPersonalMenu that can be
    modified to make the content correct. Additional parameters and keywords
    are as given to the send() method. See UserPersonalMenu documentation
    for further information.
    
    Attributes:
    language -- the abbreviated language for automatically created content,
      filled automatically if added to PopupGroup
    menuselect -- callback function that is called when user gives response
      to this popup; the callback function must accept one parameter, a dict
      that contains at least keys "popup", "userid" and "choice". The callback
      function may return a popup or popupgroup object which will be used as a
      submenu and displayed immediately after processing the resonse.
    menuselect_args -- a dictionary containing extra information that is put
      to the menuselect callback dict
    call_special -- bool, will menuselect be called with non-choice inputs too
    '''
    
    _user_popup_class = UserPersonalMenu
    
    def __init__(self, build_callback, *args, **kw):
        '''Initialize a new PersonalMenu.'''
        super(PersonalMenu, self).__init__(*args, **kw)
        self.build_callback = build_callback
    
    def _send(self, user, *args, **kw):
        '''Send this popup to _User object.'''
        userpopup = self._get_userpopup(user)
        userpopup._contents = []
        self.build_callback(user.userid, userpopup, *args, **kw)
        userpopup._send()
        return userpopup


class PagedList(PagedMenu):
    '''
    A paged list popup.
    
    Attributes:
    language -- the abbreviated language for automatically created content,
      filled automatically if added to PopupGroup
    menuselect -- callback function that is called when user gives response
      to this popup; the callback function must accept one parameter, a dict
      that contains at least keys "popup", "userid" and "choice". The callback
      function may return a popup or popupgroup object which will be used as a
      submenu and displayed immediately after processing the resonse.
    menuselect_args -- a dictionary containing extra information that is put
      to the menuselect callback dict
    title -- the title of the list
    description -- the description of the list
    options_per_page -- the number of items displayed per page (default 10)
    '''
    
    _user_popup_class = UserPagedList
    
    def __init__(self, *args, **kw):
        '''Initialize a new PagedMenu.'''
        super(PagedList, self).__init__(*args, **kw)
        self.call_special = True
        self.options_per_page = 10


