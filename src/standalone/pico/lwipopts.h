#pragma once
// Core-0 foreground polling: DHCP, ARP, IPv4, SNTP and bounded TLS/TCP.
// Physical RF owns core 1; it never calls lwIP/CYW43.
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
#define LWIP_DNS 1
#define DNS_TABLE_SIZE 2
#define DNS_MAX_REQUESTS 1
#define LWIP_DNS_SUPPORT_MDNS_QUERIES 1
#define LWIP_IGMP 1
#define LWIP_MDNS_RESPONDER 1
#define LWIP_MDNS_SEARCH 0
#define MDNS_MAX_SERVICES 1
#define MDNS_MAX_STORED_PKTS 2
#define MDNS_OUTPUT_PACKET_SIZE 512
#define LWIP_NUM_NETIF_CLIENT_DATA 1
#define LWIP_NETIF_EXT_STATUS_CALLBACK 1
// Adapter quiesces immediately, then removes/reprobes from foreground polling.
#define MDNS_RESP_USENETIF_EXTCALLBACK 0
// Probe + two delayed replies + three cooldowns + two retained TC questions.
#define MEMP_NUM_SYS_TIMEOUT (LWIP_NUM_SYS_TIMEOUT_INTERNAL + 8)
#define MEMP_NUM_IGMP_GROUP 3
#define LWIP_IPV6 0
#define LWIP_RAW 0
#define LWIP_NETIF_STATUS_CALLBACK 1
#define LWIP_NETIF_LINK_CALLBACK 1
// The RP2350 requires word-aligned lwIP heap blocks and packet pools.
#define MEM_ALIGNMENT 4
#define MEM_SIZE 32768
#define PBUF_POOL_SIZE 8
#define MEMP_NUM_UDP_PCB 4 // DHCP, SNTP, mDNS responder and asynchronous DNS.
#define LWIP_STATS 1
#define LWIP_STATS_LARGE 1
#define LWIP_STATS_DISPLAY 0
#define MEM_STATS 1
#define MEMP_STATS 1
#define LWIP_DHCP_DOES_ACD_CHECK 0
#define LWIP_TIMEVAL_PRIVATE 0
