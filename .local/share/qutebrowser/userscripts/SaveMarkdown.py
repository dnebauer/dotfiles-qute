#!/usr/bin/env python
# -*- coding: utf8 -*-

# module docstring    {{{1
""" qutebrowser userscript to save the current page as markdown

This qutebrowser userscript is designed to be called from
qutebrowser with a command like: spawn --userscript SaveMarkdown.py

This userscript takes the current page in qutebrowser, converts
it to markdown, and saves it to file. A local version of the
current page is available at a file path stored in the
environmental variable 'QUTE_HTML'. The default download
directory is taken from environmental variable
'QUTE_DOWNLOAD_DIR', and defaults to '$HOME/Downloads' if that
variable is not set. The default file name is taken from the
current page url, obtained from environmental variable
'QUTE_URL', with the extension changed to 'md'.

Credit: began life as al3xandru's html2md
        (https://github.com/al3xandru/html2md),
        commit fe9c49c, 2015-02-21
"""

# import statements    {{{1
from __future__ import print_function
import argparse
import os
import re
import sys
import wx

from BeautifulSoup import ICantBelieveItsBeautifulSoup
from BeautifulSoup import Tag, NavigableString, Declaration
from BeautifulSoup import ProcessingInstruction, Comment


# constants    {{{1
_KNOWN_ELEMENTS = ('a', 'b', 'strong', 'blockquote', 'br', 'center', 'code',
                   'dl', 'dt', 'dd', 'div', 'em', 'i', 'h1', 'h2', 'h3', 'h4',
                   'h5', 'h6', 'hr', 'img', 'li', 'ol', 'ul', 'p', 'pre',
                   'tt', 'sup')

_PHRASING_ELEMENTS = ('abbr', 'audio', 'b', 'bdo', 'br', 'button', 'canvas',
                      'cite', 'code', 'command', 'datalist', 'dfn', 'em',
                      'embed', 'i', 'iframe', 'img', 'input', 'kbd', 'keygen',
                      'label', 'mark', 'math', 'meter', 'noscript', 'object',
                      'output', 'progress', 'q', 'ruby', 'samp', 'script',
                      'select', 'small', 'span', 'strong', 'sub', 'sup',
                      'svg', 'textarea', 'time', 'var', 'video', 'wbr')

_CONDITIONAL_PHRASING_ELEMENTS = ('a', 'del', 'ins')

_ALL_PHRASING_ELEMENTS = _CONDITIONAL_PHRASING_ELEMENTS + _PHRASING_ELEMENTS

_IGNORE_ELEMENTS = ('html', 'body', 'article', 'aside', 'footer', 'header',
                    'main', 'section', 'span')

_SKIP_ELEMENTS = ('head', 'nav', 'menu', 'menuitem')

LF = unicode(os.linesep)  # noqa: F821


