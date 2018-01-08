from antlr4.error.ErrorListener import ErrorListener

import latte_tree

BOOL = 'i1'
INT = 'i32'
STRING = 'i8*'
VOID = 'void'
INTERNAL_REF_SIGN = '&'
MUL = '*'
DIV = '/'
MOD = '%'
ADD = '+'
SUB = '-'
NEG = '!'

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


class UID(object):
    last_uid = 0

    @staticmethod
    def get_uid():
        UID.last_uid += 1
        return UID.last_uid


class CompilationError(Exception):
    def __init__(self, msg, ctx):
        if ctx is None:
            self.line = 0
            self.column = 0
            self.text = ""
        else:
            self.line = ctx.start.line
            self.column = ctx.start.column
            self.text = ctx.getText()
        self.msg = msg

    def __str__(self):
        return "line {}:{} {}:\n{}".format(
            self.line, self.column, self.msg, self.text)


class ErrorRaiser(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        raise CompilationError(line, column, msg)


class VType(object):
    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if not isinstance(other, VType):
            return False
        return self.unref().name == other.unref().name

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

    def is_intboolstring(self):
        return self.is_int() or self.is_bool() or self.is_string()

    def llvm_type(self):
        raise NotImplementedError()


class VRef(VType):
    def __init__(self, vtype: VType):
        if isinstance(vtype, VRef):
            # No references to references.
            vtype = vtype.unref()
        self.vtype = vtype
        self.name = vtype.name + INTERNAL_REF_SIGN

    def unref(self):
        return self.vtype.unref()

    def llvm_type(self):
        return self.vtype.llvm_type() + "*"


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
            return latte_tree.EConst(self, 0, None)
        elif self.is_bool():
            return latte_tree.EConst(self, False, None)
        elif self.is_string():
            return latte_tree.EConst(self, b"", None)
        else:
            raise NotImplementedError()

    def llvm_type(self):
        if self.is_bool():
            return BOOL
        elif self.is_int():
            return INT
        elif self.is_void():
            return VOID
        elif self.is_string():
            return STRING
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
