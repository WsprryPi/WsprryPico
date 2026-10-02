// Read-only native inspection using the exact portable production journal loaders.
#include "network/bootstrap_codec.hpp"
#include "provisioning/access.hpp"
#include "provisioning/consumer_profile.hpp"
#include "provisioning/storage.hpp"
#include "standalone/pico/flash_layout.hpp"
#include "standalone/storage.hpp"
#include "wtp/json.hpp"
#include "wtp/sha256.hpp"

#include <algorithm>
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>
using namespace wsprrypico;
namespace {
struct ReadOnly {
    const std::vector<std::uint8_t>& bytes;
    std::size_t base, size;
    bool read(std::size_t offset, std::span<std::uint8_t> out) {
        if (offset > size || out.size() > size - offset)
            return false;
        std::copy_n(bytes.begin() + base + offset, out.size(), out.begin());
        return true;
    }
};
struct Profile : provisioning::Media {
    ReadOnly media;
    explicit Profile(const std::vector<std::uint8_t>& b) : media{b, 0x3f7000, 16384} {}
    bool read(std::size_t o, std::span<std::uint8_t> b) override {
        return media.read(o, b);
    }
    bool erase(std::size_t) override {
        return false;
    }
    bool program(std::size_t, std::span<const std::uint8_t>) override {
        return false;
    }
};
struct Access : provisioning::AccessMedia {
    ReadOnly media;
    explicit Access(const std::vector<std::uint8_t>& b) : media{b, 0x3f3000, 8192} {}
    bool read(std::size_t o, std::span<std::uint8_t> b) override {
        return media.read(o, b);
    }
    bool erase(std::size_t) override {
        return false;
    }
    bool program(std::size_t, std::span<const std::uint8_t>) override {
        return false;
    }
};
struct Operational : standalone::Flash {
    ReadOnly media;
    explicit Operational(const std::vector<std::uint8_t>& b) : media{b, 0x3fb000, 16384} {}
    bool read(std::size_t o, std::span<std::uint8_t> b) override {
        return media.read(o, b);
    }
    bool erase(std::size_t) override {
        return false;
    }
    bool program(std::size_t, std::span<const std::uint8_t>) override {
        return false;
    }
};
std::string digest(std::string_view text) {
    return network::bootstrap_digest(
        {reinterpret_cast<const std::uint8_t*>(text.data()), text.size()});
}
} // namespace
int main(int argc, char** argv) {
    if (argc != 2)
        return 2;
    std::ifstream input(argv[1], std::ios::binary);
    if (!input)
        return 2;
    std::vector<std::uint8_t> bytes(standalone::flash_layout::physical_size);
    input.read(reinterpret_cast<char*>(bytes.data()), bytes.size());
    if (input.gcount() != static_cast<std::streamsize>(bytes.size()) || input.peek() != EOF)
        return 2;
    Profile pm(bytes);
    Access am(bytes);
    Operational fm(bytes);
    provisioning::ProfileStore profile(pm);
    provisioning::AccessStore access(am);
    standalone::Store store(fm);
    const bool ph = profile.load(), ah = access.load(), sh = store.load();
    const auto* a = access.record();
    const auto cp = ph && profile.source() == provisioning::ProfileSource::ConsumerProfile
                        ? provisioning::parse_consumer_profile(profile.data())
                        : std::nullopt;
    std::string station = "null";
    if (cp)
        station = "{\"callsign\":" + wtp::json::quote(cp->callsign) +
                  ",\"locator\":" + wtp::json::quote(cp->locator) +
                  ",\"power_dbm\":" + std::to_string(cp->power_dbm) + "}";
    else if (store.config())
        station = "{\"callsign\":" + wtp::json::quote(store.config()->callsign) +
                  ",\"locator\":" + wtp::json::quote(store.config()->locator) +
                  ",\"power_dbm\":" + std::to_string(store.config()->power_dbm) + "}";
    const auto config =
        store.config() ? standalone::serialize_config(*store.config()) : std::string{};
    // Payload/config can contain secrets. Caller must retain stdout privately.
    std::cout << "{\"profile_healthy\":" << (ph ? "true" : "false")
              << ",\"profile_source\":" << static_cast<unsigned>(profile.source())
              << ",\"profile_sequence\":" << profile.sequence()
              << ",\"profile_sha256\":" << wtp::json::quote(digest(profile.data()))
              << ",\"profile_payload\":" << wtp::json::quote(profile.data())
              << ",\"access_loaded\":" << (ah ? "true" : "false")
              << ",\"access_state\":" << static_cast<unsigned>(access.state())
              << ",\"access_sequence\":" << access.sequence() << ",\"epoch\":" << (a ? a->epoch : 0)
              << ",\"reset_level\":"
              << static_cast<unsigned>(a ? a->reset.level : provisioning::ResetLevel::None)
              << ",\"reset_phase\":"
              << static_cast<unsigned>(a ? a->reset.phase : provisioning::ResetPhase::None)
              << ",\"bond_count\":" << (a ? unsigned(a->bond_count) : 0)
              << ",\"default_password\":" << (a && a->default_password ? "true" : "false")
              << ",\"operational_healthy\":" << (sh ? "true" : "false")
              << ",\"config_sequence\":" << store.config_sequence()
              << ",\"cursor_sequence\":" << store.cursor_sequence()
              << ",\"watermark\":" << store.watermark()
              << ",\"config\":" << (config.empty() ? "null" : config)
              << ",\"effective_station\":" << station << "}\n";
    return 0;
}
