
#ifndef CONFIG_H
#define CONFIG_H
#include <stdbool.h>
typedef struct {
    char address[64];
    int port;
    char upload_dir[256];
    char username[64];
    char password[64];
    bool auth_enabled;
} server_config_t;
void default_config(server_config_t*);
int load_config(const char*, server_config_t*);
#endif
