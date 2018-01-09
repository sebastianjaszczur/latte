# MRJP, rozwiązanie zadania 2, kompilator Latte

Autor: Sebastian Jaszczur
sj359674@students.mimuw.edu.pl
s.jaszczur@student.uw.edu.pl

# Setup i uruchomienie kompilatora

Wywołanie make w katalogu głównym powinno stworzyć skrypt ./latc w głównym katalogu. Jest to zwykły skrypt bash, który wykonuje src/compile.py przy pomocy python3 z virtualenv zrobionego w katalogu venv/. compile.py tworzy plik \*.ll obok \*.lat. Po wykonaniu compile.py, uruchamia się clang łączący wygenerowany kod LLVM z biblioteką standardową Latte znajdującą się w src/stdlatte.c.

# Działanie kompilatora

Kompilator ma zapisaną gramatykę w src/Latte.g4, na podstawie której, przy pomocy antlr4 został wygenerowany parser w Python3 (wszystkie pliki Latte*).

compile.py zajmuje się wczytywaniem plików i odpalaniem leksera, parsera, kompilatora itd. w odpowiedniej kolejności, używając schematu Visitor. Na podstawie drzewa parsowania latte_parser.LLVMVisitor().visit(tree) generuje drzewo z zapisanymi wszystkimi typami, sprawdzając także poprawność typowania, deklaracji zmiennych itp. Te drzewo jest zapisane jako latte_tree.Program (i inne klasy w tym pliku).

Następnie drzewo w latte_tree generuje kolejne bloki kodu w LLVM. Każdy wierzchołek przekazuje w górę albo listę linii kodu, albo listę bloków kodu (albo całą zaimplementowaną funkcję). Rezultat każdego wierzchołka jest zapisany w ostatniej zwróconej linii kodu w ostatnim bloku (nie uwzględniając ewentualnego skoku).

# Struktura katalogów

W src/ jest kod źródłowy programu.
W lib/ jest jasmin.jar, potrzebny do wygenerowania .class.
lattests/ oraz studentstests/ to testy stworzone odpowiednio przez wykładowcę i studentów.

W src/ jest także plik run_antlr.sh, który uruchamia antlr4, oraz latte_tester.ipy, który w IPython3 uruchamia testy.

Generowane są pliki latc, jak w treści zadania.
Tworzony jest także katalog venv z virtualenv Python3, żeby zainstalować antlr4.

# Używane narzędzia, biblioteki, zapożyczenia

Używam antlr4 w celu parsowania programu, Python3, IPython3 (do testów), virtualenv. Używam także clang do kompilacji wygenerowanego kodu LLVM.

W Makefile używam current_dir jak w https://stackoverflow.com/questions/18136918/how-to-get-current-relative-directory-of-your-makefile
