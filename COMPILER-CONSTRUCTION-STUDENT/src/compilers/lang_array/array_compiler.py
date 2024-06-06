from __future__ import annotations
from typing import *
from dataclasses import dataclass
from common.wasm import *
from lang_array.array_astAtom import *
import lang_array.array_ast as plainAst
import lang_array.array_tychecker as array_tychecker
import lang_array.array_transform as array_transform
from lang_array.array_compilerSupport import *
from common.compilerSupport import *

def identToWasmId(identifier: ident) -> WasmId:
    return WasmId('$' + identifier.name)

def compileStmts(stmts: list[stmt], cfg: CompilerConfig) -> list[WasmInstr]:
    wasmInstructions: list[WasmInstr] = []

    for stmt in stmts:
        match stmt:
            case StmtExp():
                wasmInstructions.extend(compileExpressions(stmt.exp, cfg))
            case Assign(var, right):
                wasmInstructions.extend(compileExpressions(right, cfg))
                wasmInstructions.append(WasmInstrVarLocal("set", id=WasmId('$' + var.name)))
            case IfStmt(ifVar, thenVar, elseVar):
                thenInstrsuctions = compileStmts(thenVar, cfg)
                elseInstructions = compileStmts(elseVar, cfg)
                ifInstructions = compileExpressions(ifVar, cfg)

                instructions: list[WasmInstr] = []
                instructions.extend(ifInstructions)

                instructions.append(WasmInstrIf(None, thenInstrsuctions, elseInstructions))

                wasmInstructions.extend(instructions)

            case WhileStmt(whileCondition, whileBody):
                loopStart = WasmId('$loopstart')
                loopEnd = WasmId('$loopend') 
                instructions: list[WasmInstr] = []

                bodyInstructions = compileStmts(whileBody, cfg)
                whileConditionInstructions = compileExpressions(whileCondition, cfg)

                body: list[WasmInstr] = []
                body += whileConditionInstructions
                body.append(WasmInstrIf(None, [],
                            [WasmInstrBranch(loopEnd, False)]))
                body.extend(bodyInstructions)
                body.append(WasmInstrBranch(loopStart, False))

                instructions.append(WasmInstrBlock(loopEnd, None, [
                    WasmInstrLoop(loopStart, body= body),
                ])) 

                wasmInstructions.extend(instructions)

            case SubscriptAssign(left, index, right):
                wasmInstructions.extend(arrayOffsetInstrs(left, index, cfg))
                wasmInstructions.extend(compileExpressions(right, cfg))
                storeInstructions = "i64" if isinstance(right, AtomExp) else "i32"
                wasmInstructions.append(WasmInstrMem(storeInstructions, "store"))


    return wasmInstructions




