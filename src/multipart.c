
#include "multipart.h"
#include "limits.h"
#include <sys/socket.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

int parse_multipart(int fd, const char *boundary, char *filename, size_t fn_size, 
                    FILE *out, size_t total) {
    if (!boundary || !*boundary) return -1;
    
    char *buf = malloc(MAX_BODY_SIZE);
    if (!buf) return -1;
    
    size_t received = 0;
    char boundary_marker[256];
    snprintf(boundary_marker, sizeof(boundary_marker), "--%s", boundary);
    
    // Читаем весь запрос
    while (received < total && received < MAX_BODY_SIZE) {
        ssize_t r = recv(fd, buf + received, MAX_BODY_SIZE - received, 0);
        if (r <= 0) { free(buf); return -1; }
        received += r;
    }
    
    if (received > MAX_BODY_SIZE) { free(buf); return -1; }
    
    // Ищем первый boundary
    char *start = strstr(buf, boundary_marker);
    if (!start) { free(buf); return -1; }
    
    // Пропускаем boundary и заголовки
    char *header_end = strstr(start, "\r\n\r\n");
    if (!header_end) { free(buf); return -1; }
    
    // Извлекаем имя файла из заголовков
    char *disposition = strstr(start, "Content-Disposition:");
    if (disposition) {
        char *name_start = strstr(disposition, "filename=\"");
        if (name_start) {
            name_start += 10;
            char *name_end = strchr(name_start, '"');
            if (name_end) {
                size_t fn_len = name_end - name_start;
                if (fn_len < fn_size) {
                    memcpy(filename, name_start, fn_len);
                    filename[fn_len] = '\0';
                }
            }
        }
    }
    
    // Начало данных файла
    char *data_start = header_end + 4;
    
    // Ищем конечный boundary
    char *end_boundary = strstr(data_start, boundary_marker);
    if (!end_boundary) { free(buf); return -1; }
    
    // Записываем данные файла (без завершающих \r\n перед boundary)
    size_t data_len = end_boundary - data_start;
    while (data_len > 0 && (data_start[data_len-1] == '\n' || data_start[data_len-1] == '\r')) {
        data_len--;
    }
    
    if (fwrite(data_start, 1, data_len, out) != data_len) {
        free(buf); return -1;
    }
    
    free(buf);
    return 0;
}
