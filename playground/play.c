#include <stdio.h>
#include <stdlib.h>
#include <string.h>


struct A {
	int a;
};

struct B(struct A) {
	int b;
};

int f() {
	struct B* x = malloc(sizeof(struct B));
	printf("%d", x->b);
	return 0;
}
