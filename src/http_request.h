
#ifndef HTTP_REQUEST_H
#define HTTP_REQUEST_H
#include <stddef.h>
typedef struct{
    char method[8];
    char path[128];
    size_t content_length;
    char content_type[128];
    char authorization[256];
} http_request_t;
int parse_http_headers(const char*, size_t, http_request_t*);
#endif