def compileExpressions(exp: exp, cfg: CompilerConfig) -> list[WasmInstr]:
    wasmInstructions: list[WasmInstr] = []
    match exp:
        case IntConst(value):
            wasmInstructions.append(WasmInstrConst("i64", value))
        case Call(name, args):    
            wasmInstructions.extend(compileCall(name, args, cfg))
        case UnOp(op_var, sub):
            match op_var:
                case USub():
                    wasmInstructions.append(WasmInstrConst(ty='i64', val=0))
                    wasmInstructions.extend(compileExpressions(sub, cfg))
                    wasmInstructions.append(WasmInstrNumBinOp(ty='i64', op='sub'))
                case Not(): 
                    wasmInstructions.extend(compileExpressions(sub, cfg))
                    wasmInstructions.append(WasmInstrConst('i32', 0))
                    wasmInstructions.append(WasmInstrIntRelOp('i32', 'eq'))
                case Array():
                    pass
        case BinOp(left, op, right):
            wasmInstructionL = compileExpressions(left, cfg)
            wasmInstructions.extend(wasmInstructionL)
            wasmInstructionR = compileExpressions(right, cfg)
            wasmInstructions.extend(wasmInstructionR)  
            match op:
                case Sub():
                    wasmInstructions.append(WasmInstrNumBinOp("i64", "sub"))
                case Add():
                    wasmInstructions.append(WasmInstrNumBinOp("i64", "add"))
                case Mul():
                    wasmInstructions.append(WasmInstrNumBinOp("i64", "mul"))
                case Eq():
                    match getTypeOfExp(left):
                        case Bool():
                            wasmInstructions.append(WasmInstrIntRelOp("i32", "eq"))
                        case Int():
                            wasmInstructions.append(WasmInstrIntRelOp("i64", "eq"))
                        case Array():
                            pass
                case NotEq():
                    match getTypeOfExp(left):
                        case Bool():
                            wasmInstructions.append(WasmInstrIntRelOp("i32", "ne"))
                        case Int():
                            wasmInstructions.append(WasmInstrIntRelOp("i64", "ne"))
                        case Array():
                            pass 
                case Less():
                    wasmInstructions.append(WasmInstrIntRelOp("i64", "lt_s"))
                case LessEq():
                    wasmInstructions.append(WasmInstrIntRelOp("i64", "le_s"))
                case Greater():
                    wasmInstructions.append(WasmInstrIntRelOp("i64", "gt_s"))
                case GreaterEq():
                    wasmInstructions.append(WasmInstrIntRelOp("i64", "ge_s"))     
                case And():
                    wasmInstructions: list[WasmInstr] = []
                    wasmInstructions+= wasmInstructionL
                    wasmInstructions.append(WasmInstrIf('i32', compileExpressions(right, cfg), [WasmInstrConst('i32',0)]))
                case Or():
                    wasmInstructions: list[WasmInstr] = []
                    wasmInstructions+= wasmInstructionL
                    wasmInstructions.append(WasmInstrIf('i32', [WasmInstrConst('i32',1)], compileExpressions(right, cfg)))
                case Is():
                    wasmInstructions.append(WasmInstrIntRelOp('i32', 'eq'))
        case Name(name):
            wasmInstructions.append(WasmInstrVarLocal(op='get', id=identToWasmId(name)))
        case BoolConst(value):
            wasmInstructions.append(WasmInstrConst(ty='i32', val=int(value)))
        case AtomExp(e):
            wasmInstructions.extend(compileExpressions(e, cfg))
        case ArrayInitStatic(elemInit):   
            wasmInstructions = []
            #inite
            initArrayInstrs = compileInitArray(IntConst(len(elemInit)), getTypeOfAtomExp(elemInit[0]), cfg)
            wasmInstructions.extend(initArrayInstrs)
            wasmInstructions.append(WasmInstrVarLocal("tee", WasmId("$@tmp_i32")))
            wasmInstructions.append(WasmInstrVarLocal("get", WasmId("$@tmp_i32")))
            index_offset = 4
            wasmInstructions.append(WasmInstrConst("i32", index_offset))
            wasmInstructions.append(WasmInstrNumBinOp("i32", "add"))
            #store,compile
            firstElemInstrs = compileExpressions(elemInit[0], cfg)
            wasmInstructions.extend(firstElemInstrs)
            arg = getTypeOfAtomExp(elemInit[0])
            storeInstr = WasmInstrMem("i64", "store") if isinstance(arg, Int) else WasmInstrMem("i32", "store")
            wasmInstructions.append(storeInstr)
            i = 1
            while i < len(elemInit):
                wasmInstructions.append(WasmInstrVarLocal("tee", WasmId("$@tmp_i32")))
                wasmInstructions.append(WasmInstrVarLocal("get", WasmId("$@tmp_i32")))
                e = elemInit[i]
                if isinstance(e.ty, Int):
                    index_offset += 8
                elif isinstance(e.ty, (Bool, Array)):
                    index_offset += 4
                wasmInstructions.append(WasmInstrConst("i32", index_offset))
                wasmInstructions.append(WasmInstrNumBinOp("i32", "add"))
                elemInstrs = compileExpressions(e, cfg)
                wasmInstructions.extend(elemInstrs)
                storeInstr = WasmInstrMem("i64", "store") if isinstance(arg, Int) else WasmInstrMem("i32", "store")
                wasmInstructions.append(storeInstr)
                i += 1
        case ArrayInitDyn(leng, elemInit):
            wasmInstructions = []
            wasmInstructions.extend(compileInitArray(leng, getTypeOfAtomExp(elemInit), cfg))
            wasmInstructions.append(WasmInstrVarLocal("tee", WasmId("$@tmp_i32")))
            wasmInstructions.append(WasmInstrVarLocal("get", WasmId("$@tmp_i32")))
            wasmInstructions.append(WasmInstrConst("i32", 4))
            wasmInstructions.append(WasmInstrNumBinOp("i32", "add"))
            wasmInstructions.append(WasmInstrVarLocal("set", WasmId("$@tmp_i32")))
            bod = []
            bod.append(WasmInstrVarLocal("get", WasmId("$@tmp_i32")))
            bod.extend(compileExpressions(elemInit, cfg))
            if isinstance(elemInit.ty, Int):
                bod.append(WasmInstrMem("i64", "store"))
            else:
                bod.append(WasmInstrMem("i32", "store"))
            bod.append(WasmInstrVarLocal("get", WasmId("$@tmp_i32")))
            bod.append(WasmInstrConst("i32", 8 if isinstance(elemInit.ty, Int) else 4))
            bod.append(WasmInstrNumBinOp("i32", "add"))
            bod.append(WasmInstrVarLocal("set", WasmId("$@tmp_i32")))
            bod_ = []
            bod_.append(WasmInstrVarLocal("get", WasmId("$@tmp_i32")))
            bod_.append(WasmInstrVarGlobal('get', Globals.freePtr))
            bod_.append(WasmInstrIntRelOp("i32", "lt_u"))
            exit_loop = WasmInstrBranch(target=WasmId("$loop_exit"), conditional=False)
            bod.extend(bod_)
            bod.append(WasmInstrIf(None, thenInstrs=[], elseInstrs=[exit_loop]))
            bod.append(WasmInstrBranch(target=WasmId("$loop_start"), conditional=False))
            loop_instr = WasmInstrLoop(WasmId("$loop_start"), body=bod)
            wasmInstructions.append(WasmInstrBlock(label=WasmId("$loop_exit"), body=[loop_instr], result=None))
        case Subscript(array, index):
            wasmInstructions.extend(arrayOffsetInstrs(array, index, cfg))
            if isinstance(array.ty, Array):
                if isinstance(array.ty.elemTy, Int):
                    wasmInstructions.append(WasmInstrMem("i64", "load"))
                else:
                    wasmInstructions.append(WasmInstrMem("i32", "load"))
    return wasmInstructions

