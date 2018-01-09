from typing import List
from latte_misc import MUL, DIV, MOD, ADD, SUB, LT, LE, GT, GE, EQ, NE, AND, \
    OR, SPECIAL, UID, VType, VFun, VClass, VBool, VInt, VString, VVoid, \
    CompilationError, NEG


def op_array(ctx, op: str, vtype1: 'VType', vtype2: 'VType' = None) \
        -> (str, 'VType'):
    if vtype2 is None:
        # (a, None) -> b
        if vtype1.is_int() and op == SUB:
            return 'sub i32 0, {}', VInt()
        if vtype1.is_bool() and op == NEG:
            return 'sub i1 1, {}', VBool()
        raise CompilationError('invalid operator', ctx)

    if vtype1 != vtype2:
        raise CompilationError('invalid operator', ctx)
    # (a, a) -> b
    if vtype1.is_int():
        # (int, int) -> int
        if op == MUL:
            return 'mul i32 {}, {}', VInt()
        elif op == DIV:
            return 'sdiv i32 {}, {}', VInt()
        elif op == MOD:
            return 'srem i32 {}, {}', VInt()
        elif op == ADD:
            return 'add i32 {}, {}', VInt()
        elif op == SUB:
            return 'sub i32 {}, {}', VInt()
        # (int, int) -> bool
        elif op == LT:
            return 'icmp slt i32 {}, {}', VBool()
        elif op == LE:
            return 'icmp sle i32 {}, {}', VBool()
        elif op == GT:
            return 'icmp sgt i32 {}, {}', VBool()
        elif op == GE:
            return 'icmp sge i32 {}, {}', VBool()
        elif op == EQ:
            return 'icmp eq i32 {}, {}', VBool()
        elif op == NE:
            return 'icmp ne i32 {}, {}', VBool()
    elif vtype1.is_bool():
        # (bool, bool) -> bool
        if op == EQ:
            return 'icmp eq i1 {}, {}', VBool()
        elif op == NE:
            return 'icmp ne i1 {}, {}', VBool()
        elif op == AND:
            return SPECIAL, VBool()
        elif op == OR:
            return SPECIAL, VBool()
    elif vtype1.is_string():
        if op == ADD:
            return 'call i8* @op_addString(i8* {}, i8* {})', VString()
    # Other
    raise CompilationError("invalid operator", ctx)


class Expr(object):
    def __init__(self, vtype: VType):
        self.vtype = vtype

    def get_code_lines(self, program: 'Program', keep_ref=False) \
            -> List['CodeLine']:
        raise NotImplementedError()

    def get_code_blocks(
            self, program: 'Program',
            next_code_block: 'CodeBlock' = None) -> List['CodeBlock']:
        code_lines = self.get_code_lines(program)
        if next_code_block:
            code_lines.extend(br_block(next_code_block))
        return [CodeBlock(code_lines, comment="expr")]


class EConst(Expr):
    def __init__(self, vtype: VType, value, ctx):
        self.value = value
        if isinstance(value, str):
            # It really should not happen.
            raise ValueError("should encounter bytes, not string value")
        self.vtype = vtype
        self.ctx = ctx

    def get_code_lines(self, program: 'Program', keep_ref=False) \
            -> List['CodeLine']:
        if self.vtype.is_int():
            code_line = CodeLine("add i32 0, {}".format(self.value))
        elif self.vtype.is_bool():
            code_line = CodeLine("add i1 0, {}".format(int(self.value)))
        elif self.vtype.is_string():
            code_line = program.constants.get_code_line(self.value)
        else:
            raise CompilationError("type not supported for consts", self.ctx)
        return [code_line]


def load_address(program, vtype: VType, register: str, ctx) -> 'CodeLine':
    if vtype.is_intboolstring():
        code_line = CodeLine(
            "load {type}, {type}* {reg}".format(reg=register,
                                                type=vtype.llvm_type()))
    else:
        raise CompilationError("type not supported for loading", ctx)
    return code_line


class EVar(Expr):
    def __init__(self, name: str, vtype: VType, ctx):
        self.name = name
        self.vtype = vtype
        self.ctx = ctx

    def get_code_lines(self, program: 'Program', keep_ref=False) \
            -> List['CodeLine']:
        vtype_unref = self.vtype.unref()
        if vtype_unref.is_intboolstring():
            code_line = CodeLine(
                # This i32 below is OK, because it's actually an index.
                "getelementptr  {type}, {type}* {name}, i32 0".format(
                    name=self.name, type=vtype_unref.llvm_type()))
        else:
            raise CompilationError(
                "type not supported for assignment", self.ctx)

        if keep_ref:
            return [code_line]
        else:
            return [code_line, load_address(
                program, vtype_unref, code_line.get_var_name(), self.ctx)]


