from typing import List

# Types
BOOL = 'i1'
INT = 'i32'

# Operators
MUL = '*'
DIV = '/'
MOD = '%'
ADD = '+'
SUB = '-'

LT = '<'
LE = '<='
GT = '>'
GE = '>='
EQ = '=='
NE = '!='

AND = '&&'
OR = '||'

# Special treatment for operator. Eg. lazy computing of 'and'.
SPECIAL = 'SPECIAL'


def op_array(op: str, vtype1: 'VType', vtype2: 'VType'=None) -> (str, 'VType'):
    if vtype1 != vtype2:
        # TODO: Add unary operators.
        raise NotImplementedError()
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
    # Other
    raise ValueError("Op not allowed: {} {} {}"
                     .format(vtype1.name, op, vtype2.name))


class UID(object):
    last_uid = 0

    @staticmethod
    def get_uid():
        UID.last_uid += 1
        return UID.last_uid


class TypeNotFound(BaseException):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return "Type not found: {}".format(self.name)


class VType(object):
    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if not isinstance(other, VType):
            return False
        return str(self.name).rstrip("*") == str(other.name).rstrip("*")

    def __ne__(self, other):
        return not (self == other)

    def unref(self):
        return self

    def is_bool(self):
        return self == VBool()

    def is_int(self):
        return self == VInt()

    def is_string(self):
        return self == VString()

    def is_void(self):
        return self == VVoid()

    def llvm_type(self):
        raise NotImplementedError()


class VList(VType):
    def __init__(self, vtype: VType):
        self.name = vtype.name + '[]'
        self.vtype = vtype


class VRef(VType):
    def __init__(self, vtype: VType):
        if isinstance(vtype, VRef):
            # No references to references.
            vtype = vtype.unref()
        self.vtype = vtype
        self.name = vtype.name + "*"

    def unref(self):
        return self.vtype.unref()

    def is_bool(self):
        return self.vtype.is_bool()

    def is_int(self):
        return self.vtype.is_int()

    def is_string(self):
        return self.vtype.is_string()

    def llvm_type(self):
        return self.llvm_type() + "*"


class VFun(VType):
    def __init__(self, rtype: VType, params: (VType,)):
        self.rtype = rtype
        self.params = params
        for param in params:
            assert isinstance(param, VType)
        self.name = "({}) -> {}".format(
            ", ".join(str(param) for param in params),
            rtype)


class VClass(VType):
    def __init__(self, name: str):
        self.name = name

    def get_default_expr(self):
        if self.is_int():
            return EConst(self, 0)
        elif self.is_bool():
            return EConst(self, False)
        elif self.is_string():
            return EConst(self, "")
        else:
            raise NotImplementedError()

    def llvm_type(self):
        if self.is_bool():
            return BOOL
        elif self.is_int():
            return INT
        else:
            raise NotImplementedError()


def VBool():
    return VClass('boolean')


def VInt():
    return VClass('int')


def VString():
    return VClass('string')


def VVoid():
    return VClass('void')


class Expr(object):
    def __init__(self, vtype: VType):
        self.vtype = vtype

    def to_str(self, ident=0):
        ret = " " * ident + "Expr\n"
        return ret

    def get_code_lines(self, program: 'Program', keep_ref=False)\
            -> List['CodeLine']:
        raise NotImplementedError()

    def get_code_blocks(
            self, program: 'Program',
            next_code_block: 'CodeBlock' = None) -> List['CodeBlock']:
        code_lines = self.get_code_lines(program)
        if next_code_block:
            next_label = next_code_block.get_label_name()
            code_lines.append(CodeLine("br label %{}".format(next_label)))
        return [CodeBlock(code_lines)]


class EConst(Expr):
    def __init__(self, vtype: VType, value):
        self.value = value
        self.vtype = vtype

    def to_str(self, ident=0):
        ret = " " * ident + "const {}:{}\n".format(self.value, self.vtype)
        return ret

    def get_code_lines(self, program: 'Program', keep_ref=False)\
            -> List['CodeLine']:
        if self.vtype.is_int():
            code_line = CodeLine("add i32 0, {}".format(self.value))
        elif self.vtype.is_bool():
            code_line = CodeLine("add i1 0, {}".format(int(self.value)))
        else:
            raise ValueError(
                "Type {} not supported for assignment".format(type))
        return [code_line]


def load_address(program, vtype: VType, register: str) -> 'CodeLine':
    if vtype.is_int():
        code_line = CodeLine(
            "load i32, i32* {}".format(register))
    elif vtype.is_bool():
        code_line = CodeLine(
            "load i1, i1* {}".format(register))
    else:
        raise ValueError(
            "Type {} not supported for loading".format(type))
    return code_line


