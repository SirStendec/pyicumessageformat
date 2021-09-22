from . import constants

SEP_OR_CLOSE = '{} or {}'.format(constants.CHAR_SEP, constants.CHAR_CLOSE)


def appendToken(context, type, text):
    if 'tokens' in context:
        context['tokens'].append({
            'type': type,
            'text': text
        })


def isAlpha(char: str) -> bool:
    if not char:
        return False
    code = ord(char)
    return (code >= 97 and code <= 122) or (code >= 65 and code <= 90)


def isDigit(char: str) -> bool:
    if not char:
        return False
    code = ord(char)
    return code >= 0x30 and code <= 0x39


def isSpace(char: str) -> bool:
    if not char:
        return False
    code = ord(char)
    return code in constants.SPACE_CHARS or \
        (code >= 0x09 and code <= 0x0D) or \
        (code >= 0x2000 and code <= 0x200D)


def skipSpace(context, ret = False):
    msg = context['msg']
    length = context['length']
    start = context['i']
    if start >= length:
        return ''

    while context['i'] < length and isSpace(msg[context['i']]):
        context['i'] += 1

    if ret:
        return msg[start:context['i']]
    elif start < context['i']:
        appendToken(context, 'space', msg[start:context['i']])


def recursion(context):
    raise SyntaxError("Too much recursion at position {}".format(context['i']))


def unexpected(char, index = None):
    if isinstance(char, dict):
        index = char['i']
        return unexpected(char['msg'][index] if index < char['length'] else '<EOF>', index)

    return SyntaxError('Unexpected "{}" at position {}'.format(char, index))


def expected(char, found, index = None):
    if isinstance(found, dict):
        index = found['i']
        return expected(char, found['msg'][index] if index < found['length'] else '<EOF>', index)

    return SyntaxError('Expected {} at position {} but found "{}"'.format(char, index, found if found else '<EOF>'))


