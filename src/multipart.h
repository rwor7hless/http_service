
#ifndef MULTIPART_H
#define MULTIPART_H
#include <stdio.h>
#include <stddef.h>
int parse_multipart(int fd, const char *boundary, char *filename, size_t fn_size, 
                    FILE *out, size_t total);
#endif
