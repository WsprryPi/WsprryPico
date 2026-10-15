#pragma once
#include <cstdint>
#include <string>
#include <string_view>

namespace wsprrypico::network {
enum class ManagementCarrier { EngineeringStation, EngineeringField, ConsumerStation, ConsumerAp };
enum class ManagementProfile { Unavailable, Blank, Recovery, Engineering, Consumer };
struct ManagementAvailability {
    ManagementProfile profile = ManagementProfile::Unavailable;
    std::uint64_t generation = 0;
    bool preclock = false;
    bool engineering_station = false, engineering_field = false;
    bool consumer_station = false, consumer_ap = false;
};
std::string management_contract(const ManagementAvailability&, ManagementCarrier,
                                std::string_view device, std::string_view boot);
} // namespace wsprrypico::network
