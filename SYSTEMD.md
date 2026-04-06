# Systemd: интеграция сервиса simple_http

---

## 1. Что такое systemd

**systemd** — это система инициализации (init system) и менеджер служб для Linux, которая с 2011–2015 годов стала стандартом де-факто в большинстве дистрибутивов (Debian, Ubuntu, Fedora, Arch, RHEL и др.).

Исторически до systemd использовались:
- **SysVinit** — shell-скрипты в `/etc/init.d/`, запуск строго последовательный
- **Upstart** (Ubuntu 2006–2014) — событийно-ориентированный, но ограниченный
- **systemd** — параллельный запуск, декларативные unit-файлы, journald, cgroups

### Что делает systemd

| Задача | Инструмент systemd |
|--------|-------------------|
| Запуск/остановка служб | `systemctl start/stop` |
| Автозапуск при загрузке | `systemctl enable` |
| Просмотр логов | `journalctl` |
| Управление сокетами | socket-активация |
| Монтирование ФС | `.mount` units |
| Расписание задач | `.timer` units |
| Изоляция процессов | namespace, cgroups |

### Как systemd запускает систему

```
firmware → bootloader → ядро → systemd (PID 1) → targets → сервисы
```

systemd сам является первым процессом (PID 1) и остаётся живым всё время работы системы. Все остальные процессы являются его потомками и управляются через **cgroups**.

---

## 2. Unit-файлы

**Unit** — это базовая единица управления в systemd. Каждый unit описывает один объект: службу, сокет, точку монтирования, таймер и т.д.

### Типы unit-файлов

| Расширение | Назначение |
|------------|-----------|
| `.service` | Процесс/служба (самый частый тип) |
| `.socket` | Сокет для socket-активации |
| `.timer` | Аналог cron — расписание запуска |
| `.mount` | Точка монтирования |
| `.target` | Группа units (аналог runlevel) |
| `.path` | Мониторинг файла/каталога |
| `.slice` | Группа в иерархии cgroups |
| `.device` | Устройство udev |

### Где хранятся unit-файлы

| Путь | Назначение | Приоритет |
|------|-----------|-----------|
| `/lib/systemd/system/` | Установленные пакетами (дистрибутив) | Низкий |
| `/etc/systemd/system/` | Администратор системы | Высокий |
| `/run/systemd/system/` | Временные (создаются в рантайме) | Средний |
| `~/.config/systemd/user/` | Пользовательские сервисы | — |

Если в `/etc/systemd/system/` есть файл с тем же именем, что и в `/lib/systemd/system/` — побеждает `/etc/`.

### Структура unit-файла

Любой unit-файл состоит из **секций** (в квадратных скобках) и **директив** внутри них:

```ini
[Unit]        # метаданные, зависимости, условия запуска
...

[Service]     # только для .service — параметры процесса
[Socket]      # только для .socket
[Timer]       # только для .timer
...

[Install]     # как unit включается в target (куда линкуется при enable)
...
```

---

## 3. Секция [Unit]

Секция общая для всех типов unit-файлов.

### Директивы метаданных

