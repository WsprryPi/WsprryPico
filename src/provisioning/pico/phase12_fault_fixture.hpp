#pragma once
#include "provisioning/reset.hpp"
namespace wsprrypico::provisioning {
void phase12_fault_capture_boot();
bool phase12_fault_consumed();
unsigned phase12_fault_stage();
void phase12_fault_restore_marker();
void phase12_reset_checkpoint(ResetCheckpoint);
void phase12_profile_programmed(std::size_t offset);
} // namespace wsprrypico::provisioning