class EVar(Expr):
    def __init__(self, name: str, vtype: VType):
        self.name = name
        self.vtype = vtype

    def to_str(self, ident=0):
        ret = " " * ident + "var {}:{}\n".format(self.name, self.vtype)
        return ret

    def get_code_lines(self, program: 'Program', keep_ref=False)\
            -> List['CodeLine']:
        vtype_unref = self.vtype.unref()
        if vtype_unref.is_int():
            code_line = CodeLine(
                "getelementptr  i32, i32* {}, i32 0".format(self.name))
        elif vtype_unref.is_bool():
            code_line = CodeLine(
                "getelementptr  i1, i1* {}, i1 0".format(self.name))
        else:
            raise ValueError(
                "Type {} not supported for assignment".format(type))

        if keep_ref:
            return [code_line]
        else:
            return [code_line, load_address(
                program, vtype_unref, code_line.get_var_name())]


class EOp(Expr):
    def __init__(self, vtype: VType, lexpr: Expr, rexpr: Expr, op):
        self.vtype = vtype
        self.lexpr = lexpr
        self.rexpr = rexpr
        self.op = op

    def to_str(self, ident=0):
        ret = " " * ident + "op {}:{}\n".format(self.op, self.vtype)
        ret += self.lexpr.to_str(ident + 2)
        ret += self.rexpr.to_str(ident + 2)
        return ret

    def get_code_lines(self, program: 'Program', keep_ref=False)\
            -> List['CodeLine']:
        l_code_lines = self.lexpr.get_code_lines(program)
        lval = l_code_lines[-1].get_var_name()
        r_code_lines = self.rexpr.get_code_lines(program)
        rval = r_code_lines[-1].get_var_name()
        code_lines = l_code_lines + r_code_lines

        instr, vtype = op_array(self.op, self.lexpr.vtype, self.rexpr.vtype)
        if instr == SPECIAL:
            raise NotImplementedError()
        else:
            code_lines.append(CodeLine(instr.format(lval, rval)))
        return code_lines


class ECall(Expr):
    def __init__(self, name: str, vtype: VType, args: [Expr]):
        self.name = name
        self.vtype = vtype
        self.args = args

    def to_str(self, ident=0):
        ret = " " * ident + "call {}:{}\n".format(self.name, self.vtype)
        for arg in self.args:
            ret += arg.to_str(ident + 2)
        return ret


class VariablesBlock(object):
    def __init__(self, upper_block: 'VariablesBlock' = None):
        self.vars = dict()
        self.arguments = []
        self.declared = set()
        self.upper = upper_block
        self.uid = UID.get_uid()

    def add_variable(self, name: str, type: VType, declare=False,
                     argument=False):
        assert isinstance(type, VType)
        if name in self.vars:
            raise NameError("Variable {} already exists.".format(name))
        self.vars[name] = type
        if argument:
            self.arguments.append(name)
        if declare:
            self.declare(name)

    def get_variable(self, name: str) -> VType:
        if name in self.vars:
            if name in self.declared:
                return self.vars[name]
            else:
                raise NameError("Variable {} not yet declared.".format(name))
        if self.upper is not None:
            return self.upper.get_variable(name)
        raise NameError("Variable {} doesn't exist.".format(name))

    def get_variable_name(self, name: str):
        if name in self.vars:
            return "%b{}_{}".format(self.uid, name)
        if self.upper is not None:
            return self.upper.get_variable_name(name)
        raise NameError("Variable {} doesn't exist.".format(name))

    def declare(self, name: str):
        assert name in self.vars
        self.declared.add(name)

    def assert_declared(self, name: str):
        if name in self.vars:
            if name not in self.declared:
                raise NameError("Variable {} not yet declared.".format(name))
        else:
            self.upper.assert_declared(name)

    def __iter__(self):
        for var in self.vars:
            yield var

    def to_str(self, ident=0):
        res = ""
        for name in self:
            res += " " * ident + "{}: {}\n".format(name,
                                                   self.get_variable(name))
        return res or (" " * ident + "--none--\n")


class Program(object):
    def __init__(self):
        self.types = dict()
        for typ in ["string", "int", "boolean", "void"]:
            self.types[typ] = VClass(typ)
        self.globals = VariablesBlock()
        self.last_vars = self.globals
        self.functions = dict()
        self.current_function = None

    def name_to_type(self, name: str) -> VType:
        if name in self.types:
            return self.types[name]

        if name.endswith("*"):
            base = VType.name_to_type(name[:-1])
            self.types[name] = VRef(base)
        elif name.endswith("[]"):
            base = VType.name_to_type(name[:-2])
            self.types[name] = VList(base)
        else:
            raise TypeNotFound(name)

    def __str__(self):
        res = "Program:\n"
        res += "  Classes:\n"
        for type in self.types:
            res += "    {}\n".format(type)
        res += "  Globals:\n"
        res += self.globals.to_str(4)
        res += "  Functions:\n"
        for fun in self.functions:
            res += self.functions[fun].to_str(4)
        return res


