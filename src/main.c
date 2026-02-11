
#include "server.h"
#include "config.h"
int main(int c,char**v){
    server_config_t cfg; default_config(&cfg);
    if(c>1) load_config(v[1],&cfg);
    return start_server(&cfg);
}
