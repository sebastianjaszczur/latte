declare void @f_printInt(i32)
declare void @f_printString(i8*)
declare void @f_error()
declare i32 @f_readInt()
declare i8* @f_readString()
declare i8* @op_addString(i8*, i8*)
declare i32 @op_eqString(i8*, i8*)
declare i32 @op_neString(i8*, i8*)

define i32 @f_main() {
  L22:  ; init
    %b2_x = alloca i1
    br label %L19

  L19:  ; assignment
    %v7 = getelementptr  i1, i1* %b2_x, i32 0
    %v8 = add i1 0, 1
    ISLAZY10:
    br i1 %v8, label %LAZY10, label %WORK10
    WORK10:
    %v9 = add i1 0, 0
    br label %LAZY10
    LAZY10:
    %v16 = phi i1 [%v8, %ISLAZY10], [%v9, %WORK10]
    store i1 %v16, i1* %v7
    br label %L6

  L6:  ; return
    %v4 = add i32 0, 0
    ret i32 %v4
}

define i32 @main() {
  MAIN:
    %ret = call i32 @f_main()
    ret i32 %ret
}

