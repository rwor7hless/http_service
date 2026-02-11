
CC=gcc
CFLAGS=-Wall -Wextra -std=c11 -O2 -g
SRC=$(wildcard src/*.c)
OBJ=$(SRC:.c=.o)
BIN=simple_http

all: $(BIN)

$(BIN): $(OBJ)
	$(CC) $(CFLAGS) -o $@ $^

clean:
	rm -f $(OBJ) $(BIN)
