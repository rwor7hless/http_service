
#include "server.h"
#include "http_request.h"
#include "http_response.h"
#include "auth.h"
#include "multipart.h"
#include "limits.h"
#include <arpa/inet.h>
#include <unistd.h>
#include <string.h>
#include <stdio.h>
#include <sys/socket.h>
#include <errno.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <sys/time.h>
#include <signal.h>
#include <time.h>
#include <stdarg.h>

/* форма встроена в бинарь, отдельный файл не нужен */
static const char html_form[] =
"<!DOCTYPE html>\n"
"<html><head><title>File Upload</title>\n"
"<script>\n"
"function uploadFile(event) {\n"
"    event.preventDefault();\n"
"    var username = prompt('Username:');\n"
"    if (!username) return;\n"
"    var password = prompt('Password:');\n"
"    if (!password) return;\n"
"    \n"
"    var form = document.getElementById('uploadForm');\n"
"    var formData = new FormData(form);\n"
"    \n"
"    var xhr = new XMLHttpRequest();\n"
"    xhr.open('POST', '/upload', true);\n"
"    \n"
"    var auth = btoa(username + ':' + password);\n"
"    xhr.setRequestHeader('Authorization', 'Basic ' + auth);\n"
"    \n"
"    xhr.onload = function() {\n"
"        if (xhr.status === 200) {\n"
"            document.getElementById('result').innerHTML = '<p style=\"color:green;\">' + xhr.responseText + '</p>';\n"
"        } else {\n"
"            document.getElementById('result').innerHTML = '<p style=\"color:red;\">Error: ' + xhr.status + ' ' + xhr.statusText + '</p>';\n"
"        }\n"
"    };\n"
"    \n"
"    xhr.onerror = function() {\n"
"        document.getElementById('result').innerHTML = '<p style=\"color:red;\">Network error</p>';\n"
"    };\n"
"    \n"
"    xhr.send(formData);\n"
"}\n"
"</script>\n"
"</head><body>\n"
"<h1>File Upload</h1>\n"
"<form id=\"uploadForm\" method=\"POST\" action=\"/upload\" enctype=\"multipart/form-data\" onsubmit=\"uploadFile(event); return false;\">\n"
"<input type=\"file\" name=\"file\" required><br><br>\n"
"<input type=\"submit\" value=\"Upload\">\n"
"</form>\n"
"<div id=\"result\"></div>\n"
"</body></html>\n";

static void log_msg(const char *level, const char *fmt, ...) {
    time_t t = time(NULL);
    struct tm *tm = localtime(&t);
    char ts[32];
    strftime(ts, sizeof(ts), "%Y-%m-%d %H:%M:%S", tm);
    fprintf(stderr, "[%s] [%s] ", ts, level);
    va_list ap;
    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
    fprintf(stderr, "\n");
    fflush(stderr);
}

static void send_html_form(int fd) {
    char response[2048];
    int len = snprintf(response, sizeof(response),
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html\r\n"
        "Content-Length: %zu\r\n"
        "\r\n%s", strlen(html_form), html_form);
    if (len > 0 && len < (int)sizeof(response)) {
        ssize_t sent = send(fd, response, len, 0);
        if (sent < 0) perror("send_html_form");
    }
}

static int extract_boundary(const char *content_type, char *boundary_out, size_t out_size) {
    const char *boundary_start = strstr(content_type, "boundary=");
    if (!boundary_start) return -1;

    boundary_start += 9;
    if (*boundary_start == '"') boundary_start++;

    size_t len = 0;
    const char *p = boundary_start;
    while (*p && *p != ';' && *p != '\r' && *p != '\n' && *p != '"' && *p != ' ') {
        if (len + 1 < out_size)
            boundary_out[len++] = *p;
        p++;
    }
    boundary_out[len] = '\0';

    return len > 0 ? 0 : -1;
}

