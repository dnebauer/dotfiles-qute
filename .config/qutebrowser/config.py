# Load autoconfig.yml
config.load_autoconfig()

# Bindings

# - only unbind when necessary, i.e., doing so causes no error

# Bindings [normal]
# - don't need to specify mode for normal mode

# - enter password: ,p
config.bind(',p', 'spawn --userscript password_fill')
# - add to Pocket: ,g ["getpocket"] | ;G (rapid hints)
config.bind(',g', 'spawn --userscript AddToPocket.py')
config.bind(';G', 'hint --rapid links userscript AddToPocket.py')
# - play video: ,v | V (hint) | ;V (rapid hints)
config.bind(',v', 'spawn umpv {url}')
config.bind('V', 'hint links spawn umpv {hint-url}')
config.bind(';V', 'hint --rapid links spawn umpv {hint-url}')
# - open url in google-chrome
config.bind(',c', 'spawn google-chrome {url}')
# - save to markdown file: ,m
config.bind(',m', 'spawn --userscript SaveMarkdown.py')
# - view source: ,s
config.bind(',s', 'spawn --userscript qutebrowser_viewsource')
# - save to text file: ,t
config.bind(',t', 'spawn --userscript SaveText.sh')
# - open tab: t (the '-s' option appends a space)
config.bind('t', 'set-cmd-text -s :open -t ')
# - next tab: J | gt | <Ctrl-PgDown>
config.unbind('J', mode='normal')
config.bind('J', 'tab-next')
config.unbind('gt', mode='normal')
config.bind('gt', 'tab-next')
config.unbind('<ctrl-pgdown>', mode='normal')
config.bind('<ctrl-pgdown>', 'tab-next')
# - previous tab: K | gT | <Ctrl-PgUp>
config.unbind('K', mode='normal')
config.bind('K', 'tab-prev')
config.bind('gT', 'tab-prev')
config.unbind('<ctrl-pgup>', mode='normal')
config.bind('<ctrl-pgup>', 'tab-prev')
# - move tab right: <Ctrl-Shift-PgDown>
config.bind('<ctrl-shift-pgdown>', 'tab-move +')
# - move tab left: <Ctrl-Shift-PgUp>
config.bind('<ctrl-shift-pgup>', 'tab-move -')
# - back: <Alt-Left>
config.bind('<alt-left>', 'back')
# - forward: <Alt-Right>
config.bind('<alt-right>', 'forward')
# - home: <Alt-Home>
config.bind('<alt-home>', 'home')

# Bindings [command]

# jump to next category in completion menu: <Ctrl-Tab>
config.unbind('<ctrl-tab>', mode='command')
config.bind('<ctrl-tab>', 'completion-item-focus next-category', mode='command')
# jump to previous category in completion menu: <Ctrl-Shift-Tab>
config.unbind('<ctrl-shift-tab>', mode='command')
config.bind('<ctrl-shift-tab>', 'completion-item-focus prev-category', mode='command')

# Settings

# use vim as default editor instead of gvim
# config.set('editor.command',
#            ['konsole', '--hide-menubar', '--hide-tabbar',
#             '-e', 'vim', '{file}'])

# [editor.command setting does not currently support URL patterns]
# set filetype when opening tiddlywiki tiddler file in external editor
# with config.pattern('*://localhost:10744') as p:
#     p.editor.command = ['gvim',
#                         '-f', '{file}',
#                         '-c', 'set filetype=tiddlywiki',
#                         '-c', 'normal {line}G{column0}l']

# change editor.command before opening external editor, then reset it
# - as a single command
# config.bind('<ctrl-w>', 'set editor.command "[\'gvim\', \'-f\', \'{file}\', \'-c\', \'normal {line}G{column0}l\', \'-c\', \'set filetype=tiddlywiki\']" ;; later 30 open-editor ;; later 500 set editor.command "[\'gvim\', \'-f\', \'{file}\', \'-c\', \'normal {line}G{column0}l\']"', mode='insert')
# - build up command from smaller elements
CHANGE_EDITOR_COMMAND = ''.join([
    'set editor.command "[',
    '\'gvim\', ',
    '\'-f\', \'{file}\', ',
    '\'-c\', \'normal {line}G{column0}l\', ',
    '\'-c\', \'set filetype=tiddlywiki\'',
    ']"',
])
OPEN_EDITOR = ''.join([
    'later 30 ',
    'open-editor',
])
RESET_EDITOR_COMMAND = ''.join([
    'later 500 ',
    'set editor.command "[',
    '\'gvim\', ',
    '\'-f\', \'{file}\', ',
    '\'-c\', \'normal {line}G{column0}l\'',
    ']"',
])
BIND_COMMAND = ' ;; '.join([
    CHANGE_EDITOR_COMMAND,
    OPEN_EDITOR,
    RESET_EDITOR_COMMAND,
])
config.bind('<ctrl-w>', BIND_COMMAND, mode='insert')
del CHANGE_EDITOR_COMMAND, OPEN_EDITOR, RESET_EDITOR_COMMAND, BIND_COMMAND
