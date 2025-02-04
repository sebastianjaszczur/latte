# Generated from Latte.g4 by ANTLR 4.7
from antlr4 import *
if __name__ is not None and "." in __name__:
    from .LatteParser import LatteParser
else:
    from LatteParser import LatteParser

# This class defines a complete generic visitor for a parse tree produced by LatteParser.

class LatteVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by LatteParser#program.
    def visitProgram(self, ctx:LatteParser.ProgramContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#classdef.
    def visitClassdef(self, ctx:LatteParser.ClassdefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#parentclass.
    def visitParentclass(self, ctx:LatteParser.ParentclassContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#field.
    def visitField(self, ctx:LatteParser.FieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#fundef.
    def visitFundef(self, ctx:LatteParser.FundefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#arg.
    def visitArg(self, ctx:LatteParser.ArgContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#block.
    def visitBlock(self, ctx:LatteParser.BlockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#item.
    def visitItem(self, ctx:LatteParser.ItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#sbloc.
    def visitSbloc(self, ctx:LatteParser.SblocContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#ssemi.
    def visitSsemi(self, ctx:LatteParser.SsemiContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#sdecl.
    def visitSdecl(self, ctx:LatteParser.SdeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#sassi.
    def visitSassi(self, ctx:LatteParser.SassiContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#sincr.
    def visitSincr(self, ctx:LatteParser.SincrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#sdecr.
    def visitSdecr(self, ctx:LatteParser.SdecrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#sretu.
    def visitSretu(self, ctx:LatteParser.SretuContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#sifel.
    def visitSifel(self, ctx:LatteParser.SifelContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#swhil.
    def visitSwhil(self, ctx:LatteParser.SwhilContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#sfor.
    def visitSfor(self, ctx:LatteParser.SforContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#sexpr.
    def visitSexpr(self, ctx:LatteParser.SexprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#viden.
    def visitViden(self, ctx:LatteParser.VidenContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#varra.
    def visitVarra(self, ctx:LatteParser.VarraContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#eiden.
    def visitEiden(self, ctx:LatteParser.EidenContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#ecomp.
    def visitEcomp(self, ctx:LatteParser.EcompContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#eor.
    def visitEor(self, ctx:LatteParser.EorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#eminu.
    def visitEminu(self, ctx:LatteParser.EminuContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#epare.
    def visitEpare(self, ctx:LatteParser.EpareContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#eelem.
    def visitEelem(self, ctx:LatteParser.EelemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#eattr.
    def visitEattr(self, ctx:LatteParser.EattrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#eintv.
    def visitEintv(self, ctx:LatteParser.EintvContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#estrv.
    def visitEstrv(self, ctx:LatteParser.EstrvContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#enull.
    def visitEnull(self, ctx:LatteParser.EnullContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#eadd.
    def visitEadd(self, ctx:LatteParser.EaddContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#emeth.
    def visitEmeth(self, ctx:LatteParser.EmethContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#enega.
    def visitEnega(self, ctx:LatteParser.EnegaContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#enew.
    def visitEnew(self, ctx:LatteParser.EnewContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#etrue.
    def visitEtrue(self, ctx:LatteParser.EtrueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#enewarr.
    def visitEnewarr(self, ctx:LatteParser.EnewarrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#emult.
    def visitEmult(self, ctx:LatteParser.EmultContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#efals.
    def visitEfals(self, ctx:LatteParser.EfalsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#eand.
    def visitEand(self, ctx:LatteParser.EandContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LatteParser#ecall.
    def visitEcall(self, ctx:LatteParser.EcallContext):
        return self.visitChildren(ctx)



del LatteParser