from LatteParser import LatteParser
from LatteVisitor import LatteVisitor
from latte_tree import Program, VariablesBlock, Function, Block, Stmt, EOp, \
    EConst, SAssi, EVar, EmptyStmt, SIfElse, SReturn, SWhile, op_array, ECall, \
    EUnaryOp, ENew, EAttr, EMeth, ENewArray, EElem
from latte_misc import MUL, DIV, MOD, ADD, SUB, LT, LE, GT, GE, EQ, NE, AND, \
    OR, VRef, VFun, VBool, VInt, VString, CompilationError, NEG, VClass, VArray, \
    UID


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

        done_type_names = set()
        changes = True
        while changes:
            class_left = None
            changes = False
            for vtype in self.program.types.values():
                if vtype.ctx is not None and vtype.name not in done_type_names:
                    if (vtype.parent_name is None or
                            vtype.parent_name in done_type_names):
                        self.visitClassdef(vtype.ctx)
                        done_type_names.add(vtype.name)
                        changes = True
                    else:
                        class_left = vtype.ctx
        if class_left:
            raise CompilationError("circular class inheritance", class_left)

        for classdef in ctx.classdef():
            class_type = self.program.name_to_type(str(classdef.IDENT()),
                                                   classdef)
            for fundef in classdef.fundef():
                self.visitFundef(fundef, class_type)
        for fundef in ctx.fundef():
            self.visitFundef(fundef)
        return self.program

    def addFundefType(self, ctx: LatteParser.FundefContext, cls: VClass=None):
        if cls:
            name = cls.name + "." + str(ctx.IDENT())
        else:
            name = str(ctx.IDENT())
        return_type = self.visit(ctx.vtype())
        arg_types = tuple(
            [self.visit(arg.vtype())
             for arg in ctx.arg()])
        if cls:
            arg_types = (cls, ) + arg_types

        vtype = VFun(return_type, arg_types)
        if cls:
            cls.add_method(str(ctx.IDENT()), vtype, name, ctx)
            _, vtype, _ = cls.methods[str(ctx.IDENT())]
        self.program.globals.add_variable(name, vtype, ctx)

    def addClassdefType(self, ctx: LatteParser.ClassdefContext):
        name = str(ctx.IDENT())
        if ctx.parentclass():
            parent_name = str(ctx.parentclass().IDENT())
        else:
            parent_name = None
        self.program.add_type(name, parent_name, ctx)

    def visitClassdef(self, ctx: LatteParser.ClassdefContext):
        name = str(ctx.IDENT())
        class_type = self.program.name_to_type(name, ctx)
        assert isinstance(class_type, VClass)
        if class_type.parent_name:
            parent_vtype = self.program.name_to_type(class_type.parent_name,
                                                     ctx)
            class_type.parent_type = parent_vtype
            class_type.copy_fields_methods(parent_vtype)

        for field in ctx.field():
            vtype = self.visit(field.vtype())
            field_name = str(field.IDENT())
            class_type.add_field(field_name, vtype, field)

        for fundef in ctx.fundef():
            self.addFundefType(fundef, class_type)

    def visitFundef(self, ctx: LatteParser.FundefContext, cls: VClass=None):
        if cls:
            name = cls.name + "." + str(ctx.IDENT())
        else:
            name = str(ctx.IDENT())

        fields = VariablesBlock(self.program.globals)
        vars = VariablesBlock(fields)

        if cls:
            for field_name in cls.fields:
                fields.add_variable(field_name, cls.fields[field_name][1], ctx)
            _, vtype, _ = cls.methods[str(ctx.IDENT())]
            vars.add_variable("this.class", vtype.params[0], ctx)
            vars.add_variable("self", cls, ctx)

        args = ["this.class"] if cls else []
        for arg in ctx.arg():
            args.append(str(arg.IDENT()))
            vars.add_variable(str(arg.IDENT()), self.visit(arg.vtype()), arg)

        self.program.last_vars = vars
        self.program.current_function = name

        block = self.visitBlock(ctx.block())

        self.program.current_function = None
        self.program.last_vars = None

        function = Function(name, fields, vars, block, args, cls, ctx)
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
        if not vexpr.vtype.unref().is_children_of(texpr.vtype.unref()):
            raise CompilationError("invalid assignment type", ctx)
        return SAssi(texpr, vexpr, ctx)

    def visitSdecl(self, ctx: LatteParser.SdeclContext):
        vtype = self.visit(ctx.vtype())
        if not (isinstance(vtype, VClass) or isinstance(vtype, VArray))\
                or vtype.is_void():
            raise CompilationError("type not declarable", ctx)
        tstmts = []
        for item in ctx.item():
            name = str(item.IDENT())
            expr = item.expr()
            if expr:
                vexpr = self.visit(expr)
            else:
                vexpr = vtype.get_default_expr()
            if not vexpr.vtype.unref().is_children_of(vtype.unref()):
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
            if rexpr.vtype.unref().is_children_of(rtype.unref()):
                return SReturn(ctx, rtype.unref(), rexpr)
        elif rtype.is_void():
            return SReturn(ctx, rtype)
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

    def visitSfor(self, ctx: LatteParser.SforContext):
        array = self.visit(ctx.expr())
        if not isinstance(array.vtype.unref(), VArray):
            raise CompilationError('not iterable type', ctx.expr())
        vtype = self.visit(ctx.vtype())
        if not array.vtype.unref().vtype.is_children_of(vtype):
            raise CompilationError('type doesn\'t match with iterable', ctx)
        varname = str(ctx.IDENT())
        itername = "iter.{}".format(UID.get_uid())
        # Outer block creation
        vars = VariablesBlock(self.program.last_vars)
        last_vars = self.program.last_vars
        self.program.last_vars = vars
        out_block = Block(vars)

        self.program.last_vars.add_variable(itername, VInt(), None)
        texpr = EVar(self.program.last_vars.get_variable_name(itername, None),
                     VRef(VInt()), None)
        out_block.stmts.append(SAssi(texpr, EConst(VInt(), 0, None), None))

        # Inner block creation

        vars2 = VariablesBlock(self.program.last_vars)
        last_vars2 = self.program.last_vars
        self.program.last_vars = vars2
        in_block = Block(vars2)

        self.program.last_vars.add_variable(varname, vtype, ctx)
        texpr2 = EVar(self.program.last_vars.get_variable_name(varname, ctx),
                     VRef(vtype), ctx)
        in_block.stmts.append(SAssi(texpr2, EElem(
            VRef(vtype),
            array,
            EVar(self.program.last_vars.get_variable_name(itername, None),
                 VRef(VInt()), None)
        ), None))
        in_block.stmts.append(SAssi(
            EVar(self.program.last_vars.get_variable_name(itername, None),
                 VRef(VInt()), None),
            EOp(VInt(),
                EVar(self.program.last_vars.get_variable_name(itername, None), VRef(VInt()), None),
                EConst(VInt(), 1, None),
                ADD, None), None))
        body = self.visit(ctx.stmt())
        in_block.stmts.append(body)

        self.program.last_vars = last_vars2

        # Cond creation
        cond = EOp(
            VBool(),
            EVar(self.program.last_vars.get_variable_name(itername, None), VRef(VInt()), None),
            EAttr("length", array, None), LT, None
        )

        # While creation
        whil = SWhile(cond, in_block)

        out_block.stmts.append(whil)

        self.program.last_vars = last_vars

        return out_block

        raise NotImplementedError()

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

    def visitEmeth(self, ctx: LatteParser.EmethContext):
        name = str(ctx.IDENT())
        obj = self.visit(ctx.expr(0))
        if name not in obj.vtype.unref().methods:
            raise CompilationError("method not found", ctx)
        field_index, vtype, llname = obj.vtype.unref().methods[name]
        assert isinstance(vtype, VFun)
        rtype = vtype.unref().rtype
        argtypes = vtype.params
        args = [self.visit(expr) for expr in ctx.expr()]

        if len(argtypes) != len(args):
            raise CompilationError("wrong number of arguments in a call", ctx)
        for arg, argtype in zip(args, argtypes):
            if not arg.vtype.unref().is_children_of(argtype):
                raise CompilationError("wrong type of an argument", ctx)

        return EMeth(name, vtype, obj.vtype.unref(), rtype, argtypes, args)

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
            if not arg.vtype.unref().is_children_of(argtype):
                raise CompilationError("wrong type of an argument", ctx)

        return ECall(name, rtype, argtypes, args)

    def visitEelem(self, ctx: LatteParser.EelemContext):
        lexpr = self.visit(ctx.expr(0))
        rexpr = self.visit(ctx.expr(1))
        if not isinstance(lexpr.vtype.unref(), VArray):
            raise CompilationError('invalid array', ctx)
        if not rexpr.vtype.is_int():
            raise CompilationError('invalid array index', ctx)
        vtype = VRef(lexpr.vtype.unref().vtype)
        return EElem(vtype, lexpr, rexpr)

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

    def visitEnewarr(self, ctx: LatteParser.EnewarrContext):
        expr = self.visit(ctx.expr())
        vtype = self.visit(ctx.vtype())
        return ENewArray(vtype, expr, ctx)

    def visitErrorNode(self, node):
        raise CompilationError("unknown error", None)

    def visitItem(self, ctx: LatteParser.ItemContext):
        # it should not happen
        assert False

    def visitVarra(self, ctx: LatteParser.VarraContext):
        return VArray(self.visit(ctx.vtype()))

    def visitViden(self, ctx: LatteParser.VidenContext):
        return self.program.name_to_type(str(ctx.IDENT()), ctx)

    def visitArg(self, ctx: LatteParser.ArgContext):
        # it should not happen
        assert False
