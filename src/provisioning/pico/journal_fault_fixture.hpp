#pragma once
#include "provisioning/reset.hpp"
namespace wsprrypico::provisioning {
void journal_fault_capture_boot();
bool journal_fault_consumed();
unsigned journal_fault_stage();
void journal_fault_restore_marker();
void journal_reset_checkpoint(ResetCheckpoint);
void journal_profile_programmed(std::size_t offset);
} // namespace wsprrypico::provisioning
