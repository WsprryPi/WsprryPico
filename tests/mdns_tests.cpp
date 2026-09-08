#include "network/mdns.hpp"

#include <cassert>
#include <iostream>
using namespace wsprrypico::network;
struct Adapter : MdnsAdapter {
    bool init_ok = true, add_ok = true, registered = false;
    unsigned inits = 0, adds = 0, removes = 0, goodbyes = 0;
    std::string label;
    bool initialize() override {
        ++inits;
        return init_ok;
    }
    bool add(std::string_view name) override {
        assert(!registered);
        ++adds;
        label = name;
        registered = add_ok;
        return add_ok;
    }
    void remove(bool goodbye) override {
        assert(registered);
        registered = false;
        ++removes;
        goodbyes += goodbye;
    }
};
int main() {
    Adapter a;
    Mdns m(a, "Pico-A.LOCAL.");
    m.poll(false, 0, 0);
    assert(a.inits == 0);
    m.poll(true, 0, 1);
    assert(a.adds == 0);
    m.poll(true, 1, 2);
    assert(m.state() == "probing" && m.advertised().empty());
    assert(a.label == "pico-a");
    m.name_result(true);
    assert(m.advertised() == "pico-a.local");
    m.network_changed();
    m.poll(true, 2, 3);
    assert(a.removes == 1 && a.adds == 2 && a.goodbyes == 0);
    assert(m.address_changes() == 1 && m.advertised().empty());
    m.name_result(true);
    m.disable(true);
    assert(a.goodbyes == 1);
    m.retry();
    m.poll(true, 3, 4);
    m.name_result(true);
    m.poll(true, 0, 5);
    assert(a.goodbyes == 1 && m.advertised().empty());
    m.poll(true, 4, 6);
    m.name_result(false);
    assert(m.state() == "conflict" && m.advertised().empty());
    assert(a.registered); // Deferred callback teardown prevents upstream UAF.
    m.poll(true, 4, 7);
    assert(!a.registered);
    auto adds = a.adds;
    for (unsigned i = 0; i != 20; ++i)
        m.poll(true, 5, i + 8);
    assert(a.adds == adds && m.conflicts() == 1);
    m.disable(true);
    m.retry();
    m.poll(true, 5, 40);
    assert(m.state() == "probing" && a.label == "pico-a");
    m.poll(true, 5, 30'000'040);
    assert(m.reason() == "probe_timeout");
    assert(!a.registered);
    m.retry();
    a.add_ok = false;
    m.poll(true, 5, 30'000'041);
    assert(m.reason() == "registration_failed");
    a.add_ok = true;
    m.retry();
    for (unsigned i = 0; i < 100; ++i) {
        m.poll(true, 1, i);
        m.name_result(true);
        m.disable(true);
        m.retry();
    }
    assert(a.inits == 1 && !a.registered);
    m.identity_failure();
    m.retry();
    m.poll(true, 1, 0);
    assert(m.reason() == "device_identity_mismatch" && !a.registered);
    Adapter b;
    b.init_ok = false;
    Mdns failure(b, "pico.local");
    failure.poll(true, 1, 0);
    failure.poll(true, 1, 1);
    assert(b.inits == 1 && failure.reason() == "initialization_failed");
    b.init_ok = true;
    failure.retry();
    failure.poll(true, 1, 2);
    assert(b.inits == 2 && b.registered);
    failure.disable(false);
    Adapter c;
    Mdns legacy(c, "");
    legacy.poll(true, 1, 0);
    assert(legacy.state() == "unconfigured" && c.inits == 0);
    Mdns invalid(c, "bad_host.local");
    invalid.retry();
    invalid.poll(true, 1, 0);
    assert(invalid.reason() == "invalid_hostname" && c.inits == 0);
    std::cout << "mDNS portable lifecycle passed\n";
}
