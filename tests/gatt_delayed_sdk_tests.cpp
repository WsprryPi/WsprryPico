// Runs the repository's admission policy through the pinned BTstack ATT server
// and its upstream host mock. No radio, controller, device, or CppUTest runtime.
#include "btstack.h"
#include "provisioning/gatt_write_admission.hpp"

#include <array>
#include <cstdlib>
#include <iostream>
#include <span>

extern "C" {
void hci_setup_le_connection(std::uint16_t handle);
void hci_deinit();
void l2cap_can_send_fixed_channel_packet_now_set_status(std::uint8_t status);
void mock_call_att_server_packet_handler(std::uint8_t type, std::uint16_t channel,
                                         std::uint8_t* packet, std::uint16_t size);
}

#define CHECK(condition)                                                                           \
    do {                                                                                           \
        if (!(condition)) {                                                                        \
            std::cerr << __LINE__ << ": " #condition "\n";                                         \
            std::exit(1);                                                                          \
        }                                                                                          \
    } while (false)

namespace {
using wsprrypico::provisioning::GattWriteAdmission;
using Result = GattWriteAdmission::Result;
constexpr std::uint16_t connection = 1;
GattWriteAdmission gate;
std::uint64_t now_ms = 100;
bool ready = false, valid = true;
unsigned callbacks = 0, accepted = 0, confirmations = 0, commands = 0;
std::uint16_t attribute = 0;

int write(std::uint16_t handle, std::uint16_t value_handle, std::uint16_t transaction,
          std::uint16_t offset, std::uint8_t* data, std::uint16_t size) {
    CHECK(handle == connection && value_handle == attribute);
    CHECK(transaction == ATT_TRANSACTION_MODE_NONE && offset == 0);
    ++callbacks;
    const auto* hci = hci_connection_for_handle(handle);
    CHECK(hci);
    const bool acknowledged =
        hci->att_server.state == ATT_SERVER_REQUEST_RECEIVED_AND_VALIDATED &&
        GattWriteAdmission::acknowledged_request(
            std::span(hci->att_server.request_buffer, hci->att_server.request_size), data, size,
            value_handle);
    if (!acknowledged)
        ++commands;
    const auto outcome = gate.admit(now_ms, ready, valid, acknowledged);
    if (outcome == Result::Deferred)
        return ATT_ERROR_WRITE_RESPONSE_PENDING;
    if (outcome != Result::Ready)
        return ATT_ERROR_INSUFFICIENT_RESOURCES;
    CHECK(size == 4 && data[0] == 7 && data[3] == 10);
    ++accepted;
    return ATT_ERROR_SUCCESS;
}

void events(std::uint8_t packet_type, std::uint16_t, std::uint8_t* packet, std::uint16_t) {
    if (packet_type != HCI_EVENT_PACKET || packet[0] != ATT_EVENT_HANDLE_VALUE_INDICATION_COMPLETE)
        return;
    ++confirmations;
    ready = true;
    CHECK(gate.resume_due(now_ms, ready, valid));
    // The upstream mock delivers can-send synchronously. This calls write()
    // before response_ready returns, exercising the adapter's ordering.
    CHECK(att_server_response_ready(connection) == ERROR_CODE_SUCCESS);
}

void input(std::uint8_t opcode) {
    std::array<std::uint8_t, 7> request{opcode,
                                        static_cast<std::uint8_t>(attribute),
                                        static_cast<std::uint8_t>(attribute >> 8),
                                        7,
                                        8,
                                        9,
                                        10};
    mock_call_att_server_packet_handler(ATT_DATA_PACKET, connection, request.data(),
                                        request.size());
}

void setup() {
    gate.reset();
    now_ms = 100;
    ready = false;
    valid = true;
    callbacks = accepted = confirmations = commands = 0;
    hci_setup_le_connection(connection);
    l2cap_can_send_fixed_channel_packet_now_set_status(1);
    att_db_util_init();
    att_db_util_add_service_uuid16(0xfff0);
    attribute = att_db_util_add_characteristic_uuid16(
        0xfff1,
        ATT_PROPERTY_WRITE | ATT_PROPERTY_WRITE_WITHOUT_RESPONSE | ATT_PROPERTY_INDICATE |
            ATT_PROPERTY_DYNAMIC,
        ATT_SECURITY_NONE, ATT_SECURITY_NONE, nullptr, 0);
    att_server_init(att_db_util_get_address(), nullptr, write);
    att_server_register_packet_handler(events);
}

void finish() {
    att_server_deinit();
    hci_deinit();
}

void insufficient_resources_response() {
    const auto* reply = l2cap_get_outgoing_buffer();
    CHECK(reply[0] == ATT_ERROR_RESPONSE && reply[1] == ATT_WRITE_REQUEST);
    CHECK(little_endian_read_16(reply, 2) == attribute);
    CHECK(reply[4] == ATT_ERROR_INSUFFICIENT_RESOURCES);
}
} // namespace

int main() {
    setup();
    input(ATT_WRITE_REQUEST);
    CHECK(callbacks == 1 && accepted == 0 && gate.pending());
    CHECK(hci_connection_for_handle(connection)->att_server.state == ATT_SERVER_RESPONSE_PENDING);
    input(ATT_WRITE_COMMAND); // Must not steal the retained acknowledged request.
    CHECK(commands == 1 && accepted == 0 && gate.pending());
    const std::uint8_t value = 1;
    CHECK(att_server_indicate(connection, attribute, &value, 1) == ERROR_CODE_SUCCESS);
    std::uint8_t confirmation = ATT_HANDLE_VALUE_CONFIRMATION;
    mock_call_att_server_packet_handler(ATT_DATA_PACKET, connection, &confirmation, 1);
    CHECK(confirmations == 1 && callbacks == 3 && accepted == 1 && !gate.pending());
    CHECK(hci_connection_for_handle(connection)->att_server.state == ATT_SERVER_IDLE);
    CHECK(l2cap_get_outgoing_buffer()[0] == ATT_WRITE_RESPONSE);
    finish();

    setup();
    input(ATT_WRITE_REQUEST);
    now_ms = 1000;
    CHECK(gate.resume_due(now_ms, true, valid));
    // A new advisory event appears before synchronous callback re-entry.
    CHECK(att_server_response_ready(connection) == ERROR_CODE_SUCCESS);
    CHECK(callbacks == 2 && accepted == 0 && gate.pending());
    CHECK(!gate.resume_due(5099, false, true));
    now_ms = 5100;
    CHECK(gate.resume_due(now_ms, false, valid));
    CHECK(att_server_response_ready(connection) == ERROR_CODE_SUCCESS);
    CHECK(callbacks == 3 && accepted == 0 && !gate.pending());
    CHECK(hci_connection_for_handle(connection)->att_server.state == ATT_SERVER_IDLE);
    insufficient_resources_response();
    finish();

    setup();
    input(ATT_WRITE_REQUEST);
    valid = false;
    CHECK(gate.resume_due(now_ms, false, valid));
    CHECK(att_server_response_ready(connection) == ERROR_CODE_SUCCESS);
    CHECK(callbacks == 2 && accepted == 0 && !gate.pending());
    CHECK(hci_connection_for_handle(connection)->att_server.state == ATT_SERVER_IDLE);
    insufficient_resources_response();
    finish();
    std::cout
        << "PASS pinned BTstack delayed write, confirmation, synchronous reentry, and rejection\n";
}
