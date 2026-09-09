#include "standalone/pico/net_trace.hpp"

#include "pico/time.h"

#include <algorithm>

namespace wsprrypico::standalone {
NetTrace* NetTrace::owner_ = nullptr;
bool NetTrace::install(netif* interface) {
    if ((owner_ && owner_ != this) || !interface || !interface->input || !interface->linkoutput) {
        ++install_errors_;
        return false;
    }
    if (interface->input == input || interface->linkoutput == output) {
        if (owner_ == this && interface_ == interface && intact())
            return true;
        ++install_errors_;
        return false;
    }
    owner_ = this;
    interface_ = interface;
    input_ = interface->input;
    output_ = interface->linkoutput;
    interface->input = input;
    interface->linkoutput = output;
    ++generation_;
    mark(1); // Installed after station creation, before connect.
    return true;
}
bool NetTrace::intact() const {
    return interface_ && interface_->input == input && interface_->linkoutput == output;
}
void NetTrace::append(Event e) {
    e.sequence = ++sequence_;
    e.generation = generation_;
    e.interface = interface_ ? interface_->num : 0;
    events_[(e.sequence - 1) % capacity] = e;
}
void NetTrace::mark(unsigned code) {
    Event e{};
    e.us = e.end_us = time_us_64();
    e.kind = 3;
    e.result = static_cast<std::int16_t>(code);
    append(e);
}
NetTrace::Event NetTrace::packet(pbuf* p, unsigned kind) const {
    Event e{};
    e.us = time_us_64();
    e.kind = static_cast<std::uint8_t>(kind);
    if (!p || p->tot_len > 1518)
        return e;
    e.length = p->tot_len;
    std::array<std::uint8_t, 94> bytes{}; // Ethernet + maximum IPv4 header + TCP minimum.
    const auto n =
        pbuf_copy_partial(p, bytes.data(), std::min<std::size_t>(bytes.size(), p->tot_len), 0);
    auto u16 = [&](std::size_t offset) { return (bytes[offset] << 8) | bytes[offset + 1]; };
    if (n < 14)
        return e;
    if (u16(12) == 0x0806) {
        e.count = std::min<unsigned>(42, n); // Ethernet and fixed Ethernet/IPv4 ARP only.
    } else if (u16(12) == 0x0800 && n >= 34 && (bytes[14] >> 4) == 4) {
        const unsigned ihl = (bytes[14] & 15) * 4;
        const unsigned transport = 14 + ihl;
        if (ihl < 20 || transport + 8 > n || (u16(20) & 0x3fff))
            return e;
        const bool mdns = bytes[23] == 17 && (u16(transport) == 5353 || u16(transport + 2) == 5353);
        const bool tcp = bytes[23] == 6 && (u16(transport) == 18443 || u16(transport + 2) == 18443);
        if (!mdns && !tcp)
            return e;
        // Fixed Ethernet/IP prefix plus transport fields; never retain application payload.
        e.count = 34;
        std::copy_n(bytes.begin(), 34, e.header.begin());
        const auto fields = std::min<unsigned>(20, n - transport);
        std::copy_n(bytes.begin() + transport, fields, e.header.begin() + 34);
        e.count += fields;
        if (mdns) {
            const unsigned udp_size = u16(transport + 4);
            if (udp_size < 20 || transport + udp_size > p->tot_len ||
                ihl + udp_size > unsigned(u16(16)))
                return Event{};
            e.hash = 2166136261U;
            std::array<std::uint8_t, 64> block{};
            for (unsigned offset = transport + 8; offset < transport + udp_size;) {
                const auto size = std::min<unsigned>(block.size(), transport + udp_size - offset);
                if (pbuf_copy_partial(p, block.data(), size, offset) != size)
                    return Event{};
                for (unsigned i = 0; i < size; ++i)
                    e.hash = (e.hash ^ block[i]) * 16777619U;
                offset += size;
            }
        }
        return e;
    }
    std::copy_n(bytes.begin(), e.count, e.header.begin());
    return e;
}
err_t NetTrace::input(pbuf* p, netif* n) {
    auto& self = *owner_;
    auto e = self.packet(p, 1);
    // Input may consume/free p or synchronously emit TX; record before handing it over.
    e.end_us = e.us;
    if (e.count)
        self.append(e);
    return self.input_(p, n);
}
err_t NetTrace::output(netif* n, pbuf* p) {
    auto& self = *owner_;
    auto e = self.packet(p, 2);
    const auto result = self.output_(n, p);
    e.end_us = time_us_64();
    e.result = result;
    if (e.count)
        self.append(e);
    return result;
}
std::string NetTrace::page(std::uint64_t after) const {
    const auto oldest = sequence_ > capacity ? sequence_ - capacity + 1 : 1;
    const auto first = std::max(after < sequence_ ? after + 1 : sequence_ + 1, oldest);
    const auto end = std::min(sequence_ + 1, first + 8);
    std::string out =
        "{\"oldest\":" + std::to_string(oldest) + ",\"latest\":" + std::to_string(sequence_) +
        ",\"overwritten\":" + std::to_string(sequence_ > capacity ? sequence_ - capacity : 0) +
        ",\"install_errors\":" + std::to_string(install_errors_) +
        ",\"intact\":" + (intact() ? "true" : "false") + ",\"events\":[";
    constexpr char hex[] = "0123456789abcdef";
    for (auto seq = first; seq < end; ++seq) {
        const auto& e = events_[(seq - 1) % capacity];
        if (seq != first)
            out += ',';
        out += "{\"seq\":" + std::to_string(e.sequence) + ",\"us\":" + std::to_string(e.us) +
               ",\"end_us\":" + std::to_string(e.end_us) +
               ",\"generation\":" + std::to_string(e.generation) +
               ",\"interface\":" + std::to_string(e.interface) +
               ",\"kind\":" + std::to_string(e.kind) + ",\"result\":" + std::to_string(e.result) +
               ",\"length\":" + std::to_string(e.length) + ",\"hash\":" + std::to_string(e.hash) +
               ",\"header\":\"";
        for (unsigned i = 0; i < e.count; ++i) {
            out += hex[e.header[i] >> 4];
            out += hex[e.header[i] & 15];
        }
        out += "\"}";
    }
    return out + "]}";
}
} // namespace wsprrypico::standalone
