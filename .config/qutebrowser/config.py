# Load autoconfig.yml
config.load_autoconfig()

# Bindings

# - only unbind when necessary, i.e., doing so causes no error

# [normal]

# - enter password: ,p
config.bind(',p', 'spawn --userscript password_fill')
# - add to Pocket: ,g ["getpocket"] | ;G (rapid hints)
config.bind(',g', 'spawn --userscript AddToPocket.py')
config.bind(';G', 'hint --rapid links userscript AddToPocket.py')
# - play video: ,v | V (hint) | ;V (rapid hints)
config.bind(',v', 'spawn umpv {url}')
config.bind('V', 'hint links spawn umpv {hint-url}')
config.bind(';V', 'hint --rapid links spawn umpv {hint-url}')
# - save to markdown file: ,m
config.bind(',m', 'spawn --userscript SaveMarkdown.sh')
# - view source: ,s
config.bind(',s', 'spawn --userscript qutebrowser_viewsource')
# - open tab: t
config.bind('t', 'set-cmd-text :open -t ')
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

# [command]

# jump to next category in completion menu: <Ctrl-Tab>
config.unbind('<ctrl-tab>', mode='command')
config.bind('<ctrl-tab>', 'completion-item-focus next-category')
# jump to previous category in completion menu: <Ctrl-Shift-Tab>
config.unbind('<ctrl-shift-tab>', mode='command')
config.bind('<ctrl-shift-tab>', 'completion-item-focus prev-category')
