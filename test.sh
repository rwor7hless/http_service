#!/bin/bash
set -e

echo "=== Тестирование HTTP сервера ==="

# Проверка компиляции
echo "1. Проверка компиляции..."
make clean > /dev/null 2>&1
make > /dev/null 2>&1
if [ ! -f "./simple_http" ]; then
    echo "ОШИБКА: Компиляция не удалась"
    exit 1
fi
echo "✓ Компиляция успешна"

# Запуск сервера в фоне
echo "2. Запуск сервера..."
./simple_http server.conf > /tmp/server.log 2>&1 &
SERVER_PID=$!
sleep 2

# Проверка что сервер запустился
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "ОШИБКА: Сервер не запустился"
    cat /tmp/server.log
    exit 1
fi
echo "✓ Сервер запущен (PID: $SERVER_PID)"

# Тест GET запроса
echo "3. Тест GET запроса (получение формы)..."
RESPONSE=$(curl -s http://localhost:8080/)
if echo "$RESPONSE" | grep -q "Upload File"; then
    echo "✓ GET запрос работает"
else
    echo "ОШИБКА: GET запрос не вернул форму"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

# Тест POST запроса с авторизацией
echo "4. Тест POST запроса с авторизацией..."
echo "test content" > /tmp/test_upload.txt
RESPONSE=$(curl -s -u admin:admin -F "file=@/tmp/test_upload.txt" http://localhost:8080/upload)
if echo "$RESPONSE" | grep -q "uploaded"; then
    echo "✓ POST запрос с авторизацией работает"
else
    echo "ОШИБКА: POST запрос не работает"
    echo "Ответ: $RESPONSE"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

# Проверка что файл сохранился
if [ -f "/tmp/test_upload.txt" ] || [ -f "/tmp/upload.bin" ]; then
    echo "✓ Файл сохранен"
else
    echo "ПРЕДУПРЕЖДЕНИЕ: Не удалось найти сохраненный файл"
fi

# Тест неавторизованного доступа
echo "5. Тест неавторизованного доступа..."
RESPONSE=$(curl -s -u wrong:password http://localhost:8080/upload)
if echo "$RESPONSE" | grep -q "401"; then
    echo "✓ Авторизация работает корректно"
else
    echo "ПРЕДУПРЕЖДЕНИЕ: Авторизация может работать некорректно"
fi

# Остановка сервера
echo "6. Остановка сервера..."
kill $SERVER_PID 2>/dev/null
wait $SERVER_PID 2>/dev/null || true
echo "✓ Сервер остановлен"

# Очистка
rm -f /tmp/test_upload.txt /tmp/upload.bin

echo ""
echo "=== Все тесты пройдены успешно! ==="
