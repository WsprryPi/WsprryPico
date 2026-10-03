#include "btstack.h"
#include "runtime/acl_credit_metrics.hpp"
#include "runtime/pico/btstack_acl_metrics.hpp"

#include <cassert>
using namespace wsprrypico::runtime;
int state = 0;
bool connected = false;
std::uint16_t available = 0;
void (*handler)(std::uint8_t, std::uint8_t*, std::uint16_t) = nullptr;
int sends = 0, returned = 0;
bool positive_response = true;
hci_connection_t connection{4};
hci_connection_t* hci_connection_for_handle(std::uint16_t handle) {
    return connected && handle == 1 ? &connection : nullptr;
}
int hci_get_state() {
    return state;
}
void hci_connections_get_iterator(btstack_linked_list_iterator_t* it) {
    it->active = connected;
}
bool btstack_linked_list_iterator_has_next(btstack_linked_list_iterator_t* it) {
    return it->active;
}
std::uint16_t hci_number_free_acl_slots_for_connection_type(int) {
    return available;
}
void register_real(void (*value)(std::uint8_t, std::uint8_t*, std::uint16_t)) {
    handler = value;
}
void incoming(std::uint8_t, std::uint8_t* packet, std::uint16_t size) {
    ++returned;
    if (size == 3 || (size == 7 && packet[5] == 0 && packet[6] == 0))
        return;
    available = 4;
    connection.num_packets_sent = 0;
}
int send_real(std::uint8_t, std::uint8_t*, int) {
    ++sends;
    // Completion may happen synchronously in the actual transport send call.
    std::uint8_t event[]{19, 5, 1, 1, 0, std::uint8_t(positive_response ? 4 : 0), 0};
    handler(4, event, sizeof(event));
    return 0;
}
extern "C" const hci_transport_t* __real_hci_transport_cyw43_instance() {
    static const hci_transport_t value{"test", register_real, send_real};
    return &value;
}
extern "C" const hci_transport_t* __wrap_hci_transport_cyw43_instance();
int main() {
    AclCreditMetrics ledger;
    assert(!ledger.snapshot(true).measured);
    ledger.observe(true, false, 3);
    assert(!ledger.snapshot(true).initialized);
    ledger.observe(true, true, 4);
    assert(ledger.snapshot(true).measured);
    ledger.observe(true, false, 1);
    ledger.sent();
    ledger.observe(true, false, 0);
    ledger.sent();
    ledger.completed(true);
    ledger.observe(true, false, 4);
    auto value = ledger.snapshot(true);
    assert(value.min_free == 0 && value.peak_outstanding == 4 && value.free == 4);
    assert(value.send_events == 2 && value.completed_events == 1 &&
           !ledger.snapshot(false).measured);
    ledger.observe(false, true, 0);
    assert(!ledger.snapshot(true).initialized);
    ledger.observe(true, true, 3);
    assert(ledger.snapshot(true).epoch == 2 && ledger.snapshot(true).min_free == 3);
    ledger.observe(true, false, 4);
    assert(!ledger.snapshot(true).measured);
    ledger.observe(false, true, 0);
    ledger.observe(true, true, 4);
    assert(!ledger.snapshot(true).measured); // Sticky faults.
    AclCreditMetrics unknown;
    unknown.sent();
    unknown.completed(false);
    unknown.transport_failed();
    unknown.observe(true, true, 4);
    assert(!unknown.snapshot(true).measured && unknown.snapshot(true).invalid_samples == 2);
    AclCreditMetrics zero;
    zero.observe(true, true, 0);
    assert(!zero.snapshot(true).initialized);
    // Exercise the actual production wrapper, including synchronous completion.
    auto transport = __wrap_hci_transport_cyw43_instance();
    assert(transport == __wrap_hci_transport_cyw43_instance());
    assert(!btstack_acl_credit_snapshot().measured);
    transport->register_packet_handler(incoming);
    state = HCI_STATE_WORKING;
    available = 4;
    assert(btstack_acl_credit_snapshot().capacity == 4);
    connected = true;
    available = 0;
    std::uint8_t packet[4]{};
    positive_response = false;
    transport->send_packet(HCI_ACL_DATA_PACKET, packet, 4);
    value = btstack_acl_credit_snapshot();
    assert(value.measured && value.send_events == 1 && value.completed_events == 0 &&
           value.free == 0);
    std::uint8_t empty_event[]{19, 1, 0};
    handler(HCI_EVENT_PACKET, empty_event, sizeof(empty_event));
    assert(btstack_acl_credit_snapshot().completed_events == 0);
    std::uint8_t actual_return[]{19, 5, 1, 1, 0, 4, 0};
    handler(HCI_EVENT_PACKET, actual_return, sizeof(actual_return));
    value = btstack_acl_credit_snapshot();
    assert(value.measured && value.min_free == 0 && value.peak_outstanding == 4);
    assert(value.free == 4 && value.send_events == 1 && value.completed_events == 1 && sends == 1 &&
           returned == 3);
    positive_response = true;
    available = 0;
    connection.num_packets_sent = 4;
    transport->send_packet(HCI_ACL_DATA_PACKET, packet, 4);
    value = btstack_acl_credit_snapshot();
    assert(value.measured && value.send_events == 2 && value.completed_events == 2 &&
           value.free == 4 && value.min_free == 0 &&
           value.peak_outstanding == 4); // Synchronous positive completion.
    connection.num_packets_sent = 4;
    std::uint8_t over_return[]{19, 5, 1, 1, 0, 5, 0};
    handler(HCI_EVENT_PACKET, over_return, sizeof(over_return));
    assert(!btstack_acl_credit_snapshot().measured);
    assert(btstack_acl_credit_snapshot().invalid_samples == 1);
    connection.num_packets_sent = 4;
    std::uint8_t duplicate_return[]{19, 9, 2, 1, 0, 3, 0, 1, 0, 3, 0};
    handler(HCI_EVENT_PACKET, duplicate_return, sizeof(duplicate_return));
    assert(btstack_acl_credit_snapshot().invalid_samples == 2);
    std::uint8_t invalid_event[]{19, 1, 1};
    handler(HCI_EVENT_PACKET, invalid_event, sizeof(invalid_event));
    assert(!btstack_acl_credit_snapshot().measured);
    assert(btstack_acl_credit_snapshot().invalid_samples == 3);
    state = 0;
    assert(!btstack_acl_credit_snapshot().measured);
}
