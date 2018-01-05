# MRJP, rozwiązanie zadania 1, kompilator Instant

Autor: Sebastian Jaszczur
sj359674@students.mimuw.edu.pl

# Setup i odpalanie kompilatora

Wywołanie make powinno stworzyć insc_llvm oraz insc_jvm. Są to zwykłe pliki bash, które wykonują src/jvm.py lub src/llvm.py przy pomocy python3 z virtualenv zrobionego w katalogu venv/. Jedynym wymaganym dodatkowym modułem w pip jest antlr4-python3-runtime.

Jeśli z jakiegoś powodu insc_llvm lub insc_jvm nie będą działać (przez ścieżki), zawsze wywołanie src/jvm.py lub src/llvm.py powinno zadziałać.

# Działanie kompilatora

Kompilator ma zapisaną gramatykę w src/Instant.g4, na podstawie której, przy pomocy antlr4 został wygenerowany parser w Python3.

Poza Instant.g4 ręcznie zostały napisane tylko pliki w src: jvm.py oraz llvm.py . Każdy z nich korzysta ze schematu Visitor.

## Działanie części LLVM

Klasa LLVMVisitor odwiedza kolejno wierzchołki grafu i generuje kolejne linie wyjściowego kodu. Jednocześnie obiekt przechowuje informacje o ostatnio używanym registrze, a także ostatnim registrze pod każdą zmienną.

Wygenerowane linie są umieszczane w główną funkcję programu.

## Działanie części JVM

Klasa JVMVisitor także odwiedza kolejno wierzchołki grafu i generuje kolejne linie kodu. Jednak zamiast zapisywać je po kolei, jako stan obiektu, każda metoda zwraca wygenerowane linie i potrzebą wielkość stosu. Następnie każdy operator wybiera jako pierwszą do wstawienia tę część wyrażenia, która potrzebuje więcej stosu i wstawia jej linie jako pierwsze - co pozwala zminimalizować wielkość stosu.

W przypadku wykonania "w odwrotnej kolejności" podczęści operatorów odejmowania i dzielenia, dodawana jest też operacja swap.

# Struktura katalogów

W src/ jest kod źródłowy.
W lib/ jest jasmin.jar, potrzebny do wygenerowania .class.
W examples/ są dwa przykłady kodu .ins.

Generowane są pliki insc_jvm i insc_llvm, jak w treści zadania.
Tworzony jest także katalog venv z virtualenv Python3, żeby zainstalować antlr4.

# Używane narzędzia, biblioteki, zapożyczenia

Używam antlr4 w celu parsowania programu, Python3 i biblioteki standardowej, virtualenv, i oczywiście, jasmin oraz llvm.

W Makefile używam current_dir jak w https://stackoverflow.com/questions/18136918/how-to-get-current-relative-directory-of-your-makefile
