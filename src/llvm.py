import os
import sys
from antlr4 import InputStream, CommonTokenStream
from antlr4.tree.Tree import TerminalNodeImpl

from LatteLexer import LatteLexer
from LatteParser import LatteParser
from LatteVisitor import LatteVisitor
from typedtree import Program, VFun, VariablesBlock, Block, Function, Stmt, \
    Expr, EConst, EOp, ECall, EVar, VRef, SAssi, EmptyStmt, SIfElse, SWhile, \
    SReturn

# TODO: Better error handling

HELP = "Run this program with file.ins argument only."
EXTENSION_LATTE = ".lat"
EXTENSION_LL = ".ll"
EXTENSION_BC = ".bc"

# TODO: BEFORE/AFTER refactor
BEFORE = """
@dnl = internal constant [4 x i8] c"%d\\0A\\00"

declare i32 @printf(i8*, ...)

define void @printInt(i32 %x) {
  %t0 = getelementptr [4 x i8], [4 x i8]* @dnl, i32 0, i32 0
  call i32 (i8*, ...) @printf(i8* %t0, i32 %x)
  ret void
}

define i32 @main() {
  """

AFTER = """
  ret i32 0
}
"""


class LLVMVariableException(Exception):
    def __init__(self, name, ctx):
        self.name = name
        self.ctx = ctx


