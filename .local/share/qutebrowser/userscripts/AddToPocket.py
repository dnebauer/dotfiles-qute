#!/usr/bin/env python3

# module docstring    {{{1
""" qutebrowser userscript to add the current page to Pocket

This qutebrowser userscript is designed to be called from
qutebrowser with a command like:
'qutebrowser --userscript AddToPocket'.

This userscript takes the current page in qutebrowser and
adds it to Pocket. The current page url is obtained from
environmental variable 'QUTE_URL'. The script first attempts
to send this url to Pocket by email (add@getpocket.com). In
Windows Outlook is used. In other operating systems the
generic python module 'smtplib' is used. If the attempt to
send by email fails the script attempts to add the url to
Pocket via the Pocket website
(http://www.getpocket.com/edit).

Feedback is sent to qutebrowser's status line. This process
uses environmental variable 'QUTE_FIFO' which holds the name
of a named pipe (unix and mac os) or regular file (windows)
used in communicating with qutebrowser.

Details about the mail server and email account to use are
obtained from ~/qute_mail.ini. The file format is:

    [server]
    address = ...
    port = ...

    [account]
    login = ...
    password = ...
    email = ...

Note that while the email value must be provided, it is
ignored in Windows: the default Outlook email account is
used.
"""

# import statements    {{{1
import os
import sys
import textwrap
import argparse
import email.message
import platform
if platform.system() == 'Windows':
    import win32com.client
else:
    import smtplib
import configparser  # noqa: flake8: module level import not at top of file
import inflect    # noqa: flake8: module level import not at top of file


