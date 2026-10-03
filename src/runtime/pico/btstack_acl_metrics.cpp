#include "runtime/pico/btstack_acl_metrics.hpp"

#include "btstack.h"
#include "pico/btstack_hci_transport_cyw43.h"

namespace {
wsprrypico::runtime::AclCreditMetrics metrics;
const hci_transport_t* original = nullptr;
hci_transport_t observed{};
void (*incoming)(std::uint8_t, std::uint8_t*, std::uint16_t) = nullptr;

void sample() {
    const bool working = hci_get_state() == HCI_STATE_WORKING;
    btstack_linked_list_iterator_t iterator;
    hci_connections_get_iterator(&iterator);
    const bool empty = !btstack_linked_list_iterator_has_next(&iterator);
    metrics.observe(working, empty,
                    working ? hci_number_free_acl_slots_for_connection_type(BD_ADDR_TYPE_LE_PUBLIC)
                            : 0);
}
bool valid_completions(const std::uint8_t* packet, std::uint16_t size, std::uint32_t& returned) {
    returned = 0;
    if (size < 3 || size != 3u + 4u * packet[2] || packet[1] != size - 2u)
        return false;
    // Public connection lookup/fields, before BTstack can clamp an over-return.
    // The one-byte event length bounds this to at most 63 handle records.
    for (unsigned i = 0; i < packet[2]; ++i) {
        const auto offset = 3u + 4u * i;
        const auto handle = std::uint16_t((packet[offset] | (packet[offset + 1u] << 8u)) & 0xfffu);
        std::uint32_t total = 0;
        for (unsigned j = 0; j <= i; ++j) {
            const auto previous = 3u + 4u * j;
            const auto other =
                std::uint16_t((packet[previous] | (packet[previous + 1u] << 8u)) & 0xfffu);
            if (handle == other)
                total += std::uint16_t(packet[previous + 2u] | (packet[previous + 3u] << 8u));
        }
        const auto* connection = hci_connection_for_handle(handle);
        if ((!connection && total) || (connection && total > connection->num_packets_sent))
            return false;
        returned += std::uint16_t(packet[offset + 2u] | (packet[offset + 3u] << 8u));
    }
    return true;
}
void received(std::uint8_t type, std::uint8_t* packet, std::uint16_t size) {
    const bool completed =
        type == HCI_EVENT_PACKET && size && packet[0] == HCI_EVENT_NUMBER_OF_COMPLETED_PACKETS;
    if (completed) {
        sample(); // Before BTstack returns credits; queued sends may run in incoming().
        std::uint32_t returned = 0;
        const bool valid = valid_completions(packet, size, returned);
        metrics.completed(valid, returned != 0);
    }
    incoming(type, packet, size);
    sample(); // Includes actual startup capacity and credit returns/disconnects.
}
void register_handler(void (*handler)(std::uint8_t, std::uint8_t*, std::uint16_t)) {
    incoming = handler;
    original->register_packet_handler(received);
}
int send(std::uint8_t type, std::uint8_t* packet, int size) {
    if (type == HCI_ACL_DATA_PACKET) {
        // Pinned BTstack increments num_packets_sent BEFORE every transport
        // fragment call. Observe before the transport can synchronously complete.
        sample();
        metrics.sent();
    }
    const int result = original->send_packet(type, packet, size);
    if (type == HCI_ACL_DATA_PACKET && result)
        metrics.transport_failed();
    return result;
}
} // namespace
extern "C" const hci_transport_t* __real_hci_transport_cyw43_instance(void);
extern "C" const hci_transport_t* __wrap_hci_transport_cyw43_instance(void) {
    if (!original) {
        original = __real_hci_transport_cyw43_instance();
        observed = *original;
        observed.register_packet_handler = register_handler;
        observed.send_packet = send;
    }
    return &observed;
}
namespace wsprrypico::runtime {
AclCreditSnapshot btstack_acl_credit_snapshot() {
    if (original)
        sample();
    return metrics.snapshot(original && incoming);
}
} // namespace wsprrypico::runtime
