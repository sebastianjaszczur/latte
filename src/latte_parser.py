from LatteParser import LatteParser
from LatteVisitor import LatteVisitor
from latte_tree import Program, VariablesBlock, Function, Block, Stmt, EOp, \
    EConst, SAssi, EVar, EmptyStmt, SIfElse, SReturn, SWhile, op_array, ECall, \
    EUnaryOp, ENew, EAttr
from latte_misc import MUL, DIV, MOD, ADD, SUB, LT, LE, GT, GE, EQ, NE, AND, \
    OR, VRef, VFun, VBool, VInt, VString, CompilationError, NEG, VClass


class LLVMVariableException(Exception):
    def __init__(self, name, ctx):
        self.name = name
        self.ctx = ctx


class LLVMVisitor(LatteVisitor):
    def __init__(self):
        self.program = Program()

    def visitProgram(self, ctx: LatteParser.ProgramContext):
        for classdef in ctx.classdef():
            self.addClassdefType(classdef)
        for fundef in ctx.fundef():
            self.addFundefType(fundef)

        for classdef in ctx.classdef():
            self.visitClassdef(classdef)
        for fundef in ctx.fundef():
            self.visitFundef(fundef)
        return self.program

    def addFundefType(self, ctx: LatteParser.FundefContext):
        name = str(ctx.IDENT())
        return_type = self.program.name_to_type(str(ctx.vtype().IDENT()), ctx)
        arg_types = tuple(
            [self.program.name_to_type(str(arg.vtype().IDENT()), arg)
             for arg in ctx.arg()])

        self.program.globals.add_variable(name, VFun(return_type, arg_types),
                                          ctx)

    def addClassdefType(self, ctx:LatteParser.ClassdefContext):
        name = str(ctx.IDENT())
        self.program.add_type(name, ctx)

    def visitClassdef(self, ctx: LatteParser.ClassdefContext):
        name = str(ctx.IDENT())
        class_type = self.program.name_to_type(name, ctx)
        assert isinstance(class_type, VClass)
        for field in ctx.field():
            vtype = self.program.name_to_type(str(field.vtype().IDENT()), field)
            field_name = str(field.IDENT())
            class_type.add_field(field_name, vtype, field)

    def visitFundef(self, ctx: LatteParser.FundefContext):
        name = str(ctx.IDENT())

        vars = VariablesBlock(self.program.globals)
        args = []
        for arg in ctx.arg():
            args.append(str(arg.IDENT()))
            vars.add_variable(
                str(arg.IDENT()),
                self.program.name_to_type(str(arg.vtype().IDENT()), arg), arg)

        self.program.last_vars = vars
        self.program.current_function = name

        block = self.visitBlock(ctx.block())

        self.program.current_function = None
        self.program.last_vars = None

        function = Function(name, vars, block, args, ctx)
        self.program.functions[name] = function

    def visitBlock(self, ctx: LatteParser.BlockContext):
        vars = VariablesBlock(self.program.last_vars)
        last_vars = self.program.last_vars
        self.program.last_vars = vars

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
        return self.visitDecrIncr(ctx, ADD)

    def visitSdecr(self, ctx: LatteParser.SdecrContext):
        return self.visitDecrIncr(ctx, SUB)

    def visitDecrIncr(self, ctx, op: str):
        texpr = self.visit(ctx.expr())
        if not isinstance(texpr.vtype, VRef):
            raise CompilationError("invalid incr/decr target", ctx)
        if not texpr.vtype.is_int():
            raise CompilationError("invalid incr/decr type", ctx)
        vexpr = EOp(VInt(), self.visit(ctx.expr()),
                    EConst(VInt(), 1, ctx), op, ctx)
        return SAssi(texpr, vexpr, ctx)

    def visitSassi(self, ctx: LatteParser.SassiContext):
        vexpr = self.visit(ctx.expr(1))
        texpr = self.visit(ctx.expr(0))
        if not isinstance(texpr.vtype, VRef):
            raise CompilationError("invalid assignment target", ctx)
        if vexpr.vtype != texpr.vtype:
            raise CompilationError("invalid assignment type", ctx)
        return SAssi(texpr, vexpr, ctx)

    def visitSdecl(self, ctx: LatteParser.SdeclContext):
        '''
        for stmt in ctx.stmt():
            if not isinstance(stmt, LatteParser.SdeclContext):
                continue
            vtype = self.program.name_to_type(str(stmt.vtype().IDENT()), stmt)
            for item in stmt.item():
                vars.add_variable(str(item.IDENT()), vtype, stmt)
        '''
        vtype = self.program.name_to_type(str(ctx.vtype().IDENT()), ctx)
        if not isinstance(vtype, VClass) or vtype.is_void():
            raise CompilationError("type not declarable", ctx)
        tstmts = []
        for item in ctx.item():
            name = str(item.IDENT())
            expr = item.expr()
            if expr:
                vexpr = self.visit(expr)
            else:
                vexpr = vtype.get_default_expr()
            if vtype != vexpr.vtype:
                raise CompilationError("invalid assignment type", item)
            self.program.last_vars.add_variable(name, vtype, item)
            texpr = EVar(self.program.last_vars.get_variable_name(name, item),
                         VRef(vtype), ctx)
            if not isinstance(texpr.vtype, VRef):
                raise CompilationError("invalid declaration target", ctx)
            tstmts.append(SAssi(texpr, vexpr, item))
        return tstmts

    def visitSexpr(self, ctx: LatteParser.SexprContext):
        return self.visit(ctx.expr())

    def visitSifel(self, ctx: LatteParser.SifelContext):
        condition = self.visit(ctx.expr())
        if not condition.vtype.is_bool():
            raise CompilationError("invalid condition type", ctx)
        if isinstance(ctx.stmt(0), LatteParser.SdeclContext):
            raise CompilationError(
                "declaration not allowed directly in if-body", ctx)
        if isinstance(ctx.stmt(1), LatteParser.SdeclContext):
            raise CompilationError(
                "declaration not allowed directly in else-body", ctx)
        ifstmt = self.visit(ctx.stmt(0))
        if ctx.stmt(1):
            elsestmt = self.visit(ctx.stmt(1))
        else:
            elsestmt = EmptyStmt()
        return SIfElse(condition, ifstmt, elsestmt)

    def visitSretu(self, ctx: LatteParser.SretuContext):
        funtype = self.program.last_vars.get_variable(
            self.program.current_function, ctx)
        assert isinstance(funtype, VFun)
        rtype = funtype.rtype
        if ctx.expr():
            rexpr = self.visit(ctx.expr())
            if rexpr.vtype == rtype:
                return SReturn(ctx, rexpr)
        elif rtype.is_void():
            return SReturn(ctx)
        raise CompilationError("invalid return statement", ctx)

    def visitSsemi(self, ctx: LatteParser.SsemiContext):
        return EmptyStmt()

    def visitSwhil(self, ctx: LatteParser.SwhilContext):
        condition = self.visit(ctx.expr())
        if not condition.vtype.is_bool():
            raise CompilationError("invalid condition type", ctx)
        if isinstance(ctx.stmt(), LatteParser.SdeclContext):
            raise CompilationError(
                "declaration not allowed directly in while-body", ctx)
        body = self.visit(ctx.stmt())
        return SWhile(condition, body)

    def visitEpare(self, ctx:LatteParser.EpareContext):
        return self.visit(ctx.expr())

    def visitEintv(self, ctx: LatteParser.EintvContext):
        vtype = VInt()
        val = int(str(ctx.INT()))
        if val >= 2**32:
            raise CompilationError('integer too big', ctx)
        return EConst(vtype, val, ctx)

    def visitEtrue(self, ctx: LatteParser.EtrueContext):
        vtype = VBool()
        return EConst(vtype, True, ctx)

    def visitEfals(self, ctx: LatteParser.EfalsContext):
        vtype = VBool()
        return EConst(vtype, False, ctx)

    def visitEstrv(self, ctx: LatteParser.EstrvContext):
        vtype = VString()
        val = bytes(
            bytes(str(ctx.STRING())[1:-1], "utf-8").decode("unicode_escape"),
            'utf-8')
        self.program.constants.add_constant(val)
        return EConst(vtype, val, ctx)

    def visitEadd(self, ctx: LatteParser.EaddContext):
        if ctx.ADD():
            op = ADD
        elif ctx.SUB():
            op = SUB
        else:
            raise CompilationError("unknown operator", ctx)
        lexpr = self.visit(ctx.expr(0))
        rexpr = self.visit(ctx.expr(1))
        _, vtype = op_array(ctx, op, lexpr.vtype, rexpr.vtype)
        return EOp(vtype, lexpr, rexpr, op, ctx)

    def visitEmult(self, ctx: LatteParser.EmultContext):
        if ctx.MUL():
            op = MUL
        elif ctx.DIV():
            op = DIV
        elif ctx.MOD():
            op = MOD
        else:
            raise CompilationError("unknown operator", ctx)
        lexpr = self.visit(ctx.expr(0))
        rexpr = self.visit(ctx.expr(1))
        _, vtype = op_array(ctx, op, lexpr.vtype, rexpr.vtype)
        return EOp(vtype, lexpr, rexpr, op, ctx)

    def visitEand(self, ctx: LatteParser.EandContext):
        op = AND
        lexpr = self.visit(ctx.expr(0))
        rexpr = self.visit(ctx.expr(1))
        _, vtype = op_array(ctx, op, lexpr.vtype, rexpr.vtype)
        return EOp(vtype, lexpr, rexpr, op, ctx)

    def visitEor(self, ctx: LatteParser.EandContext):
        op = OR
        lexpr = self.visit(ctx.expr(0))
        rexpr = self.visit(ctx.expr(1))
        _, vtype = op_array(ctx, op, lexpr.vtype, rexpr.vtype)
        return EOp(vtype, lexpr, rexpr, op, ctx)

    def visitEcomp(self, ctx: LatteParser.EcompContext):
        if ctx.LT():
            op = LT
        elif ctx.LE():
            op = LE
        elif ctx.GT():
            op = GT
        elif ctx.GE():
            op = GE
        elif ctx.EQ():
            op = EQ
        elif ctx.NE():
            op = NE
        else:
            raise CompilationError("unknown operator", ctx)
        lexpr = self.visit(ctx.expr(0))
        rexpr = self.visit(ctx.expr(1))
        _, vtype = op_array(ctx, op, lexpr.vtype, rexpr.vtype)
        return EOp(vtype, lexpr, rexpr, op, ctx)

    def visitEcall(self, ctx: LatteParser.EcallContext):
        name = str(ctx.IDENT())
        vtype = self.program.globals.get_variable(name, ctx)
        assert isinstance(vtype, VFun)
        rtype = vtype.rtype
        argtypes = vtype.params
        args = [self.visit(arg) for arg in ctx.expr()]

        if len(argtypes) != len(args):
            raise CompilationError("wrong number of arguments in a call", ctx)
        for arg, argtype in zip(args, argtypes):
            if arg.vtype != argtype:
                raise CompilationError("wrong type of an argument", ctx)

        return ECall(name, rtype, argtypes, args)

    def visitEiden(self, ctx: LatteParser.EidenContext):
        name = str(ctx.IDENT())
        vtype = self.program.last_vars.get_variable(name, ctx)
        return EVar(self.program.last_vars.get_variable_name(name, ctx),
                    VRef(vtype), ctx)

    def visitEminu(self, ctx: LatteParser.EminuContext):
        op = SUB
        expr = self.visit(ctx.expr())
        _, vtype = op_array(ctx, op, expr.vtype)
        return EUnaryOp(vtype, expr, op, ctx)

    def visitEnega(self, ctx: LatteParser.EnegaContext):
        op = NEG
        expr = self.visit(ctx.expr())
        _, vtype = op_array(ctx, op, expr.vtype)
        return EUnaryOp(vtype, expr, op, ctx)

    def visitEnull(self, ctx: LatteParser.EnullContext):
        classname = str(ctx.IDENT())
        vtype = self.program.name_to_type(classname, ctx)
        return EConst(vtype, None, ctx)

    def visitEattr(self, ctx: LatteParser.EattrContext):
        expr = self.visit(ctx.expr())
        attr = str(ctx.IDENT())
        return EAttr(attr, expr, ctx)

    def visitEnew(self, ctx: LatteParser.EnewContext):
        classname = str(ctx.IDENT())
        vtype = self.program.name_to_type(classname, ctx)
        return ENew(vtype, ctx)

    def visitErrorNode(self, node):
        raise CompilationError("unknown error", None)

    def visitItem(self, ctx: LatteParser.ItemContext):
        # it should not happen
        assert False

    def visitVtype(self, ctx: LatteParser.VtypeContext):
        # it should not happen
        assert False

    def visitArg(self, ctx: LatteParser.ArgContext):
        # it should not happen
        assert False
