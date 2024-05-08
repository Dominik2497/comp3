from lark import ParseTree
from lang_var.var_ast import *
from parsers.common import *

grammarFile = "./src/parsers/lang_var/var_grammar.lark"

def parseModule(args: ParserArgs) -> mod:
    stmt_list: list[stmt] = []
    parseTree = parseAsTree(args, grammarFile, 'lvar')
    for child in parseTree.children:
        stmt_list.append(parseTreeToStmtAst(asTree(child)))
    ast = Module(
        stmt_list
        )
    return ast

def parseTreeToStmtAst(t: ParseTree) -> stmt:
    match t.data:
        case 'assign' :
            var_name = asToken(t.children[0]).value
            right_expr = parseTreeToExpAst(asTree(t.children[1]))
            return Assign(var=Ident(var_name), right=right_expr)
        case 'expr_stmt':
            return StmtExp(exp=parseTreeToExpAst(asTree(t.children[0])))
        case kind:
            raise Exception(f'unhandled parse tree of kind {kind} for sttm: {t}')

def parseTreeToExpAst(t: ParseTree) -> exp:
    match t.data:
        case 'int_exp':
            return IntConst(int(asToken(t.children[0]).value))
        case 'add_exp':
            e1, e2 = [asTree(c) for c in t.children]
            return BinOp(parseTreeToExpAst(e1), Add(), parseTreeToExpAst(e2))
        case 'mul_exp':
            e1, e2 = [asTree(c) for c in t.children]
            return BinOp(parseTreeToExpAst(e1), Mul(), parseTreeToExpAst(e2))
        case 'exp' | 'exp_1' | 'exp_2' | 'paren_exp':
            return parseTreeToExpAst(asTree(t.children[0]))
        case 'sub_exp':
            e1, e2 = [asTree(c) for c in t.children]
            return BinOp(parseTreeToExpAst(e1), Sub(), parseTreeToExpAst(e2))
        case 'var_ident':
            return Name(Ident(asToken(t.children[0]).value))
        case 'call_function':
            func_name = asToken(t.children[0]).value
            args: list[exp] = []
            if len(t.children) > 1:
                for arg in asTree(t.children[1]).children:
                    result = parseTreeToExpAst(asTree(arg))
                    args.append(result)
            return Call(name=Ident(func_name), args=args)
        case 'neg_exp':
            return UnOp(op=USub(), arg=parseTreeToExpAst(asTree(t.children[0])))
        case kind:
            raise Exception(f'unhandled parse tree of kind {kind} for exp: {t}')
        
        

