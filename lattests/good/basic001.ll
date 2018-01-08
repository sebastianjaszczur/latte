declare void @f_printInt(i32)
declare void @f_printString(i8*)
declare void @f_error()
declare i32 @f_readInt()
declare i8* @f_readString()
declare i8* @op_addString(i8*, i8*)
declare i32 @op_eqString(i8*, i8*)
declare i32 @op_neString(i8*, i8*)

define i32 @f_main() {
  L19:  ; init
    %b2_x = alloca i32
    br label %L16

  L16:  ; assignment
    %v12 = getelementptr  i32, i32* %b2_x, i32 0
    %v13 = add i32 0, 0
    store i32 %v13, i32* %v12
    br label %L11

  L11:  ; assignment
    %v7 = getelementptr  i32, i32* %b2_x, i32 0
    %v8 = add i32 0, 1
    store i32 %v8, i32* %v7
    br label %L6

  L6:  ; return
    %v4 = add i32 0, 1
    ret i32 %v4
}

define i32 @main() {
  MAIN:
    %ret = call i32 @f_main()
    ret i32 %ret
}

