
#include "config.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
void default_config(server_config_t *c){
    memset(c, 0, sizeof(*c));
    strncpy(c->address, "0.0.0.0", sizeof(c->address) - 1);
    c->port=8080;
    strncpy(c->upload_dir, "/tmp", sizeof(c->upload_dir) - 1);
    strncpy(c->username, "admin", sizeof(c->username) - 1);
    strncpy(c->password, "admin", sizeof(c->password) - 1);
    c->auth_enabled=1;
}
int load_config(const char*path, server_config_t*c){
    FILE*f=fopen(path,"r"); if(!f) return -1;
    char l[256],k[64],v[128];
    while(fgets(l,sizeof l,f)){
        if(sscanf(l,"%63[^=]=%127s",k,v)==2){
            if(!strcmp(k,"address")){
                strncpy(c->address, v, sizeof(c->address) - 1);
                c->address[sizeof(c->address) - 1] = '\0';
            }
            else if(!strcmp(k,"port"))c->port=atoi(v);
            else if(!strcmp(k,"upload_dir")){
                strncpy(c->upload_dir, v, sizeof(c->upload_dir) - 1);
                c->upload_dir[sizeof(c->upload_dir) - 1] = '\0';
            }
            else if(!strcmp(k,"username")){
                strncpy(c->username, v, sizeof(c->username) - 1);
                c->username[sizeof(c->username) - 1] = '\0';
            }
            else if(!strcmp(k,"password")){
                strncpy(c->password, v, sizeof(c->password) - 1);
                c->password[sizeof(c->password) - 1] = '\0';
            }
            else if(!strcmp(k,"auth_enabled"))c->auth_enabled=!strcmp(v,"true");
        }
    }
    fclose(f); return 0;
}
