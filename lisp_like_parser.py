"""
copied from here:
https://github.com/DerekHarter/python-lisp-parser
"""

import re

def tokenize(txt):
    """Tokenize a Lisp-like program
    
    Break up a program of ascii text on tokens and return a list of the tokens.  This function
    considers any sequence of whitespace and the ( and ) as the only valid delimeters between
    tokens, which should be good enough for now.  We use Python re library to split up based on our
    small list of delimiters.
    
    Parameters
    -----------
    txt : string
        An ascii string of lisp text to be tokenized
    
    Returns
    -------
    tokens : list
        A list of the recognized tokens in the text
    """
    # split into tokens, use whitespace or the ( or ) character as delimeters
    # the following usage of re.split also returns the delimiters that were matched
    tokens = re.split('(\s+|\(|\))', txt)
    
    # the previous re returns all delimiters, including string of whitespace and empty matches.
    # we remove all empty or whitespace only matches, which leaves only valid tokens
    return [t for t in tokens if len(t) and not t.isspace()]


def parse(txt):
    """Parse a Lisp-like program
    
    Parse a program/string of Lisp-like ascii text.  This function is an interface to the
    main recursive parsing routines.  This function expects a raw python string of ascii
    text.  It first attempts to tokenize the string using blank space and the '(' and ')'
    characters as delimiters.  Given this list of tokens, it then attempts to parse the
    list into an abstract syntax tree.  This function users helper functions to do the
    actual tokenization and parsing tasks.  This function expects a correctly formatted
    lisp program, and it checks that the resulting AST is well formatted and that no tokens
    are left over after the parse.
    
    Parameters
    ----------
    txt : string
        An ascii string of lisp text to be parsed
    
    Returns
    -------
    ast : list (of python lists)
        An abstract syntax tree, the result of parsing the Lisp-like code into operator/operand
        lists, ready for interpretation.
    """
    # tokenize the text
    tokens = tokenize(txt)
    
    # attempt to parse the tokens
    ast, tokens = parse_list(tokens)
    
    # check if all tokens consumed
    if len(tokens) > 0:
        raise SyntaxError("(parse) Error: not all tokens consumed <%s>" % str(tokens))
        
    # return the result
    return ast

    
def parse_list(tokens):
    """Parse a List
    
    Consume a (operator operand1 operand2 operand3 ...) expression.  Syntatically
    the opening '(' is always followed by an operator, and then a list of at least 1 or
    up to many operands.  This function consumes the opening '(' and the operator and
    then calls another function to get the list of operands.  When the operands are
    gathered, this funciton expects and consumes the closing ')'.  The resulting 
    parse is put into a list, and the list and any remaining tokens are returned by
    this function.
    
    Parameters
    ----------
    tokens : list
        A python list of valid tokens.  This function expects the first token to be the '('
        keyword, and the second token will be an operator.
        
    Returns
    -------
    ast : list (of python lists)
        Return the resulting abstract syntax tree as a list of lists
    tokens : list of strings
        Also any remaining tokens after parsing the current list and operands are returned
        (to be used for further parsing).
    """
    # expect '(' always as first token for this function
    if len(tokens) == 0 or tokens[0] != '(':
        raise SyntaxError("(parse_list) Error: expected '(' token, found <%s>" % str(tokens))
    first = tokens.pop(0) # consume the opening '('

    # consume the operator and all operands
    operator = tokens.pop(0) # operator always after opening ( syntatically
    operands, tokens = parse_operands(tokens)
    ast = [operator]
    ast.extend(operands)
    #if len(operands) == 1:
    #    ast = {operator:operands[0]}    
    #else:
    #    ast = {operator:operands}
    # consume the matching ')'
    if len(tokens) == 0 or tokens[0] != ')':
        raise SyntaxError("(parse_list) Error: expected ')' token, found <%s>: " % str(tokens))
    first = tokens.pop(0) 
        
    return ast, tokens


def parse_operands(tokens):
    """Consume a sequence of operands
    
    We consume all of the operands of a Lisp like stream of tokens.  We keep going till
    there are no tokens left to consume, or we reach a closing ')' expression.  In addition
    this function will recursively call parse_list() if it sees an opening '(', in order to
    get the sub AST parsed expression.  Syntatically a sub AST is simply an additional 
    operand of the current list of operands, so if one is found it is just appended to the
    list, and we then continue on trying to parse other operands.
    
    Parameters
    ----------
    tokens : list
        A python list of valid tokens.  
        
    Returns
    -------
    ast : list
        A partial list of the parsed abstract syntax tree, basically all of the operands we
        could consume from the stream of tokens we were given (including any parsed
        subexpressions).
    tokens : list
        A list of token strings.  The remaining tokens in the parse stream (needed for
        further processing).
    """
    operands = []
    while len(tokens) > 0:
        # peek at next token, and if not an operand then stop
        if tokens[0] == ')':
            break

        # if next token is a '(', need to get sublist/subexpression
        if tokens[0] == '(':
            subast, tokens = parse_list(tokens)
            operands.append(subast)
            continue # need to continue trying to see if more operands after the sublist
            
        # otherwise token must be some sort of an operand
        operand = tokens.pop(0) # consume the token and parse it
        
        # assume we have an operand, try and cast numeric operands, or
        # if not numeric simply leave and treat as a string value
        operands.append(decode_operand(operand))
    
    return operands, tokens


def decode_operand(token):
    """Decode a single token string
    
    Decode a single token string being interpreted syntatically as an operand.  Currently we
    try and determine if the token can be interpreted as a float or an int constant.  If it can
    not be interpreted as either of these, we default to interpreting the token as a string constant.
    
    Parameters
    ----------
    token : string
        A python string holding a single token we are trying to decode
        
    Returns
    -------
    value : int/float/string
        Returns the decoded operand.  The type of the returned value depends solely on the format of
        the token being interpreted, and the purpose of the function is to return the best type
        given the token.
    """
    if is_int(token):
        return int(token)
    elif is_float(token):
        return float(token)
    else: # default to a string
        return str(token)

    
def is_float(s):
    """Test if float
    
    Function to test whether given string can be interpreted as a valid floating
    point literal value or not.
    
    Parameters
    ----------
    s : string
        A python string holding a symbol to test
        
    Returns
    -------
    result : boolean
        True if the string is a valid floating point value, False otherwise
    """
    try:
        float(s)
        return True
    except ValueError:
        return False


def is_int(s):
    """Test if int
    
    Function to test whether given string can be interpreted as a valid integer
    literal value or not.
    
    Parameters
    ----------
    s : string
        A python string holding a symbol to test
        
    Returns
    -------
    result : boolean
        True if the string is a valid integer, False otherwise
    """
    try:
        int(s)
        return True
    except ValueError:
        return False