"""Compile the actual target INFO suffix to check bytes and temporary allocations.

This host allocation regression is not a target reserve measurement. The physical
browser failure and corrected target acceptance remain separate evidence.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class InfoFormattingTests(unittest.TestCase):
    def test_info_suffix_preserves_bytes_without_copying_existing_report(self):
        repo = Path(__file__).resolve().parents[1]
        source = (repo / 'src/standalone/pico/main.cpp').read_text()
        start = source.index('            auto status = scheduler.status();')
        suffix = source[start:source.index('\n        }', start)]
        compiler = os.environ.get('CXX') or shutil.which('c++')
        self.assertTrue(compiler, 'Existing host C++ compiler required')
        code = r'''
#include <algorithm>
#include <cstddef>
#include <cstdlib>
#include <iostream>
#include <new>
#include <string>
#include "usb/console_reply.hpp"
static std::size_t live = 0, peak = 0, allocation_limit = 0;
struct alignas(std::max_align_t) Header { std::size_t size; };
void* operator new(std::size_t n) {
    if (allocation_limit && n > allocation_limit) throw std::bad_alloc();
    auto* p = static_cast<Header*>(std::malloc(sizeof(Header) + n));
    if (!p) std::abort();
    p->size = n; live += n; peak = std::max(peak, live); return p + 1;
}
void operator delete(void* v) noexcept {
    if (v) { auto* p = static_cast<Header*>(v) - 1; live -= p->size; std::free(p); }
}
void operator delete(void* v, std::size_t) noexcept { operator delete(v); }
struct Scheduler {
    std::string value;
    std::string status() { return value; }
};
std::string format(std::string result, Scheduler& scheduler) { ACTUAL_SUFFIX }
wsprrypico::usb::ConsoleResponse format_pages(wsprrypico::usb::ConsoleResponse result,
                                            Scheduler& scheduler) { ACTUAL_SUFFIX }
int main() {
    for (const auto payload : {std::string{}, std::string("{}"), std::string(1100, 's')}) {
        for (const bool newline : {false, true}) {
            Scheduler scheduler{payload + (newline ? "\n" : "")};
            const std::string prefix(4400, 'i');
            const auto expected = prefix + ",\"status\":" + payload + "}\n";
            std::string input = prefix;
            input.reserve(8192); // The existing report already has enough capacity.
            const auto baseline = live; peak = live;
            auto output = format(std::move(input), scheduler);
            const auto temporary_peak = peak - baseline;
            if (output != expected || output.capacity() < 8192 || temporary_peak > 4096)
                return 1;
            std::cout << payload.size() << ' ' << newline << ' ' << temporary_peak << '\n';
        }
    }
    // The real INFO suffix crosses the old 8192-byte capacity while a maximum
    // job leaves small heap holes. Reproduce its doubled allocation failure,
    // then retain the identical response with nullable page allocation.
    Scheduler scheduler{std::string(1100, 's') + "\n"};
    const std::string prefix(8100, 'i');
    const auto expected = prefix + ",\"status\":" + std::string(1100, 's') + "}\n";
    std::string original; original.reserve(8192); original += prefix;
    bool rejected = false;
    allocation_limit = 8193;
    try { (void)format(std::move(original), scheduler); }
    catch (const std::bad_alloc&) { rejected = true; }
    if (!rejected) return 2;
    auto pages = wsprrypico::usb::ConsoleResponse::paged();
    pages += prefix;
    auto actual = format_pages(std::move(pages), scheduler);
    if (!actual.valid()) return 3;
    allocation_limit = 0;
    std::string decoded;
    for (std::size_t offset = 0; offset < actual.size();) {
        const auto part = actual.at(offset, 64); decoded += part; offset += part.size();
    }
    if (decoded != expected) return 4;
    std::cout << "paged INFO preserves bytes after original growth failure\n";
}
'''.replace('ACTUAL_SUFFIX', suffix)
        with tempfile.TemporaryDirectory(prefix='r3-info-format-') as directory:
            root = Path(directory)
            cpp, executable = root / 'check.cpp', root / 'check'
            cpp.write_text(code)
            built = subprocess.run([compiler, '-std=c++20', '-O2', '-I'+str(repo/'src'), str(cpp), '-o', str(executable)],
                                   capture_output=True, text=True, timeout=60)
            self.assertEqual(built.returncode, 0, built.stderr)
            checked = subprocess.run([str(executable)], capture_output=True, text=True, timeout=15)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertEqual(len(checked.stdout.splitlines()), 7)


if __name__ == '__main__':
    unittest.main()
