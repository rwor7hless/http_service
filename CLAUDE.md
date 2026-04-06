# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run

```bash
make          # build -> ./simple_http
make clean    # remove objects and binary

./simple_http [server.conf]   # run with optional config file
```

Default config (no file): `0.0.0.0:8080`, upload dir `/tmp`, auth enabled (`admin:admin`).

## Testing

```bash
bash test.sh   # full integration test (builds, starts server, runs curl tests, stops server)
```

Manual curl tests:
```bash
curl http://localhost:8080/                              # get upload form
curl -u admin:admin -F "file=@/path/to/file" http://localhost:8080/upload   # upload
```

## systemd Deployment

```bash
sudo cp simple_http /usr/local/bin/
sudo cp simple_http.service /etc/systemd/system/
sudo cp server.conf /etc/simple_http.conf
sudo systemctl enable --now simple_http
```

## Architecture

Single-threaded, single-process HTTP server with no dependencies beyond libc. One connection is handled at a time (blocking accept loop).

**Request flow:**
1. `main.c` — loads `server_config_t` from optional config file, calls `start_server()`
2. `src/server.c:start_server()` — accept loop; reads headers into a single `MAX_HEADER_SIZE` (8192 byte) buffer, routes on method + path
3. `src/http_request.c` — `parse_http_headers()` fills `http_request_t` (method, path, content-type, authorization, content-length)
4. `src/server.c` — for `POST /upload`: checks Basic Auth via `check_auth()`, then streams the body into a temp file via `parse_multipart()`
5. `src/multipart.c:parse_multipart()` — allocates the entire body (`Content-Length` bytes, max `MAX_BODY_SIZE` = 50 MB) into memory, extracts filename from `Content-Disposition`, writes file data to the already-opened `FILE*`
6. `src/auth.c` — hand-rolled Base64 decoder + `strcmp` credential check against config values
7. `src/http_response.c` — `http_error()` sends standard error responses

**Config keys** (`server.conf` format: `key=value`):
`address`, `port`, `upload_dir`, `username`, `password`, `auth_enabled` (`true`/`false`)

**Key limits** (`src/limits.h`): header buffer 8 KB, body max 50 MB, socket timeout 10 s.

**HTML upload form** is embedded as a C string literal in `server.c` — no static file needed.
