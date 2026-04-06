# Ликбез по коду HTTP-сервера на C

Это небольшой HTTP-сервер для загрузки файлов. Принимает файлы через браузер, проверяет Basic-аутентификацию, сохраняет файлы в указанную директорию. Весь код — однопоточный, без форков, без threads: одно соединение за раз.

---

## Оглавление

1. [limits.h — константы](#limitsh)
2. [config.h / config.c — конфигурация](#configh--configc)
3. [auth.h / auth.c — аутентификация](#authh--authc)
4. [http_request.h / http_request.c — разбор запроса](#http_requesthc)
5. [http_response.h / http_response.c — отправка ошибок](#http_responsehc)
6. [multipart.h / multipart.c — парсинг тела запроса](#multiparth--multipartc)
7. [server.h / server.c — главный цикл сервера](#serverh--serverc)
8. [main.c — точка входа](#mainc)
9. [Словарик C-идиом](#словарик-c-идиом)

---

## limits.h

Файл с тремя `#define` — просто именованные числа, чтобы не было магии в коде.

```c
#define MAX_HEADER_SIZE 8192             // буфер для HTTP-заголовков: 8 KB
#define MAX_BODY_SIZE   (50*1024*1024)   // максимальный размер тела: 50 MB
#define SOCKET_TIMEOUT  10               // таймаут сокета в секундах
```

**`#define`** — это не переменная, это текстовая подстановка. Препроцессор перед компиляцией буквально вставляет число вместо имени. Типа нет, проверок нет — просто замена строки на строку.

**`#ifndef` / `#define` / `#endif`** — стандартный "include guard". Защищает от того, чтобы один и тот же заголовочный файл не подключился дважды (что сломало бы компиляцию из-за повторных объявлений).

---

## config.h / config.c

### Структура `server_config_t`

```c
typedef struct {
    char address[64];     // IP-адрес вида "0.0.0.0" или "127.0.0.1"
    int  port;            // номер порта, например 8080
    char upload_dir[256]; // путь к папке для загрузок
    char username[64];    // логин для Basic Auth
    char password[64];    // пароль для Basic Auth
    bool auth_enabled;    // включена ли аутентификация
} server_config_t;
```

**`typedef struct { ... } server_config_t`** — объявляем структуру (набор полей) и сразу даём ей псевдоним `server_config_t`. Без `typedef` пришлось бы писать `struct server_config_t` каждый раз.

**`char address[64]`** — массив из 64 символов прямо внутри структуры. Не указатель, не malloc — данные лежат прямо там, в теле структуры. IP-адрес "0.0.0.0" занимает 7 символов + нулевой байт, так что 64 — с запасом.

**`bool`** — тип "истина/ложь". В C нет встроенного bool, он приходит из `<stdbool.h>`. Под капотом это просто `int` (0 = false, не-0 = true), но так читабельнее.

---

### `default_config(server_config_t *c)`

```c
void default_config(server_config_t *c){
    memset(c, 0, sizeof(*c));
    strncpy(c->address, "0.0.0.0", sizeof(c->address) - 1);
    c->port = 8080;
    strncpy(c->upload_dir, "/tmp", sizeof(c->upload_dir) - 1);
    strncpy(c->username, "admin", sizeof(c->username) - 1);
    strncpy(c->password, "admin", sizeof(c->password) - 1);
    c->auth_enabled = 1;
}
```

Принимает: указатель на структуру конфигурации.
Возвращает: ничего (`void`).
Делает: заполняет структуру значениями по умолчанию.

**`server_config_t *c`** — это указатель. `c` — не сама структура, а адрес в памяти, где она лежит. Через `->` обращаемся к полям по указателю. Это эквивалент `(*c).port = 8080`.

**`memset(c, 0, sizeof(*c))`** — заполняет `sizeof(*c)` байт начиная с адреса `c` нулями. `sizeof(*c)` — размер того, на что указывает `c`, то есть всей структуры. Без этого в полях будет мусор.

- `memset(ptr, значение, кол-во_байт)` — из `<string.h>`. Побайтово заполняет память.

**`strncpy(c->address, "0.0.0.0", sizeof(c->address) - 1)`** — копирует строку с ограничением по длине. `-1` оставляет место для нулевого байта `\0` в конце.

**`c->auth_enabled = 1`** — присваиваем 1 (true). В C `1` и `true` — одно и то же для `bool`.

---

### `load_config(const char *path, server_config_t *c)`

```c
int load_config(const char *path, server_config_t *c){
    FILE *f = fopen(path, "r");
    if (!f) return -1;
    char l[256], k[64], v[128];
    while (fgets(l, sizeof l, f)) {
        /* Пропускаем строки без '=' и пустые строки */
        if (sscanf(l, "%63[^=]=%127s", k, v) == 2) {
            if (!strcmp(k, "address")) { ... }
            else if (!strcmp(k, "port")) c->port = atoi(v);
            ...
        }
    }
    fclose(f); return 0;
}
```

Принимает: путь к файлу и указатель на структуру конфига.
Возвращает: `0` при успехе, `-1` если файл не открылся.
Делает: читает файл построчно, разбирает пары `ключ=значение`, записывает в структуру.

**`const char *path`** — указатель на строку, которую не будем изменять (`const` — обещание компилятору). Строки в C — массивы символов, заканчивающиеся `\0`. Указатель хранит адрес первого символа.

**`FILE *f`** — указатель на структуру, описывающую открытый файл. Сама структура внутри стандартной библиотеки, нам нужен только "хэндл".

**`fopen(path, "r")`** — открывает файл для чтения. Возвращает `FILE *` или `NULL` если не нашёлся. Режимы: `"r"` — чтение, `"w"` — запись (с обнулением), `"wb"` — запись в бинарном режиме.

**`if (!f) return -1`** — если `fopen` вернул `NULL`, файл не открылся. `!f` то же самое что `f == NULL`. По конвенции Unix: `0` = успех, отрицательное = ошибка.

**`fgets(l, sizeof l, f)`** — читает одну строку из файла. Не более `sizeof l - 1` символов, добавляет `\0`. Возвращает `NULL` когда файл кончился. `while(fgets(...))` — классический способ читать файл построчно.

**`sscanf(l, "%63[^=]=%127s", k, v)`** — разбирает строку по шаблону. Возвращает количество успешно разобранных полей.
- `%63[^=]` — читать до 63 символов, которые не `=`. Это ключ.
- `=%127s` — пропускаем `=`, читаем слово до пробела (до 127 символов). Это значение.
- Если вернулось `2` — строка корректная.

**`strcmp(k, "address")`** — сравнивает строки побайтово. Возвращает `0` если строки равны. `!strcmp(...)` — "строки равны".

**`atoi(v)`** — конвертирует строку `"8080"` в число `8080`. Без проверки ошибок — если строка не число, вернёт `0`.

**`fclose(f)`** — закрывает файл. Всегда закрывай открытые файлы.

---

## auth.h / auth.c

### Статичная `idx(char c)`

```c
static int idx(char c){
    if('A'<=c&&c<='Z') return c-'A';
    if('a'<=c&&c<='z') return c-'a'+26;
    if('0'<=c&&c<='9') return c-'0'+52;
    if(c=='+') return 62;
    if(c=='/') return 63;
    return -1;
}
```

Принимает: один символ.
Возвращает: его числовой индекс в алфавите Base64 (0–63), или -1 если символ не Base64.

**`static`** (вне функции) — "видно только в этом файле". C-аналог `private`. Без `static` функция была бы глобальной и могла конфликтовать с одноимёнными в других файлах.

**`c - 'A'`** — арифметика символов. `'A'` имеет ASCII-код 65, `'B'` — 66, итд. Вычитая `'A'`, получаем индекс: для `'A'` — 0, для `'Z'` — 25.

---

### Статичная `b64(const char *in, unsigned char *out)`

```c
static int b64(const char *in, unsigned char *out){
    int v=0, b=-8, l=0;
    for(; *in; in++){
        int d=idx(*in); if(d<0) break;
        v=(v<<6)+d; b+=6;
        if(b>=0){ out[l++]=(v>>b)&0xFF; b-=8; }
    }
    return l;
}
```

Принимает: строку Base64 и буфер для результата.
Возвращает: количество декодированных байт.
Делает: декодирует Base64 в бинарные данные.

**`unsigned char *out`** — указатель на байты без знака (0–255). Обычный `char` знаковый (-128..127), что создаёт проблемы с бинарными данными. `unsigned char` — явно беззнаковый.

**`for(; *in; in++)`** — цикл по строке. `*in` — символ по адресу `in`. Когда доходим до `\0` (конец строки), условие ложно, цикл завершается. `in++` — сдвигаем указатель на следующий символ.

**`v=(v<<6)+d`** — битовые операции. `<<6` сдвигает `v` влево на 6 бит. Каждый Base64-символ несёт 6 бит, накапливаем их в `v`.

**`(v>>b)&0xFF`** — берём из `v` один байт (8 бит). `>>b` — сдвиг вправо, `&0xFF` — маскируем все биты кроме младших восьми.

**`out[l++]`** — запись в буфер с постинкрементом. Сначала используется текущий `l` как индекс, затем `l` увеличивается. Классическая C-идиома.

---

### `check_auth(const char *h, const server_config_t *c)`

```c
int check_auth(const char *h, const server_config_t *c){
    if(strncmp(h, "Basic ", 6)) return 0;
    unsigned char d[128]={0};
    b64(h+6, d);
    char exp[128];
    snprintf(exp, sizeof exp, "%s:%s", c->username, c->password);
    return strcmp((char*)d, exp)==0;
}
```

Принимает: строку заголовка `Authorization` и указатель на конфиг.
Возвращает: `1` если авторизация прошла, `0` если нет.
Делает: декодирует Base64 из заголовка, сравнивает с логином:паролем из конфига.

**`strncmp(h, "Basic ", 6)`** — сравнивает первые 6 символов. Если `h` не начинается с `"Basic "`, сразу возвращаем 0.

**`h+6`** — арифметика указателей. Если `h` указывает на `"Basic dXNlcjpwYXNz"`, то `h+6` указывает на `"dXNlcjpwYXNz"`. Не копируем, просто смотрим с другого места той же строки.

**`unsigned char d[128]={0}`** — буфер на стеке, нулями. `={0}` — первый элемент = 0, остальные тоже = 0 (так работает C). Стек не требует `free`.

**`snprintf(exp, sizeof exp, "%s:%s", c->username, c->password)`** — форматирует строку в буфер. Как `printf`, но пишет в строку. `sizeof exp` — защита от переполнения.

**`(char*)d`** — приведение типа. `d` это `unsigned char *`, `strcmp` ожидает `char *`. Говорим компилятору "считай это `char *`". Данные те же, тип другой.

---

## http_request.h/c

### Структура `http_request_t`

```c
typedef struct{
    char   method[8];          // "GET" или "POST"
    char   path[128];          // "/", "/upload" и т.п.
    size_t content_length;     // значение заголовка Content-Length
    char   content_type[128];  // "multipart/form-data; boundary=..."
    char   authorization[256]; // "Basic dXNlcjpwYXNz"
} http_request_t;
```

**`size_t`** — тип для размеров. Беззнаковый, на 64-битной системе — 64 бита. Всегда используй для размеров буферов и индексов массивов.

---

### `parse_http_headers(const char *b, size_t l, http_request_t *r)`

```c
int parse_http_headers(const char *b, size_t l __attribute__((unused)), http_request_t *r){
    memset(r, 0, sizeof *r);
    sscanf(b, "%7s %127s", r->method, r->path);
    const char *h;
    if((h=strstr(b,"Content-Length:"))) r->content_length=atol(h+15);
    if((h=strstr(b,"Content-Type:")))   sscanf(h,"Content-Type: %127[^\r\n]",r->content_type);
    if((h=strstr(b,"Authorization:")))  sscanf(h,"Authorization: %255[^\r\n]",r->authorization);
    return 0;
}
```

Принимает: буфер с HTTP-запросом, его размер, указатель на структуру запроса.
Возвращает: всегда `0`.
Делает: разбирает HTTP-запрос, извлекает метод, путь и заголовки.

**`__attribute__((unused))`** — GCC-расширение. Говорит компилятору: "параметр `l` намеренно не используется, не ругайся предупреждением". Есть в сигнатуре для совместимости.

**`sscanf(b, "%7s %127s", r->method, r->path)`** — разбирает первую строку запроса.
- Первая строка HTTP: `GET /upload HTTP/1.1`
- `%7s` — слово до 7 символов → `r->method` ("GET" или "POST")
- `%127s` — следующее слово → `r->path` ("/upload")

**`strstr(b, "Content-Length:")`** — ищет подстроку. Возвращает указатель на первое вхождение или `NULL`.

**`if((h=strstr(...)))`** — присваивание внутри условия. Сначала выполняется `strstr`, результат в `h`, потом `h` проверяется на `NULL`. Одна строка вместо двух.

**`h+15`** — пропускаем `"Content-Length:"` (15 символов). `h` смотрит на `"Content-Length: 12345\r\n"`, `h+15` — уже на `" 12345\r\n"`.

**`%127[^\r\n]`** — в `sscanf` квадратные скобки задают допустимые символы. `[^\r\n]` — "любые кроме `\r` и `\n`". Читаем всю строку заголовка до конца.

---

## http_response.h/c

### `http_error(int fd, int c, const char *m)`

```c
void http_error(int fd, int c, const char *m){
    char b[256];
    int len = snprintf(b, sizeof b, "HTTP/1.1 %d %s\r\nContent-Length:0\r\n\r\n", c, m);
    if (len > 0) {
        ssize_t sent = send(fd, b, len, 0);
        if (sent < 0) perror("http_error");
    }
}
```

Принимает: дескриптор сокета, HTTP-код ошибки, текст статуса.
Возвращает: ничего.
Делает: формирует и отправляет HTTP-ответ с кодом ошибки и пустым телом.

**`int fd`** — файловый дескриптор. В Unix сокеты, файлы и трубы — всё это числа, через которые ядро знает объект. `fd` — адрес сокета клиента.

**`ssize_t`** — знаковый `size_t`. Нужен потому что `send` и `recv` могут вернуть `-1` — отрицательное в беззнаковый `size_t` не влезет.

**`send(fd, b, len, 0)`** — отправляет данные через сокет. `send(сокет, буфер, размер, флаги)`. Флаги `0` — нам не нужны. Возвращает количество отправленных байт или `-1`.

**`perror("http_error")`** — выводит `"http_error: описание_ошибки"` в stderr. Описание берётся из глобального `errno`, который система ставит при ошибке.

---

## multipart.h / multipart.c

### `parse_multipart(...)`

```c
int parse_multipart(int fd, const char *boundary, char *filename, size_t fn_size,
                    FILE *out, size_t total, const char *initial_data, size_t initial_len)
```

Принимает:
- `int fd` — сокет, из которого читаем
- `const char *boundary` — строка-разделитель из Content-Type
- `char *filename` — буфер куда запишем имя файла
- `size_t fn_size` — размер этого буфера
- `FILE *out` — уже открытый файл, куда пишем содержимое
- `size_t total` — полный ожидаемый размер тела (из Content-Length)
- `const char *initial_data` — кусок тела, уже прочитанный вместе с заголовками
- `size_t initial_len` — его длина

Возвращает: `0` при успехе, `-1` при ошибке.

**Зачем `initial_data`?** При чтении HTTP-запроса `recv` читает заголовки и начало тела одним куском. После разбора заголовков часть тела уже в памяти — передаём её чтобы не потерять.

---

```c
char *buf = malloc(total + 1);
if (!buf) return -1;
```

**`malloc(total + 1)`** — выделяет память в куче. Возвращает `void *` или `NULL`. `+1` — место для `\0`. Память не инициализирована — там может быть что угодно. Обязательно нужно `free(buf)` потом.

---

```c
if (initial_data && initial_len > 0) {
    size_t copy_len = (initial_len < total) ? initial_len : total;
    memcpy(buf, initial_data, copy_len);
    received = copy_len;
}
```

**`(initial_len < total) ? initial_len : total`** — тернарный оператор. Берём минимум из двух чисел.

**`memcpy(buf, initial_data, copy_len)`** — побайтовое копирование. В отличие от `strcpy` не останавливается на `\0` — правильно для бинарных данных.

---

```c
while (received < total) {
    ssize_t r = recv(fd, buf + received, total - received, 0);
    if (r <= 0) { free(buf); return -1; }
    received += r;
}
```

**`recv(fd, buf + received, total - received, 0)`** — читает данные из сокета. Возвращает количество прочитанных байт, `0` если соединение закрыто, `-1` при ошибке.

**`buf + received`** — арифметика указателей. `buf` — начало буфера, `buf + received` — позиция после уже принятых данных. Следующая порция пишется туда.

**`r <= 0`** — клиент отключился или ошибка. `free(buf)` перед каждым `return` — C-дисциплина ручного управления памятью.

---

```c
char *start      = strstr(buf, boundary_marker);
char *header_end = strstr(start, "\r\n\r\n");
```

Multipart-тело выглядит так:

```
--boundary\r\n
Content-Disposition: form-data; name="file"; filename="photo.jpg"\r\n
\r\n
<байты файла>
--boundary--
```

`strstr` находит ключевые точки: начало части (`--boundary`), конец заголовков части (`\r\n\r\n`).

---

```c
char *name_start = strstr(disposition, "filename=\"");
name_start += 10;
char *name_end = strchr(name_start, '"');
size_t fn_len = name_end - name_start;
```

**`name_start += 10`** — сдвигаем на 10 символов (длина `filename="`), оказываемся прямо на имени файла.

**`strchr(name_start, '"')`** — ищет первое вхождение символа в строке. Ищем закрывающую кавычку.

**`name_end - name_start`** — разность указателей. Оба в одном буфере. `name_start` на начало имени, `name_end` на кавычку. Разность = длина имени файла.

---

```c
char *data_start  = header_end + 4;          /* после \r\n\r\n */
char *end_boundary = strstr(data_start, boundary_marker);
size_t data_len   = end_boundary - data_start;
while (data_len > 0 && (data_start[data_len-1] == '\n' || data_start[data_len-1] == '\r'))
    data_len--;
```

`header_end` на `\r\n\r\n`. `+4` перешагивает их — попадаем на данные файла. `end_boundary - data_start` — длина данных. Обрезаем trailing `\r\n` — браузер всегда дописывает их перед финальным boundary.

---

```c
if (fwrite(data_start, 1, data_len, out) != data_len) {
    free(buf); return -1;
}
free(buf);
```

**`fwrite(буфер, размер_элемента, кол-во_элементов, файл)`** — записывает бинарные данные в файл. Здесь: `1 * data_len` = `data_len` байт. Возвращает количество записанных элементов.

`free(buf)` — во всех путях выхода. Это проверено Valgrind — утечек нет.

---

## server.h / server.c

### `static const char html_form[]`

```c
static const char html_form[] = "<!DOCTYPE html>...";
```

**`static const char html_form[]`** — строковый массив в сегменте данных программы (не стек, не куча). `static` (на уровне файла) — "видна только в этом файле". `const` — менять нельзя. Размер компилятор посчитает сам.

HTML с формой встроен прямо в бинарник — не нужен отдельный файл на диске.

---

### `static void log_msg(const char *level, const char *fmt, ...)`

```c
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
```

Принимает: уровень ("INFO"/"WARN"/"ERR"), строку формата и произвольные аргументы.
Делает: выводит строку вида `[2026-03-24 12:00:00] [INFO] сообщение` в stderr.

**`...`** — вариадические аргументы. Переменное число параметров, как у `printf`.

**`time(NULL)`** — текущее время как секунды с 1 января 1970 ("Unix epoch").

**`localtime(&t)`** — разбивает Unix-время на год/месяц/день/часы/минуты/секунды в `struct tm`. Возвращает указатель на статический внутренний буфер (не нужно освобождать).

**`strftime(ts, sizeof(ts), "%Y-%m-%d %H:%M:%S", tm)`** — форматирует время в строку. Как `sprintf` но для дат.

**`fprintf(stderr, ...)`** — выводит в stderr. Логи принято писать туда, а не в stdout. journald перехватывает stderr службы и кладёт в системный журнал.

**`va_list ap`** — переменная для обхода вариадических аргументов.

**`va_start(ap, fmt)`** — инициализирует `ap`. Последний именованный параметр перед `...` — это `fmt`.

**`vfprintf(stderr, fmt, ap)`** — версия `fprintf` для готового `va_list`. Передаём вариадические аргументы дальше по цепочке.

**`va_end(ap)`** — завершаем работу с `va_list`. Обязательно.

**`fflush(stderr)`** — принудительно сбрасывает буфер. Вывод в C буферизован — без `fflush` лог может не появиться сразу если программа упадёт.

---

### `static void send_html_form(int fd)`

```c
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
```

Принимает: дескриптор клиентского сокета.
Делает: собирает HTTP 200 OK с HTML-формой и отправляет клиенту.

**`strlen(html_form)`** — считает символы до `\0`. Нужно для заголовка `Content-Length` — браузер должен знать сколько байт ждать.

**`%zu`** — спецификатор для `size_t`. Важно использовать правильный — несовпадение типа и спецификатора это undefined behavior.

**`(int)sizeof(response)`** — `sizeof` возвращает `size_t`, `len` типа `int`. Приводим к одному типу чтобы сравнить без предупреждений.

---

### `static int extract_boundary(...)`

```c
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
```

Принимает: строку Content-Type, буфер для boundary, размер буфера.
Возвращает: `0` при успехе, `-1` если boundary не нашёлся.
Делает: вытаскивает разделитель из `"multipart/form-data; boundary=abc123"`.

**`boundary_start += 9`** — пропускаем `"boundary="` (9 символов), `boundary_start` смотрит на само значение.

**`*boundary_start == '"'`** — разыменовываем: берём символ по адресу. Boundary мог быть в кавычках — сдвигаемся мимо.

**`boundary_out[len] = '\0'`** — добавляем нулевой терминатор. Без него это не строка, а просто байты. Всегда добавляй `\0` в конец строки, собранной вручную.

---

### `int start_server(server_config_t *c)`

Главная функция. Принимает конфиг, запускает бесконечный цикл. Возвращает `-1` только при фатальной ошибке инициализации.

#### Инициализация сокета

```c
int s = socket(AF_INET, SOCK_STREAM, 0);
```

**`socket(AF_INET, SOCK_STREAM, 0)`** — создаёт сокет. `AF_INET` — IPv4. `SOCK_STREAM` — TCP. Возвращает дескриптор или `-1`.

```c
setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &o, sizeof o);
```

**`SO_REUSEADDR`** — разрешить переиспользовать адрес сразу после закрытия. Без этого после перезапуска несколько минут будет `bind: Address already in use`.

```c
a.sin_port        = htons(c->port);
a.sin_addr.s_addr = inet_addr(c->address);
```

**`htons(c->port)`** — "host to network short". Конвертирует порт из порядка байт процессора в сетевой (big-endian). Сеть ожидает big-endian, x86 — little-endian. Всегда конвертируй.

**`inet_addr("0.0.0.0")`** — строку IP в 32-битное число в сетевом порядке байт.

```c
bind(s, (void*)&a, sizeof a);
listen(s, 5);
```

**`bind`** — привязывает сокет к IP:port. Без него сокет "в воздухе".

**`listen(s, 5)`** — переводит в режим прослушивания. `5` — размер очереди ожидающих соединений.

---

#### SIGPIPE

```c
signal(SIGPIPE, SIG_IGN);
```

**`signal(SIGPIPE, SIG_IGN)`** — `SIGPIPE` посылается процессу когда он пишет в закрытый сокет. По умолчанию убивает процесс. `SIG_IGN` — игнорировать. После этого `send` просто вернёт `-1`.

---

#### Главный цикл

```c
for(;;){
    int cl = accept(s, 0, 0);
    ...
    close(cl);
}
```

**`for(;;)`** — бесконечный цикл.

**`accept(s, 0, 0)`** — блокирует пока кто-то не подключится, возвращает новый дескриптор для общения с клиентом. Серверный `s` остаётся слушать дальше.

---

#### IP клиента

```c
struct sockaddr_in peer = {0};
socklen_t plen = sizeof(peer);
getpeername(cl, (struct sockaddr*)&peer, &plen);
char peer_ip[INET_ADDRSTRLEN];
inet_ntop(AF_INET, &peer.sin_addr, peer_ip, sizeof(peer_ip));
```

**`getpeername`** — заполняет структуру адресом другой стороны.

**`inet_ntop`** — из 32-битного числа в строку вида `"192.168.1.1"`. "network to presentation". `INET_ADDRSTRLEN` — константа, достаточная для IPv4-адреса (16 символов).

---

#### Таймаут

```c
struct timeval tv;
tv.tv_sec  = SOCKET_TIMEOUT;
tv.tv_usec = 0;
setsockopt(cl, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
setsockopt(cl, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));
```

**`struct timeval`** — структура для времени: секунды + микросекунды. `SO_RCVTIMEO`/`SO_SNDTIMEO` — таймауты приёма/отправки. Если клиент молчит 10 секунд — `recv` вернёт `EAGAIN`.

---

#### Чтение запроса

```c
ssize_t r = recv(cl, buf, sizeof buf - 1, 0);
buf[r] = 0;
```

**`recv`** — читает из сокета. `sizeof buf - 1` — оставляем место для `\0`. После `recv` вручную ставим `buf[r] = 0` — превращаем принятые байты в строку.

---

#### Маршрутизация

```c
if (strcmp(req.method,"GET")==0){ ... close(cl); continue; }
if (c->auth_enabled && !check_auth(req.authorization,c)){ ... }
if (strcmp(req.method,"POST")==0 && strcmp(req.path,"/upload")==0){ ... }
```

Смотрим метод и путь, решаем что делать. `continue` — к следующей итерации цикла (следующий клиент).

---

#### Обработка загрузки

```c
char *body_ptr  = strstr(buf, "\r\n\r\n");
body_ptr += 4;
size_t header_len      = body_ptr - buf;
size_t initial_body_len = (size_t)r > header_len ? (size_t)r - header_len : 0;
```

`"\r\n\r\n"` — разделитель заголовков и тела в HTTP. `body_ptr - buf` — разность указателей = длина заголовков в байтах. `r - header_len` — сколько байт тела уже попало при первом `recv`.

```c
char *display_name = strrchr(final_path, '/');
display_name = display_name ? display_name + 1 : final_path;
```

**`strrchr`** — ищет последнее вхождение символа. Для `"/tmp/photo.jpg"` вернёт указатель на последний `/`. `+1` — за слэш, получаем `"photo.jpg"`.

```c
rename(filepath, final_path);
unlink(filepath);
```

**`rename`** — переименовывает файл. Атомарная операция. Сначала пишем во временный `upload.bin`, потом переименовываем в настоящее имя.

**`unlink`** — удаляет файл. Если парсинг провалился — убираем мусор.

---

## main.c

```c
int main(int c, char **v){
    server_config_t cfg;
    default_config(&cfg);
    if (c > 1) load_config(v[1], &cfg);
    return start_server(&cfg);
}
```

**`int c, char **v`** — аргументы командной строки. `v[0]` — имя программы, `v[1]` — первый аргумент (путь к конфигу). Обычно пишут `argc, argv`, здесь сокращено.

**`server_config_t cfg`** — структура на стеке `main`. Живёт всё время работы программы.

**`default_config(&cfg)`** — передаём адрес структуры (`&cfg`). Если передать `cfg` без `&`, функция получит копию и изменения не сохранятся.

**`return start_server(&cfg)`** — `start_server` в нормальной ситуации не возвращается (бесконечный цикл). Если вернула — значит ошибка при старте.

---

## Словарик C-идиом

### Указатели и адреса

Указатель — переменная, хранящая адрес в памяти. `int *p` — `p` хранит адрес `int`. `*p` — читаем/пишем `int` по этому адресу. `&x` — взять адрес `x`. Нужны когда функция должна изменить что-то снаружи, или данные слишком большие чтобы копировать.

### Арифметика указателей

`p + n` — сдвиг на `n` элементов (не байт — элементов того типа). `p1 - p2` — количество элементов между двумя указателями. `p++` — следующий элемент.

### `static`

- На уровне файла (вне функции): "видно только в этом `.c`". Аналог `private`.
- Внутри функции: переменная инициализируется один раз и живёт всю программу.

### `const`

Обещание не менять. `const char *p` — строку не трогаем. Компилятор предупредит если нарушишь.

### `size_t` vs `ssize_t`

`size_t` — беззнаковый, для размеров. `ssize_t` — знаковый, для результатов `recv`/`send` (могут вернуть -1). Никогда не храни результат `recv` в `size_t` — `-1` превратится в огромное число.

### `malloc` / `free`

Динамическая память: `malloc` выделяет, `free` освобождает. Каждый `malloc` — ровно один `free`. Не освободил — утечка. Освободил дважды — крэш. После `free` лучше обнулить: `p = NULL`.

### Строки в C

Строка — массив `char`, последний элемент `'\0'`. Без `\0` строковые функции читают мусор. Всегда выделяй `длина + 1` байт. `"hello"` — литерал длиной 6 байт (5 + `\0`).

### `if((h = strstr(...)))`

Присваивание внутри условия. Сначала выполняется `strstr`, результат в `h`, потом `h` проверяется на `NULL`. Одна строка вместо двух. Распространённая C-идиома.
