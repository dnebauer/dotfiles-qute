#!/usr/bin/env bash
# Qutebrowser userscript that converts the current page to plain text and saves
# it to a filepath specified by the user.
#
# Uses w3m to convert html to text. The following are non-default changes to
# the output:
# - outputs as utf-8 (with w3m '-O UTF-8' option)
# - hyperlinks are appended to output as list (with w3m 'display_link_number'
#   option)
# - replace default list marker, '^  • ', with markdown-style marker, '^* '
#   (with sed)
#
# Suggested keybinding (for "save text"):
# spawn --userscript SaveText.sh
#     st
#
# Requirements:
# - assumed to be available (not tested for): command
# - tested for: basename, cp, w3m, mktemp, sed, zenity

set -e

# default download directory
DOWNLOAD_DIR=${DOWNLOAD_DIR:-$QUTE_DOWNLOAD_DIR}
DOWNLOAD_DIR=${DOWNLOAD_DIR:-$HOME/Downloads}
# save-as dialog
ZENITY=${ZENITY:-zenity}
# w3m command
W3M=${W3M:-w3m}
# sed command
SED="${SED:-sed}"
# mktemp command
MKTEMP="${MKTEMP:-mktemp}"
# rm command
RM="${RM:-rm}"
# cp command
CP="${CP:-cp}"
# default file path
FILE_NAME="$(basename "$QUTE_URL")"
FILE_NAME_TXT="${FILE_NAME%.*}.txt"
DEFAULT_PATH="$DOWNLOAD_DIR/$FILE_NAME_TXT"

# subroutines
msg() {
    # msg TYPE MESSAGE
    # - display message MSG of type TYPE ('info' or 'error')
    local cmd="$1" ; shift ; local msg="$*"
    echo "message-$cmd '${msg//\'/\\\'}'" >> "$QUTE_FIFO"
}
info() {
    # info MSG
    # - display message MSG
    msg info "$*"
}
die() {
    # die MSG
    # - display error message MSG and exit
    msg error "$*"
    # the above error message already informs the user about the failure;
    # no additional "userscript exited with status 1" is needed.
    exit 0
}
replace() {
    # replace FILE TARGET REPLACE
    # - throughout FILE replace string TARGET with string REPLACE
    local file="$1" target="$2" replace="$3"
    $SED -i -e "s/$target/$replace/g" "$file" || true
}
required() {
    # required CMD [CMD2 ...]
    # - check that CMDs are available; die if any are not
    local -a cmds
    while [ $# -gt 0 ] ; do cmds=("${cmds[@]}" "$1") ; shift ; done
    for cmd in "${cmds[@]}" ; do
        if ! command -v "$cmd" > /dev/null ; then
            die "Command not found in PATH: ${cmd}"
        fi
    done
}

# requirements
[ -d "$DOWNLOAD_DIR" ] || die "Download directory not found: $DOWNLOAD_DIR"
required "$ZENITY" "$W3M" "$SED" "$MKTEMP" "$RM" "$CP"

# get download file path
dl_path="$( \
    $ZENITY \
        --title 'Save as...' \
        --file-selection \
            --save \
            --filename="$DEFAULT_PATH" \
            --confirm-overwrite \
            --file-filter="*.txt" \
    )" || true
[ -n "$dl_path" ] || die 'No download file path set'

# convert html file to temporary text file
temp_file="$($MKTEMP --tmpdir qutebrowser_XXXXXXXX.txt)"
$W3M -T "text/html" -o display_link_number=1 -O UTF-8 < "$QUTE_HTML" \
    > "$temp_file" \
    || true
[ -f "$temp_file" ] || die 'Unable to generate text output file'
[ -s "$temp_file" ] || die 'Text output file is empty'

# replace bullet list marker (U+2022 = "•") with markdown-style asterisk
replace "$temp_file" '^[[:space:]]*•[[:space:]]*' '* ' || true

# copy temp file to output file location
if [ -f "$dl_path" ];  then
    $RM "$dl_path" || true
    [ -f "${dl_path}" ] && die "Unable to overwrite existing file ${dl_path}"
fi
$CP "$temp_file" "$dl_path" || true
[ -f "${dl_path}" ] || die "Unable to save $dl_path"

# if here then must have succeeded
info "Saved $dl_path"
