# Быстрая проверка работы сервера

## Запуск сервера

```bash
./simple_http server.conf
```

Вы должны увидеть:
```
Server started on 0.0.0.0:8080
Upload directory: /tmp
Auth enabled: yes
```

## Проверка что порт поднялся

В другом терминале выполните:

```bash
# Проверка процесса
ps aux | grep simple_http | grep -v grep

# Проверка порта
ss -tlnp | grep 8080
# или
netstat -tlnp | grep 8080
```

Вы должны увидеть что-то вроде:
```
LISTEN 0      5            0.0.0.0:8080       0.0.0.0:*
```

## Тестирование через браузер

Откройте браузер и перейдите на:
```
http://localhost:8080
```

Вы должны увидеть форму для загрузки файла.

## Тестирование через curl

```bash
# GET запрос (форма)
curl http://localhost:8080/

# POST запрос с авторизацией
curl -u admin:admin -F "file=@server.conf" http://localhost:8080/upload
```

## Если порт не поднимается

1. Проверьте, не занят ли порт другим процессом:
```bash
sudo lsof -i :8080
# или
sudo fuser 8080/tcp
```

2. Если порт занят, убейте процесс или измените порт в `server.conf`

3. Проверьте логи ошибок:
```bash
./simple_http server.conf 2>&1 | tee server.log
```

4. Проверьте права доступа:
```bash
ls -la simple_http
chmod +x simple_http
```