| Директива | Описание |
|-----------|---------|
| `Description=` | Человекочитаемое описание сервиса |
| `Documentation=` | Ссылки на документацию (man:, https://) |

### Директивы зависимостей

Это одна из самых важных частей — определяет порядок и условия запуска.

| Директива | Смысл |
|-----------|-------|
| `After=X` | Запустить **после** X (только порядок, не зависимость) |
| `Before=X` | Запустить **до** X |
| `Requires=X` | Жёсткая зависимость: если X не запустится — этот unit тоже упадёт |
| `Wants=X` | Мягкая зависимость: попробовать запустить X, но если не вышло — не критично |
| `BindsTo=X` | Если X остановился — этот unit тоже остановится |
| `Conflicts=X` | Не может работать одновременно с X |
| `PartOf=X` | При остановке/перезапуске X — этот unit тоже |

**Важный нюанс:** `After=` и `Requires=`/`Wants=` — разные вещи.
- `Requires=network.target` говорит «мне нужен network», но не говорит когда.
- `After=network.target` говорит «запускаться только после network».
- Обычно пишут оба вместе.

### Targets (аналоги runlevel)

| Target | Смысл |
|--------|-------|
| `network.target` | Сетевые интерфейсы подняты |
| `network-online.target` | Сеть полностью готова (есть IP, маршруты) |
| `multi-user.target` | Многопользовательский режим без GUI (аналог runlevel 3) |
| `graphical.target` | С GUI (аналог runlevel 5) |
| `sysinit.target` | Базовая инициализация системы завершена |

---

## 4. Секция [Service]

Описывает как запускать, останавливать и перезапускать процесс.

### Тип сервиса (Type=)

| Значение | Описание |
|----------|---------|
| `simple` (по умолчанию) | ExecStart — это и есть главный процесс |
| `forking` | Процесс форкается, родитель завершается (классика SysV) |
| `oneshot` | Выполняется один раз и завершается (скрипты) |
| `notify` | Процесс сам уведомляет systemd через `sd_notify()` о готовности |
| `exec` | Как simple, но ждёт завершения execve() |
| `idle` | Запускается только когда очередь заданий пуста |

### Запуск процесса

| Директива | Описание |
|-----------|---------|
| `ExecStart=` | Команда запуска (обязательная) |
| `ExecStartPre=` | Выполнить до запуска (например, создать директорию) |
| `ExecStartPost=` | Выполнить после запуска |
| `ExecStop=` | Команда для остановки (по умолчанию — SIGTERM) |
| `ExecReload=` | Команда для перезагрузки конфига (SIGHUP) |
| `WorkingDirectory=` | Рабочая директория процесса |
| `Environment=` | Переменные окружения |
| `EnvironmentFile=` | Файл с переменными окружения |

### Перезапуск (Restart=)

| Значение | Когда перезапускать |
|----------|-------------------|
| `no` (по умолчанию) | Никогда |
| `on-failure` | При ненулевом коде выхода или по сигналу |
| `on-abnormal` | По сигналу, таймауту, watchdog |
| `always` | Всегда, даже при `systemctl stop` |
| `on-success` | Только при нулевом коде выхода |

Дополнительные параметры:

| Директива | Описание |
|-----------|---------|
| `RestartSec=` | Пауза перед перезапуском (по умолчанию 100ms) |
| `StartLimitBurst=` | Максимум перезапусков за интервал |
| `StartLimitIntervalSec=` | Интервал для подсчёта перезапусков |

### Пользователь и права

| Директива | Описание |
|-----------|---------|
| `User=` | От какого пользователя запускать |
| `Group=` | От какой группы запускать |
| `DynamicUser=true` | Создать временного пользователя автоматически |
| `UMask=` | Маска прав для создаваемых файлов |

### Директории (автосоздание)

| Директива | Путь | Описание |
|-----------|------|---------|
| `StateDirectory=name` | `/var/lib/name` | Постоянные данные сервиса |
| `RuntimeDirectory=name` | `/run/name` | Временные данные (удаляются при остановке) |
| `CacheDirectory=name` | `/var/cache/name` | Кэш |
| `LogsDirectory=name` | `/var/log/name` | Логи |
| `ConfigurationDirectory=name` | `/etc/name` | Конфиги |

Директории создаются автоматически при запуске с правильным владельцем.

---

## 5. Изоляция и безопасность в [Service]

Это мощный инструмент systemd — sandboxing процесса без контейнеров.

### Файловая система

| Директива | Описание |
|-----------|---------|
| `ProtectSystem=strict` | `/`, `/usr`, `/boot` — только чтение |
| `ProtectSystem=full` | `/usr`, `/boot` — только чтение |
| `ProtectSystem=true` | `/usr` — только чтение |
| `ProtectHome=true` | `/home`, `/root`, `/run/user` — недоступны |
| `ReadWritePaths=` | Исключение из ProtectSystem — разрешить запись |
| `ReadOnlyPaths=` | Явно только чтение |
| `InaccessiblePaths=` | Полностью скрыть путь |
| `PrivateTmp=true` | Отдельный `/tmp` для процесса |

### Привилегии

| Директива | Описание |
|-----------|---------|
| `NoNewPrivileges=true` | Запрет `setuid`, `setcap` для дочерних процессов |
| `PrivateDevices=true` | Скрыть все устройства `/dev` кроме базовых |
| `CapabilityBoundingSet=` | Ограничить набор capabilities (например `CAP_NET_BIND_SERVICE`) |
| `AmbientCapabilities=` | Передать capability непривилегированному процессу |

### Ядро и пространства имён

| Директива | Описание |
|-----------|---------|
| `ProtectKernelTunables=true` | Запрет записи в `/proc/sys` |
| `ProtectKernelModules=true` | Запрет загрузки модулей ядра |
| `ProtectKernelLogs=true` | Запрет доступа к `/proc/kmsg`, `/dev/kmsg` |
| `ProtectControlGroups=true` | Запрет записи в cgroups |
| `RestrictNamespaces=true` | Запрет создания namespace (clone, unshare) |
| `LockPersonality=true` | Зафиксировать ABI (запрет `personality()`) |

### Сеть и системные вызовы

| Директива | Описание |
|-----------|---------|
| `RestrictAddressFamilies=` | Разрешить только указанные семейства сокетов |
| `SystemCallFilter=` | Whitelist/blacklist системных вызовов (seccomp) |
| `SystemCallArchitectures=native` | Только нативная архитектура |
| `MemoryDenyWriteExecute=true` | Запрет RWX-памяти (JIT-защита) |
| `RestrictRealtime=true` | Запрет RT-приоритетов планировщика |
| `IPAddressDeny=` | Файрвол на уровне сервиса |

---

## 6. Секция [Install]

Определяет, как unit включается в систему при `systemctl enable`.

| Директива | Описание |
|-----------|---------|
| `WantedBy=multi-user.target` | При enable создаётся симлинк в `/etc/systemd/system/multi-user.target.wants/` |
| `RequiredBy=` | Жёсткая версия WantedBy |
| `Also=` | При enable/disable одновременно включать другие units |
| `Alias=` | Дополнительное имя для этого unit |

`systemctl enable` просто создаёт симлинк. `systemctl start` — реально запускает. `systemctl enable --now` — и то и другое.

---

## 7. Разбор simple_http.service

```ini
[Unit]
Description=Simple HTTP Upload Server
After=network-online.target
Wants=network-online.target
```

**`After=network-online.target` + `Wants=network-online.target`** — правильная пара.

- `network.target` — интерфейсы подняты, но IP может ещё не быть
- `network-online.target` — сеть полностью готова: есть IP-адрес, маршруты настроены

Для HTTP-сервера, который сразу при старте вызывает `bind()`, нужен именно `network-online.target`. Используем `Wants=` (мягкая зависимость), а не `Requires=` — если сети нет, сервер всё равно попробует запуститься (актуально для offline-систем).

---

```ini
[Service]
ExecStart=/usr/local/bin/simple_http /etc/simple_http.conf
Restart=on-failure
```

**`ExecStart`** — полный путь к бинарю и конфигу. Полный путь обязателен (systemd не использует `PATH` из shell).

**`Restart=on-failure`** — перезапуск при ненулевом коде выхода или по сигналу (кроме SIGTERM/SIGINT). Если сервер упал из-за ошибки — автоматически поднимется. Нормальная остановка через `systemctl stop` перезапуск не вызывает.

---

```ini
DynamicUser=true
```

Вместо создания отдельного системного пользователя вручную (`useradd -r simple_http`) — systemd создаёт **временного пользователя** автоматически при каждом запуске. Пользователь существует только пока сервис работает, его UID уникален и не пересекается с другими. Файлы в `StateDirectory` сохраняют владельца между перезапусками через UID mapping.

---

```ini
StateDirectory=simple_http
StateDirectoryMode=0700
```

Автоматически создаёт `/var/lib/simple_http` с владельцем — динамическим пользователем. Директория **сохраняется** между перезапусками (в отличие от `RuntimeDirectory`). Режим `0700` — только владелец (сам сервис) может читать и писать.

---

```ini
UMask=0077
```

Маска прав для файлов, создаваемых сервисом. `0077` означает: от `0666` (файл) вычитаем `0077` → получаем `0600` (rw-------). Загруженные файлы будут доступны только владельцу процесса.

---

```ini
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/simple_http
PrivateTmp=true
```

- **`ProtectSystem=strict`** — монтирует `/`, `/usr`, `/boot` в read-only namespace. Процесс физически не может записать ничего вне разрешённых путей.
- **`ProtectHome=true`** — `/home`, `/root`, `/run/user` становятся пустыми директориями (через bind mount).
- **`ReadWritePaths=/var/lib/simple_http`** — исключение из `ProtectSystem`: только этот каталог доступен на запись.
- **`PrivateTmp=true`** — процесс получает свой изолированный `/tmp` и `/var/tmp`. Другие процессы в системе его не видят.

---

```ini
NoNewPrivileges=true
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictAddressFamilies=AF_INET
LockPersonality=true
MemoryDenyWriteExecute=true
RestrictRealtime=true
RestrictNamespaces=true
```

- **`NoNewPrivileges=true`** — ни сам процесс, ни его дочерние процессы не смогут получить новые привилегии через `setuid`/`setcap`. Даже если в бинаре установлен setuid-бит — он не сработает.
- **`PrivateDevices=true`** — `/dev` заменяется минимальным набором (`null`, `zero`, `random`, `urandom`, `full`, `tty`). Нет доступа к дискам, сетевым устройствам, etc.
- **`ProtectKernelTunables=true`** — `/proc/sys` только для чтения. Нельзя изменить параметры ядра через `sysctl`.
- **`ProtectKernelModules=true`** — запрет `init_module`/`finit_module`. Нельзя загрузить или выгрузить модули ядра.
- **`ProtectControlGroups=true`** — иерархия cgroups только для чтения. Нельзя перемещать процессы между группами.
- **`RestrictAddressFamilies=AF_INET`** — разрешены только IPv4-сокеты. Вызовы `socket(AF_INET6, ...)`, `socket(AF_UNIX, ...)` и т.д. вернут `EAFNOSUPPORT`. Сервер работает только на IPv4 — это соответствует коду (`AF_INET` в `server.c:113`).
- **`LockPersonality=true`** — фиксирует домен выполнения (запрет `personality()`). Предотвращает переключение в эмуляцию другого ABI (например, 32-bit).
- **`MemoryDenyWriteExecute=true`** — запрет создания страниц памяти одновременно writeable и executable (W^X). Блокирует JIT-компиляцию и большинство техник shellcode-инъекций.
- **`RestrictRealtime=true`** — запрет `SCHED_FIFO` и `SCHED_RR`. Сервис не может «захватить» CPU, вытеснив другие процессы.
- **`RestrictNamespaces=true`** — запрет `clone(CLONE_NEW*)` и `unshare()`. Нельзя создать новые network/mount/user namespace — это блокирует ряд техник побега из sandbox.

---

```ini
[Install]
WantedBy=multi-user.target
```

При `systemctl enable simple_http` создаётся симлинк:
```
/etc/systemd/system/multi-user.target.wants/simple_http.service
    → /etc/systemd/system/simple_http.service
```

`multi-user.target` — стандартный многопользовательский режим (без GUI). Большинство серверных сервисов вешаются именно сюда.

---

## 8. Что можно было бы добавить

Это директивы, которые логично подошли бы к данному сервису, но не используются:

### Ограничение ресурсов

```ini
MemoryMax=128M          # максимум RAM (убьёт процесс при превышении)
MemoryHigh=96M          # мягкий лимит (начинает throttle)
CPUQuota=50%            # не более 50% одного ядра
TasksMax=10             # максимум потоков/процессов
LimitNOFILE=1024        # максимум открытых файловых дескрипторов
```

### Мониторинг зависания

```ini
WatchdogSec=30          # если процесс не отвечает 30с — перезапуск
```
(Требует поддержки в коде через `sd_notify(0, "WATCHDOG=1")`)

### Более строгая сеть

```ini
RestrictAddressFamilies=AF_INET AF_INET6   # добавить IPv6
IPAddressDeny=any                           # запретить все IP
IPAddressAllow=192.168.0.0/16              # разрешить только локалку
```

### Логирование

```ini
StandardOutput=journal   # stdout → journald (уже дефолт)
StandardError=journal    # stderr → journald (уже дефолт)
SyslogIdentifier=simple_http  # метка в журнале
```

### Системные вызовы (seccomp)

```ini
SystemCallFilter=@system-service   # разрешить только стандартные для сервисов
SystemCallFilter=~@privileged      # запретить привилегированные
SystemCallArchitectures=native     # только нативная архитектура
```

### Уведомление о готовности

```ini
Type=notify              # сервис сам скажет systemd когда готов принимать запросы
TimeoutStartSec=10       # если за 10с не уведомил — ошибка старта
```
(Требует вызова `sd_notify(0, "READY=1")` в коде после `bind()`/`listen()`)

### Конфигурирование перезапусков

```ini
RestartSec=5             # подождать 5с перед перезапуском
StartLimitBurst=3        # не более 3 перезапусков
StartLimitIntervalSec=60 # за 60 секунд
```

---

## 9. Основные команды управления

```bash
# Установка
sudo cp simple_http.service /etc/systemd/system/
sudo systemctl daemon-reload        # перечитать unit-файлы

# Включение и запуск
sudo systemctl enable simple_http   # автозапуск при загрузке
sudo systemctl start simple_http    # запустить сейчас
sudo systemctl enable --now simple_http  # оба действия сразу

# Управление
sudo systemctl stop simple_http     # остановить
sudo systemctl restart simple_http  # перезапустить
sudo systemctl reload simple_http   # перезагрузить конфиг (если есть ExecReload)

# Статус и логи
systemctl status simple_http        # состояние, последние строки лога
journalctl -u simple_http           # все логи сервиса
journalctl -u simple_http -f        # в реальном времени
journalctl -u simple_http --since "1 hour ago"

# Анализ безопасности
systemd-analyze security simple_http   # оценка уровня изоляции (0-10)
```

---

## 10. Итоговая оценка unit-файла

Файл написан на высоком уровне для учебного проекта:

- Зависимости прописаны корректно (`network-online.target`)
- Используется `DynamicUser` — не нужно создавать пользователя вручную
- `StateDirectory` решает вопрос с правами на upload_dir автоматически
- Набор директив изоляции перекрывает основные векторы: ФС, устройства, ядро, сеть, память
- `RestrictAddressFamilies=AF_INET` точно соответствует коду сервера

Для продакшена не хватает ограничений ресурсов (`MemoryMax`, `CPUQuota`) и `StartLimitBurst`/`RestartSec`, чтобы бесконечный цикл перезапусков не положил систему. Но для курсача — полный порядок.