class LLVMVisitor(LatteVisitor):
    def __init__(self):
        self.program = Program()

    def visitProgram(self, ctx: LatteParser.ProgramContext):
        for fundef in ctx.fundef():
            self.addFundefType(fundef)
        self.visitChildren(ctx)
        return self.program

    def addFundefType(self, ctx: LatteParser.FundefContext):
        name = str(ctx.IDENT())
        return_type = self.program.name_to_type(str(ctx.vtype().IDENT()))
        arg_types = tuple(
            [self.program.name_to_type(str(arg.vtype().IDENT()))
             for arg in ctx.arg()])

        self.program.globals.add_variable(name, VFun(return_type, arg_types),
                                          declare=True)

    def visitFundef(self, ctx: LatteParser.FundefContext):
        name = str(ctx.IDENT())

        args = VariablesBlock(self.program.globals)
        for arg in ctx.arg():
            args.add_variable(
                str(arg.IDENT()),
                self.program.name_to_type(str(arg.vtype().IDENT())),
                declare=True)

        block = self.visitBlock(ctx.block(), args)
        function = Function(name, block)

        self.program.functions[name] = function

    def visitBlock(self, ctx: LatteParser.BlockContext, vars=None):
        if vars is None:
            vars = VariablesBlock(self.program.last_vars)
        last_vars = self.program.last_vars
        self.program.last_vars = vars

        for stmt in ctx.stmt():
            if not isinstance(stmt, LatteParser.SdeclContext):
                continue
            vtype = self.program.name_to_type(str(stmt.vtype().IDENT()))
            for item in stmt.item():
                vars.add_variable(str(item.IDENT()), vtype)

        block = Block(vars)

        for stmt in ctx.stmt():
            typed_stmt = self.visit(stmt)
            try:
                # We assume it's iterable.
                for tstmt in typed_stmt:
                    assert isinstance(tstmt, Stmt)
                    block.stmts.append(tstmt)
            except TypeError:
                block.stmts.append(typed_stmt)

        self.program.last_vars = last_vars

        return block

    def visitSbloc(self, ctx: LatteParser.SblocContext):
        return self.visit(ctx.block())

    def visitSincr(self, ctx: LatteParser.SincrContext):
        return self.visitDecrIncr(ctx, '+')

    def visitSdecr(self, ctx: LatteParser.SdecrContext):
        return self.visitDecrIncr(ctx, '-')

    def visitDecrIncr(self, ctx, plusminus: str):
        texpr = self.visit(ctx.expr())
        if not isinstance(texpr.vtype, VRef):
            raise ValueError("Invalid incr/decr target.")
        if self.program.name_to_type('int') != texpr.vtype:
            raise ValueError("Only int supported for incr/decr")
        vexpr = EOp(self.program.name_to_type('int'),
                    self.visit(ctx.expr()),
                    EConst(self.program.name_to_type('int'), 1),
                    plusminus)
        return SAssi(texpr, vexpr)

    def visitSassi(self, ctx: LatteParser.SassiContext):
        vexpr = self.visit(ctx.expr(1))
        texpr = self.visit(ctx.expr(0))
        if not isinstance(texpr.vtype, VRef):
            raise ValueError("Invalid assignment target.")
        return SAssi(texpr, vexpr)

    def visitSdecl(self, ctx: LatteParser.SdeclContext):
        vtype = self.program.name_to_type(str(ctx.vtype().IDENT()))
        tstmts = []
        for item in ctx.item():
            name = str(item.IDENT())
            expr = item.expr()
            if expr:
                vexpr = self.visit(expr)
            else:
                vexpr = vtype.get_default_expr()
            texpr = EVar(name, VRef(vtype))
            if not isinstance(texpr.vtype, VRef):
                raise ValueError("Invalid declaration target.")
            tstmts.append(SAssi(texpr, vexpr))
            self.program.last_vars.declare(name)
        return tstmts

    def visitSexpr(self, ctx: LatteParser.SexprContext):
        return self.visit(ctx.expr())

    def visitSifel(self, ctx: LatteParser.SifelContext):
        condition = self.visit(ctx.expr())
        if condition.vtype != self.program.name_to_type('boolean'):
            raise ValueError("Invalid condition type")
        ifstmt = self.visit(ctx.stmt(0))
        if ctx.stmt(1):
            elsestmt = self.visit(ctx.stmt(1))
        else:
            elsestmt = EmptyStmt()
        return SIfElse(condition, ifstmt, elsestmt)

    def visitSretu(self, ctx: LatteParser.SretuContext):
        # TODO: Type-checking
        # TODO: Cheking if everywhere we have return.
        if ctx.expr():
            rexpr = self.visit(ctx.expr())
            return SReturn(rexpr)
        else:
            return SReturn()

    def visitSsemi(self, ctx: LatteParser.SsemiContext):
        return EmptyStmt()

    def visitSwhil(self, ctx: LatteParser.SwhilContext):
        condition = self.visit(ctx.expr())
        if condition.vtype != self.program.name_to_type('boolean'):
            raise ValueError("Invalid condition type")
        body = self.visit(ctx.stmt())
        return SWhile(condition, body)

    def visitEintv(self, ctx: LatteParser.EintvContext):
        vtype = self.program.name_to_type('int')
        val = int(str(ctx.INT()))
        return EConst(vtype, val)

    def visitEtrue(self, ctx: LatteParser.EtrueContext):
        vtype = self.program.name_to_type('boolean')
        return EConst(vtype, True)

    def visitEfals(self, ctx: LatteParser.EfalsContext):
        vtype = self.program.name_to_type('boolean')
        return EConst(vtype, False)

    def visitEstrv(self, ctx: LatteParser.EstrvContext):
        # TODO: fix strings
        raise TypeError("Strings are not handled well.")

    def visitEadd(self, ctx: LatteParser.EaddContext):
        if ctx.ADD():
            op = "+"
        elif ctx.SUB():
            op = "-"
        else:
            raise NameError("Unknown operator.")
        lexpr = self.visit(ctx.expr(0))
        rexpr = self.visit(ctx.expr(1))
        if lexpr.vtype == rexpr.vtype == self.program.name_to_type('int'):
            vtype = self.program.name_to_type('int')
        elif (lexpr.vtype == rexpr.vtype == self.program.name_to_type('string')
              and op == "+"):
            vtype = self.program.name_to_type('string')
        else:
            raise NameError("Wrong types")
        return EOp(vtype, lexpr, rexpr, op)

    def visitEmult(self, ctx: LatteParser.EmultContext):
        if ctx.MUL():
            op = "*"
        elif ctx.DIV():
            op = "/"
        elif ctx.MOD():
            op = "%"
        else:
            raise NameError("Unknown operator.")
        lexpr = self.visit(ctx.expr(0))
        rexpr = self.visit(ctx.expr(1))
        if lexpr.vtype == rexpr.vtype == self.program.name_to_type('int'):
            vtype = self.program.name_to_type('int')
        else:
            raise NameError("Wrong types")
        return EOp(vtype, lexpr, rexpr, op)

    def visitEand(self, ctx: LatteParser.EandContext):
        op = "&&"
        lexpr = self.visit(ctx.expr(0))
        rexpr = self.visit(ctx.expr(1))
        if lexpr.vtype == rexpr.vtype == self.program.name_to_type('boolean'):
            vtype = self.program.name_to_type('boolean')
        else:
            raise NameError("Wrong types")
        return EOp(vtype, lexpr, rexpr, op)

    def visitEor(self, ctx: LatteParser.EandContext):
        op = "||"
        lexpr = self.visit(ctx.expr(0))
        rexpr = self.visit(ctx.expr(1))
        if lexpr.vtype == rexpr.vtype == self.program.name_to_type('boolean'):
            vtype = self.program.name_to_type('boolean')
        else:
            raise NameError("Wrong types")
        return EOp(vtype, lexpr, rexpr, op)

    def visitEcomp(self, ctx: LatteParser.EcompContext):
        # TODO: comparison of strings
        # TODO: comparison of bools?
        if ctx.LT():
            op = "<"
        elif ctx.LE():
            op = "<="
        elif ctx.GT():
            op = ">"
        elif ctx.GE():
            op = ">="
        elif ctx.EQ():
            op = "=="
        elif ctx.NE():
            op = "!="
        else:
            raise NameError("Unknown operator.")
        lexpr = self.visit(ctx.expr(0))
        rexpr = self.visit(ctx.expr(1))
        if lexpr.vtype == rexpr.vtype == self.program.name_to_type('int'):
            vtype = self.program.name_to_type('boolean')
        else:
            raise NameError("Wrong types")
        return EOp(vtype, lexpr, rexpr, op)

    def visitEcall(self, ctx: LatteParser.EcallContext):
        name = str(ctx.IDENT())
        vtype = self.program.globals.get_variable(name)
        assert isinstance(vtype, VFun)
        rtype = vtype.rtype
        argtypes = vtype.params
        args = [self.visit(arg) for arg in ctx.expr()]

        if len(argtypes) != len(args):
            raise ValueError("Wrong number of arguments to function.")
        for arg, argtype in zip(args, argtypes):
            print(arg.vtype.__class__, argtype.__class__)
            if arg.vtype != argtype:
                raise ValueError("Wrong type of an argument to {}".format(name))

        return ECall(name, rtype, args)

    def visitEiden(self, ctx: LatteParser.EidenContext):
        name = str(ctx.IDENT())
        vtype = self.program.last_vars.get_variable(name)
        return EVar(name, VRef(vtype))

    def visitEminu(self, ctx: LatteParser.EminuContext):
        # TODO: onesided operators
        pass

    def visitEnega(self, ctx: LatteParser.EnegaContext):
        # TODO: onesided operators
        pass

    def visitErrorNode(self, node):
        # TODO: Error handling; idea: gather all errors in one place, show them all
        pass

    def visitItem(self, ctx: LatteParser.ItemContext):
        # it should not happen
        assert False

    def visitVtype(self, ctx: LatteParser.VtypeContext):
        # TODO: maybe replace those ugly vtypes to strings?
        # it should not happen
        assert False

    def visitArg(self, ctx: LatteParser.ArgContext):
        # it should not happen
        assert False


