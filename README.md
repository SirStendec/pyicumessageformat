# pyicumessageformat

An unopinionated library for parsing ICU MessageFormat messages into both
ASTs and, optionally, token lists.

This library is mainly a re-implementation of the JavaScript library
[format-message-parse](https://www.npmjs.com/package/format-message-parse)
with a few extra configuration flags.

[format-message-parse](https://www.npmjs.com/package/format-message-parse)
and `pyicumessageformat` are both licensed MIT.


## Parser Options

```python
from pyicumessageformat import Parser

# The following are the default values for the various available
# settings for the Parser.
parser = Parser({
    # Known types that include sub-messages.
    'submessage_types': ['plural', 'selectordinal', 'select'],

    # Sub-message types that are numeric and support "#" in sub-messages.
    'subnumeric_types': ['plural', 'selectordinal'],

    # Whether or not to parse simple XML-style tags. When this is False,
    # XML-style tags will be treated as plain text.
    'allow_tags': False,

    # The type that should be set for tags. This should be set to a
    # unique value that will not overlap with any placeholder types.
    'tag_type': 'tag',

    # Whether or not to parse sub-messages for unknown types. When this
    # is set to False and an unknown type has sub-messages, a syntax
    # error will be raised.
    'loose_submessages': False,

    # Whether or not spaces should be allowed in format strings.
    'allow_format_spaces': True,

    # Whether or not the parser should require known types with
    # sub-messages to have an "other" selector.
    # See "Require Other" below in README for more details.
    'require_other': True
})
```

### Require Other

The `require_other` setting has a few valid possible values.

* `True`: All known sub-message types are required to have an "other"
    selector.
* `False`: No types are required to have an "other" selector.
* `"subnumeric"`: All known numeric sub-message types are required to have an
    "other" selector.
* `"all"`: All types, including unknown types, with sub-messages are required
    to have an "other" selector.

Additionally, `require_other` can be a list of types. In that event, only those
types will be required to have an "other" selector.


## Parsing

The Parser has a single method that is intended to be called externally:

### `parse(input: str, tokens?: list) -> AST`

Simply pass in a string, and get an AST back:

```python
>>> ast = parser.parse('''Hello, <b>{firstName}</b>! You have {messages, plural,
    =0 {no messages}
    =1 {one message}
    other {# messages}
} and you're {completion, number, percentage} done.''')
>>> ast
[
    'Hello, ',
    {
        'name': 'b',
        'type': 'tag',
        'contents': [
            {
                'name': 'firstName'
            }
        ]
    },
    '! You have ',
    {
        'name': 'messages',
        'type': 'plural',
        'options': {
            '=0': ['no messages'],
            '=1': ['one message'],
            'other': [
                {
                    'name': 'messages',
                    'type': 'number'
                },
                ' messages'
            ]
        }
    },
    " and you're ",
    {
        'name': 'completion',
        'type': 'number',
        'format': 'percentage'
    },
    ' done.'
]
```

If there is an error in the message, `parse(...)` will raise a
`SyntaxError`:

```python
>>> parser.parse('Hello, {name{!')
SyntaxError: Expected , or } at position 12 but found {
```

If you include an empty list for `tokens`, you can also get back your
input in a tokenized format. Please note that tokenization stops
when an error is encountered:

```python
>>> tokens = []
>>> parse('Hello, {firstName}! You are {age, number} years old.', tokens)
>>> tokens
[
    {'type': 'text', 'text': 'Hello, '},
    {'type': 'syntax', 'text': '{'},
    {'type': 'name', 'text': 'firstName'},
    {'type': 'syntax', 'text': '}'},
    {'type': 'text', 'text': '! You are '},
    {'type': 'syntax', 'text': '{'},
    {'type': 'name', 'text': 'age'},
    {'type': 'syntax', 'text': ','},
    {'type': 'space', 'text': ' '},
    {'type': 'type', 'text': 'number'},
    {'type': 'syntax', 'text': '}'},
    {'type': 'text', ' years old.'}
]

>>> tokens = []
>>> parser.parse('Hello, {name{!', tokens)
SyntaxError: Expected , or } at position 12 but found {
>>> tokens
[
    {'type': 'text', 'text': 'Hello, '},
    {'type': 'syntax', 'text': '{'},
    {'type': 'name', 'text': 'name'}
]
```

## AST Format

```typescript
type AST = Node[];
type Node = string | Placeholder;

type Placeholder = Tag | Variable;

type Tag = {
    name: string;
    type: 'tag';
    contents?: AST;
};

type Variable = {
    name: string;
    type?: string;
    offset?: number;
    format?: string;
    options?: Submessages;
}

type Submessages = {
    [selector: string]: AST;
};
```
