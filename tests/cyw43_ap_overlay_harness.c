// Compile the actual pinned AP initializer against observable ioctl boundaries.
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
typedef struct { uint8_t spid_buf[512]; } cyw43_int_t;
typedef cyw43_int_t cyw43_ll_t;
#define CYW_INT_FROM_LL(x) (x)
#define SDPCM_HEADER_LEN 12
#define SDPCM_GET 0
#define SDPCM_SET 1
#define WLC_GET_VAR 262
#define WLC_SET_WSEC_PMK 268
#define WLC_SET_CHANNEL 30
#define WLC_SET_GMODE 110
#define WLC_SET_DTIMPRD 78
#define WWD_STA_INTERFACE 0
#define WWD_AP_INTERFACE 1
#define CYW43_AUTH_OPEN 0
#define CYW43_AUTH_WPA_TKIP_PSK 1
#define CYW43_AUTH_WPA2_AES_PSK 2
#define CYW43_AUTH_WPA2_MIXED_PSK 3
#define CYW43_AUTH_WPA3_SAE_AES_PSK 4
#define CYW43_AUTH_WPA3_WPA2_AES_PSK 5
#define CYW43_WPA_AUTH_PSK 4
#define CYW43_WPA2_AUTH_PSK 128
#define CYW43_WPA3_AUTH_SAE_PSK 0x40000
#define CYW43_WPA_MAX_PASSWORD_LEN 63
#define CYW43_WPA_SAE_MAX_PASSWORD_LEN 128
#define CYW43_EINVAL 22
#define MFP_NONE 0
#define MFP_CAPABLE 1
#define MFP_REQUIRED 2
static uint32_t selected_auth;
static void cyw43_put_le16(uint8_t *p,uint16_t v){p[0]=v;p[1]=v>>8;}
static void cyw43_put_le32(uint8_t *p,uint32_t v){memcpy(p,&v,4);}
static uint32_t cyw43_get_le32(const uint8_t *p){uint32_t v;memcpy(&v,p,4);return v;}
static void cyw43_do_ioctl(cyw43_int_t *s,int op,int cmd,int n,uint8_t *buf,int itf){if(op==SDPCM_GET)memset(buf,0,4);}
static void cyw43_write_iovar_u32(cyw43_int_t *s,const char *name,uint32_t v,int itf){}
static void cyw43_write_iovar_n(cyw43_int_t *s,const char *name,size_t n,const uint8_t *buf,int itf){}
static void cyw43_set_ioctl_u32(cyw43_int_t *s,int cmd,uint32_t v,int itf){}
static void cyw43_delay_ms(int ms){}
static void cyw43_write_iovar_u32_u32(cyw43_int_t *s,const char *name,uint32_t index,uint32_t v,int itf){if(!strcmp(name,"bsscfg:wpa_auth")){assert(index==WWD_AP_INTERFACE);selected_auth=v;}}
int cyw43_ll_wifi_ap_init(cyw43_ll_t*,size_t,const uint8_t*,uint32_t,size_t,const uint8_t*,uint32_t);
static int check_ap_auth(void){
 cyw43_int_t s={0};const uint8_t ssid[]="test",key[]="test-key";
 selected_auth=0;
 assert(cyw43_ll_wifi_ap_init(&s,4,ssid,CYW43_AUTH_WPA2_AES_PSK,8,key,1)==0);
 assert(selected_auth==(EXPECT_FIXED?CYW43_WPA2_AUTH_PSK:(CYW43_WPA_AUTH_PSK|CYW43_WPA2_AUTH_PSK)));
 selected_auth=0;
 assert(cyw43_ll_wifi_ap_init(&s,4,ssid,CYW43_AUTH_WPA2_MIXED_PSK,8,key,1)==0);
 assert(selected_auth==(CYW43_WPA_AUTH_PSK|CYW43_WPA2_AUTH_PSK));
 selected_auth=0;
 assert(cyw43_ll_wifi_ap_init(&s,4,ssid,CYW43_AUTH_OPEN,0,key,1)==0);assert(selected_auth==0);
 assert(cyw43_ll_wifi_ap_init(&s,4,ssid,CYW43_AUTH_WPA2_AES_PSK,64,key,1)==-CYW43_EINVAL);
 return 0;
}