def print_parse_tree(tree, indent_level=0):
    if isinstance(tree, TerminalNodeImpl):
        return
    print(("| " * indent_level) + "> " + str(tree.__class__.__name__),
          str(tree.getText()))
    for c in tree.getChildren():
        print_parse_tree(c, indent_level + 1)


def generate_ll(sourcefile, outputfile):
    inputstrewam = InputStream(sourcefile.read())
    lexer = LatteLexer(inputstrewam)
    tokenstream = CommonTokenStream(lexer)
    parser = LatteParser(tokenstream)
    tree = parser.program()

    print("Parse tree")
    print_parse_tree(tree)
    print()

    # print(BEFORE)#, file=outputfile)
    print(LLVMVisitor().visit(tree))  # , file=outputfile)
    # print(AFTER)#, file=outputfile)


def main():
    if len(sys.argv) != 2:
        print(HELP, file=sys.stderr)
        print("There is a wrong number of arguments.", file=sys.stderr)
        sys.exit(1)
    sourcename = str(sys.argv[1])

    if not sourcename.endswith(EXTENSION_LATTE):
        print(HELP, file=sys.stderr)
        print("The file extension is not recognized.", file=sys.stderr)
        sys.exit(2)
    basename = sourcename[:-len(EXTENSION_LATTE)]
    llname = basename + EXTENSION_LL

    print("Compiling {} to {}".format(sourcename, llname))
    try:
        with open(sourcename, "r") as sourcefile:
            with open(llname, "w") as llfile:
                generate_ll(sourcefile, llfile)
    except LLVMVariableException as ve:
        firstToken = ve.ctx.parser.getTokenStream().get(
            ve.ctx.getSourceInterval()[0])
        print("line {}:{} variable not declared before: '{}'".format(
            firstToken.line, firstToken.column, ve.name),
            file=sys.stderr)
        os.remove(llname)
        exit(3)

    os.system("llvm-as {}".format(llname))

    print("Done.")


if __name__ == '__main__':
    main()
