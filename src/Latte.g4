grammar Latte;

// programs

program
	: (fundef | classdef)*
	;

classdef
	: 'class' IDENT ('extends' parentclass)? '{' (field | fundef)*'}'
	;

parentclass
	: IDENT
	;

field
	: vtype IDENT ';'
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

stmt
	: block # sbloc
	| ';' # ssemi
	| vtype item (',' item)* ';' # sdecl
	| expr '=' expr ';' # sassi
	| expr '++' ';' # sincr
	| expr '--' ';' # sdecr
	| 'return' expr? ';' # sretu
	| 'if' '(' expr ')' stmt ('else' stmt)? # sifel
	| 'while' '(' expr ')' stmt # swhil
	| expr ';' #sexpr
	;

// types

vtype
	: IDENT
	;

// expr

expr
	: IDENT # eiden
	| INT # eintv
	| STRING #estrv
	| 'false' #efals
	| 'true' #etrue
	| IDENT '(' (expr (',' expr)*)? ')' #ecall
	| expr '.' IDENT '(' (expr (',' expr)*)? ')' #emeth
	| expr '.' IDENT #eattr
	| '-' expr #eminu
	| '!' expr #enega
	| expr (MUL|DIV|MOD) expr #emult
	| expr (ADD|SUB) expr #eadd
	| expr (LT|LE|GT|GE|EQ|NE) expr #ecomp
	| <assoc=right> expr '&&' expr #eand
	| <assoc=right> expr '||' expr #eor
	| '(' IDENT ')' 'null' #enull
	| 'new' IDENT #enew
	| '(' expr ')' # epare
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

COMMENT_SL
	: ('#' | '//') ~( '\r' | '\n' )* -> skip;

COMMENT_ML
	: ('/*' ( (~'*') | ( '*' (~'/') ) )* '*/') -> skip;

// idents

fragment Letter  : Capital | Small ;
fragment Capital : [A-Z] ;
fragment Small   : [a-z] ;
fragment Digit : [0-9] ;

INT : Digit+ ;
fragment ID_First : Letter | '_';
IDENT : ID_First (ID_First | Digit)* ;

STRING : '"' ( ~('\\'|'"') | '\\"' | '\\\\' | '\\n' | '\\t' )* '"';