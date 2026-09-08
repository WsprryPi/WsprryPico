/* Project-owned integration around immutable SDK-pinned lwIP mdns.c.
 * See docs/development/mdns-responder.md and docs/licenses/lwip-mdns.txt.
 * Including the exact upstream translation unit permits bounded initialization
 * and complete cleanup of its private retained-packet list without an SDK patch.
 */
#include "standalone/pico/mdns_lwip.h"

#include <limits.h>
#include WSPRRY_PICO_LWIP_MDNS_SOURCE

static mdns_name_result_cb_t application_callback;
static int started;
static int changed;
static unsigned goodbye_attempts, goodbye_failures, rejected_packets;
NETIF_DECLARE_EXT_CALLBACK(wsprry_netif_callback)

static void increment(unsigned* value) {
    if (*value != UINT_MAX)
        ++*value;
}
static void cancel_timers(struct netif* interface) {
    sys_untimeout(mdns_probe_and_announce, interface);
    sys_untimeout(mdns_multicast_timeout_reset_ipv4, interface);
    sys_untimeout(mdns_multicast_probe_timeout_reset_ipv4, interface);
    sys_untimeout(mdns_multicast_timeout_25ttl_reset_ipv4, interface);
    sys_untimeout(mdns_send_multicast_msg_delayed_ipv4, interface);
    sys_untimeout(mdns_send_unicast_msg_delayed_ipv4, interface);
}
static void quiesce(struct netif* interface) {
    struct mdns_host* host = NETIF_TO_HOST(interface);
    if (host) {
        cancel_timers(interface);
        host->state = MDNS_STATE_OFF;
    }
}
static void name_result(struct netif* interface, u8_t result, s8_t slot) {
    if (result == MDNS_PROBING_CONFLICT)
        quiesce(interface);
    if (application_callback)
        application_callback(interface, result, slot);
}
static void interface_changed(struct netif* interface, netif_nsc_reason_t reason,
                              const netif_ext_callback_args_t* args) {
    LWIP_UNUSED_ARG(args);
    if (NETIF_TO_HOST(interface) && (reason & (LWIP_NSC_STATUS_CHANGED | LWIP_NSC_LINK_CHANGED |
                                               LWIP_NSC_IPV4_ADDRESS_CHANGED))) {
        quiesce(interface);
        changed = 1;
    }
}
static void receive_bounded(void* context, struct udp_pcb* pcb, struct pbuf* packet,
                            const ip_addr_t* address, u16_t port) {
    struct netif* interface = ip_current_input_netif();
    struct mdns_host* host = interface ? NETIF_TO_HOST(interface) : NULL;
    mdns_resp_state_enum_t before;
    if (!packet)
        return;
    // Bound parsing and retained truncated packets to one IPv4 Ethernet payload.
    if (!host || host->state == MDNS_STATE_OFF || packet->tot_len > 1472 ||
        !netif_is_up(interface) || !netif_is_link_up(interface) ||
        ip4_addr_isany_val(*netif_ip4_addr(interface))) {
        increment(&rejected_packets);
        pbuf_free(packet);
        return;
    }
    before = host->state;
    mdns_recv(context, pcb, packet, address, port);
    // Upstream re-probes established-name conflicts without its result callback.
    // This deployment must latch instead of continuing to use an uncertain name.
    if (before >= MDNS_STATE_ANNOUNCING && host->state == MDNS_STATE_PROBE_WAIT)
        name_result(interface, MDNS_PROBING_CONFLICT, 0);
}
err_t wsprry_mdns_init(mdns_name_result_cb_t callback) {
    err_t result;
    application_callback = callback;
    if (started)
        return ERR_OK;
    mdns_pcb = udp_new_ip_type(IPADDR_TYPE_V4);
    if (!mdns_pcb)
        return ERR_MEM;
    result = udp_bind(mdns_pcb, IP_ANY_TYPE, LWIP_IANA_PORT_MDNS);
    if (result != ERR_OK) {
        udp_remove(mdns_pcb);
        mdns_pcb = NULL;
        return result;
    }
    LWIP_MEMPOOL_INIT(MDNS_PKTS);
    mdns_pcb->ttl = MDNS_IP_TTL;
    udp_recv(mdns_pcb, receive_bounded, NULL);
    mdns_netif_client_id = netif_alloc_client_data_id();
    mdns_resp_register_name_result_cb(name_result);
    netif_add_ext_callback(&wsprry_netif_callback, interface_changed);
    started = 1;
    return ERR_OK;
}
err_t wsprry_mdns_add(struct netif* interface, const char* label) {
    if (!started || !interface || !label || !*label || !netif_is_up(interface) ||
        !netif_is_link_up(interface) || ip4_addr_isany_val(*netif_ip4_addr(interface)))
        return ERR_VAL;
    if (NETIF_TO_HOST(interface))
        return ERR_ALREADY;
    changed = 0;
    return mdns_resp_add_netif(interface, label);
}
static err_t goodbye(struct netif* interface) {
    // Reuse upstream's A/PTR generation, including compressed domain encoding.
    struct mdns_outmsg message;
    struct mdns_outpacket packet;
    struct dns_hdr header;
    err_t result;
    u16_t offset = SIZEOF_DNS_HDR;
    unsigned record;
    memset(&message, 0, sizeof(message));
    memset(&packet, 0, sizeof(packet));
    memset(&header, 0, sizeof(header));
    message.flags = DNS_FLAG1_RESPONSE | DNS_FLAG1_AUTHORATIVE;
    message.cache_flush = 1;
    message.host_replies = REPLY_HOST_A | REPLY_HOST_PTR_V4;
    result = mdns_create_outpacket(interface, &message, &packet);
    if (result != ERR_OK || !packet.pbuf)
        goto done;
    for (record = 0; record < packet.answers; ++record) {
        struct mdns_domain domain;
        u16_t end = mdns_readname(packet.pbuf, offset, &domain);
        u16_t length;
        unsigned byte;
        if (end == MDNS_READNAME_ERROR || end + 10U > packet.write_offset ||
            pbuf_copy_partial(packet.pbuf, &length, 2, end + 8) != 2) {
            result = ERR_VAL;
            goto done;
        }
        for (byte = 0; byte < 4; ++byte)
            pbuf_put_at(packet.pbuf, end + 4 + byte, 0);
        offset = end + 10 + lwip_ntohs(length);
    }
    header.flags1 = message.flags;
    header.numanswers = lwip_htons(packet.answers);
    pbuf_take(packet.pbuf, &header, sizeof(header));
    pbuf_realloc(packet.pbuf, packet.write_offset);
    result = udp_sendto_if(mdns_pcb, packet.pbuf, &v4group, LWIP_IANA_PORT_MDNS, interface);
done:
    if (packet.pbuf)
        pbuf_free(packet.pbuf);
    return result;
}
void wsprry_mdns_remove(struct netif* interface, int send_goodbye) {
    struct mdns_packet** current;
    if (!started || !interface || !NETIF_TO_HOST(interface))
        return;
    if (send_goodbye && netif_is_up(interface) && netif_is_link_up(interface) &&
        !ip4_addr_isany_val(*netif_ip4_addr(interface))) {
        increment(&goodbye_attempts);
        if (goodbye(interface) != ERR_OK)
            increment(&goodbye_failures);
    }
    quiesce(interface);
    current = &pending_tc_questions;
    while (*current) {
        struct mdns_packet* packet = *current;
        if (packet->pbuf->if_idx != netif_get_index(interface)) {
            current = &packet->next_tc_question;
            continue;
        }
        *current = packet->next_tc_question;
        sys_untimeout(mdns_handle_tc_question, packet);
        while (packet->next_answer) {
            struct mdns_packet* answer = packet->next_answer;
            packet->next_answer = answer->next_answer;
            pbuf_free(answer->pbuf);
            LWIP_MEMPOOL_FREE(MDNS_PKTS, answer);
        }
        pbuf_free(packet->pbuf);
        LWIP_MEMPOOL_FREE(MDNS_PKTS, packet);
    }
    (void)mdns_resp_remove_netif(interface);
}
int wsprry_mdns_network_changed(void) {
    int result = changed;
    changed = 0;
    return result;
}
unsigned wsprry_mdns_goodbye_attempts(void) {
    return goodbye_attempts;
}
unsigned wsprry_mdns_goodbye_failures(void) {
    return goodbye_failures;
}
unsigned wsprry_mdns_rejected_packets(void) {
    return rejected_packets;
}
size_t wsprry_mdns_host_bytes(void) {
    return sizeof(struct mdns_host);
}
size_t wsprry_mdns_packet_bytes(void) {
    return sizeof(struct mdns_packet);
}