class Parser:
    def __init__(self, options = None):
        self.options = {
            'subnumeric_types': ['plural', 'selectordinal'],
            'submessage_types': ['plural', 'selectordinal', 'select'],
            'maximum_depth': 50,
            'allow_tags': False,
            'strict_tags': False,
            'tag_prefix': None,
            'tag_type': 'tag',
            'include_indices': False,
            'loose_submessages': False,
            'allow_format_spaces': True,
            'require_other': True
        }

        if isinstance(options, dict):
            self.options.update(options)


    def parse(self, input: str, tokens: list = None):
        if not isinstance(input, str):
            raise TypeError("input must be string")

        context = {
            'msg': input,
            'length': len(input),
            'i': 0,
            'depth': 0
        }

        if tokens is not None:
            if not isinstance(tokens, list):
                raise TypeError("tokens must be list or None")
            context['tokens'] = tokens

        try:
            return self._parseAST(context, None)
        except RecursionError:
            # Any RecursionError is also a syntax error
            # because there is no reasonable reason to have
            # such a deeply nested ICU MessageFormat string.
            # Re-throw it as a SyntaxError as though we hit
            # the maximum allowed depth.
            raise recursion(context)
        except IndexError:
            # Any IndexErrors we may encounter are actually
            # syntax errors as we try to read parts of the
            # string that don't exist. Ideally there would
            # not be any IndexErrors, and we'd always catch
            # the issue and return a SyntaxError, but just
            # in case.
            raise SyntaxError

    def _parseAST(self, context, parent):
        msg = context['msg']
        length = context['length']
        start = context['i']
        out = []

        text = self._parseText(context, parent)
        if text:
            out.append(text)
            appendToken(context, 'text', msg[start:context['i']])

        while context['i'] < length:
            i = context['i']
            char = msg[i]
            if char == constants.CHAR_CLOSE:
                if not parent:
                    raise unexpected(context)
                break

            if parent and self.options['allow_tags'] and msg[i:i+len(constants.TAG_END)] == constants.TAG_END and self._canReadTag(context, parent, True):
                break

            out.append(self._parsePlaceholder(context, parent))
            start = context['i']
            text = self._parseText(context, parent)
            if text:
                out.append(text)
                appendToken(context, 'text', msg[start:context['i']])

        return out


    def _canReadTag(self, context, parent, require_closing = False):
        msg = context['msg']
        length = context['length']
        start = context['i']
        current = context['i']
        if not self.options['allow_tags']:
            return False

        char = msg[current] if current < length else None
        if char != constants.CHAR_TAG_OPEN:
            return False

        if self.options['strict_tags'] and not require_closing:
            return True

        current += 1
        char = msg[current] if current < length else None

        # We're trying to close a tag.
        if char == constants.CHAR_TAG_CLOSE:
            if self.options['strict_tags']:
                return True

            current += 1
            char = msg[current] if current < length else None

        elif require_closing:
            return False

        # Do we have a tag prefix?
        if self.options['tag_prefix']:
            return self.options['tag_prefix'] == msg[current:current + len(self.options['tag_prefix'])]

        elif isAlpha(char):
            return True

        return False


    def _parseText(self, context, parent, is_arg_style = False):
        msg = context['msg']
        length = context['length']
        start = context['i']
        is_hash_special = parent and parent['type'] in self.options['subnumeric_types']
        is_tag_special = self.options['allow_tags']
        allow_arg_spaces = self.options['allow_format_spaces']

        text = ''
        trailing_space = 0

        while context['i'] < length:
            char = msg[context['i']]
            is_space = isSpace(char)

            if char in constants.VAR_CHARS or \
                    (is_hash_special and char == constants.CHAR_HASH) or \
                    (is_tag_special and char == constants.CHAR_TAG_OPEN and self._canReadTag(context, parent)) or \
                    (is_arg_style and not allow_arg_spaces and is_space):
                break

            if is_space:
                trailing_space += 1
            else:
                trailing_space = 0

            if char == constants.CHAR_ESCAPE:
                context['i'] += 1
                if context['i'] < length:
                    char = msg[context['i']]
                    if char == constants.CHAR_ESCAPE:
                        # Escaped Escape
                        text += char
                        context['i'] += 1

                    elif char in constants.VAR_CHARS or \
                            (is_hash_special and char == constants.CHAR_HASH) or \
                            (is_tag_special and char == constants.CHAR_TAG_OPEN) or \
                            is_arg_style:
                        text += char
                        context['i'] += 1
                        while context['i'] < length:
                            nxt = msg[context['i']]
                            if nxt == constants.CHAR_ESCAPE:
                                context['i'] += 1
                                if context['i'] < length and msg[context['i']] == constants.CHAR_ESCAPE:
                                    text += nxt
                                else:
                                    break
                            else:
                                text += nxt

                            context['i'] += 1

                    else:
                        context['i'] += 1
                        text += constants.CHAR_ESCAPE + char
                else:
                    text += char
            else:
                text += char
                context['i'] += 1

        # Trim trailing spaces from arg styles.
        if is_arg_style and trailing_space:
            trimmed = len(text) - trailing_space
            if trimmed <= 0:
                context['i'] = start
                return ''
            else:
                context['i'] -= trailing_space
                return text[0: trimmed]

        return text


    def _tokenIndices(self, token, start, end):
        if self.options['include_indices']:
            token['start'] = start
            token['end'] = end
        return token


    def _parsePlaceholder(self, context, parent):
        msg = context['msg']
        length = context['length']
        is_hash_special = parent and parent['type'] in self.options['subnumeric_types']

        start_idx = context['i']
        char = msg[start_idx] if start_idx < length else None
        if is_hash_special and char == constants.CHAR_HASH:
            appendToken(context, 'hash', char)
            context['i'] += 1
            return self._tokenIndices({
                'type': 'number',
                'name': parent['name'],
                'hash': True
            }, start_idx, context['i'])

        tag = self._parseTag(context, parent)
        if tag:
            return tag

        # This should never happen, but let's be sure.
        if char != constants.CHAR_OPEN:
            raise expected(constants.CHAR_OPEN, context)

        appendToken(context, 'syntax', char)

        context['i'] += 1
        skipSpace(context)

        name = self._parseName(context)
        if not name:
            raise expected('placeholder name', context)

        appendToken(context, 'name', name)
        token = {
            'name': name
        }

        skipSpace(context)
        char = msg[context['i']] if context['i'] < length else None

        if char == constants.CHAR_CLOSE:
            appendToken(context, 'syntax', char)
            context['i'] += 1
            return self._tokenIndices(token, start_idx, context['i'])

        if char != constants.CHAR_SEP:
            raise expected(SEP_OR_CLOSE, context)

        appendToken(context, 'syntax', char)
        context['i'] += 1

        skipSpace(context)

        ttype = self._parseName(context)
        if not ttype:
            raise expected('placeholder type', context)

        appendToken(context, 'type', ttype)
        token['type'] = ttype

        skipSpace(context)
        char = msg[context['i']] if context['i'] < length else None
        if char == constants.CHAR_CLOSE:
            appendToken(context, 'syntax', char)
            if ttype in self.options['submessage_types']:
                raise expected('{} sub-messages'.format(ttype), context)

            context['i'] += 1
            return self._tokenIndices(token, start_idx, context['i'])

        if char != constants.CHAR_SEP:
            raise expected(SEP_OR_CLOSE, context)

        appendToken(context, 'syntax', char)
        context['i'] += 1
        skipSpace(context)

        if ttype in self.options['subnumeric_types']:
            offset = self._parseOffset(context)
            token['offset'] = offset if offset else 0
            if offset:
                skipSpace(context)

        if ttype in self.options['submessage_types']:
            messages = self._parseSubmessages(context, token)
            if not messages:
                raise expected('{} sub-messages'.format(ttype), context)
            token['options'] = messages

        else:
            start = context['i']
            fmt = self._parseText(context, token, True)
            if not fmt:
                raise expected('placeholder style', context)

            end = context['i']
            spaces = skipSpace(context, True)

            if self.options['loose_submessages'] and msg[context['i']] == constants.CHAR_OPEN:
                # Instead of a format, we should handle submessages.
                # Rewind and try again.
                context['i'] = start
                messages = self._parseSubmessages(context, token)
                if not messages:
                    raise expected('{} sub-messages'.format(ttype), context)
                token['options'] = messages

            else:
                token['format'] = fmt
                appendToken(context, 'style', msg[start:end])
                if spaces:
                    appendToken(context, 'space', spaces)

        skipSpace(context)
        char = msg[context['i']] if context['i'] < length else None
        if char != constants.CHAR_CLOSE:
            raise expected(constants.CHAR_CLOSE, context)

        appendToken(context, 'syntax', char)
        context['i'] += 1
        return self._tokenIndices(token, start_idx, context['i'])


    def _parseTag(self, context, parent):
        if not self.options['allow_tags']:
            return None

        if not self._canReadTag(context, parent):
            return None

        msg = context['msg']
        length = context['length']
        i = context['i']
        start_idx = i
        char = msg[i] if i < length else None

        if char != constants.CHAR_TAG_OPEN:
            return None

        if msg[i:i + len(constants.TAG_END)] == constants.TAG_END:
            raise unexpected(constants.TAG_END, i)

        context['i'] += 1

        name = self._parseName(context, True)
        if not name:
            if not self.options['strict_tags']:
                context['i'] = start_idx
                return

            raise expected('tag name', context)

        appendToken(context, 'syntax', char)

        token = {
            'type': self.options['tag_type'],
            'name': name
        }
        appendToken(context, 'name', name)
        skipSpace(context)

        i = context['i']
        if i < length and msg[i:i + len(constants.TAG_CLOSING)] == constants.TAG_CLOSING:
            appendToken(context, 'syntax', constants.TAG_CLOSING)
            context['i'] += len(constants.TAG_CLOSING)
            return self._tokenIndices(token, start_idx, context['i'])

        char = msg[i] if i < length else None
        if char != constants.CHAR_TAG_END:
            raise expected(constants.CHAR_TAG_END + ' or ' + constants.TAG_CLOSING, context)

        appendToken(context, 'syntax', char)
        context['i'] += 1

        children = self._parseAST(context, token)
        if children:
            token['contents'] = children
        end = context['i']

        if end < length and msg[end:end + len(constants.TAG_END)] != constants.TAG_END:
            raise expected(constants.TAG_END, context)

        appendToken(context, 'syntax', constants.TAG_END)
        context['i'] += len(constants.TAG_END)

        close_name = self._parseName(context, True)
        if close_name:
            appendToken(context, 'name', close_name)
        if close_name != name:
            raise expected(constants.TAG_END + name + constants.CHAR_TAG_END, msg[end] if end < length else '<EOF>', end)

        skipSpace(context)
        char = msg[context['i']] if context['i'] < length else None
        if char != constants.CHAR_TAG_END:
            raise expected(constants.CHAR_TAG_END, context)

        appendToken(context, 'syntax', char)
        context['i'] += 1
        return self._tokenIndices(token, start_idx, context['i'])


    def _parseName(self, context, is_tag = False):
        msg = context['msg']
        length = context['length']
        name = ''

        while context['i'] < length:
            char = msg[context['i']]
            if char in constants.VAR_CHARS or char == constants.CHAR_SEP or \
                    char == constants.CHAR_HASH or char == constants.CHAR_ESCAPE or \
                    isSpace(char) or (is_tag and char in constants.TAG_CHARS):
                break

            name += char
            context['i'] += 1

        return name


    def _parseOffset(self, context):
        msg = context['msg']
        length = context['length']
        start = context['i']

        if start >= length or msg[start:start + len(constants.OFFSET)] != constants.OFFSET:
            return 0

        appendToken(context, 'offset', constants.OFFSET)
        context['i'] += len(constants.OFFSET)
        skipSpace(context)

        start = context['i']
        while context['i'] < length and (isDigit(msg[context['i']]) or (context['i'] == start and msg[context['i']] == '-')):
            context['i'] += 1

        if start == context['i']:
            raise expected('offset number', context)

        offset = msg[start:context['i']]
        appendToken(context, 'number', offset)
        return int(offset, 10)


    def _parseSubmessages(self, context, parent):
        msg = context['msg']
        length = context['length']
        options = {}

        context['depth'] += 1

        while context['i'] < length and msg[context['i']] != constants.CHAR_CLOSE:
            selector = self._parseName(context)
            if not selector:
                raise expected('sub-message selector', context)
            appendToken(context, 'selector', selector)
            skipSpace(context)

            options[selector] = self._parseSubmessage(context, parent)
            skipSpace(context)

        context['depth'] -= 1

        if not options:
            return None

        req = self.options['require_other']
        ttype = parent['type'] if parent else None
        if req == 'all':
            req = True
        elif req == 'subnumeric':
            req = self.options['subnumeric_types']
        elif req and not isinstance(req, list):
            req = self.options['submessage_types']
        if isinstance(req, list):
            req = ttype in req

        if req and not 'other' in options:
            raise expected('{} sub-message other'.format(ttype), context)

        return options


    def _parseSubmessage(self, context, parent):
        if context['depth'] >= self.options['maximum_depth']:
            raise recursion(context)

        msg = context['msg']
        length = context['length']
        if context['i'] >= length or msg[context['i']] != constants.CHAR_OPEN:
            raise expected(constants.CHAR_OPEN, context)

        appendToken(context, 'syntax', constants.CHAR_OPEN)
        context['i'] += 1

        message = self._parseAST(context, parent)

        char = msg[context['i']] if context['i'] < length else None
        if char != constants.CHAR_CLOSE:
            raise expected(constants.CHAR_CLOSE, context)

        appendToken(context, 'syntax', constants.CHAR_CLOSE)
        context['i'] += 1

        return message