class EUnaryOp(Expr):
    def __init__(self, vtype: VType, expr: Expr, op, ctx):
        self.vtype = vtype
        self.expr = expr
        self.op = op
        self.ctx = ctx

    def get_code_lines(self, program: 'Program', keep_ref=False) \
            -> List['CodeLine']:
        code_lines = self.expr.get_code_lines(program)
        val = code_lines[-1].get_var_name()

        instr, vtype = op_array(self.ctx, self.op, self.expr.vtype)
        code_lines.append(CodeLine(instr.format(val)))
        return code_lines


class EOp(Expr):
    def __init__(self, vtype: VType, lexpr: Expr, rexpr: Expr, op, ctx):
        self.vtype = vtype
        self.lexpr = lexpr
        self.rexpr = rexpr
        self.op = op
        self.ctx = ctx

    def get_code_lines(self, program: 'Program', keep_ref=False) \
            -> List['CodeLine']:
        l_code_lines = self.lexpr.get_code_lines(program)
        lval = l_code_lines[-1].get_var_name()
        r_code_lines = self.rexpr.get_code_lines(program)
        rval = r_code_lines[-1].get_var_name()
        code_lines = l_code_lines + r_code_lines

        instr, vtype = op_array(self.ctx, self.op, self.lexpr.vtype,
                                self.rexpr.vtype)
        if instr == SPECIAL:
            if self.vtype.is_bool():
                code_lines = []
                code_lines.extend(l_code_lines)
                uid = UID.get_uid()
                code_lines.append(CodeLine('br label %ISLAZY{}'.format(uid),
                                           save_result=False))
                code_lines.append(CodeLine("ISLAZY{}:".format(uid),
                                           save_result=False))
                if self.op == OR:
                    code_lines.append(CodeLine(
                        "br i1 {}, label %LAZY{}, label %WORK{}".format(
                            lval, uid, uid), save_result=False))
                elif self.op == AND:
                    code_lines.append(CodeLine(
                        "br i1 {}, label %WORK{}, label %LAZY{}".format(
                            lval, uid, uid), save_result=False))
                else:
                    raise CompilationError('invalid operator', self.ctx)
                code_lines.append(CodeLine("WORK{}:".format(uid),
                                           save_result=False))
                code_lines.extend(r_code_lines)
                code_lines.append(CodeLine('br label %WORKED{}'.format(uid),
                                           save_result=False))
                code_lines.append(CodeLine("WORKED{}:".format(uid),
                                           save_result=False))
                code_lines.append(CodeLine('br label %LAZY{}'.format(uid),
                                           save_result=False))
                code_lines.append(CodeLine("LAZY{}:".format(uid),
                                           save_result=False))
                code_lines.append(CodeLine(
                    "phi i1 [{lval}, %ISLAZY{uid}], [{rval}, %WORKED{uid}]"
                    .format(lval=lval, rval=rval, uid=uid)
                ))
            else:
                raise NotImplementedError()
        else:
            code_lines.append(CodeLine(instr.format(lval, rval)))
        return code_lines


class ECall(Expr):
    def __init__(self, name: str, vtype: VType, argtypes: List[VType],
                 args: List[Expr]):
        self.name = name
        self.vtype = vtype
        self.argtypes = argtypes
        self.args = args

    def get_code_lines(self, program: 'Program', keep_ref=False) \
            -> List['CodeLine']:
        code_lines = []
        arg_strings = []
        for (arg, argtype) in zip(self.args, self.argtypes):
            code_lines.extend(arg.get_code_lines(program))
            argval = code_lines[-1].get_var_name()
            assert isinstance(argtype, VType)
            arg_strings.append("{} {}".format(argtype.llvm_type(), argval))

        rtype = self.vtype
        call_line = CodeLine("call {rtype} @f_{name}({args})".format(
            rtype=rtype.llvm_type(), name=self.name,
            args=", ".join(arg_strings)
        ), save_result=(not rtype.is_void()))
        return code_lines + [call_line]


class VariablesBlock(object):
    def __init__(self, upper_block: 'VariablesBlock' = None):
        self.vars = dict()
        self.upper = upper_block
        self.uid = UID.get_uid()

    def add_variable(self, name: str, type: VType, ctx):
        assert isinstance(type, VType)
        if name in self.vars:
            raise CompilationError("variable already exists", ctx)
        self.vars[name] = type

    def get_variable(self, name: str, ctx) -> VType:
        if name in self.vars:
            return self.vars[name]
        if self.upper is not None:
            return self.upper.get_variable(name, ctx)
        raise CompilationError("variable not yet declared", ctx)

    def get_variable_name(self, name: str, ctx):
        if name in self.vars:
            return "%b{}_{}".format(self.uid, name)
        if self.upper is not None:
            return self.upper.get_variable_name(name, ctx)
        raise CompilationError("variable doesn't exist", ctx)

    def __iter__(self):
        for var in self.vars:
            yield var


