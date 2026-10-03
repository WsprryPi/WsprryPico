#include "provisioning/access.hpp"

#include <algorithm>
#include <cassert>
#include <filesystem>
#include <fstream>
#include <string>
#include <sys/wait.h>
#include <unistd.h>
#include <vector>
using namespace wsprrypico::provisioning;
struct TestAccessMedia final : AccessMedia {
    std::vector<std::uint8_t>& bytes;
    explicit TestAccessMedia(std::vector<std::uint8_t>& value) : bytes(value) {}
    bool read(std::size_t offset, std::span<std::uint8_t> out) override {
        if (offset > access_media_size || out.size() > access_media_size - offset)
            return false;
        std::copy_n(bytes.begin() + 0x3f3000 + offset, out.size(), out.begin());
        return true;
    }
    bool erase(std::size_t offset) override {
        if (offset % access_slot_size || offset > access_media_size - access_slot_size)
            return false;
        std::fill_n(bytes.begin() + 0x3f3000 + offset, access_slot_size, 255);
        return true;
    }
    bool program(std::size_t offset, std::span<const std::uint8_t> page) override {
        if (offset % 256 || page.size() != 256 || offset > access_media_size - 256)
            return false;
        for (std::size_t i = 0; i < page.size(); ++i)
            bytes[0x3f3000 + offset + i] &= page[i];
        return true;
    }
};
int main(int argc, char** argv) {
    assert(argc == 2);
    const auto root =
        std::filesystem::temp_directory_path() / ("p12-field-mode-" + std::to_string(getpid()));
    assert(std::filesystem::create_directory(root));
    std::vector<std::uint8_t> bytes(4194304, 0x51);
    std::fill(bytes.begin() + 0x3f3000, bytes.begin() + 0x3f5000, 255);
    TestAccessMedia media(bytes);
    AccessStore store(media);
    assert(store.load());
    AccessRecord record;
    record.password = "wspr-test";
    record.default_password = true;
    record.epoch = 1;
    assert(store.initialize(record));
    record.epoch = 2;
    record.bond_count = 2;
    record.bonds[0] = 17;
    record.bonds[1] = 29;
    assert(store.replace(record));
    const auto original = bytes;
    const auto input = root / "baseline.bin", output = root / "field.bin";
    {
        std::ofstream file(input, std::ios::binary);
        file.write(reinterpret_cast<const char*>(bytes.data()), bytes.size());
    }
    std::filesystem::permissions(input, std::filesystem::perms::owner_read |
                                            std::filesystem::perms::owner_write);
    auto invoke = [&] {
        const auto pid = fork();
        assert(pid >= 0);
        if (!pid) {
            execl(argv[1], argv[1], "--backup", input.c_str(), "--enable-field-mode", "yes",
                  "--output", output.c_str(), nullptr);
            _exit(127);
        }
        int status = 0;
        assert(waitpid(pid, &status, 0) == pid);
        return WIFEXITED(status) ? WEXITSTATUS(status) : 128;
    };
    assert(invoke() == 0);
    {
        std::ifstream file(output, std::ios::binary);
        file.read(reinterpret_cast<char*>(bytes.data()), bytes.size());
        assert(file.gcount() == static_cast<std::streamsize>(bytes.size()));
    }
    TestAccessMedia final_media(bytes);
    AccessStore final_store(final_media);
    assert(final_store.load() && final_store.record());
    auto actual = *final_store.record();
    assert(actual.field_mode);
    actual.field_mode = false;
    assert(actual == record);
    assert(std::equal(bytes.begin(), bytes.begin() + 0x3f3000, original.begin()));
    assert(std::equal(bytes.begin() + 0x3f5000, bytes.end(), original.begin() + 0x3f5000));
    assert(invoke() != 0); // Existing output must never be overwritten.
    std::filesystem::remove_all(root);
}
