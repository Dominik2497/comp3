from parsers.common import *

type Json = str | int | dict[str, Json]

def ruleJson(toks: TokenStream) -> Json:
    """
    Parses a JSON object, a JSON string, or a JSON number.
    """
    token = toks.lookahead()
    if token.type == 'STRING':
        token = toks.ensureNext('STRING')
        return token.value.strip('"')
    elif token.type == 'INT':
        token = toks.ensureNext('INT')
        return int(token.value)
    elif token.type == 'LBRACE':
        return ruleEntryList(toks)
    else:
        raise ParseError(f"Unexpected token: {token.type}")


def ruleEntryList(toks: TokenStream) -> dict[str, Json]:
    """
    Parses a JSON object.
    """
    entries: dict[str, Json] = {}
    toks.ensureNext('LBRACE')
    while toks.lookahead().type != 'RBRACE':
        token = toks.ensureNext('STRING')
        key = token.value.strip('"')
        toks.ensureNext('COLON')
        value = ruleJson(toks)
        entries[key] = value
        if toks.lookahead().type == 'COMMA':
            toks.ensureNext('COMMA')
    toks.ensureNext('RBRACE')
    return entries

def parse(code: str) -> Json:
    parser = mkLexer("./src/parsers/tinyJson/tinyJson_grammar.lark")
    tokens = list(parser.lex(code))
    log.info(f'Tokens: {tokens}')
    toks = TokenStream(tokens)
    res = ruleJson(toks)
    toks.ensureEof(code)
    return res