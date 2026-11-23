// SPDX-License-Identifier: MIT
#pragma once
#include "wtp/job_service.hpp"
namespace wsprrypico::wtp {
std::string error_json(ErrorCode code);
std::string status_json(const ServiceStatus& status);
std::string state_name(State state);
}