class AddToPocket(object):    # {{{1

    # class docstring    {{{2
    """ send url to qutebrowser by email

    assumes the existence of correctly written configuration file
    ~/qute_mail.ini

    assumes this userscript has been called from within qutebrowser
    with a command like 'spawn --userscript AddToPocket'

    usage:

    pocket = AddToPocket()
    pocket.read_config()
    pocket.add()
    """

    def __init__(self):    # {{{2

        """ initialise variables """

    # mail server and account (to come from config file)
        self.__server = {'smtp': None, 'port': None}
        self.__account = {'login': None, 'password': None, 'email': None}

    # url to send (qute-set environmental variable)
        self.__url = os.getenv('QUTE_URL')
        if not self.__url:
            self.__abort('Missing environmental variable QUTE_URL')

    # web page title (optional qute-set environmental variable)
        self.__title = os.getenv('QUTE_TITLE')  # command mode
        if not self.__title:
            self.__title = os.getenv('QUTE_SELECTED_TEXT')  # hints mode
        if not self.__title:  # desperation mode
            head = self.__url
            while head:  # walk back through url till get non-empty part
                head, tail = os.path.split(head)
                if tail:
                    self.__title = tail
                    break

    # message pipe to qute (qute-set environmental variable)
        self.__fifo = os.getenv('QUTE_FIFO')
        if not self.__fifo:
            self.__abort('Missing environmental variable QUTE_FIFO')

    # configuration file is ~/qute_mail.ini
        self.__conf = os.path.join(os.path.expanduser('~'), 'qute_mail.ini')
        if not os.path.isfile(self.__conf):
            self.__abort("Cannot find config file '" + self.__conf + "'")

    # pluraliser
        self.__plural = inflect.engine()

    @staticmethod
    def __simplify(string):    # {{{2

        """ simplify string so it can be part of qutebrower command

        commands cannot contain newlines or unbalanced quotes, so:
        - if string is multiline take only first line
        - strip all quotes from string

        for visual simplicity also strip final period if present
        """

        simple = str(string).splitlines()[0]
        return simple.rstrip('.').replace("'", "").replace('"', '')

    def __abort(self, message):    # {{{2

        """ exit script on failure

        assume message is simplified, i.e., no newlines or quotes

        exiting without error status means error message is not followed
        in status bar by an exit status message, and the first message
        remains visible for a fraction longer
        """

        cmd = 'message-error "' + message + '"'
        self.__send_command(cmd)
        sys.exit()

    def __success(self):    # {{{2

        """ exit script on success """

        msg = (('Added to Pocket: ' + self.__title) if self.__title
               else 'Added page to Pocket')
        cmd = 'message-info "' + msg + '"'
        self.__send_command(cmd)
        sys.exit()

    def __send_command(self, command):    # {{{2

        """ send command to qutebrowser via pipe

        cannot open pipe in append mode ('a') because it
        causes the userscript to exit with status 1
        """

        fifo = open(self.__fifo, 'w')
        fifo.write(command)
        fifo.close()

    def read_config(self):    # {{{2

        """ read configuration file ~/qute_mail.ini """

    # read in config file
        config = configparser.ConfigParser()
        try:
            config.read(self.__conf)
        except configparser.Error as err:
            self.__abort("Failed to read '" + self.__conf + "': " +
                         self.__simplify(err))

    # extract and check variables from config file
        self.__server['smtp'] = config.get('server', 'address',
                                           fallback=None)
        self.__server['port'] = config.getint('server', 'port',
                                              fallback=None)
        self.__account['login'] = config.get('account', 'login',
                                             fallback=None)
        self.__account['password'] = config.get('account', 'password',
                                                fallback=None)
        self.__account['email'] = config.get('account', 'email',
                                             fallback=None)
        check = {'smtp': self.__server['smtp'],
                 'port': self.__server['port'],
                 'login': self.__account['login'],
                 'password': self.__account['password'],
                 'email': self.__account['email']}
        missing = {key: check[key] for key in check if not check[key]}
        if len(missing) > 0:
            self.__abort('Missing config ' +
                         self.__plural.plural_noun('value', len(missing)) +
                         ': ' + ', '.join(missing.keys()))

    def add(self):    # {{{2

        """ add url to Pocket

        first try email (Outlook in Windows, otherwise smtp,
        then try adding via getpocket website
        """

    # first try to add by sending email
        if platform.system() == 'Windows':
            self.__send_outlook_email()
        else:
            self.__send_smtp_email()

    # if still here, then email attempt failed, so
    # try using getpocket website
        cmd = 'open www.getpocket.com/edit?url=' + self.__url
        self.__send_command(cmd)

    # effect of previous command is to open pocket website,
    # and the website will clearly convey the outcome
        sys.exit()

    def __send_smtp_email(self):    # {{{2

        """ send smtp email to Pocket email address """

        try:
    # create email
            mail = email.message.Message()
            mail['To'] = 'add@getpocket.com'
            mail['From'] = self.__account['email']
            mail['Subject'] = 'Add to Pocket'
            mail.add_header('Content-Type', 'text/plain')
            mail.set_payload(self.__url)

    # send email
            server = smtplib.SMTP(self.__server['smtp'], self.__server['port'])
            server.login(self.__account['login'], self.__account['password'])
            server.sendmail(self.__account['email'], mail['To'],
                            mail.as_string())
            server.quit()
        except smtplib.SMTPException:
            return

    # assume success if no exceptions occurred
        self.__success()

    def __send_outlook_email(self):    # {{{2

        """ send Outlook email to Pocket email address """

        try:
            const = win32com.client.constants
            const.olMailItem = 0x0
            obj = win32com.client.Dispatch('Outlook.Application')
            mail = obj.CreateItem(const.olMailItem)
            mail.To = 'add@getpocket.com'
            mail.Subject = 'Add to Pocket'
            mail.Body = self.__url
            mail.Send()
        except win32com.client.exception:
            return

    # report success
        self.__success()


def usage():    # {{{1

    """ print help if requested """

    description = textwrap.dedent('''\
    qutebrowser userscript to add the current page to Pocket

    This qutebrowser userscript is designed to be called from
    qutebrowser with a command like:
    'qutebrowser --userscript AddToPocket'.

    This userscript takes the current page in qutebrowser and
    adds it to Pocket.  The current page url is obtained from
    environmental variable 'QUTE_URL'. The script attempts to
    send this url to Pocket by email (add@getpocket.com). In
    Windows Outlook is used. In other operating systems the
    generic python module 'smtplib' is used.

    Feedback is sent to qutebrowser's status line. This process
    uses environmental variable 'QUTE_FIFO' which holds the name
    of a named pipe (unix and mac os) or regular file (windows)
    used in communicating with qutebrowser.

    Details about the mail server and email account to use are
    obtained from ~/qute_mail.ini. The file format is:

        [server]
        address = ...
        port = ...

        [account]
        login = ...
        password = ...
        email = ...

    Note that while the email value must be provided, it is
    ignored in Windows: the default Outlook email account is
    used.
    ''')
    argparse.ArgumentParser(formatter_class=argparse.
                            RawDescriptionHelpFormatter,
                            description=description).parse_args()    # }}}1


def main():

    """ script execution starts here """

    usage()
    pocket = AddToPocket()
    pocket.read_config()
    pocket.add()


if __name__ == '__main__':
    main()

# vim:fdm=marker:
