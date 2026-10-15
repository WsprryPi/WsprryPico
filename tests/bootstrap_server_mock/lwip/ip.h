#pragma once
#include "lwip/tcp.h"
inline void* ip_current_input_netif() {
    return nullptr;
}
inline void tcp_bind_netif(tcp_pcb*, void*) {}
