
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
    
    // Пропускаем кавычки если есть
    if (*boundary_start == '"') boundary_start++;
    
    size_t len = 0;
    const char *p = boundary_start;
    while (*p && *p != ';' && *p != '\r' && *p != '\n' && *p != '"' && *p != ' ') {
        if (len + 1 < out_size) {
            boundary_out[len++] = *p;
        }
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
    
    // Создаем директорию для загрузок если не существует
    struct stat st;
    if(stat(c->upload_dir,&st)!=0){
        if(mkdir(c->upload_dir,0755)<0){
            perror("mkdir upload_dir"); 
        }
    }
    
    fprintf(stderr, "Server started on %s:%d\n", c->address, c->port);
    fprintf(stderr, "Upload directory: %s\n", c->upload_dir);
    fprintf(stderr, "Auth enabled: %s\n", c->auth_enabled ? "yes" : "no");
    fflush(stderr);
    
    // Игнорируем SIGPIPE чтобы не падать при закрытии соединения
    signal(SIGPIPE, SIG_IGN);
    
    for(;;){
        int cl=accept(s,0,0);
        if(cl<0){ perror("accept"); continue; }
        
        // Устанавливаем таймаут для чтения
        struct timeval tv;
        tv.tv_sec = SOCKET_TIMEOUT;
        tv.tv_usec = 0;
        setsockopt(cl, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
        setsockopt(cl, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));
        
        char buf[MAX_HEADER_SIZE];
        ssize_t r=recv(cl,buf,sizeof buf-1,0);
        if(r<=0){ 
            if(r<0 && errno != EAGAIN && errno != EWOULDBLOCK) perror("recv");
            close(cl); continue; 
        }
        buf[r]=0;
        
        http_request_t req;
        parse_http_headers(buf,r,&req);
        
        // Обработка GET запроса для формы (без авторизации)
        if(strcmp(req.method,"GET")==0){
            if(strcmp(req.path,"/")==0 || strcmp(req.path,"/index.html")==0){
                send_html_form(cl);
                close(cl); continue;
            }
            http_error(cl,404,"Not Found"); 
            close(cl); continue;
        }
        
        // Для POST запросов требуется авторизация
        if(c->auth_enabled && !check_auth(req.authorization,c)){
            http_error(cl,401,"Unauthorized"); 
            close(cl); continue;
        }
        
        // Обработка POST запроса
        if(strcmp(req.method,"POST")==0 && strcmp(req.path,"/upload")==0){
            // Находим начало тела запроса в буфере
            char *body_ptr = strstr(buf, "\r\n\r\n");
            if(!body_ptr){
                http_error(cl,400,"Bad Request: Incomplete headers");
                close(cl); continue;
            }
            body_ptr += 4;
            size_t header_len = body_ptr - buf;
            size_t initial_body_len = (size_t)r > header_len ? (size_t)r - header_len : 0;
            
            char boundary[128];
            if(extract_boundary(req.content_type, boundary, sizeof(boundary))<0){
                http_error(cl,400,"Bad Request: No boundary");
                close(cl); continue;
            }
            
            char filename[256] = "upload.bin";
            char filepath[512];
            snprintf(filepath, sizeof(filepath), "%s/%s", c->upload_dir, filename);
            
            FILE*f=fopen(filepath,"wb");
            if(!f){
                perror("fopen");
                http_error(cl,500,"Internal Server Error");
                close(cl); continue;
            }
            
            int result = parse_multipart(cl, boundary, filename, sizeof(filename), 
                                        f, req.content_length,
                                        body_ptr, initial_body_len);
            fclose(f);
            
            if(result<0){
                unlink(filepath);
                http_error(cl,400,"Bad Request: Failed to parse multipart");
                close(cl); continue;
            }
            
            // Используем правильное имя файла если было извлечено
            char final_path[512];
            if(strcmp(filename,"upload.bin")!=0 && filename[0]!='\0'){
                snprintf(final_path, sizeof(final_path), "%s/%s", c->upload_dir, filename);
                if(rename(filepath, final_path)!=0){
                    perror("rename");
                }
            } else {
                strncpy(final_path, filepath, sizeof(final_path));
            }
            
            // Извлекаем только имя файла для ответа
            const char *display_name = strrchr(final_path, '/');
            display_name = display_name ? display_name + 1 : final_path;
            
            char success_msg[512];
            int msg_len = snprintf(success_msg, sizeof(success_msg),
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain\r\n"
                "Content-Length: %zu\r\n"
                "\r\nFile uploaded: %s", strlen(display_name) + 15, display_name);
            send(cl, success_msg, msg_len, 0);
            close(cl); continue;
        }
        
        http_error(cl,404,"Not Found"); 
        close(cl);
    }
}
