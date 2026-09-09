#pragma once
#include "lwip/apps/mdns.h"

#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
// One IPv4 station, one boot-long PCB. No socket or hardware dependency.
err_t wsprry_mdns_init(mdns_name_result_cb_t callback);
err_t wsprry_mdns_add(struct netif* interface, const char* label);
// Quiesce replies and submit one goodbye, retaining membership/netif resources.
// Success is local stack submission, not radio transmission or peer delivery.
err_t wsprry_mdns_withdraw(struct netif* interface);
void wsprry_mdns_remove(struct netif* interface, int goodbye);
int wsprry_mdns_network_changed(void);
unsigned wsprry_mdns_goodbye_attempts(void);
unsigned wsprry_mdns_goodbye_failures(void);
unsigned wsprry_mdns_rejected_packets(void);
size_t wsprry_mdns_host_bytes(void);
size_t wsprry_mdns_packet_bytes(void);
#ifdef __cplusplus
}
#endif
