
#include "http_request.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
int parse_http_headers(const char*b,size_t l __attribute__((unused)),http_request_t*r){
    memset(r,0,sizeof *r);
    sscanf(b,"%7s %127s",r->method,r->path);
    const char*h;
    if((h=strstr(b,"Content-Length:")))r->content_length=atol(h+15);
    if((h=strstr(b,"Content-Type:")))sscanf(h,"Content-Type: %127[^\r\n]",r->content_type);
    if((h=strstr(b,"Authorization:")))sscanf(h,"Authorization: %255[^\r\n]",r->authorization);
    return 0;
}
