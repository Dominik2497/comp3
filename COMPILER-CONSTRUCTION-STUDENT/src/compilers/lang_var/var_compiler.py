from lang_var.var_ast import *
from common.wasm import *
import lang_var.var_tychecker as var_tychecker
from common.compilerSupport import *

def identToWasmId(ident: Ident) -> WasmId:
    return WasmId('$' + ident.name)

def compileStmts(stmts: list[stmt]) -> list[WasmInstr]:
    wasmInstructions: list[WasmInstr] = []

    for stmt in stmts:
        match stmt:
            case StmtExp():
                wasmInstructions.extend(compileExpressions(stmt.exp))
            case Assign(var, right):
                wasmInstructions.extend(compileExpressions(right))
                wasmInstructions.append(WasmInstrVarLocal(op='set', id=identToWasmId(var)))

    return wasmInstructions

def compileExpressions(exp: exp) -> list[WasmInstr]:
    wasmInstructions: list[WasmInstr] = [] 

    match exp:
        case IntConst(value):
            wasmInstructions.append(WasmInstrConst('i64', value))
        case Call(name):
            wasmInstructions.extend(compileCall(exp))
        case UnOp(USub(), sub):
            wasmInstructions.append(WasmInstrConst(ty='i64', val=0))
            wasmInstructions.extend(compileExpressions(sub))
            wasmInstructions.append(WasmInstrNumBinOp(ty='i64', op='sub'))
        case BinOp(left, op, right):
            wasmInstructions += compileExpressions(left)
            wasmInstructions += compileExpressions(right)
            match op:
                case Sub():
                    wasmInstructions.append(WasmInstrNumBinOp(ty='i64', op='sub'))
                case Add():
                    wasmInstructions.append(WasmInstrNumBinOp(ty='i64', op='add'))
                case Mul():
                    wasmInstructions.append(WasmInstrNumBinOp(ty='i64', op='mul'))
        case Name(name):
            wasmInstructions.append(WasmInstrVarLocal(op='get', id=identToWasmId(name)))
    return wasmInstructions
    
def compileCall(call: Call) -> list[WasmInstr]:
    match call:
        case Call(Ident('print'), args):
            return compilePrint_i64(args)
        case Call(Ident('input_int'), args):
            return [WasmInstrCall(WasmId('$input_i64'))]
        case _:
            raise ValueError("wrong function call: ", call)

def compilePrint_i64(args: list[exp]) -> list[WasmInstr]:
    instructions: list[WasmInstr] = []
    for arg in args:
        instructions.extend(compileExpressions(arg))
    instructions.append(WasmInstrCall(WasmId('$print_i64')))
    return instructions

def compileModule(m: mod, cfg: CompilerConfig) -> WasmModule:
    vars = var_tychecker.tycheckModule(m)
    instrs = compileStmts(m.stmts)
    idMain = WasmId('$main')
    locals_: list[tuple[WasmId, WasmValtype]] = [(identToWasmId(x), 'i64') for x in vars]
    return WasmModule(imports=wasmImports(cfg.maxMemSize),
                      exports=[WasmExport("main", WasmExportFunc(idMain))],
                      globals=[],
                      data=[],
                      funcTable=WasmFuncTable([]),
                      funcs=[WasmFunc(idMain, [], None, locals_, instrs)])



