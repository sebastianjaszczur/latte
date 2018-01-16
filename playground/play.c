#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct list {
	int x;
	struct list* next;
};

struct list* f(int x) {
	struct list a;
	a.x = x;
	a.next = NULL;
	return &a;
}