# class SaveMarkdown(object)    {{{1
class SaveMarkdown(object):

    # class docstring    {{{2
    """ main class processing html """

    # pylint: disable=too-many-instance-attributes,too-many-statements
    # sticking with original design for now

    def __init__(self):    # {{{2

        # markdown converter variables #

        self._processed = False
        self._options = {
            'attrs': False,          # element attributes in output*
            'footnotes': True,       # convert footnotes*
            'fenced_code': True,     # fenced code output
            'critic_markup': False,  # support CriticMarkup
            'def_list': True         # convert definition lists
        }                            # * = custom markdown extension
        self._text_buffer = []  # maintains a buffer, usu. for block elements
        self._attributes_stack = []
        self._indentation_stack = []  # maintains a stack of indentation types
        self._inside_block = False
        self._inside_footnote = False
        self._list_level = 0
        self._list_item_has_block = False
        self._output = u''
        self._footnote_ref = 0
        self._set_processors()
        self._markdown = u''

        # qutebrowser interaction variables #

        # message pipe
        self._fifo = os.getenv('QUTE_FIFO')
        if not self._fifo:
            self._abort('Missing environmental variable QUTE_FIFO')
        # input file path
        self._inpath = os.getenv('QUTE_HTML')
        if not self._inpath:
            self._abort('Missing environmental variable QUTE_HTML')
        if not os.path.isfile(self._inpath):
            self._abort('Cannot find input file ' + self._inpath)
        if not os.access(self._inpath, os.R_OK):
            self._abort('Cannot access input file ' + self._inpath)
        # input file content
        # pylint: disable=bare-except
        # need to catch all errors because script is hidden
        try:
            with open(self._inpath, 'r') as filehandle:
                self._html = filehandle.read()
        except IOError as err:
            io_errmsg = "I/O error({0}): {1}".format(err.errno, err.strerror)
            self._abort(io_errmsg)
        except:
            errmsg = "Unexpected error:", sys.exc_info()[0]
            self._abort(errmsg)
        self._soup = ICantBelieveItsBeautifulSoup(self._html)
        # default download directory
        self._download_dir = os.getenv('QUTE_DOWNLOAD_DIR')
        if not self._download_dir:
            self._download_dir = os.path.join(os.path.expanduser('~'),
                                              'Downloads')
        if not os.path.isdir(self._download_dir):
            self._abort('No variable QUTE_DOWNLOAD and no directory '
                        + self._download_dir)
        # default download file
        url = os.getenv('QUTE_URL')
        if not url:
            self._abort('Missing environmental variable QUTE_URL')
        download_file = os.path.basename(url)
        if not download_file:
            download_file = 'output.html'
        download_base = os.path.splitext(download_file)[0]
        if not download_base:
            download_base = 'output'
        self._download_file = download_base + '.md'
        # output markdown file path
        self._outpath = u''

    def generate_output(self):    # {{{2

        """ generate markdown output """

        if not self._processed:
            self._process(self._soup)
            if self._text_buffer:
                self._flush_buffer()
            self._processed = True

        self._markdown = self._output.rstrip()

    def success(self):    # {{{2

        """ exit script on success """

        msg = 'Saved as ' + self._outpath
        cmd = 'message-info "' + msg + '"'
        self._send_command(cmd)
        sys.exit()

    def write_output(self):    # {{{2

        """ write markdown output file """

        # pylint: disable=bare-except
        # need to catch all errors because script is hidden
        self._set_output_path()
        try:
            with open(self._outpath, 'w') as filehandle:
                filehandle.write(self._markdown.encode('utf8'))
        except IOError as err:
            io_errmsg = "I/O error({0}): {1}".format(err.errno, err.strerror)
            self._abort(io_errmsg)
        except:
            errmsg = "Unexpected error:", sys.exc_info()[0]
            self._abort(errmsg)

    def _abort(self, message):    # {{{2

        # exiting without error status means error message is not followed
        # in status bar by an exit status message, and the first message
        # remains visible for a fraction longer

        cmd = 'message-error "' + message + '"'
        self._send_command(cmd)
        sys.exit()

    def _comment(self, tag):    # {{{2
        if not self._options['critic_markup']:
            return
        self._text_buffer.append(u"{>>")
        self._text_buffer.append(tag)
        self._text_buffer.append(u"<<}")

    def _elem_attrs(self, tag_name, attrs, sep):    # {{{2
        # process element attributes
        # pylint: disable=no-self-use
        # too difficult to move from object
        if not attrs:
            return u""
        attr_arr = []
        lattrs = attrs.copy()
        if 'id' in lattrs:
            attr_arr.append("#%s" % lattrs['id'])
            del lattrs['id']
        if 'class' in lattrs:
            # pylint: disable=expression-not-assigned
            [attr_arr.append(sv) for sv in lattrs['class'].split()]
            del lattrs['class']
        for key, value in lattrs.items():
            use_sep = False
            for content in (' ', ':', '-', ';'):
                if value.find(content) > -1:
                    use_sep = True
                    break
            if use_sep:
                attr_arr.append("%s='%s'" % (key, value))
            else:
                attr_arr.append("%s=%s" % (key, value))
        return u"[%s](\"{{%s:%s}}\")" % (sep, tag_name, " ".join(attr_arr))

    def _flush_buffer(self):    # {{{2
        if self._text_buffer:
            self._write(''.join(self._text_buffer))

    def _is_empty(self, value):    # {{{2
        # pylint: disable=no-self-use
        # too difficult to move from object
        if not value:
            return True
        svalue = value.strip(' \t\n\r')
        if not svalue:
            return True
        return False

    def _known_div(self, div_tag):    # {{{2
        # pylint: disable=no-self-use
        # too difficult to move from object
        for child in div_tag.contents:
            if isinstance(child, (NavigableString, Comment)):
                continue
            if isinstance(child, Tag) and child.name in _KNOWN_ELEMENTS:
                continue
            return False
        return True

    def _proc(self, tag):    # {{{2
        if isinstance(tag, Tag):
            self._process_tag(tag)
        elif isinstance(tag, NavigableString) and not self._is_empty(tag):
            self._text_buffer.append(tag.strip('\n\r'))

    def _process(self, element):    # {{{2
        if isinstance(element, Comment):
            self._comment(element)
            return
        if element.string and not self._is_empty(element.string):
            txt = element.string
            if not _is_inline(element):
                txt = txt.lstrip()
                txt = re.sub('\n+', '\n', txt, re.M)
                txt = re.sub(' +', ' ', txt)
                txt = re.sub('\n ', '\n', txt)
            self._text_buffer.append(txt)
            return
        for idx, tag in enumerate(element.contents):
            if isinstance(tag, Tag):
                self._process_tag(tag)
            elif isinstance(tag, Comment):
                self._comment(tag)
            elif isinstance(tag, NavigableString) and not self._is_empty(tag):
                txt = tag.strip('\n\r')
                if idx == 0 and not _is_inline(element):
                    self._text_buffer.append(txt.lstrip(' \t'))
                else:
                    self._text_buffer.append(txt)

    def _process_footnotes(self, tag):    # {{{2
        # pylint: disable=too-many-branches
        self._write('', sep=LF * 2)
        index = 0
        for item in tag.findAll('li'):
            buffer_ = []
            index += 1
            links = item.findAll('a')

            if links:
                links[-1].extract()

            buffer_.append("[^%s]: " % index)

            children = []
            for child in item.contents:
                if isinstance(child, NavigableString):
                    if not self._is_empty(child):
                        children.append(child)
                elif isinstance(child, Tag):
                    children.append(child)
            if (len(children) == 1
                    and isinstance(children[0], Tag)
                    and children[0].name == 'p'):
                children = children[0].contents
            for child in children:
                if isinstance(child, NavigableString):
                    buffer_.append(child)
                elif isinstance(child, Tag):
                    if (child.name in ('a', 'b', 'strong', 'code', 'del',
                                       'em', 'i', 'img', 'tt')):
                        self._process_tag(child)
                        buffer_.extend(self._text_buffer)
                        self._text_buffer = []
                    else:
                        buffer_.append(unicode(child))  # noqa: F821

            footnote = u''.join(buffer_).strip(' \n\r')
            if footnote.endswith('()'):
                footnote = footnote[:-2]

            self._write(footnote, sep=LF*2)

    def _process_tag(self, tag):    # {{{2
        _tag_func = self._elements.get(tag.name)

        if _tag_func:
            _tag_func(tag)
            return

        # even if they contain information there's no way to convert it
        if tag.name in _SKIP_ELEMENTS:
            return

        # go to the children
        if tag.name in _IGNORE_ELEMENTS:
            self._process(tag)
            return

        if self._inside_block:
            self._text_buffer.append(unicode(tag))  # noqa: F821
        else:
            self._write(unicode(tag), sep=LF * 2)  # noqa: F821

    def _push_attributes(self, tag=None, tagname=None, attrs=None):    # {{{2
        attr_dict = None
        if tag:
            tagname = tag.name
            if tag.attrs:
                attr_dict = dict(tag.attrs)
            elif attrs:
                attr_dict = attrs
            else:
                attr_dict = {}
        if tagname and attrs:
            attr_dict = attrs
        if attr_dict:
            self._attributes_stack.append((tagname, attr_dict))

    def _remove_attrs(self, attrs, *keys):    # {{{2
        # remove attributes
        # pylint: disable=no-self-use
        # too difficult to move from object
        if not attrs:
            return
        for k in keys:
            try:
                del attrs[k]
            except KeyError:
                pass

    def _set_processors(self):    # {{{2
        self._elements = {
            'a': self._tag_a,
            'b': self._tag_strong,
            'strong': self._tag_strong,
            'blockquote': self._tag_blockquote,
            'br': self._tag_br,
            'code': self._tag_code,
            'tt': self._tag_code,
            'center': self._tag_center,
            'div': self._tag_div,
            'em': self._tag_em,
            'i': self._tag_em,
            'h1': self._tag_h,
            'h2': self._tag_h,
            'h3': self._tag_h,
            'h4': self._tag_h,
            'h5': self._tag_h,
            'h6': self._tag_h,
            'hr': self._tag_hr,
            'img': self._tag_img,
            'li': self._tag_li,
            'ol': self._tag_list,
            'ul': self._tag_list,
            'p': self._tag_p,
            'pre': self._tag_pre,
        }
        if self._options['footnotes']:
            self._elements['sup'] = self._tag_sup
        if self._options['critic_markup']:
            self._elements['ins'] = self._tag_ins
            self._elements['del'] = self._tag_del
            self._elements['u'] = self._tag_u
        if self._options['def_list']:
            self._elements['dl'] = self._tag_dl
            self._elements['dt'] = self._tag_dt
            self._elements['dd'] = self._tag_dd

    def _set_output_path(self):    # {{{2
        # pylint: disable=unused-variable
        app = wx.App()  # noqa: F841
        frame = wx.Frame(None, -1, 'win.py')
        frame.SetDimensions(0, 0, 200, 50)
        message = "Save as..."
        glob = "Markdown files (*.md)|*.md"
        with wx.FileDialog(None, message,
                           self._download_dir, self._download_file, glob,
                           wx.FD_SAVE) as file_dialog:
            if file_dialog.ShowModal() == wx.ID_CANCEL:
                self._abort('No download file path set')
            self._outpath = file_dialog.GetPath()

    def _send_command(self, command):    # {{{2

        # cannot open pipe in append mode ('a') because it
        # causes the userscript to exit with status 1

        fifo = open(self._fifo, 'w')
        fifo.write(command)
        fifo.close()

    def _simple_attrs(self, attrs):    # {{{2
        # convert attributes to string
        # pylint: disable=no-self-use
        # too difficult to move from object
        if not attrs:
            return u""

        attr_arr = []
        lattrs = attrs.copy()
        if 'id' in lattrs:
            attr_arr.append("#%s" % lattrs['id'])
            del lattrs['id']
        if 'class' in lattrs:
            # pylint: disable=expression-not-assigned
            [attr_arr.append(sv) for sv in lattrs['class'].split()]
            del lattrs['class']

        for key, value in lattrs.items():
            use_sep = False
            for content in (' ', ':', '-', ';'):
                if value.find(content) > -1:
                    use_sep = True
                    break
            if use_sep:
                attr_arr.append("%s='%s'" % (key, value))
            else:
                attr_arr.append("%s=%s" % (key, value))
        return u"{{%s}}" % " ".join(attr_arr)

    def _tag_a(self, tag):    # {{{2
        if tag.get('href'):
            self._text_buffer.append(u'[')
            self._process(tag)
            self._text_buffer.append(u']')
            self._text_buffer.append(u'(')
            self._text_buffer.append(tag['href'])
            attrs = dict(tag.attrs) if tag.attrs else {}
            self._remove_attrs(attrs, 'href', 'title')
            attrs_str = self._simple_attrs(attrs)
            if attrs_str or tag.get('title'):
                self._text_buffer.append(u' "')
                if tag.get('title'):
                    self._text_buffer.append(tag['title'])
                    if attrs_str:
                        self._text_buffer.append(u' ')
                if attrs_str:
                    self._text_buffer.append(attrs_str)
                self._text_buffer.append(u'"')
            self._text_buffer.append(u')')
        else:
            self._text_buffer.append(unicode(tag))  # noqa: F821

    def _tag_blockquote(self, tag):    # {{{2
        # process a <BLOCKQUOTE>

        self._push_attributes(tag=tag)
        self._inside_block = True
        self._indentation_stack.append('bq')
        self._process(tag)
        self._write_block(sep=LF * 2)
        self._indentation_stack.pop()
        self._inside_block = False

    def _tag_br(self, tag):    # {{{2
        # process <BR>
        # pylint: disable=unused-argument
        self._text_buffer.append(u"  " + LF)

    def _tag_code(self, tag):    # {{{2
        # process <CODE> and <TT>
        self._text_buffer.append(u"`")
        self._text_buffer.append(tag.getText())
        self._text_buffer.append(u"`")

    def _tag_center(self, tag):    # {{{2
        # process <CENTER>
        if self._options['attrs']:
            (self._push_attributes(tagname='p',
                                   attrs={'style': 'text-align:center;'}))
        self._process(tag)
        self._write_block(sep=LF * 2)

    def _tag_dd(self, tag):    # {{{2
        self._indentation_stack.append('dd')
        self._process(tag)
        has_multi_dd = False
        next_tag = tag.nextSibling
        while next_tag:
            if isinstance(next_tag, Tag):
                if next_tag.name == 'dd':
                    has_multi_dd = True
                    break
                else:
                    break
            next_tag = next_tag.nextSibling
        if has_multi_dd:
            self._write_block(sep=LF)
        else:
            self._write_block(sep=LF * 2)
        self._indentation_stack.pop()

    def _tag_del(self, tag):    # {{{2
        if tag.string:
            self._text_buffer.append(u"{--")
            self._process(tag)
            self._text_buffer.append(u"--}")
        else:
            # this is a very hacky solution
            self._text_buffer.append(u"{--")
            for child in reversed(tag.contents):
                if isinstance(child, Tag):
                    child.append(u"--}")
                    break
                if (isinstance(child, NavigableString)
                        and not self._is_empty(child)):
                    child += u"--}"
                    break
            self._process(tag)

    def _tag_div(self, tag):    # {{{2
        # process <DIV>
        div_class = tag.get('class')
        if (self._options['footnotes']
                and div_class
                and div_class.find('footnote') > -1):
            self._inside_footnote = True
            self._flush_buffer()
            self._process_footnotes(tag)
            self._inside_footnote = False
            return

        if self._known_div(tag):
            self._inside_block = True
            self._process(tag)
            self._write_block(sep=LF * 2)
            self._inside_block = False
        else:
            self._write(unicode(tag), sep=LF * 2)  # noqa: F821

    def _tag_dl(self, tag):    # {{{2
        self._inside_block = True
        self._process(tag)
        self._write_block(sep=LF * 2)
        self._inside_block = False

    def _tag_dt(self, tag):    # {{{2
        self._process(tag)
        self._write_block(sep=LF)

    def _tag_em(self, tag):    # {{{2
        # process <EM> and <I>
        self._text_buffer.append(u"*")
        self._process(tag)
        self._text_buffer.append(u"*")

    def _tag_h(self, tag):    # {{{2
        self._push_attributes(tag=tag)
        self._inside_block = True
        self._text_buffer.append(u'#' * int(tag.name[1]) + ' ')
        self._process(tag)
        self._write_block(sep=LF * 2)
        self._inside_block = False
        self._text_buffer = []

    def _tag_hr(self, tag):    # {{{2
        # pylint: disable=unused-argument
        if not self._inside_footnote:
            self._write(LF + u'-----', sep=LF * 2)

    def _tag_img(self, tag):    # {{{2
        self._text_buffer.append(u'![')
        self._text_buffer.append(tag.get('alt') or tag.get('title') or '')
        self._text_buffer.append(u']')
        self._text_buffer.append(u'(')
        self._text_buffer.append(tag['src'])
        attrs = dict(tag.attrs) if tag.attrs else {}
        self._remove_attrs(attrs, 'src', 'title', 'alt')
        attrs_str = self._simple_attrs(attrs)
        if attrs_str or tag.get('title'):
            self._text_buffer.append(u' "')
            if tag.get('title'):
                self._text_buffer.append(tag['title'])
                if attrs_str:
                    self._text_buffer.append(u' ')
            if attrs_str:
                self._text_buffer.append(attrs_str)
            self._text_buffer.append(u'"')
        self._text_buffer.append(u')')

    def _tag_ins(self, tag):    # {{{2
        # CriticMarkup support
        if tag.string:
            self._text_buffer.append(u"{++")
            self._process(tag)
            self._text_buffer.append(u"++}")
        else:
            # this is a very hacky solution
            self._text_buffer.append(u"{++")
            for child in reversed(tag.contents):
                if isinstance(child, Tag):
                    child.append(u"++}")
                    break
                if (isinstance(child, NavigableString)
                        and not self._is_empty(child)):
                    child += u"++}"
                    break
            self._process(tag)

    def _tag_li(self, tag):    # {{{2
        # pylint: disable=too-many-branches
        # stick with original code for now
        list_item_has_block = False
        last_block_name = None
        blocks_counter = 0
        self._push_attributes(tag=tag)
        if tag.string:
            if not self._is_empty(tag.string):
                self._text_buffer.append(tag.string.strip())
            self._write_block(sep=LF)
        else:
            elements = []
            for child in tag.contents:
                if isinstance(child, Tag):
                    elements.append(child)
                elif (isinstance(child, NavigableString)
                      and not self._is_empty(child)):
                    elements.append(child)
            prev_was_text = False
            for child in elements:
                if isinstance(child, NavigableString):
                    self._text_buffer.append(child.strip())
                    prev_was_text = True
                    continue
                if isinstance(child, Tag):
                    if child.name in ('blockquote', 'dl', 'ol', 'p', 'pre',
                                      'ul', 'h1', 'h2', 'h3', 'h4', 'h5',
                                      'h6'):
                        blocks_counter += 1
                        list_item_has_block = True
                        last_block_name = child.name
                        if prev_was_text:
                            prev_was_text = False
                            self._write_block(sep=LF * 2)
                        else:
                            self._write_block(sep=LF)
                    self._process_tag(child)

        if list_item_has_block:
            trim_newlines = False
            #        if last_block_name == 'p' and blocks_counter < 3:
            #          trim_newlines = True
            if last_block_name in ('ul', 'ol') and blocks_counter < 2:
                trim_newlines = True
            if trim_newlines and self._output[-2:] == LF * 2:
                self._output = self._output[:-1]
        if self._indentation_stack[-1] in ('cul', 'col'):
            self._indentation_stack[-1] = self._indentation_stack[-1][1:]

    def _tag_list(self, tag):    # {{{2
        self._list_level += 1
        self._push_attributes(tag=tag)
        self._indentation_stack.append(tag.name)
        self._process(tag)
        self._indentation_stack.pop()
        self._list_level -= 1
        self._write('', sep=LF)
        if self._list_level == 0:
            self._write('', sep=LF)

    def _tag_p(self, tag):    # {{{2
        # must finish it by 2 * os.linesep
        self._push_attributes(tag=tag)
        self._inside_block = True
        self._process(tag)
        self._write_block(sep=LF * 2)
        self._inside_block = False

    def _tag_pre(self, tag):    # {{{2
        self._push_attributes(tag=tag)
        self._inside_block = True
        self._indentation_stack.append('pre')
        _prefix = u''
        _suffix = u''
        if self._options['fenced_code'] == 'github':
            _prefix = u"```"
            attrs = dict(tag.attrs)
            if 'class' in attrs:
                _prefix += attrs['class'].strip()
            _prefix += LF
            _suffix = LF + u"```"
        elif self._options['fenced_code'] == 'php':
            _prefix = u"~~~"
            attrs = dict(tag.attrs)
            if 'class' in attrs:
                _prefix += attrs['class'].strip()
            _prefix += LF
            _suffix = LF + u"~~~"

        if tag.string:
            (self._text_buffer.append(_prefix +
                                      tag.renderContents().strip(' \t\n\r') +
                                      _suffix))
        else:
            elements = ([child for child in tag.contents
                         if isinstance(child, Tag)])
            if len(elements) == 1 and elements[0].name == 'code':
                (self._text_buffer.append(
                    _prefix +
                    elements[0].renderContents().strip(' \t\n\r') +
                    _suffix))
            else:
                (self._text_buffer.append(_prefix +
                                          tag.renderContents().strip(
                                              ' \t\n\r') + _suffix))
        self._write_block(sep=LF*2)
        self._indentation_stack.pop()
        self._inside_block = False

    def _tag_strong(self, tag):    # {{{2
        # process <B> and <STRONG>
        self._text_buffer.append(u"**")
        self._process(tag)
        self._text_buffer.append(u"**")

    def _tag_sup(self, tag):    # {{{2
        _id = tag.get('id')
        if not _id:
            self._write(unicode(tag))  # noqa: F821
            return
        if _FOOTNOTE_REF_RE.match(_id):
            self._footnote_ref += 1
            self._text_buffer.append(u'[^%s]' % self._footnote_ref)
        else:
            self._write(unicode(tag))  # noqa: F821

    def _tag_u(self, tag):    # {{{2
        self._text_buffer.append(u"{==")
        self._process(tag)
        self._text_buffer.append(u"==}{>><<}")

    def _write(self, value, sep=u''):    # {{{2
        if (value and value[0] == LF and self._output
                and self._output[-1] == LF):
            value = value[len(LF):]
        self._output += _entity2ascii(value) + sep

    def _write_block(self, sep=u''):    # {{{2
        # pylint: disable=too-many-branches
        if not self._attributes_stack and not self._text_buffer:
            return
        indentation = u''
        extra_indentation = u''
        for idx in range(len(self._indentation_stack)):
            indent_type = self._indentation_stack[idx]
            if indent_type == 'bq':
                indentation += u'> '
                extra_indentation += u'> '
            elif indent_type == 'pre':
                if self._options['fenced_code'] == 'default':
                    indentation += u' ' * 4
                    extra_indentation += u' ' * 4
                elif self._options['fenced_code'] == 'github':
                    pass
                elif self._options['fenced_code'] == 'php':
                    pass
            elif indent_type == 'ol':
                indentation += u'1.  '
                extra_indentation += u' ' * 4
                self._indentation_stack[idx] = 'col'
            elif indent_type == 'ul':
                indentation += u'*   '
                extra_indentation += (u' ' * 4)
                self._indentation_stack[idx] = 'cul'
            elif indent_type == 'cul':
                indentation += (u' ' * 4)
                extra_indentation += (u' ' * 4)
            elif indent_type == 'col':
                indentation += (u' ' * 4)
                extra_indentation += (u' ' * 4)
            elif indent_type == 'dd':
                indentation += (u':   ')
                extra_indentation += (u' ' * 4)

        attributes = []
        if self._options['attrs']:
            for tagname, attrs in self._attributes_stack:
                attributes.append(self._elem_attrs(tagname, attrs, '..'))

        self._attributes_stack = []

        txt = indentation
        txt += ''.join(self._text_buffer)
        txt = txt.replace(u'\r\n', LF)
        if sep and txt.endswith(LF):
            txt = txt.rstrip(LF)
        if attributes:
            txt += u' ' + u' '.join(attributes)
        txt = txt.replace(u'\n', LF + extra_indentation)

        self._write(txt, sep)
        self._text_buffer = []


def _entity2ascii(val):    # {{{1
    for ent, asc in _ENTITY_DICT.items():
        val = val.replace(ent, asc)
    return val


_ENTITY_DICT = {
    '&#8212;': '--',
    '&#8216;': "'",
    '&#8217;': "'",
    '&#8220;': '"',
    '&#8221;': '"',
    '&#8230;': '...',
    u'…': '...',
}


def _is_inline(element):    # {{{1
    if (isinstance(element, (NavigableString, Declaration,
                             ProcessingInstruction, Comment))):
        return False
    if (isinstance(element, Tag)
            and (element.name in ('blockquote', 'center', 'dl', 'dt', 'dd',
                                  'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                                  'li', 'ol', 'ul', 'p'))):
        return False
    return True


_FOOTNOTE_REF_RE = re.compile('fnr(ef)*')


def usage():    # {{{1

    """ print help and process arguments """

    parser = (argparse.ArgumentParser(
        description='Qutebrowser userscript to save current page as markdown'))
    parser.parse_args()


def main():    # {{{1

    """ script execution starts here """

    usage()
    save_md = SaveMarkdown()
    save_md.generate_output()
    save_md.write_output()
    save_md.success()


if __name__ == '__main__':
    main()

# vim:fdm=marker:
