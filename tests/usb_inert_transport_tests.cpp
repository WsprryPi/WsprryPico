#include "usb_transport_fixture.hpp"
#include <cassert>
#include <iostream>

int main() {
    using namespace wsprrypico::usb;
    static_assert(USB_ITF_CONSOLE == 0 && USB_ITF_RESERVED == 2 &&
                  USB_ITF_MANAGEMENT == 4 && USB_ITF_LOGGING == 6);
    reset();
    open(USB_CDC_RESERVED);
    // Arbitrary binary input is discarded without a reply.
    const std::string frame(15, '\xff');
    for(unsigned i=0;i<256;++i)
        ports[USB_CDC_RESERVED].rx.insert(ports[USB_CDC_RESERVED].rx.end(),frame.begin(),frame.end());
    const auto before=ports[USB_CDC_RESERVED].rx.size();
    service();
    assert(before-ports[USB_CDC_RESERVED].rx.size()==kServiceBytes);
    assert(ports[USB_CDC_RESERVED].delivered.empty() && ports[USB_CDC_RESERVED].pending.empty());
    open(USB_CDC_CONSOLE);open(USB_CDC_MANAGEMENT);open(USB_CDC_LOGGING);
    (void)take_console_reset();(void)take_management_reset();(void)take_logging_reset();
    for(unsigned i=0;i<32;++i) {
        ports[USB_CDC_RESERVED].rx.insert(ports[USB_CDC_RESERVED].rx.end(),128,0xff);
        ports[USB_CDC_MANAGEMENT].rx.push_back(0x4d);
        std::array<std::uint8_t,1> request{};
        assert(management_transport_read(request)==1 && request[0]==0x4d);
        assert(management_transport_write(request)==1);
        assert(console_write("console\n") && logging_write("logging\n"));
        const auto queued=ports[USB_CDC_RESERVED].rx.size();
        service();
        assert(queued-ports[USB_CDC_RESERVED].rx.size()==kServiceBytes);
        assert(ports[USB_CDC_MANAGEMENT].delivered.size()==i+1);
        assert(ports[USB_CDC_CONSOLE].delivered.size()==(i+1)*8);
        assert(ports[USB_CDC_LOGGING].delivered.size()==(i+1)*8);
        assert(ports[USB_CDC_RESERVED].delivered.empty());
        assert(!take_console_reset() && !take_management_reset() && !take_logging_reset());
    }
    tud_cdc_line_state_cb(USB_CDC_RESERVED,false,false);
    assert(!take_console_reset() && !take_management_reset() && !take_logging_reset());
    assert(ports[USB_CDC_RESERVED].rx.empty());
    reset();
    assert(!console_connected() && !management_connected() && !logging_connected());
    std::cout << "Reserved CDC is bounded/inert; Console, Management and Logging remain serviced under flooding\n";
}
