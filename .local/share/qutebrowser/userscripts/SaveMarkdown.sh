#!/usr/bin/env bash
# Qutebrowser userscript that converts the current page to markdown and saves
# it to a filepath specified by the user.
#
# Suggested keybinding (for "save markdown"):
# spawn --userscript SaveMarkdown.sh
#     sm
#
# Requirements:
#  - assumed to be available (not tested for): which
#  - tested for: basename, cp, html2text, mktemp, sed, zenity

set -e

# default download directory
DOWNLOAD_DIR=${DOWNLOAD_DIR:-$QUTE_DOWNLOAD_DIR}
DOWNLOAD_DIR=${DOWNLOAD_DIR:-$HOME/Downloads}
# save-as dialog
ZENITY=${ZENITY:-zenity}
# html2text command
HTML2TEXT=${HTML2TEXT:-html2text}
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
FILE_NAME_MD="${FILE_NAME%.*}.md"
DEFAULT_PATH="$DOWNLOAD_DIR/$FILE_NAME_MD"

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
escape() {
    # escape FILE CHAR
    # - throughout FILE escape character CHAR with backslash
    local file="$1" char="$2"
    $SED -i -e "s/$char/\\\\$char/g" "$file" || true
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
        if ! which "$cmd" > /dev/null ; then
            die "Command not found in PATH: ${cmd}"
        fi
    done
}

# requirements
[ -d "$DOWNLOAD_DIR" ] || die "Download directory not found: $DOWNLOAD_DIR"
required "$ZENITY" "$HTML2TEXT" "$SED" "$MKTEMP" "$RM" "$CP"

# get download file path
md_path="$( \
    $ZENITY \
        --title 'Save as...' \
        --file-selection \
            --save \
            --filename="$DEFAULT_PATH" \
            --confirm-overwrite \
            --file-filter="*.md" \
    )" || true
[ -n "$md_path" ] || die 'No download file path set'

# convert html file to temporary markdown file
temp_file="$($MKTEMP --tmpdir qutebrowser_XXXXXXXX.md)"
$HTML2TEXT -utf8 -width 1000000 "$QUTE_HTML" \
    | $SED -e '/.*/G' \
    > "$temp_file" \
    || true
[ -f "$temp_file" ] || die 'Unable to generate markdown output file'
[ -s "$temp_file" ] || die 'Markdown output file is empty'

# escape and replace special characters
escape "$temp_file" '_' || true
escape "$temp_file" '*' || true
replace "$temp_file" '“' '"' || true
replace "$temp_file" '”' '"' || true
replace "$temp_file" "’" "'" || true
replace "$temp_file" "‘" "'" || true
replace "$temp_file" "‒" "--" || true
replace "$temp_file" "–" "--" || true
replace "$temp_file" "—" "--" || true
replace "$temp_file" "…" "..." || true

# copy temp file to output file location
if [ -f "$md_path" ];  then
    $RM "$md_path" || true
    [ -f "${md_path}" ] && die "Unable to overwrite existing file ${md_path}"
fi
$CP "$temp_file" "$md_path" || true
[ -f "${md_path}" ] || die "Unable to save $md_path"

# if here then must have succeeded
info "Saved $md_path"
