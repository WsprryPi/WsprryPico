#pragma once
// Single-core foreground polling: DHCP, ARP, IPv4, SNTP and bounded TLS/TCP.
#define NO_SYS 1
#define LWIP_SOCKET 0
#define LWIP_NETCONN 0
#define LWIP_TCP 1
#define TCP_MSS 1460
#define TCP_WND (2 * TCP_MSS)
#define TCP_SND_BUF (4 * TCP_MSS)
#define TCP_SND_QUEUELEN 32
#define MEMP_NUM_TCP_PCB 4
#define MEMP_NUM_TCP_PCB_LISTEN 1
#define MEMP_NUM_TCP_SEG 32
#define TCP_LISTEN_BACKLOG 1
#define LWIP_UDP 1
#define LWIP_DHCP 1
#define LWIP_DNS 0
#define LWIP_IPV6 0
#define LWIP_RAW 0
#define LWIP_NETIF_STATUS_CALLBACK 1
#define LWIP_NETIF_LINK_CALLBACK 1
// The RP2350 requires word-aligned lwIP heap blocks and packet pools.
#define MEM_ALIGNMENT 4
#define MEM_SIZE 32768
#define PBUF_POOL_SIZE 8
#define MEMP_NUM_UDP_PCB 3
#define LWIP_STATS 0
#define LWIP_DHCP_DOES_ACD_CHECK 0
#define LWIP_TIMEVAL_PRIVATE 0