class Constants(object):
    def __init__(self):
        self.constants = dict()  # val -> name

    def _get_declaration_line(self, val: bytes) -> str:
        name = self.constants[val]
        size = len(val) + 1  # +1 because of null byte.

        llval = "".join(["\\" + str(hex(c))[2:].rjust(2, "0").upper()
                         for c in val]) + "\\00"
        line = "{name} = internal constant[{size} x i8] c\"{val}\"".format(
            name=name, size=size, val=llval
        )
        return line

    def get_source(self) -> str:
        lines = []
        for constant in self.constants:
            lines.append(self._get_declaration_line(constant))
        return "\n".join(lines)

    def add_constant(self, value: bytes):
        if value in self.constants:
            return
        self.constants[value] = "@sc_" + str(UID.get_uid())

    def get_code_line(self, val: bytes) -> 'CodeLine':
        size = len(val) + 1
        code = "bitcast [{size} x i8]* {name} to i8*".format(
            size=size, name=self.constants[val])
        return CodeLine(code)


class Program(object):
    def __init__(self):
        self.types = dict()  # name -> VType
        for typ in ["string", "int", "boolean", "void"]:
            self.types[typ] = VClass(typ)
        self.globals = VariablesBlock()
        self.constants = Constants()
        self.last_vars = self.globals
        self.functions = dict()  # name -> Function
        self.current_function = None

        self.globals.add_variable("printInt", VFun(VVoid(), (VInt(),)), None)
        self.globals.add_variable("printString", VFun(VVoid(), (VString(),)),
                                  None)
        self.globals.add_variable("error", VFun(VVoid(), tuple()), None)
        self.globals.add_variable("readInt", VFun(VInt(), tuple()), None)
        self.globals.add_variable("readString", VFun(VString(), tuple()), None)

    def name_to_type(self, name: str, ctx) -> VType:
        if name in self.types:
            return self.types[name]
        raise CompilationError("type not found", ctx)

    def do_checks(self):
        if 'main' not in self.globals.vars:
            raise CompilationError('main not defined', None)
        if self.globals.get_variable('main', None) != VFun(VInt(), tuple()):
            raise CompilationError('main has wrong signature',
                                   self.functions['main'].ctx)

    def get_source(self):
        source = ""
        source += "declare void @f_printInt(i32)\n"
        source += "declare void @f_printString(i8*)\n"
        source += "declare void @f_error()\n"
        source += "declare i32 @f_readInt()\n"
        source += "declare i8* @f_readString()\n"

        source += "declare i8* @op_addString(i8*, i8*)\n"

        source += self.constants.get_source() + '\n'
        for function in self.functions.values():
            source += function.get_source(self) + "\n\n"
        source += "define i32 @main() {\n"
        source += "  MAIN:\n"
        source += "    %ret = call i32 @f_main()\n"
        source += "    ret i32 %ret\n"
        source += "}\n"

        return source


class Stmt(object):
    def get_code_blocks(
            self, program: Program,
            next_code_block: 'CodeBlock' = None) -> List['CodeBlock']:
        raise NotImplementedError()


def br_block(block: 'CodeBlock') -> List['CodeLine']:
    if block:
        return [CodeLine("br label %{}".format(block.get_label_name()),
                         save_result=False)]
    else:
        return []


def cond_br_block(cond: 'CodeLine', true_block: 'CodeBlock',
                  false_block: 'CodeBlock') -> List['CodeLine']:
    assert true_block
    assert false_block
    return [CodeLine(
        "br i1 {}, label %{}, label %{}".format(
            cond.get_var_name(), true_block.get_label_name(),
            false_block.get_label_name()),
        save_result=False)]


class EmptyStmt(Stmt):
    def get_code_blocks(
            self, program: Program,
            next_code_block: 'CodeBlock' = None) -> List['CodeBlock']:
        code_lines = (br_block(next_code_block))
        return [CodeBlock(code_lines, comment="empty stmt")]