def compileCall(name, args, cfg) -> list[WasmInstr]:
    wasmInstructions = []
    # Collect
    for arg in args:
        expr_instrs = compileExpressions(arg, cfg)
        for instr in expr_instrs:
            wasmInstructions.append(instr)
    # Handle
    if name.name == "print":
        first_arg = args[0]
        if isinstance(first_arg, Subscript):
            array_type = first_arg.array.ty
            if isinstance(array_type, Array):
                elem_type = array_type.elemTy
                if isinstance(elem_type, Int):
                    wasmInstructions.append(WasmInstrCall(WasmId("$print_i64")))
                elif isinstance(elem_type, Bool):
                    wasmInstructions.append(WasmInstrCall(WasmId("$print_bool")))
                elif isinstance(elem_type, Array):
                    wasmInstructions.append(WasmInstrCall(WasmId("$print_i32")))
        else:
            first_arg_type = getTypeOfExp(first_arg)
            if isinstance(first_arg_type, Int):
                wasmInstructions.append(WasmInstrCall(WasmId("$print_i64")))
            elif isinstance(first_arg_type, Bool):
                wasmInstructions.append(WasmInstrCall(WasmId("$print_bool")))

    if name.name == "input_int":
        input_instr = WasmInstrCall(WasmId("$input_i64"))
        wasmInstructions.append(input_instr)

    if name.name == "len":
        len_instrs = arrayLenInstrs()
        for instr in len_instrs:
            wasmInstructions.append(instr)

    return wasmInstructions

