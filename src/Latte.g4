grammar Latte;

// programs

program
	: fundef*
	;

fundef
	: vtype IDENT '(' (arg (',' arg)*)? ')' block
	;

arg
	: vtype IDENT
	;

// statements

block
	: '{' stmt* '}'
	;

item
	: IDENT
	| IDENT '=' expr
	;

assign
	: expr '=' expr
	| expr '++'
	| expr '--'
	;

stmt
	: block # sbloc
	| ';' # ssemi
	| vtype item (',' item)* ';' # sdecl
	| assign ';' # sassi
	| 'return' expr? ';' # sretu
	| 'if' '(' expr ')' stmt ('else' stmt)? # sifel
	| 'while' '(' expr ')' stmt # swhil
	| expr #sexpr
	;

// types

vtype
	: IDENT
	;

// expr

expr
	: IDENT # eiden
	| INT # eintv
	| Strval #estrv
	| 'false' #efals
	| 'true' #etrue
	| IDENT '(' (expr (',' expr)*)? ')' #ecall
	| '-' expr #eminu
	| '!' expr #enega
	| expr (MUL|DIV|MOD) expr #emult
	| expr (ADD|SUB) expr #eadd
	| expr (LT|LE|GT|GE|EQ|NE) expr #ecomp
	| <assoc=right> expr '&&' expr #eand
	| <assoc=right> expr '||' expr #eor
	;

// operators

MUL : '*' ;
DIV : '/' ;
MOD : '%' ;

ADD : '+' ;
SUB : '-' ;

LT : '<' ;
LE : '<=' ;
GT : '>' ;
GE : '>=' ;
EQ : '==' ;
NE : '!=' ;



// comments, whitespace

WS
	: (' ' | '\r' | '\t' | '\n')+ ->  skip;

CHAR : ~('/'|'"') | '//' | '/"';


COMMENT_SL
	: ('#' | '//') ~( '\r' | '\n' )* -> skip;

COMMENT_ML
	: ('/*' ()* '*/') -> skip;

// idents

Strval
	: '"' CHAR* '"'
	;

fragment Letter  : Capital | Small ;
fragment Capital : [A-Z\u00C0-\u00D6\u00D8-\u00DE] ;
fragment Small   : [a-z\u00DF-\u00F6\u00F8-\u00FF] ;
fragment Digit : [0-9] ;

INT : Digit+ ;
fragment ID_First : Letter | '_';
IDENT : ID_First (ID_First | Digit)* ;




