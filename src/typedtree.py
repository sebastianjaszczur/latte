from operator import iadd
from typing import List


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
    def __init__(self, name):
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
        if isinstance(self, VRef):
            return self.vtype.unref()
        return self


class VList(VType):
    def __init__(self, vtype):
        self.name = vtype.name + '[]'
        self.vtype = vtype


class VRef(VType):
    def __init__(self, vtype):
        if isinstance(vtype, VRef):
            # No references to references.
            vtype = vtype.unref()
        self.vtype = vtype
        self.name = vtype.name + "*"


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
    def __init__(self, name: str, fields: {str: VType}, methods: {str: VFun}):
        self.name = name
        self.fields = fields
        self.methods = methods

    def get_default_expr(self):
        if self.name == 'int':
            return EConst(self, 0)
        elif self.name == 'boolean':
            return EConst(self, False)
        elif self.name == 'str':
            return EConst(self, "")
        else:
            raise ValueError("Default for {} not available.".format(self))


class Expr(object):
    def __init__(self, vtype: VType):
        self.vtype = vtype

    def to_str(self, ident=0):
        ret = " " * ident + "Expr\n"
        return ret

    def get_code_lines(self, program: 'Program', keep_ref=False) -> List['CodeLine']:
        return [CodeLine("Generic code line", save_result=True)]
        # raise NotImplementedError

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


class EVar(Expr):
    def __init__(self, name: str, vtype: VType):
        self.name = name
        self.vtype = vtype

    def to_str(self, ident=0):
        ret = " " * ident + "var {}:{}\n".format(self.name, self.vtype)
        return ret


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
        self.declared = set()
        self.upper = upper_block

    def add_variable(self, name: str, type: VType, declare=False):
        assert isinstance(type, VType)
        if name in self.vars:
            raise NameError("Variable already exists.")
        self.vars[name] = type
        if declare:
            self.declare(name)

    def get_variable(self, name: str):
        if name in self.vars:
            if name in self.declared:
                return self.vars[name]
            else:
                raise NameError("Variable {} not yet declared.".format(name))
        if self.upper is not None:
            return self.upper.get_variable(name)
        raise NameError("Variable doesn't exist.")

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
            self.types[typ] = VClass(typ, fields={}, methods={})
        self.globals = VariablesBlock()
        self.last_vars = self.globals
        self.functions = dict()

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
        return [CodeBlock([CodeLine("Generic code stmt")])]


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

        type = self.vexpr.vtype.unref()
        if type == program.name_to_type('int'):
            s_code_line = CodeLine("store i32 {}, i32* {}".format(v_val, t_var),
                                   save_result=False)
        elif type == program.name_to_type('boolean'):
            s_code_line = CodeLine("store i1 {}, i1* {}".format(v_val, t_var),
                                   save_result=False)
        else:
            raise ValueError(
                "Type {} not supported for assignment".format(type))

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
        false_blocks = self.ifstmt.get_code_blocks(program, end_block)

        # Cond block
        cond_lines = self.cond.get_code_lines(program)

        brlines = cond_br_block(cond_lines[-1], true_blocks[0], false_blocks[0])
        cond_block = CodeBlock(cond_lines + brlines, False)

        # Setting ending appropriately
        end_block.ending = true_blocks[-1].ending and false_blocks[-1].ending

        # Concatenation and return
        code_blocks = [cond_block] + true_blocks + false_blocks + [end_block]
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
            rline = "ret {}".format(vname)
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
        source_lines = ["  {}: #{}".format(self.get_label_name(),
                                           "END" if self.ending else "")]
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
        code_blocks = []
        for stmt in self.stmts[::-1]:
            new_code_blocks = stmt.get_code_blocks(program, next_code_block)
            if len(new_code_blocks) > 0:
                next_code_block = new_code_blocks[0]
                if new_code_blocks[-1].ending:
                    # remove the rest, because we returned
                    code_blocks = []
                code_blocks = new_code_blocks + code_blocks
        return code_blocks


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

    def get_source(self, program):
        code_blocks = self.get_code_blocks(program)
        first_label = code_blocks[0].get_label_name()

        source_lines = [
            "define void @{}(SOMETHINGS){{".format(self.name),
            "  BEG:",
            "    initialization of vars goes here!",
            "    br label %{}".format(first_label),
        ]

        for code_block in code_blocks:
            source_lines.append(code_block.get_source())
        return "\n".join(source_lines)