def getTypeOfExp(e: exp) -> ty:
    if e.ty is None:
        raise TypeError("IS NONE")
    else:
        if isinstance(e.ty, NotVoid):
            return e.ty.ty
        elif isinstance(e.ty, Void):
            raise TypeError("IS VOID")

def getTypeOfAtomExp(e: atomExp) -> ty:
    if e.ty is None:
        raise TypeError("IS NONE")
    else:
        return e.ty

def compileModule(m: plainAst.mod, cfg: CompilerConfig) -> WasmModule:
    vars = array_tychecker.tycheckModule(m)
    ctx = array_transform.Ctx()
    atom_stmts = array_transform.transStmts(m.stmts, ctx)
    instrs = compileStmts(atom_stmts, cfg)
    idMain = WasmId('$main')
    locals_list_vars = [
        (identToWasmId(ident), 'i64' if isinstance(var_info.ty, Int) else 'i32')
        for ident, var_info in vars.items()
    ]
    local_list_fresh = [
        (identToWasmId(var_name), 'i64' if isinstance(var_info, Int) else 'i32')
        for var_name, var_info in ctx.freshVars.items()
    ]
    list = []
    list.extend(locals_list_vars)
    list.extend(local_list_fresh)
    list.extend(Locals.decls())

    return WasmModule(imports=wasmImports(cfg.maxMemSize),
                      exports=[WasmExport("main", WasmExportFunc(idMain))],
                      globals=Globals.decls(),
                      data=Errors.data(),
                      funcTable=WasmFuncTable([]),
                      funcs=[WasmFunc(idMain, [], None, list, instrs)])



def compileInitArray(lenExp: atomExp, elemTy: ty, cfg: CompilerConfig) -> list[WasmInstr]:
    init_instr: list[WasmInstr] = []
    array_len = compileExpressions(lenExp, cfg)

    init_instr.extend(array_len)
    init_instr.extend(checkArraySize(elemTy, cfg))
    init_instr.extend(checkArrayLength(array_len))

    init_instr.extend(computeHeader(array_len, elemTy))
    init_instr.extend(moveFreePtr(array_len))
    
    return init_instr

def checkArraySize(elemTy: ty, cfg: CompilerConfig) -> list[WasmInstr]:
    size_instrs: list[WasmInstr] = []
    size = 8 if isinstance(elemTy, Int) else 4
    size_instrs.append(WasmInstrConst("i64", size))
    size_instrs.append(WasmInstrNumBinOp("i64", "mul"))
    size_instrs.append(WasmInstrConst("i64", cfg.maxArraySize))
    size_instrs.append(WasmInstrIntRelOp("i64", "gt_s"))
    
    error_instrs = generateErrorInstrs()
    size_instrs.append(WasmInstrIf(None, error_instrs, []))
    
    return size_instrs

def checkArrayLength(array_len: list[WasmInstr]) -> list[WasmInstr]:
    length_instrs: list[WasmInstr] = []
    
    length_instrs.extend(array_len)
    length_instrs.append(WasmInstrConst("i64", 0))
    length_instrs.append(WasmInstrIntRelOp("i64", "lt_s"))
    
    error_instrs = generateErrorInstrs()
    length_instrs.append(WasmInstrIf(None, error_instrs, []))
    
    return length_instrs

def computeHeader(array_len: list[WasmInstr], elemTy: ty) -> list[WasmInstr]:
    header_instrs: list[WasmInstr] = []
    
    header_instrs.append(WasmInstrVarGlobal("get", WasmId("$@free_ptr")))
    header_instrs.extend(array_len)
    header_instrs.append(WasmInstrConvOp("i32.wrap_i64"))
    header_instrs.append(WasmInstrConst("i32", 4))
    header_instrs.append(WasmInstrNumBinOp("i32", "shl"))
    header_flag = WasmInstrConst("i32", 3 if isinstance(elemTy, Array) else 1)
    header_instrs.append(header_flag)
    header_instrs.append(WasmInstrNumBinOp("i32", "xor"))
    header_instrs.append(WasmInstrMem("i32", "store"))
    
    return header_instrs