class Stmt(object):
    def to_str(self, ident=0):
        ret = " " * ident + "Generic Stmt\n"
        return ret

    def get_code_blocks(
            self, program: Program,
            next_code_block: 'CodeBlock' = None) -> List['CodeBlock']:
        raise NotImplementedError


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
    def to_str(self, ident=0):
        ret = " " * ident + "EmptyStmt\n"
        return ret

    def get_code_blocks(
            self, program: Program,
            next_code_block: 'CodeBlock' = None) -> List['CodeBlock']:
        code_lines = (br_block(next_code_block))
        return [CodeBlock(code_lines)]


class SAssi(Stmt):
    def __init__(self, texpr: Expr, vexpr: Expr):
        self.texpr = texpr
        self.vexpr = vexpr

    def to_str(self, ident=0):
        ret = " " * ident + "Assi\n"
        ret += self.texpr.to_str(ident + 2)
        ret += self.vexpr.to_str(ident + 2)
        return ret

    def get_code_blocks(
            self, program: Program,
            next_code_block: 'CodeBlock' = None) -> List['CodeBlock']:
        t_code_lines = self.texpr.get_code_lines(program, keep_ref=True)
        t_var = t_code_lines[-1].get_var_name()

        v_code_lines = self.vexpr.get_code_lines(program)
        v_val = v_code_lines[-1].get_var_name()

        vtype = self.vexpr.vtype.unref()
        if vtype.is_int():
            s_code_line = CodeLine("store i32 {}, i32* {}".format(v_val, t_var),
                                   save_result=False)
        elif vtype.is_bool():
            s_code_line = CodeLine("store i1 {}, i1* {}".format(v_val, t_var),
                                   save_result=False)
        else:
            raise ValueError(
                "Type {} not supported for assignment".format(vtype))

        # br_line
        br_lines = br_block(next_code_block)

        # Concatenation
        code_lines = t_code_lines + v_code_lines + [s_code_line] + br_lines
        return [CodeBlock(code_lines)]


class SIfElse(Stmt):
    def __init__(self, cond: Expr, ifstmt: Stmt, elsestmt: Stmt):
        self.cond = cond
        self.ifstmt = ifstmt
        # It will be set - maybe EmptyStmt
        self.elsestmt = elsestmt

    def to_str(self, ident=0):
        ret = " " * ident + "IfElse\n"
        ret += self.cond.to_str(ident + 2)
        ret += self.ifstmt.to_str(ident + 2)
        ret += self.elsestmt.to_str(ident + 2)
        return ret

    def get_code_blocks(
            self, program: Program,
            next_code_block: 'CodeBlock' = None) -> List['CodeBlock']:
        # End block
        brlines = br_block(next_code_block)
        end_block = CodeBlock(brlines)
        
        # True blocks
        true_blocks = self.ifstmt.get_code_blocks(program, end_block)

        # False blocks
        false_blocks = self.elsestmt.get_code_blocks(program, end_block)

        # Cond block
        cond_lines = self.cond.get_code_lines(program)

        brlines = cond_br_block(cond_lines[-1], true_blocks[0], false_blocks[0])
        cond_block = CodeBlock(cond_lines + brlines, False)

        # Setting ending appropriately
        if true_blocks[-1].ending and false_blocks[-1].ending:
            # If those blocks are ending, false block will indicate this.
            end_blocks = []
        else:
            end_blocks = [end_block]

        # Concatenation and return
        code_blocks = [cond_block] + true_blocks + false_blocks
        return code_blocks


class SWhile(Stmt):
    def __init__(self, cond: Expr, body: Stmt):
        self.cond = cond
        self.body = body

    def to_str(self, ident=0):
        ret = " " * ident + "While\n"
        ret += self.cond.to_str(ident + 2)
        ret += self.body.to_str(ident + 2)
        return ret

    def get_code_blocks(
            self, program: Program,
            next_code_block: 'CodeBlock' = None) -> List['CodeBlock']:
        if isinstance(self.cond, EConst):
            if self.cond.value:
                code_blocks = self.body.get_code_blocks(program, None)
                brlines = br_block(code_blocks[0])
                code_blocks[-1].codelines.extend(brlines)
                code_blocks[-1].ending = True  # It never returns, so it's OK.
            else:
                return []
        # End block
        brlines = br_block(next_code_block)
        end_block = CodeBlock(brlines)

        # It'll just jump to condition.
        first_code_block = CodeBlock([])

        # Main body
        code_blocks = self.body.get_code_blocks(program, first_code_block)

        # Condition
        cond_lines = self.cond.get_code_lines(program)

        brlines = cond_br_block(cond_lines[-1], code_blocks[0], end_block)
        cond_block = CodeBlock(cond_lines + brlines, False)

        # Jumping to condition from first code block.
        br_cond_lines = br_block(cond_block)

        first_code_block.codelines.extend(br_cond_lines)

        # Concateneting code blocks.
        code_blocks = [first_code_block] + code_blocks + [cond_block] + [end_block]
        return code_blocks


