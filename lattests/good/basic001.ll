declare void @f_printInt(i32)
declare void @f_printString(i8*)
declare void @f_error()
declare i32 @f_readInt()
declare i8* @f_readString()
declare i8* @op_addString(i8*, i8*)

define void @f_f(i32 %x) {
  L26:  ; init
    %b5_x = alloca i32
    store i32 %x, i32* %b5_x
    br label %L22

  L22:  ; init
    %b6_x = alloca i32
    br label %L19

  L19:  ; assignment
    %v12 = getelementptr  i32, i32* %b6_x, i32 0
    %v13 = getelementptr  i32, i32* %b5_x, i32 0
    %v14 = load i32, i32* %v13
    %v15 = add i32 0, 2
    %v16 = add i32 %v14, %v15
    store i32 %v16, i32* %v12
    br label %L11

  L11:  ; expr
    %v8 = getelementptr  i32, i32* %b6_x, i32 0
    %v9 = load i32, i32* %v8
    call void @f_printInt(i32 %v9)
    ret void
}

define i32 @f_main() {
  L34:  ; init
    br label %L32

  L32:  ; init
    br label %L30

  L30:  ; return
    %v28 = add i32 0, 1
    ret i32 %v28
}

define i32 @main() {
  MAIN:
    %ret = call i32 @f_main()
    ret i32 %ret
}

