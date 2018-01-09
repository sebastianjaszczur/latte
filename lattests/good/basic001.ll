declare void @f_printInt(i32)
declare void @f_printString(i8*)
declare void @f_error()
declare i32 @f_readInt()
declare i8* @f_readString()
declare i8* @op_addString(i8*, i8*)

define i32 @f_main() {
  L14:  ; init
    br label %L12

  L12:  ; init
    br label %L10

  L10:  ; return
    %v8 = add i32 0, 2
    ret i32 %v8
}

define void @f_f(i32 %x) {
  L33:  ; init
    %b5_x = alloca i32
    store i32 %x, i32* %b5_x
    br label %L29

  L29:  ; init
    %b6_x = alloca i32
    br label %L26

  L26:  ; assignment
    %v19 = getelementptr  i32, i32* %b6_x, i32 0
    %v20 = getelementptr  i32, i32* %b5_x, i32 0
    %v21 = load i32, i32* %v20
    %v22 = add i32 0, 2
    %v23 = add i32 %v21, %v22
    store i32 %v23, i32* %v19
    br label %L18

  L18:  ; expr
    %v15 = getelementptr  i32, i32* %b6_x, i32 0
    %v16 = load i32, i32* %v15
    call void @f_printInt(i32 %v16)
    ret void
}

define i32 @main() {
  MAIN:
    %ret = call i32 @f_main()
    ret i32 %ret
}

