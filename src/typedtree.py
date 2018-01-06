from operator import iadd


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
        ret = " "*ident + "Expr\n"
        return ret


class EConst(Expr):
    def __init__(self, vtype: VType, value):
        self.value = value
        self.vtype = vtype

    def to_str(self, ident=0):
        ret = " "*ident + "const {}:{}\n".format(self.value, self.vtype)
        return ret


class EVar(Expr):
    def __init__(self, name: str, vtype: VType):
        self.name = name
        self.vtype = vtype

    def to_str(self, ident=0):
        ret = " "*ident + "var {}:{}\n".format(self.name, self.vtype)
        return ret


class EOp(Expr):
    def __init__(self, vtype: VType, lexpr: Expr, rexpr: Expr, op):
        self.vtype = vtype
        self.lexpr = lexpr
        self.rexpr = rexpr
        self.op = op

    def to_str(self, ident=0):
        ret = " "*ident + "op {}:{}\n".format(self.op, self.vtype)
        ret += self.lexpr.to_str(ident+2)
        ret += self.rexpr.to_str(ident+2)
        return ret


class ECall(Expr):
    def __init__(self, name: str, vtype: VType, args: [Expr]):
        self.name = name
        self.vtype = vtype
        self.args = args

    def to_str(self, ident=0):
        ret = " "*ident + "call {}:{}\n".format(self.name, self.vtype)
        for arg in self.args:
            ret += arg.to_str(ident+2)
        return ret


class VariablesBlock(object):
    def __init__(self, upper_block: 'VariablesBlock'=None):
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
            res += " "*ident + "{}: {}\n".format(name, self.get_variable(name))
        return res or (" "*ident + "--none--\n")


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
        ret = " "*ident + "Generic Stmt\n"
        return ret


class EmptyStmt(object):
    def to_str(self, ident=0):
        ret = " " * ident + "EmptyStmt\n"
        return ret


class SAssi(Stmt):
    def __init__(self, texpr, vexpr):
        self.texpr = texpr
        self.vexpr = vexpr

    def to_str(self, ident=0):
        ret = " "*ident + "Assi\n"
        ret += self.texpr.to_str(ident+2)
        ret += self.vexpr.to_str(ident + 2)
        return ret


class SIfElse(Stmt):
    def __init__(self, cond, ifstmt, elsestmt):
        self.cond = cond
        self.ifstmt = ifstmt
        self.elsestmt = elsestmt

    def to_str(self, ident=0):
        ret = " "*ident + "IfElse\n"
        ret += self.cond.to_str(ident+2)
        ret += self.ifstmt.to_str(ident+2)
        ret += self.elsestmt.to_str(ident+2)
        return ret


class SWhile(Stmt):
    def __init__(self, cond, body):
        self.cond = cond
        self.body = body

    def to_str(self, ident=0):
        ret = " "*ident + "While\n"
        ret += self.cond.to_str(ident+2)
        ret += self.body.to_str(ident+2)
        return ret


class SReturn(Stmt):
    def __init__(self, expr=None):
        self.expr = expr

    def to_str(self, ident=0):
        ret = " "*ident + "Return\n"
        if self.expr is not None:
            ret += self.expr.to_str(ident+2)
        return ret


class Block(Stmt):
    def __init__(self, vars: VariablesBlock):
        self.vars = vars
        self.stmts = []

    def to_str(self, ident=0, header=True):
        if header:
            ret = " "*ident + "block:\n"
        else:
            ret = ""
        ret += " "*ident + "  Vars:\n"
        ret += self.vars.to_str(ident+4)
        ret += " " * ident + "  Stmts:\n"
        for stmt in self.stmts:
            ret += stmt.to_str(ident+4)
        return ret


class Function(object):
    def __init__(self, name: str, block: Block):
        self.name = name
        self.block = block

    def to_str(self, ident=0):
        ret = " "*ident + "funtion {}:\n".format(self.name)
        ret += self.block.to_str(ident+2, header=False)
        return ret



