# Инструкция по тестированию HTTP сервера

## Сборка проекта

```bash
make clean
make
```

## Базовое тестирование

### 1. Запуск сервера

```bash
./simple_http server.conf
```

Сервер запустится на `0.0.0.0:8080` (по умолчанию).

### 2. Тестирование через браузер

1. Откройте браузер и перейдите по адресу: `http://localhost:8080`
2. Вы увидите форму для загрузки файла
3. Выберите файл и нажмите "Upload"
4. При запросе авторизации используйте:
   - Username: `admin`
   - Password: `admin`
   - (или значения из `server.conf`)

### 3. Тестирование через curl

#### GET запрос (получение формы):
```bash
curl http://localhost:8080/
```

#### POST запрос с авторизацией:
```bash
curl -u admin:admin -F "file=@/path/to/your/file.txt" http://localhost:8080/upload
```

#### POST запрос без авторизации (если auth_enabled=false):
```bash
curl -F "file=@/path/to/your/file.txt" http://localhost:8080/upload
```

### 4. Проверка загруженных файлов

Загруженные файлы сохраняются в директорию, указанную в `server.conf` (по умолчанию `/tmp`):

```bash
ls -la /tmp/
```

## Отладка с gcc

### Компиляция с отладочной информацией

Проект уже настроен для отладки. Makefile использует флаг `-g`:

```bash
make clean
make
```

### Запуск под gdb

```bash
gdb ./simple_http
(gdb) run server.conf
```

### Проверка на утечки памяти и ошибки

Используйте `valgrind` (см. раздел ниже).

## Профилирование с Valgrind

### Установка Valgrind (если не установлен)

```bash
# Arch Linux
sudo pacman -S valgrind

# Ubuntu/Debian
sudo apt-get install valgrind
```

### Проверка на утечки памяти

```bash
valgrind --leak-check=full --show-leak-kinds=all --track-origins=yes \
  ./simple_http server.conf
```

### Проверка на ошибки использования памяти

```bash
valgrind --tool=memcheck --leak-check=full \
  --show-leak-kinds=all --track-origins=yes \
  --verbose ./simple_http server.conf
```

### Проверка на гонки данных (если будет многопоточность)

```bash
valgrind --tool=helgrind ./simple_http server.conf
```

### Тестирование с нагрузкой

В другом терминале запустите несколько запросов:

```bash
# Простой тест
for i in {1..10}; do
  curl -u admin:admin -F "file=@/etc/passwd" http://localhost:8080/upload
done
```

### Оптимизация для Valgrind

Если нужно ускорить проверку, можно использовать:

```bash
valgrind --leak-check=summary --show-leak-kinds=definite \
  ./simple_http server.conf
```

## Тестирование как systemd сервис

### 1. Установка

```bash
# Скопируйте бинарник
sudo cp simple_http /usr/local/bin/
sudo chmod +x /usr/local/bin/simple_http

# Скопируйте конфигурацию
sudo cp server.conf /etc/simple_http.conf

# Скопируйте unit файл
sudo cp simple_http.service /etc/systemd/system/

# Создайте директорию для загрузок
sudo mkdir -p /var/lib/simple_http/uploads
sudo chown nobody:nogroup /var/lib/simple_http/uploads

# Обновите конфигурацию для использования правильной директории
sudo sed -i 's|upload_dir=/tmp|upload_dir=/var/lib/simple_http/uploads|' /etc/simple_http.conf
```

### 2. Запуск сервиса

```bash
sudo systemctl daemon-reload
sudo systemctl start simple_http
sudo systemctl status simple_http
```

### 3. Проверка логов

```bash
sudo journalctl -u simple_http -f
```

### 4. Автозапуск при загрузке

```bash
sudo systemctl enable simple_http
```

### 5. Остановка сервиса

```bash
sudo systemctl stop simple_http
```

## Тестирование различных сценариев

### Тест 1: Большой файл

```bash
# Создайте тестовый файл
dd if=/dev/zero of=test_large.bin bs=1M count=10

# Загрузите его
curl -u admin:admin -F "file=@test_large.bin" http://localhost:8080/upload
```

### Тест 2: Неправильная авторизация

```bash
curl -u wrong:password -F "file=@test.txt" http://localhost:8080/upload
# Должен вернуть 401 Unauthorized
```

### Тест 3: Неправильный путь

```bash
curl http://localhost:8080/wrong/path
# Должен вернуть 404 Not Found
```

### Тест 4: Неправильный метод

```bash
curl -X PUT http://localhost:8080/upload
# Должен вернуть 404 Not Found
```

### Тест 5: Проверка обработки ошибок

```bash
# Запустите сервер на занятом порту
./simple_http server.conf &
sleep 1
./simple_http server.conf  # Должна быть ошибка bind
```

## Проверка безопасности

### Тест на переполнение буфера

Valgrind поможет обнаружить проблемы с памятью:

```bash
valgrind --tool=memcheck ./simple_http server.conf
```

### Тест на обработку специальных символов в имени файла

```bash
# Создайте файл с "опасным" именем
echo "test" > "test;rm -rf /"
curl -u admin:admin -F "file=@test;rm -rf /" http://localhost:8080/upload
```

## Автоматизированное тестирование

Создайте скрипт `test.sh`:

```bash
#!/bin/bash
set -e

echo "Starting server..."
./simple_http server.conf &
SERVER_PID=$!
sleep 2

echo "Testing GET request..."
curl -s http://localhost:8080/ | grep -q "Upload File" || exit 1

echo "Testing POST upload..."
curl -s -u admin:admin -F "file=@server.conf" http://localhost:8080/upload | grep -q "uploaded" || exit 1

echo "Testing unauthorized access..."
curl -s -u wrong:password http://localhost:8080/upload | grep -q "401" || exit 1

echo "All tests passed!"
kill $SERVER_PID
```

Запуск:
```bash
chmod +x test.sh
./test.sh
```
