#include <stdio.h>
#include <stdlib.h>
#include <string.h>


struct list {
	int a;
	char prev;
	int x;
	char next;
};

int f() {
	struct list* x = malloc(sizeof(struct list));
	printf("%d", x->x);
	return 0;
}
