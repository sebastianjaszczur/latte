import sys

from antlr4 import InputStream, CommonTokenStream
from antlr4.tree.Tree import TerminalNodeImpl

from LatteLexer import LatteLexer
from LatteParser import LatteParser
from latte_visitor import LLVMVisitor
from latte_misc import ErrorRaiser, CompilationError

HELP = "Run this program with code.lat argument only."
EXTENSION_LATTE = ".lat"
EXTENSION_LL = ".ll"

DEBUG = False


def print_debug(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)


def print_err(*args, **kwargs):
    kwargs['file'] = sys.stderr
    print(*args, **kwargs)


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
        lexer.removeErrorListeners()
        lexer.addErrorListener(ErrorRaiser())
        tokenstream = CommonTokenStream(lexer)
        parser = LatteParser(tokenstream)
        parser.removeErrorListeners()
        parser.addErrorListener(ErrorRaiser())
        tree = parser.program()

        print_debug("Parse tree")
        print_parse_tree(tree)
        print_debug()

        print_debug("Visiting")
        program = LLVMVisitor().visit(tree)

        print_debug("CODE")
        program.do_checks()
        source = program.get_source()
    except CompilationError as e:
        print_err("ERROR")
        print_err(str(e))
        exit(1)

    print_err("OK")
    print_debug(source)
    print(source, file=outputfile)


def main():
    if len(sys.argv) != 2:
        print_err(HELP, file=sys.stderr)
        print_err("There is a wrong number of arguments.", file=sys.stderr)
        sys.exit(1)
    sourcename = str(sys.argv[1])

    if not sourcename.endswith(EXTENSION_LATTE):
        print_err(HELP, file=sys.stderr)
        print_err("The file extension is not recognized.", file=sys.stderr)
        sys.exit(2)
    basename = sourcename[:-len(EXTENSION_LATTE)]
    llname = basename + EXTENSION_LL

    print_debug("Compiling {} to {}".format(sourcename, llname))

    try:
        with open(sourcename, "r") as sourcefile:
            with open(llname, "w") as llfile:
                generate_ll(sourcefile, llfile)
    except Exception:
        print_err("ERROR")
        print_err("unexpected exception during compilation:")
        raise

    print_debug("Done.")


if __name__ == '__main__':
    main()