class SAssi(Stmt):
    def __init__(self, texpr: Expr, vexpr: Expr, ctx):
        self.texpr = texpr
        self.vexpr = vexpr
        self.ctx = ctx

    def get_code_blocks(
            self, program: Program,
            next_code_block: 'CodeBlock' = None) -> List['CodeBlock']:
        t_code_lines = self.texpr.get_code_lines(program, keep_ref=True)
        t_var = t_code_lines[-1].get_var_name()

        v_code_lines = self.vexpr.get_code_lines(program)
        v_val = v_code_lines[-1].get_var_name()

        vtype = self.vexpr.vtype.unref()
        if vtype.is_intboolstring():
            s_code_line = CodeLine("store {type} {val}, {type}* {tar}".format(
                val=v_val, tar=t_var, type=vtype.llvm_type()),
                save_result=False)
        else:
            raise CompilationError("invalid assignment", self.ctx)

        # br_line
        br_lines = br_block(next_code_block)

        # Concatenation
        code_lines = t_code_lines + v_code_lines + [s_code_line] + br_lines
        return [CodeBlock(code_lines, comment="assignment")]


class SIfElse(Stmt):
    def __init__(self, cond: Expr, ifstmt: Stmt, elsestmt: Stmt):
        self.cond = cond
        self.ifstmt = ifstmt
        # It will be set - maybe EmptyStmt
        self.elsestmt = elsestmt

    def get_code_blocks(
            self, program: Program,
            next_code_block: 'CodeBlock' = None) -> List['CodeBlock']:
        if isinstance(self.cond, EConst):
            if self.cond.value:
                return self.ifstmt.get_code_blocks(program, next_code_block)
            else:
                return self.elsestmt.get_code_blocks(program, next_code_block)
        # End block
        brlines = br_block(next_code_block)
        end_block = CodeBlock(brlines, comment="end-if")

        # True blocks
        true_blocks = self.ifstmt.get_code_blocks(program, end_block)

        # False blocks
        false_blocks = self.elsestmt.get_code_blocks(program, end_block)

        # Cond block
        cond_lines = self.cond.get_code_lines(program)

        brlines = cond_br_block(cond_lines[-1], true_blocks[0], false_blocks[0])
        cond_block = CodeBlock(cond_lines + brlines, False, comment="if")

        # Setting ending appropriately
        if true_blocks[-1].ending and false_blocks[-1].ending:
            # If those blocks are ending, false block will indicate this.
            end_blocks = []
        else:
            end_blocks = [end_block]

        # Concatenation and return
        code_blocks = [cond_block] + true_blocks + false_blocks + end_blocks
        return code_blocks


class SWhile(Stmt):
    def __init__(self, cond: Expr, body: Stmt):
        self.cond = cond
        self.body = body

    def get_code_blocks(
            self, program: Program,
            next_code_block: 'CodeBlock' = None) -> List['CodeBlock']:
        # Maybe end endless loop only if there is a return inside?
        if isinstance(self.cond, EConst):
            if self.cond.value:
                code_blocks = self.body.get_code_blocks(program, None)
                brlines = br_block(code_blocks[0])
                code_blocks[-1].codelines.extend(brlines)
                code_blocks[-1].ending = True  # It never returns, so it's OK.
                return code_blocks
            else:
                return []
        # End block
        brlines = br_block(next_code_block)
        end_block = CodeBlock(brlines, comment="end-while")

        # It'll just jump to condition.
        first_code_block = CodeBlock([], comment="while")

        # Main body
        code_blocks = self.body.get_code_blocks(program, first_code_block)

        # Condition
        cond_lines = self.cond.get_code_lines(program)

        brlines = cond_br_block(cond_lines[-1], code_blocks[0], end_block)
        cond_block = CodeBlock(cond_lines + brlines, False,
                               comment="cond-while")

        # Jumping to condition from first code block.
        br_cond_lines = br_block(cond_block)

        first_code_block.codelines.extend(br_cond_lines)

        # Concateneting code blocks.
        code_blocks = [first_code_block] + code_blocks + [cond_block] + [
            end_block]
        return code_blocks


class SReturn(Stmt):
    def __init__(self, ctx, expr=None):
        self.expr = expr
        self.ctx = ctx

    def get_code_blocks(
            self, program: Program,
            next_code_block: 'CodeBlock' = None) -> List['CodeBlock']:
        del next_code_block  # We won't go there, because we return.
        if self.expr:
            codelines = self.expr.get_code_lines(program)
            vname = codelines[-1].get_var_name()
            vtype = self.expr.vtype.unref()
            if vtype.is_intboolstring():
                rline = "ret {type} {name}".format(name=vname,
                                                   type=vtype.llvm_type())
            else:
                raise CompilationError('invalid return type', self.ctx)
            codelines.append(CodeLine(rline, save_result=False))
        else:
            codelines = [CodeLine("ret void", save_result=False)]
        code_block = CodeBlock(codelines, ending=True, comment="return")
        return [code_block]


