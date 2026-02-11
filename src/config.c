
#include "config.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
void default_config(server_config_t *c){
    strcpy(c->address,"0.0.0.0");
    c->port=8080;
    strcpy(c->upload_dir,"/tmp");
    strcpy(c->username,"admin");
    strcpy(c->password,"admin");
    c->auth_enabled=1;
}
int load_config(const char*path, server_config_t*c){
    FILE*f=fopen(path,"r"); if(!f) return -1;
    char l[256],k[64],v[128];
    while(fgets(l,sizeof l,f)){
        if(sscanf(l,"%63[^=]=%127s",k,v)==2){
            if(!strcmp(k,"address"))strcpy(c->address,v);
            else if(!strcmp(k,"port"))c->port=atoi(v);
            else if(!strcmp(k,"upload_dir"))strcpy(c->upload_dir,v);
            else if(!strcmp(k,"username"))strcpy(c->username,v);
            else if(!strcmp(k,"password"))strcpy(c->password,v);
            else if(!strcmp(k,"auth_enabled"))c->auth_enabled=!strcmp(v,"true");
        }
    }
    fclose(f); return 0;
}
