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
#include <string>
static std::size_t live = 0, peak = 0;
struct alignas(std::max_align_t) Header { std::size_t size; };
void* operator new(std::size_t n) {
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
}
'''.replace('ACTUAL_SUFFIX', suffix)
        with tempfile.TemporaryDirectory(prefix='r3-info-format-') as directory:
            root = Path(directory)
            cpp, executable = root / 'check.cpp', root / 'check'
            cpp.write_text(code)
            built = subprocess.run([compiler, '-std=c++20', '-O2', str(cpp), '-o', str(executable)],
                                   capture_output=True, text=True, timeout=60)
            self.assertEqual(built.returncode, 0, built.stderr)
            checked = subprocess.run([str(executable)], capture_output=True, text=True, timeout=15)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertEqual(len(checked.stdout.splitlines()), 6)


if __name__ == '__main__':
    unittest.main()
