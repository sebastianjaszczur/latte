import os
import sys
from antlr4 import InputStream, CommonTokenStream
from antlr4.tree.Tree import TerminalNodeImpl

from LatteLexer import LatteLexer
from LatteParser import LatteParser
from LatteVisitor import LatteVisitor
from typedtree import Program, VFun, VariablesBlock, Block, Function, Stmt, \
    Expr, EConst, EOp

HELP = "Run this program with file.ins argument only."
EXTENSION_LATTE = ".lat"
EXTENSION_LL = ".ll"
EXTENSION_BC = ".bc"

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
        self.nextName = 1
        self.lines = []
        self.vars = dict()
        self.program = Program()

    def getNextName(self):
        name = "%i" + str(self.nextName)
        self.nextName += 1
        return name

    def getVar(self, name, ctx):
        if name in self.vars:
            return "%v_{var}_{num}".format(var=name, num=self.vars[name])
        else:
            raise LLVMVariableException(name, ctx)

    def createVar(self, name, ctx):
        if name not in self.vars:
            self.vars[name] = 0
        self.vars[name] += 1
        return self.getVar(name, ctx)

    def visitProgram(self, ctx: LatteParser.ProgramContext):
        for fundef in ctx.fundef():
            self.addFundefType(fundef)
        self.visitChildren(ctx)
        return self.program

    def addFundefType(self, ctx: LatteParser.FundefContext):
        name = str(ctx.IDENT())
        return_type = str(ctx.vtype().IDENT())
        arg_types = tuple([str(arg.vtype().IDENT()) for arg in ctx.arg()])

        self.program.globals.add_variable(name, VFun(return_type, arg_types))

    def visitFundef(self, ctx: LatteParser.FundefContext):
        name = str(ctx.IDENT())

        args = VariablesBlock(self.program.globals)
        for arg in ctx.arg():
            args.add_variable(str(arg.IDENT()), str(arg.vtype().IDENT()))

        block = self.visitBlock(ctx.block(), args)
        function = Function(name, block)

        self.program.functions[name] = function

    def visitBlock(self, ctx:LatteParser.BlockContext, vars=None):
        if vars is None:
            vars = VariablesBlock(self.program.last_vars)
        last_vars = self.program.last_vars
        self.program.last_vars = vars
        # ???

        for stmt in ctx.stmt():
            if not isinstance(stmt, LatteParser.SdeclContext):
                continue
            vtype = str(stmt.vtype().IDENT())
            for item in stmt.item():
                vars.add_variable(str(item.IDENT()), vtype)

        block = Block(vars)

        for stmt in ctx.stmt():
            block.stmts.append(self.visit(stmt))

        self.program.last_vars = last_vars

        return block

    def visitSassi(self, ctx:LatteParser.SassiContext):
        return Stmt()

    def visitSbloc(self, ctx:LatteParser.SblocContext):
        return self.visit(ctx.block())

    def visitSdecl(self, ctx:LatteParser.SdeclContext):
        return Stmt()

    def visitSexpr(self, ctx:LatteParser.SexprContext):
        return self.visit(ctx.expr())

    def visitSifel(self, ctx:LatteParser.SifelContext):
        return Stmt()

    def visitSretu(self, ctx:LatteParser.SretuContext):
        return Stmt()

    def visitSsemi(self, ctx:LatteParser.SsemiContext):
        return Stmt()

    def visitSwhil(self, ctx:LatteParser.SwhilContext):
        return Stmt()

    def visitEintv(self, ctx:LatteParser.EintvContext):
        vtype = self.program.name_to_type('int')
        val = int(str(ctx.INT()))
        return EConst(vtype, val)

    def visitEstrv(self, ctx:LatteParser.EstrvContext):
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
            vtype = lexpr.vtype
        elif (lexpr.vtype == rexpr.vtype == self.program.name_to_type('string')
                and op == "+"):
            vtype = lexpr.vtype
        else:
            raise NameError("Wrong types")
        return EOp(vtype, lexpr, rexpr, op)

    def visitEmult(self, ctx:LatteParser.EmultContext):
        if ctx.MUL():
            op = "*"
        elif ctx.DIV():
            op = "-"
        elif ctx.MOD():
            op = "-"
        else:
            raise NameError("Unknown operator.")
        lexpr = self.visit(ctx.expr(0))
        rexpr = self.visit(ctx.expr(1))
        if lexpr.vtype == rexpr.vtype == self.program.name_to_type('int'):
            vtype = lexpr.vtype
        else:
            raise NameError("Wrong types")
        return EOp(vtype, lexpr, rexpr, op)


    '''
    def visitSass(self, ctx: LatteParser.SassContext):
        name = self.createVar(ctx.IDENT().symbol.text, ctx)
        res0 = self.visit(ctx.expr())
        line = "{name} = add i32 {res}, 0".format(name=name, res=res0)
        self.lines.append(line)

    def visitSexpr(self, ctx: LatteParser.EaddContext):
        res0 = self.visitChildren(ctx)
        self.lines.append("call void @printInt(i32 {})".format(res0))

    def visitEop(self, op, ctx: LatteParser.EaddContext):
        res0 = self.visit(ctx.expr(0))
        res1 = self.visit(ctx.expr(1))
        name = self.getNextName()
        line = "{name} = {op} i32 {a0}, {a1}".format(
            name=name, op=op, a0=res0, a1=res1)
        self.lines.append(line)
        return name

    def visitEadd(self, ctx: LatteParser.EaddContext):
        return self.visitEop("add", ctx)

    def visitEsub(self, ctx: LatteParser.EaddContext):
        return self.visitEop("sub", ctx)

    def visitEmuldiv(self, ctx: LatteParser.EaddContext):
        op = "mul" if ctx.MUL() is not None else "sdiv"
        return self.visitEop(op, ctx)

    def visitEint(self, ctx: LatteParser.EintContext):
        return ctx.INT().symbol.text

    def visitEident(self, ctx: LatteParser.EidentContext):
        return self.getVar(ctx.IDENT().symbol.text, ctx)

    def visitEpar(self, ctx:LatteParser.EparContext):
        return self.visit(ctx.expr())
    '''


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

    #print(BEFORE)#, file=outputfile)
    print(LLVMVisitor().visit(tree))#, file=outputfile)
    #print(AFTER)#, file=outputfile)


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
