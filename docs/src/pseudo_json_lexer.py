from pygments.lexer import RegexLexer, bygroups
from pygments.token import Text, Number, String, Punctuation, Keyword, Name, Comment

class PseudoJsonLexer(RegexLexer):
    """
    Advanced pseudo JSON lexer for API docs.
    - Keys -> Name.Tag
    - String values -> String (except "...")
    - Placeholders -> Name.Variable
    - Numbers -> Number
    - Booleans/null -> Keyword
    - Comments starting with # -> Comment
    - Ignores standalone ... anywhere
    """
    name = 'PseudoJSON'
    aliases = ['pseudojson']
    filenames = ['*.pseudojson']

    tokens = {
        'root': [
            (r'\s+', Text),
            # comments (even inline)
            (r'#.*$', Comment),
            # punctuation
            (r'[{}\[\],:]', Punctuation),
            # booleans/null
            (r'\b(true|false|null)\b', Keyword),
            # numbers
            (r'\d+(\.\d+)?', Number),
            # key-value pair: key as Name.Tag
            (r'(")([^"]+)(")(\s*)(:)', bygroups(String, Name.Tag, String, Text, Punctuation)),
            # placeholder values like <...>
            (r'<[^>]+>', Name.Variable),
            # string values, skip "..."
            (r'"(?!\.\.\.)(\\.|[^"\\])*"', String),
            # ignore literal "..."
            (r'"\.{3}"', Text),
            # ignore standalone ... (inside arrays or anywhere)
            (r'\.\.\.', Text),
        ]
    }