class CodeBlock(object):
    def __init__(self, codelines: ['CodeLine'], ending=False, comment=None):
        self.codelines = codelines
        self.uid = UID.get_uid()
        self.ending = ending
        self.comment = ("  ; " + comment) if comment else ""

    def get_label_name(self):
        return "L{}".format(self.uid)

    def get_source(self):
        source_lines = ["  {}:{}".format(self.get_label_name(), self.comment)]
        for codeline in self.codelines:
            source_lines.append("    " + codeline.code)
        return "\n".join(source_lines)


class CodeLine(object):
    def __init__(self, code: str, save_result=True):
        self.uid = UID.get_uid()
        self.code = code
        self.save_result = save_result
        if save_result:
            self.code = self.get_var_name() + " = " + self.code

    def get_var_name(self):
        if self.save_result:
            return "%v{}".format(self.uid)
        else:
            return None


class Block(Stmt):
    def __init__(self, vars: VariablesBlock):
        self.vars = vars
        self.stmts = []
        self.uid = UID.get_uid()

    def get_code_blocks(
            self, program: Program,
            next_code_block: 'CodeBlock' = None) -> List['CodeBlock']:
        # The main part of code blocks
        code_blocks = []
        for stmt in self.stmts[::-1]:
            new_code_blocks = stmt.get_code_blocks(program, next_code_block)
            if len(new_code_blocks) > 0:
                next_code_block = new_code_blocks[0]
                if new_code_blocks[-1].ending:
                    # remove the rest, because we returned
                    code_blocks = []
                code_blocks = new_code_blocks + code_blocks

        init_codelines = []
        for varname in self.vars.vars:
            block_varname = self.vars.get_variable_name(varname, None)
            vtype = self.vars.vars[varname]
            if vtype.is_intboolstring():
                init_codelines.append(CodeLine("{var} = alloca {type}".format(
                    var=block_varname, type=vtype.llvm_type()),
                    save_result=False))
            else:
                raise NotImplementedError()
        if code_blocks:
            init_codelines.extend(br_block(code_blocks[0]))
        init_block = CodeBlock(init_codelines, comment="init")
        return [init_block] + code_blocks


class Function(object):
    def __init__(self, name: str, arg_vars: VariablesBlock, block: Block, ctx):
        self.name = name
        self.block = block
        self.ctx = ctx
        self.arg_vars = arg_vars

    def get_code_blocks(self, program: Program) -> List['CodeBlock']:
        code_blocks = self.block.get_code_blocks(program)

        # Make initialization code block
        init_codelines = []
        for varname in self.arg_vars.vars:
            reg_varname = self.arg_vars.get_variable_name(varname, None)
            vtype = self.arg_vars.vars[varname]
            if vtype.is_intboolstring():
                init_codelines.append(CodeLine("{var} = alloca {type}".format(
                    var=reg_varname, type=vtype.llvm_type()),
                    save_result=False))
                init_codelines.append(CodeLine(
                    "store {type} %{var}, {type}* {b_var}".format(
                        var=varname, b_var=reg_varname,
                        type=vtype.llvm_type()), save_result=False))
            else:
                raise CompilationError('unexpected argument type', self.ctx)
        if code_blocks:
            init_codelines.extend(br_block(code_blocks[0]))
        init_block = CodeBlock(init_codelines, comment="init")

        return [init_block] + code_blocks

    def get_source(self, program: Program):
        code_blocks = self.get_code_blocks(program)

        if program.globals.get_variable(self.name, self.ctx).rtype.is_void():
            if not code_blocks:
                code_blocks.append(CodeBlock([], ending=True))
            codeline = CodeLine('ret void', save_result=False)
            code_blocks[-1].codelines.append(codeline)
        elif (not code_blocks) or (not code_blocks[-1].ending):
            raise CompilationError("function doesn't return", self.ctx)

        arg_strings = []
        for argname in self.arg_vars.vars:
            vtype = self.arg_vars.get_variable(argname, None)
            if vtype.is_intboolstring():
                arg_strings.append('{} %{}'.format(vtype.llvm_type(), argname))
            else:
                raise NotImplementedError()

        rtype = program.globals.get_variable(self.name, None).rtype.llvm_type()

        begin_lines = [
            "define {} @f_{}({}) {{".format(rtype, self.name,
                                            ", ".join(arg_strings)),
        ]

        end_lines = [
            "}"
        ]

        block_lines = "\n\n".join(
            [code_block.get_source() for code_block in code_blocks])

        return "\n".join(begin_lines + [block_lines] + end_lines)
