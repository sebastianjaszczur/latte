#include <stdio.h>
#include <stdlib.h>

void f_printInt(int x) {
	printf("%d\n", x);
}

void f_printString(char* x) {
	printf("%s\n", x);
}

void f_error() {
	printf("runtime error\n");
	exit(1);
}

int f_readInt() {
	int x;
	if(scanf("%d", &x) < 0) {
		printf("runtime error: readInt\n");
		exit(1);
	}
	return x;
}

char* f_readString() {
	char* x = NULL;
	size_t mem_size = 0;
	ssize_t str_len = 0;
	while(str_len == 0) {
		free(x);
		mem_size = 0;
		str_len = getline(&x, &mem_size, stdin);
		if(str_len < 0) {
			printf("runtime error: readString\n");
			exit(1);
		}
		if(str_len > 0 && x[str_len-1] == '\n') {
			x[str_len-1] = '\0';
			str_len--;
		}
	}
	return x;
}

char* op_addString(char* left, char* right) {
	size_t left_len = strlen(left);
	size_t right_len = strlen(right);
	size_t result_len = left_len + right_len;

	char* result = malloc(result_len + 1);
	strcpy(result, left);
	strcpy(result + left_len, right);
	return result;
}

int op_eqString(char* left, char* right) {
	size_t result = str_equal(left, right);
	if(result != 0)
		return 1;
	return 0;
}

int op_neString(char* left, char* right) {
	return 1 - op_eqString(left, right);
}