def moveFreePtr(array_len: list[WasmInstr]) -> list[WasmInstr]:
    free_ptr_instrs: list[WasmInstr] = []
    
    free_ptr_instrs.append(WasmInstrVarGlobal("get", WasmId("$@free_ptr")))
    free_ptr_instrs.extend(array_len)
    free_ptr_instrs.append(WasmInstrConvOp("i32.wrap_i64"))
    free_ptr_instrs.append(WasmInstrConst("i32", 8))
    free_ptr_instrs.append(WasmInstrNumBinOp("i32", "mul"))
    free_ptr_instrs.append(WasmInstrConst("i32", 4))
    free_ptr_instrs.append(WasmInstrNumBinOp("i32", "add"))
    free_ptr_instrs.append(WasmInstrVarGlobal("get", WasmId("$@free_ptr")))
    free_ptr_instrs.append(WasmInstrNumBinOp("i32", "add"))
    free_ptr_instrs.append(WasmInstrVarGlobal("set", WasmId("$@free_ptr")))
    
    return free_ptr_instrs

def generateErrorInstrs() -> list[WasmInstr]:
    return [
        WasmInstrConst("i32", 0),
        WasmInstrConst("i32", 14),
        WasmInstrCall(WasmId("$print_err")),
        WasmInstrTrap()
    ]


def arrayLenInstrs() -> list[WasmInstr]:
    array_len_instrs: list[WasmInstr] = [#
        WasmInstrMem("i32","load"),
        WasmInstrConst("i32", 4),
        WasmInstrNumBinOp("i32","shr_u"),
        WasmInstrConvOp("i64.extend_i32_u")
    ]
    return array_len_instrs

def get_index_check_instructions(indexExp: atomExp,cfg: CompilerConfig) -> list[WasmInstr]:
    instructions: list[WasmInstr] = []
    instructions.extend(compileExpressions(indexExp, cfg))
    instructions.extend(compileExpressions(indexExp, cfg))
    instructions.append(WasmInstrConst("i64", 0))
    instructions.append(WasmInstrIntRelOp("i64", "lt_s"))
    thenInstructions: list[WasmInstr] = [
        WasmInstrConst("i32", 14),
        WasmInstrConst("i32", 10),
        WasmInstrCall(WasmId("$print_err")),
        WasmInstrTrap()
    ]
    instructions.append(WasmInstrIf(None, thenInstructions, []))
    return instructions

def get_element_size(elem_ty: Type) -> int:
    return 8 if isinstance(elem_ty, Int) else 4

def arrayOffsetInstrs(arrayExp: atomExp, indexExp: atomExp, cfg: CompilerConfig) -> list[WasmInstr]:

    wasmInstructions: list[WasmInstr] = []

    wasmInstructions.extend(get_index_check_instructions(indexExp,cfg))

    wasmInstructions.extend(compileExpressions(arrayExp, cfg))
    wasmInstructions.extend(arrayLenInstrs())
    wasmInstructions.append(WasmInstrIntRelOp("i64", "ge_s"))
    thenInstructions: list[WasmInstr] = [
        WasmInstrConst("i32", 14),
        WasmInstrConst("i32", 10),
        WasmInstrCall(WasmId("$print_err")),
        WasmInstrTrap()
    ]
    wasmInstructions.append(WasmInstrIf(None, thenInstructions, []))
    wasmInstructions.extend(compileExpressions(arrayExp, cfg))
    wasmInstructions.extend(compileExpressions(indexExp, cfg))
    wasmInstructions.append(WasmInstrConvOp("i32.wrap_i64"))
    elem_size = get_element_size(arrayExp.ty.elemTy) if isinstance(arrayExp.ty, Array) else 4
    wasmInstructions.append(WasmInstrConst("i32", elem_size))
    wasmInstructions.append(WasmInstrNumBinOp("i32", "mul"))
    wasmInstructions.append(WasmInstrConst("i32", 4))
    wasmInstructions.append(WasmInstrNumBinOp("i32", "add"))
    wasmInstructions.append(WasmInstrNumBinOp("i32", "add"))
    return wasmInstructions