int start_server(server_config_t*c){
    int s=socket(AF_INET,SOCK_STREAM,0);
    if(s<0){ perror("socket"); return -1; }

    int o=1;
    if(setsockopt(s,SOL_SOCKET,SO_REUSEADDR,&o,sizeof o)<0){
        perror("setsockopt"); close(s); return -1;
    }

    struct sockaddr_in a={0};
    a.sin_family=AF_INET;
    a.sin_port=htons(c->port);
    a.sin_addr.s_addr=inet_addr(c->address);

    if(bind(s,(void*)&a,sizeof a)<0){
        perror("bind"); close(s); return -1;
    }

    if(listen(s,5)<0){
        perror("listen"); close(s); return -1;
    }

    struct stat st;
    if(stat(c->upload_dir,&st)!=0){
        if(mkdir(c->upload_dir,0755)<0)
            perror("mkdir upload_dir");
    }

    log_msg("INFO", "server started on %s:%d", c->address, c->port);
    log_msg("INFO", "upload dir: %s", c->upload_dir);
    log_msg("INFO", "auth: %s", c->auth_enabled ? "enabled" : "disabled");

    signal(SIGPIPE, SIG_IGN); /* иначе падаем если клиент закрыл соединение */

    for(;;){
        int cl=accept(s,0,0);
        if(cl<0){ perror("accept"); continue; }

        struct sockaddr_in peer={0};
        socklen_t plen=sizeof(peer);
        getpeername(cl,(struct sockaddr*)&peer,&plen);
        char peer_ip[INET_ADDRSTRLEN];
        inet_ntop(AF_INET,&peer.sin_addr,peer_ip,sizeof(peer_ip));
        log_msg("INFO", "connection from %s:%d", peer_ip, ntohs(peer.sin_port));

        struct timeval tv;
        tv.tv_sec = SOCKET_TIMEOUT;
        tv.tv_usec = 0;
        setsockopt(cl, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
        setsockopt(cl, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));

        char buf[MAX_HEADER_SIZE];
        ssize_t r=recv(cl,buf,sizeof buf-1,0);
        if(r<=0){
            if(r<0 && errno != EAGAIN && errno != EWOULDBLOCK)
                log_msg("WARN", "%s recv error: %s", peer_ip, strerror(errno));
            else
                log_msg("WARN", "%s closed connection before sending data", peer_ip);
            close(cl); continue;
        }
        buf[r]=0;

        http_request_t req;
        parse_http_headers(buf,r,&req);
        log_msg("INFO", "%s \"%s %s\" content-length=%zu",
                peer_ip, req.method, req.path, req.content_length);

        if(strcmp(req.method,"GET")==0){
            if(strcmp(req.path,"/")==0 || strcmp(req.path,"/index.html")==0){
                log_msg("INFO", "%s -> 200 GET /", peer_ip);
                send_html_form(cl);
                close(cl); continue;
            }
            log_msg("WARN", "%s -> 404 GET %s", peer_ip, req.path);
            http_error(cl,404,"Not Found");
            close(cl); continue;
        }

        if(strcmp(req.method,"POST")==0 && strcmp(req.path,"/upload")==0){
            if(c->auth_enabled && !check_auth(req.authorization,c)){
                log_msg("WARN", "%s -> 401 bad credentials", peer_ip);
                http_error(cl,401,"Unauthorized");
                close(cl); continue;
            }
            char *body_ptr = strstr(buf, "\r\n\r\n");
            if(!body_ptr){
                log_msg("WARN", "%s -> 400 incomplete headers", peer_ip);
                http_error(cl,400,"Bad Request: Incomplete headers");
                close(cl); continue;
            }
            body_ptr += 4;
            size_t header_len = body_ptr - buf;
            size_t initial_body_len = (size_t)r > header_len ? (size_t)r - header_len : 0;

            char boundary[128];
            if(extract_boundary(req.content_type, boundary, sizeof(boundary))<0){
                log_msg("WARN", "%s -> 400 no boundary in Content-Type", peer_ip);
                http_error(cl,400,"Bad Request: No boundary");
                close(cl); continue;
            }

            /* имя файла узнаем только из тела, пока пишем во временный */
            char filename[256] = "upload.bin";
            char filepath[512];
            snprintf(filepath, sizeof(filepath), "%s/%s", c->upload_dir, filename);

            FILE*f=fopen(filepath,"wb");
            if(!f){
                log_msg("ERR", "fopen %s: %s", filepath, strerror(errno));
                http_error(cl,500,"Internal Server Error");
                close(cl); continue;
            }

            log_msg("INFO", "%s receiving file, size=%zu bytes", peer_ip, req.content_length);

            int result = parse_multipart(cl, boundary, filename, sizeof(filename),
                                        f, req.content_length,
                                        body_ptr, initial_body_len);
            fclose(f);

            if(result<0){
                unlink(filepath);
                log_msg("WARN", "%s -> 400 multipart parse failed", peer_ip);
                http_error(cl,400,"Bad Request: Failed to parse multipart");
                close(cl); continue;
            }

            char final_path[512];
            if(strcmp(filename,"upload.bin")!=0 && filename[0]!='\0'){
                snprintf(final_path, sizeof(final_path), "%s/%s", c->upload_dir, filename);
                if(rename(filepath, final_path)!=0)
                    log_msg("WARN", "rename %s -> %s: %s", filepath, final_path, strerror(errno));
            } else {
                strncpy(final_path, filepath, sizeof(final_path));
            }

            const char *display_name = strrchr(final_path, '/');
            display_name = display_name ? display_name + 1 : final_path;

            log_msg("INFO", "%s -> 200 uploaded \"%s\" (%zu bytes)",
                    peer_ip, display_name, req.content_length);

            char success_msg[512];
            int msg_len = snprintf(success_msg, sizeof(success_msg),
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain\r\n"
                "Content-Length: %zu\r\n"
                "\r\nFile uploaded: %s", strlen(display_name) + 15, display_name);
            send(cl, success_msg, msg_len, 0);
            close(cl); continue;
        }

        log_msg("WARN", "%s -> 404 %s %s", peer_ip, req.method, req.path);
        http_error(cl,404,"Not Found");
        close(cl);
    }
}
