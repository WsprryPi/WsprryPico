# SPDX-License-Identifier: MIT
cmake_minimum_required(VERSION 3.24)
project(ReleasePiAgainstP158 LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
foreach(pair IN ITEMS "OLD_PI|a2437d1bf026e91ea95ac7e2a7a0101e3c4f11a1" "PICO_SOURCE|804e8a06585ec5a0e650e69fcd71ada398b6cc9f" "MBEDTLS_SOURCE|0bebf8b8c7f07abe3571ded48a11aa907a1ffb20")
    string(REPLACE "|" ";" parts "${pair}")
    list(GET parts 0 var)
    list(GET parts 1 pin)
    execute_process(COMMAND git -C "${${var}}" rev-parse HEAD OUTPUT_VARIABLE revision OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
    execute_process(COMMAND git -C "${${var}}" status --porcelain --untracked-files=all OUTPUT_VARIABLE dirty OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
    if(NOT revision STREQUAL pin OR NOT dirty STREQUAL "")
        message(FATAL_ERROR "${var} must be clean at ${pin}")
    endif()
endforeach()
if(NOT PAIR_BUILD)
    message(FATAL_ERROR "PAIR_BUILD must name the freshly built approved current Pi/Pico pair")
endif()
# Reuse only the old test fixture's boundary doubles. Product sources below
# come directly from the guarded, unchanged release checkout.
file(READ "${OLD_PI}/src/tests/network/consumer_interop.cpp" fixture)
string(REPLACE "int main(int argc, char **argv) {" "int unchanged_release_main(int argc, char **argv) {" fixture "${fixture}")
string(REGEX REPLACE "\\}[^}]*$" "  return 0;\n}\n" fixture "${fixture}")
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/unchanged_fixture.hpp" "${fixture}")
set(products wtp_integration/consumer_radio.cpp wtp_integration/configuration.cpp
    wtp_integration/browser_api.cpp wtp_integration/network_http.cpp
    wtp_integration/plain_tcp.cpp wtp_integration/tls.cpp wtp_runtime_bridge.cpp
    wtp_integration/output_lease.cpp wtp_integration/usb_cdc.cpp privileged_network_policy.cpp
    backend_http_guard.cpp support_request_guard.cpp httplib.cpp
    wtp_integration/application.cpp wtp_integration/status.cpp wtp_integration/scheduler.cpp
    wtp_integration/backend.cpp wtp_integration/execution_plan.cpp
    WSPR-Transmitter/src/execution_plan_compiler.cpp WSPR-Transmitter/src/transmission_controller.cpp)
list(TRANSFORM products PREPEND "${OLD_PI}/src/")
add_executable(release_p158 consumer_interop.cpp ${products})
target_compile_definitions(release_p158 PRIVATE WSPRRYPI_CONSUMER_CRYPTO_TEST=1 WSPRRY_PICO_MULTI_SESSIONS=1 WSPRRY_PICO_RECOVERY=1 MBEDTLS_CONFIG_FILE="${PICO_SOURCE}/src/network/pico/mbedtls_config.h")
target_compile_options(release_p158 PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
target_include_directories(release_p158 PRIVATE "${CMAKE_CURRENT_BINARY_DIR}" "${OLD_PI}/src" "${OLD_PI}/src/tests/network" "${OLD_PI}/src/WTP-Client/include" "${OLD_PI}/src/WSPR-Transmitter/src" "${PICO_SOURCE}/src" "${PICO_SOURCE}/tests" "${MBEDTLS_SOURCE}/include")
target_link_libraries(release_p158 PRIVATE ${PAIR_BUILD}/libpico_consumer_fixture.a ${PAIR_BUILD}/mbedtls/libmbedcrypto.a ssl crypto ${PAIR_BUILD}/client/libwtp_client.a pthread)
