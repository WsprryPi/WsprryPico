#pragma once
#include <cstdint>
constexpr int HCI_STATE_WORKING = 2, HCI_EVENT_PACKET = 4, HCI_ACL_DATA_PACKET = 2;
constexpr int HCI_EVENT_NUMBER_OF_COMPLETED_PACKETS = 19, BD_ADDR_TYPE_LE_PUBLIC = 0;
struct btstack_linked_list_iterator_t {
    bool active;
};
struct hci_transport_t {
    const char* name;
    void (*register_packet_handler)(void (*)(std::uint8_t, std::uint8_t*, std::uint16_t));
    int (*send_packet)(std::uint8_t, std::uint8_t*, int);
};
int hci_get_state();
void hci_connections_get_iterator(btstack_linked_list_iterator_t*);
bool btstack_linked_list_iterator_has_next(btstack_linked_list_iterator_t*);
std::uint16_t hci_number_free_acl_slots_for_connection_type(int);

struct hci_connection_t {
    std::uint8_t num_packets_sent;
};
hci_connection_t* hci_connection_for_handle(std::uint16_t);
