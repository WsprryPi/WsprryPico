#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the production cold-stop methods against deterministic GPIO registers.

The Pico adapter is SDK-bound. Compile its actual method bodies unchanged with
the minimal register API below; a fake sink alone misses unopened-adapter bugs.
Physical boot and pad verification remain separate deployment evidence.
"""
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = Path(os.environ.get('PICO_DRIVER_SOURCE', root / 'src/rf/pico/pico_pio_dma.cpp')).read_text()

def method(signature):
    start = source.index(signature)
    opening = source.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]

fixture = r'''
#include <cassert>
constexpr unsigned GPIO_FUNC_SIO=5, GPIO_OVERRIDE_LOW=2, GPIO_OUT=1;
struct Registers { unsigned function=0, override_value=0, initializations=0;
    bool direction=false, latch=false, external_high=false; } gpio;
unsigned gpio_get_function(unsigned) { return gpio.function; }
void gpio_init(unsigned) { gpio.direction=false; gpio.latch=false; gpio.function=GPIO_FUNC_SIO; ++gpio.initializations; }
void gpio_set_outover(unsigned,unsigned value) { gpio.override_value=value; }
void gpio_put(unsigned,bool value) { gpio.latch=value; }
void gpio_set_dir(unsigned,bool value) { gpio.direction=value; }
bool gpio_is_dir_out(unsigned) { return gpio.direction; }
bool gpio_get_out_level(unsigned) { return gpio.latch; }
bool gpio_get(unsigned) { return gpio.external_high || (gpio.direction && gpio.override_value!=GPIO_OVERRIDE_LOW && gpio.latch); }
unsigned get_core_num() { return 1; }
unsigned cancelled=0, disabled=0;
void hardware_alarm_cancel(unsigned) { ++cancelled; }
void pio_sm_set_enabled(void*,unsigned,bool) { ++disabled; }
struct PicoPioDma {
    unsigned rf_pin=2, core_=1, sm_=0, alarm_=0; void* pio_=nullptr;
    bool launched_=false, running=false;
    bool active() const { return pio_ && running; }
    void force_inactive(); bool rf_inactive_verified() const;
};
'''
fixture += method('void PicoPioDma::force_inactive()') + '\n'
fixture += method('bool PicoPioDma::rf_inactive_verified() const') + '\n'
fixture += r'''
int main() {
    PicoPioDma adapter;
    assert(!adapter.rf_inactive_verified()); // Default input is not proof.
    adapter.force_inactive();
    assert(adapter.pio_==nullptr && cancelled==0 && disabled==0);
    assert(gpio.function==GPIO_FUNC_SIO && gpio.direction && !gpio.latch);
    assert(gpio.override_value==GPIO_OVERRIDE_LOW && adapter.rf_inactive_verified());
    adapter.force_inactive();
    assert(gpio.initializations==1 && adapter.rf_inactive_verified()); // No repeated OE cycling.
    gpio.external_high=true;
    assert(!adapter.rf_inactive_verified()); // Pad disagreement must still fail closed.
    adapter.force_inactive(); assert(!adapter.rf_inactive_verified());
    gpio.external_high=false; gpio.direction=false;
    assert(!adapter.rf_inactive_verified());
    gpio.direction=true; gpio.latch=true;
    assert(!adapter.rf_inactive_verified());
    adapter.force_inactive(); assert(adapter.rf_inactive_verified());
    adapter.pio_=&adapter; adapter.running=true;
    assert(!adapter.rf_inactive_verified());
    adapter.running=false; assert(adapter.rf_inactive_verified());
    gpio.external_high=true; assert(!adapter.rf_inactive_verified());
}
'''
with tempfile.TemporaryDirectory(prefix='pico-cold-stop-') as directory:
    temporary = Path(directory)
    cpp = temporary / 'test.cpp'
    cpp.write_text(fixture)
    compiler = os.environ.get('CXX', 'c++')
    subprocess.run([compiler, '-std=c++20', '-Wall', '-Wextra', '-Werror', str(cpp), '-o', str(temporary / 'test')], check=True)
    subprocess.run([str(temporary / 'test')], check=True)
print('Production Pico cold stop: unopened pad establishment, no PIO allocation, repeated stop and failed readback passed')
