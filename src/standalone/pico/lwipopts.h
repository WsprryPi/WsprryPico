#pragma once
// Single-core foreground polling. Only DHCP, ARP, IPv4 and unicast SNTP/UDP.
#define NO_SYS 1
#define LWIP_SOCKET 0
#define LWIP_NETCONN 0
#define LWIP_TCP 0
#define LWIP_UDP 1
#define LWIP_DHCP 1
#define LWIP_DNS 0
#define LWIP_IPV6 0
#define LWIP_RAW 0
#define LWIP_NETIF_STATUS_CALLBACK 1
#define LWIP_NETIF_LINK_CALLBACK 1
// The RP2350 requires word-aligned lwIP heap blocks and packet pools.
#define MEM_ALIGNMENT 4
#define MEM_SIZE 8192
#define PBUF_POOL_SIZE 8
#define MEMP_NUM_UDP_PCB 3
#define LWIP_STATS 0
#define LWIP_DHCP_DOES_ACD_CHECK 0
#define LWIP_TIMEVAL_PRIVATE 0