class SReturn(Stmt):
    def __init__(self, expr=None):
        self.expr = expr

    def to_str(self, ident=0):
        ret = " " * ident + "Return\n"
        if self.expr is not None:
            ret += self.expr.to_str(ident + 2)
        return ret

    def get_code_blocks(
            self, program: Program,
            next_code_block: 'CodeBlock' = None) -> List['CodeBlock']:
        del next_code_block  # We won't go there, because we return.
        if self.expr:
            codelines = self.expr.get_code_lines(program)
            vname = codelines[-1].get_var_name()
            vtype = self.expr.vtype
            if vtype.is_int():
                rline = "ret i32 {}".format(vname)
            elif vtype.is_bool():
                rline = "ret i1 {}".format(vname)
            else:
                raise NotImplementedError("Type not supproted")
            codelines.append(CodeLine(rline, save_result=False))
        else:
            codelines = [CodeLine("ret void", save_result=False)]
        code_block = CodeBlock(codelines, ending=True)
        return [code_block]


class CodeBlock(object):
    def __init__(self, codelines: ['CodeLine'], ending=False):
        self.codelines = codelines
        self.uid = UID.get_uid()
        self.ending = ending

    def get_label_name(self):
        return "L{}".format(self.uid)

    def get_source(self):
        source_lines = ["  {}:".format(self.get_label_name())]
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

    def to_str(self, ident=0, header=True):
        if header:
            ret = " " * ident + "block:\n"
        else:
            ret = ""
        ret += " " * ident + "  Vars:\n"
        ret += self.vars.to_str(ident + 4)
        ret += " " * ident + "  Stmts:\n"
        for stmt in self.stmts:
            ret += stmt.to_str(ident + 4)
        return ret

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

        # Make initialization code block

        init_codelines = []
        for varname in self.vars.vars:
            block_varname = self.vars.get_variable_name(varname)
            vtype = self.vars.vars[varname]
            if vtype.is_int():
                init_codelines.append(
                    CodeLine("{} = alloca i32".format(block_varname),
                             save_result=False))
                if varname in self.vars.arguments:
                    init_codelines.append(
                        CodeLine("store i32 %{}, i32* {}".format(varname,
                                                                 block_varname),
                                 save_result=False))
            elif vtype.is_bool():
                init_codelines.append(
                    CodeLine("{} = alloca i1".format(block_varname),
                             save_result=False))
                if varname in self.vars.arguments:
                    init_codelines.append(
                        CodeLine("store i1 %{}, i1* {}".format(varname,
                                                               block_varname),
                                 save_result=False))
            else:
                raise NotImplementedError(
                    "Type {} of {} unavailable for init".format(vtype, varname))
        if code_blocks:
            init_codelines.extend(br_block(code_blocks[0]))
        init_block = CodeBlock(init_codelines)
        return [init_block] + code_blocks


class Function(object):
    def __init__(self, name: str, block: Block):
        self.name = name
        self.block = block

    def to_str(self, ident=0):
        ret = " " * ident + "funtion {}:\n".format(self.name)
        ret += self.block.to_str(ident + 2, header=False)
        return ret

    def get_code_blocks(self, program: Program) -> List['CodeBlock']:
        return self.block.get_code_blocks(program)

    def get_source(self, program: Program):
        code_blocks = self.get_code_blocks(program)
        if not program.last_vars.get_variable(self.name).rtype.is_void():
            if (not code_blocks) or (not code_blocks[-1].ending):
                raise ValueError("Function {} doesn't have return.".format(
                    self.name))

        arg_strings = []
        for argname in self.block.vars.arguments:
            vtype = self.block.vars.get_variable(argname)
            if vtype.is_int():
                arg_strings.append('i32 %{}'.format(argname))
            elif vtype.is_bool():
                arg_strings.append('i1 %{}'.format(argname))
            else:
                raise NotImplementedError("Type {} of {} not supported yet."
                                          .format(vtype.name, argname))

        source_lines = [
            "define void @{}({}){{".format(self.name, ", ".join(arg_strings)),
        ]

        end_source_lines = [
            "}"
        ]

        for code_block in code_blocks:
            source_lines.append(code_block.get_source())
        return "\n".join(source_lines + end_source_lines)
