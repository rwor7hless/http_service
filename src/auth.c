
#include "auth.h"
#include <string.h>
#include <stdio.h>
static int idx(char c){
    if('A'<=c&&c<='Z')return c-'A';
    if('a'<=c&&c<='z')return c-'a'+26;
    if('0'<=c&&c<='9')return c-'0'+52;
    if(c=='+')return 62;
    if(c=='/')return 63;
    return -1;
}
static int b64(const char*in,unsigned char*out){
    int v=0,b=-8,l=0;
    for(;*in;in++){
        int d=idx(*in); if(d<0)break;
        v=(v<<6)+d; b+=6;
        if(b>=0){ out[l++]=(v>>b)&0xFF; b-=8; }
    }
    return l;
}
int check_auth(const char*h,const server_config_t*c){
    if(strncmp(h,"Basic ",6))return 0;
    unsigned char d[128]={0};
    b64(h+6,d);
    char exp[128];
    snprintf(exp,sizeof exp,"%s:%s",c->username,c->password);
    return strcmp((char*)d,exp)==0;
}
