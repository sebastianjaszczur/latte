import os
import sys

from antlr4 import InputStream, CommonTokenStream
from antlr4.tree.Tree import TerminalNodeImpl

from LatteLexer import LatteLexer
from LatteParser import LatteParser
from parser import LLVMVariableException, LLVMVisitor

# TODO: Better error handling

HELP = "Run this program with file.late argument only."
EXTENSION_LATTE = ".lat"
EXTENSION_LL = ".ll"
EXTENSION_BC = ".bc"

DEBUG = True


def print_debug(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)


def print_err(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)


def print_parse_tree(tree, indent_level=0):
    if isinstance(tree, TerminalNodeImpl):
        return
    print_debug(("| " * indent_level) + "> " + str(tree.__class__.__name__),
                str(tree.getText()))
    for c in tree.getChildren():
        print_parse_tree(c, indent_level + 1)


def generate_ll(sourcefile, outputfile):
    try:
        inputstrewam = InputStream(sourcefile.read())
        lexer = LatteLexer(inputstrewam)
        tokenstream = CommonTokenStream(lexer)
        parser = LatteParser(tokenstream)
        tree = parser.program()

        print_debug("Parse tree")
        print_parse_tree(tree)
        print_debug()

        print_debug("Visiting")
        program = LLVMVisitor().visit(tree)
        print_debug(program)
        print_debug()

        print_debug("CODE")
        program.do_checks()
        source = program.get_source()
    except Exception as e:
        print_err("Unknown exception: {}".format(e))
        exit(1)

    print_err("OK\n")
    print(source, file=outputfile)


def main():
    if len(sys.argv) != 2:
        print_debug(HELP, file=sys.stderr)
        print_debug("There is a wrong number of arguments.", file=sys.stderr)
        sys.exit(1)
    sourcename = str(sys.argv[1])

    if not sourcename.endswith(EXTENSION_LATTE):
        print_debug(HELP, file=sys.stderr)
        print_debug("The file extension is not recognized.", file=sys.stderr)
        sys.exit(2)
    basename = sourcename[:-len(EXTENSION_LATTE)]
    llname = basename + EXTENSION_LL

    print_debug("Compiling {} to {}".format(sourcename, llname))
    try:
        with open(sourcename, "r") as sourcefile:
            with open(llname, "w") as llfile:
                generate_ll(sourcefile, llfile)
    except LLVMVariableException as ve:
        firstToken = ve.ctx.parser.getTokenStream().get(
            ve.ctx.getSourceInterval()[0])
        print_debug("line {}:{} variable not declared before: '{}'".format(
            firstToken.line, firstToken.column, ve.name),
            file=sys.stderr)
        os.remove(llname)
        exit(3)

    os.system("llvm-as {}".format(llname))

    print_debug("Done.")


if __name__ == '__main__':
    main()
