
#include "http_response.h"
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
void http_error(int fd,int c,const char*m){
    char b[256];
    int len = snprintf(b,sizeof b,"HTTP/1.1 %d %s\r\nContent-Length:0\r\n\r\n",c,m);
    if (len > 0) {
        ssize_t sent = send(fd, b, len, 0);
        if (sent < 0) perror("http_error");
    }
}
