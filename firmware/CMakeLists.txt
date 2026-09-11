set(WSPRRY_PICO_FIRMWARE_VERSION "0.0.0-devel" CACHE STRING "Firmware identity")

execute_process(
    COMMAND git -C "${CMAKE_CURRENT_LIST_DIR}/.." rev-parse --short=12 HEAD
    OUTPUT_VARIABLE WSPRRY_PICO_GIT_REVISION
    OUTPUT_STRIP_TRAILING_WHITESPACE
    RESULT_VARIABLE WSPRRY_PICO_GIT_RESULT
)
if(NOT WSPRRY_PICO_GIT_RESULT EQUAL 0)
    set(WSPRRY_PICO_GIT_REVISION "unknown")
endif()
execute_process(
    COMMAND git -C "${CMAKE_CURRENT_LIST_DIR}/.." diff --quiet --ignore-submodules HEAD --
    RESULT_VARIABLE WSPRRY_PICO_GIT_DIRTY
)
if(WSPRRY_PICO_GIT_DIRTY EQUAL 1)
    string(APPEND WSPRRY_PICO_GIT_REVISION "-dirty")
elseif(NOT WSPRRY_PICO_GIT_DIRTY EQUAL 0)
    string(APPEND WSPRRY_PICO_GIT_REVISION "-unknown")
endif()

configure_file(
    ${CMAKE_CURRENT_LIST_DIR}/firmware_identity.hpp.in
    ${CMAKE_CURRENT_BINARY_DIR}/generated/firmware_identity.hpp
    @ONLY
)

add_executable(WsprryPico
    ../src/standalone/pico/main.cpp
    ../src/standalone/pico/adapters.cpp
    ../src/standalone/pico/net_trace.cpp
    pico_adapters.cpp
    usb_descriptors.c
    ../src/usb/transport.cpp
)
target_include_directories(WsprryPico PRIVATE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_BINARY_DIR}/generated
)
target_compile_definitions(WsprryPico PRIVATE
    PICO_NO_BI_PROGRAM_BUILD_DATE=1
    PICO_STACK_SIZE=0x4000
    WSPRRY_PICO_RF_OUTPUT_DISABLED=1
    WSPRRY_PICO_RF_SAMPLE_RATE_HZ=${WSPRRY_PICO_RF_SAMPLE_RATE_HZ}
    PICO_PANIC_FUNCTION=wsprrypico_panic
)
set_source_files_properties(pico_adapters.cpp usb_descriptors.c ../src/usb/transport.cpp PROPERTIES
    COMPILE_OPTIONS "-Wall;-Wextra;-Werror"
)
target_link_libraries(WsprryPico PRIVATE
    wsprrypico_core
    pico_stdlib
    pico_rand
    pico_time
    pico_unique_id
    hardware_flash
    pico_cyw43_arch_lwip_poll
    tinyusb_device
)

# Reserve 16 KiB at the top of RP2350 main SRAM for the primary stack.
# SDK linker symbols relocate SCRATCH_Y without overlapping the heap or core 1.
# Recursive depth-16 JSON validation exceeds the default 2 KiB scratch stack.
target_link_options(WsprryPico PRIVATE
    "LINKER:--defsym=RAM_LENGTH=0x7c000"
    "LINKER:--defsym=SCRATCH_Y_ORIGIN=0x2007c000"
    "LINKER:--defsym=SCRATCH_Y_LENGTH=0x4000"
)

set_target_properties(WsprryPico PROPERTIES
    C_STANDARD 11 C_STANDARD_REQUIRED ON C_EXTENSIONS ON)
pico_enable_stdio_uart(WsprryPico 0)
pico_enable_stdio_usb(WsprryPico 0)

pico_set_program_name(WsprryPico "WsprryPico")
pico_set_program_version(WsprryPico "${WSPRRY_PICO_FIRMWARE_VERSION}")
pico_set_program_description(WsprryPico "Standalone RF-inhibited ${WSPRRY_PICO_GIT_REVISION}")
pico_add_extra_outputs(WsprryPico)

# Explicit diagnostic target: no WTP endpoint or UTC claim; boots without a job.
add_executable(WsprryPico-RFBench EXCLUDE_FROM_ALL
    ../src/rf/pico/bench_main.cpp usb_descriptors.c ../src/usb/transport.cpp)
target_include_directories(WsprryPico-RFBench PRIVATE
    ${CMAKE_CURRENT_LIST_DIR} ${CMAKE_CURRENT_BINARY_DIR}/generated)
target_compile_definitions(WsprryPico-RFBench PRIVATE
    WSPRRY_PICO_RF_BENCH=1 PICO_NO_BI_PROGRAM_BUILD_DATE=1 PICO_STACK_SIZE=0x4000)
target_link_libraries(WsprryPico-RFBench PRIVATE
    wsprrypico_pico_rf pico_unique_id tinyusb_device)
set_source_files_properties(../src/rf/pico/bench_main.cpp PROPERTIES
    COMPILE_OPTIONS "-Wall;-Wextra;-Werror;-fstack-usage")
set_target_properties(WsprryPico-RFBench PROPERTIES
    C_STANDARD 11 C_STANDARD_REQUIRED ON C_EXTENSIONS ON)
target_link_options(WsprryPico-RFBench PRIVATE
    "LINKER:--defsym=RAM_LENGTH=0x7c000"
    "LINKER:--defsym=SCRATCH_Y_ORIGIN=0x2007c000"
    "LINKER:--defsym=SCRATCH_Y_LENGTH=0x4000")
pico_enable_stdio_uart(WsprryPico-RFBench 0)
pico_enable_stdio_usb(WsprryPico-RFBench 0)
pico_set_program_name(WsprryPico-RFBench "WsprryPico-RFBench")
pico_set_program_version(WsprryPico-RFBench "${WSPRRY_PICO_FIRMWARE_VERSION}")
pico_set_program_description(WsprryPico-RFBench "GP2 bench ${WSPRRY_PICO_GIT_REVISION}")
pico_add_extra_outputs(WsprryPico-RFBench)

# Explicit integration target: real RF remains absent from the default image.
add_executable(WsprryPico-RFWTP EXCLUDE_FROM_ALL
    rf_wtp_main.cpp pico_adapters.cpp usb_descriptors.c ../src/usb/transport.cpp)
target_include_directories(WsprryPico-RFWTP PRIVATE
    ${CMAKE_CURRENT_LIST_DIR} ${CMAKE_CURRENT_BINARY_DIR}/generated)
target_compile_definitions(WsprryPico-RFWTP PRIVATE
    WSPRRY_PICO_RF_WTP=1 PICO_NO_BI_PROGRAM_BUILD_DATE=1 PICO_STACK_SIZE=0x4000)
target_link_libraries(WsprryPico-RFWTP PRIVATE
    wsprrypico_pico_rf pico_rand pico_time pico_unique_id tinyusb_device)
set_source_files_properties(rf_wtp_main.cpp PROPERTIES
    COMPILE_OPTIONS "-Wall;-Wextra;-Werror;-fstack-usage")
set_target_properties(WsprryPico-RFWTP PROPERTIES
    C_STANDARD 11 C_STANDARD_REQUIRED ON C_EXTENSIONS ON)
target_link_options(WsprryPico-RFWTP PRIVATE
    "LINKER:--defsym=RAM_LENGTH=0x7c000"
    "LINKER:--defsym=SCRATCH_Y_ORIGIN=0x2007c000"
    "LINKER:--defsym=SCRATCH_Y_LENGTH=0x4000")
pico_enable_stdio_uart(WsprryPico-RFWTP 0)
pico_enable_stdio_usb(WsprryPico-RFWTP 0)
pico_set_program_name(WsprryPico-RFWTP "WsprryPico-RFWTP")
pico_set_program_version(WsprryPico-RFWTP "${WSPRRY_PICO_FIRMWARE_VERSION}")
pico_set_program_description(WsprryPico-RFWTP "WTP GP2 integration ${WSPRRY_PICO_GIT_REVISION}")
pico_add_extra_outputs(WsprryPico-RFWTP)

# Standalone time and storage integration. WTP and RF bench targets stay separate.
target_include_directories(WsprryPico PRIVATE ${CMAKE_SOURCE_DIR}/src/standalone/pico)
set_source_files_properties(../src/standalone/pico/main.cpp ../src/standalone/pico/adapters.cpp
    PROPERTIES COMPILE_OPTIONS "-Wall;-Wextra;-Werror;-fstack-usage")
add_executable(WsprryPico-StandaloneRF EXCLUDE_FROM_ALL
    ../src/standalone/pico/main.cpp ../src/standalone/pico/adapters.cpp
    pico_adapters.cpp usb_descriptors.c ../src/usb/transport.cpp)
target_include_directories(WsprryPico-StandaloneRF PRIVATE
    ${CMAKE_CURRENT_LIST_DIR} ${CMAKE_CURRENT_BINARY_DIR}/generated
    ${CMAKE_SOURCE_DIR}/src/standalone/pico)
target_compile_definitions(WsprryPico-StandaloneRF PRIVATE
    WSPRRY_PICO_STANDALONE_RF=1 PICO_NO_BI_PROGRAM_BUILD_DATE=1 PICO_STACK_SIZE=0x4000
    PICO_PANIC_FUNCTION=wsprrypico_panic PICO_CORE1_STACK_SIZE=0)
target_sources(WsprryPico-StandaloneRF PRIVATE ../src/rf/pico/worker.cpp)
target_link_libraries(WsprryPico-StandaloneRF PRIVATE
    wsprrypico_pico_rf pico_rand pico_time pico_unique_id hardware_flash pico_flash pico_multicore
    pico_cyw43_arch_lwip_poll tinyusb_device)
set_target_properties(WsprryPico-StandaloneRF PROPERTIES
    C_STANDARD 11 C_STANDARD_REQUIRED ON C_EXTENSIONS ON)
target_link_options(WsprryPico-StandaloneRF PRIVATE
    "LINKER:--defsym=RAM_LENGTH=0x7c000"
    "LINKER:--defsym=SCRATCH_Y_ORIGIN=0x2007c000"
    "LINKER:--defsym=SCRATCH_Y_LENGTH=0x4000")
pico_enable_stdio_uart(WsprryPico-StandaloneRF 0)
pico_enable_stdio_usb(WsprryPico-StandaloneRF 0)
pico_set_program_name(WsprryPico-StandaloneRF "WsprryPico-StandaloneRF")
pico_set_program_version(WsprryPico-StandaloneRF "${WSPRRY_PICO_FIRMWARE_VERSION}")
pico_set_program_description(WsprryPico-StandaloneRF "Standalone GP2 integration ${WSPRRY_PICO_GIT_REVISION}")
pico_add_extra_outputs(WsprryPico-StandaloneRF)
foreach(image WsprryPico WsprryPico-StandaloneRF)
    target_sources(${image} PRIVATE ${CMAKE_SOURCE_DIR}/src/runtime/pico/heap_metrics.c)
    target_compile_definitions(${image} PRIVATE WSPRRY_PICO_HEAP_METRICS=1)
    target_compile_options(${image} PRIVATE -fstack-usage)
    foreach(function _malloc_r _calloc_r _realloc_r _free_r mallinfo)
        target_link_options(${image} PRIVATE "LINKER:--wrap=${function}")
    endforeach()
    add_custom_command(TARGET ${image} POST_BUILD
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/check_heap_hooks.py
                $<TARGET_FILE:${image}> VERBATIM)
    set_property(TARGET ${image} APPEND PROPERTY LINK_DEPENDS
                 ${CMAKE_SOURCE_DIR}/scripts/check_heap_hooks.py)
endforeach()
set_source_files_properties(${CMAKE_SOURCE_DIR}/src/runtime/pico/heap_metrics.c PROPERTIES
    COMPILE_OPTIONS "-Wall;-Wextra;-Werror;-fstack-usage")
if(WSPRRY_PICO_RF_RENDER_IN_RAM)
    set(rf_renderer_placement ram)
else()
    set(rf_renderer_placement flash)
endif()
add_custom_command(TARGET WsprryPico-StandaloneRF POST_BUILD
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/check_rf_renderer.py
            $<TARGET_FILE:WsprryPico-StandaloneRF> --expect ${rf_renderer_placement}
    VERBATIM)
set_property(TARGET WsprryPico-StandaloneRF APPEND PROPERTY LINK_DEPENDS
             ${CMAKE_SOURCE_DIR}/scripts/check_rf_renderer.py)

# Reserve journals plus the RP2350-E10 boot sector on every maintained image.
# Override only the linker region; PICO_FLASH_SIZE_BYTES retains physical capacity.
foreach(image WsprryPico WsprryPico-RFBench WsprryPico-RFWTP WsprryPico-StandaloneRF rf_driver_linkcheck)
    pico_add_linker_script_override_path(${image} ${CMAKE_SOURCE_DIR}/cmake/standalone_link FILES memory_flash.incl)
endforeach()

include(${CMAKE_SOURCE_DIR}/cmake/mbedtls_alert_overlay.cmake)
wsprry_mbedtls_alert_overlay(pico_mbedtls_tls INTERFACE_SOURCES "${PICO_MBEDTLS_PATH}")
include(${CMAKE_SOURCE_DIR}/cmake/network.cmake)

# Immutable pinned lwIP responder plus a narrow lifecycle integration wrapper.
# Do not also link pico_lwip_mdns: the wrapper includes its mdns.c translation unit.
set_source_files_properties(
    ${CMAKE_SOURCE_DIR}/src/standalone/pico/mdns_lwip.c
    ${PICO_LWIP_PATH}/src/apps/mdns/mdns_domain.c
    ${PICO_LWIP_PATH}/src/apps/mdns/mdns_out.c
    PROPERTIES COMPILE_OPTIONS "-fstack-usage")
foreach(image WsprryPico WsprryPico-StandaloneRF)
    target_sources(${image} PRIVATE
        ${CMAKE_SOURCE_DIR}/src/standalone/pico/mdns_lwip.c
        ${PICO_LWIP_PATH}/src/apps/mdns/mdns_domain.c
        ${PICO_LWIP_PATH}/src/apps/mdns/mdns_out.c)
    target_compile_definitions(${image} PRIVATE
        WSPRRY_PICO_LWIP_MDNS_SOURCE="${PICO_LWIP_PATH}/src/apps/mdns/mdns.c")
endforeach()

# Reset-surviving nested shutdown breadcrumbs; never patch SDK or physical RF images.
target_sources(WsprryPico PRIVATE ../src/standalone/pico/shutdown_trace.cpp)
foreach(operation cyw43_cb_tcpip_deinit dhcp_stop netif_remove igmp_stop
                  cyw43_wifi_update_multicast_filter cyw43_wifi_leave)
    target_link_options(WsprryPico PRIVATE "LINKER:--wrap=${operation}")
endforeach()
set_source_files_properties(../src/standalone/pico/shutdown_trace.cpp PROPERTIES
    COMPILE_OPTIONS "-Wall;-Wextra;-Werror;-fstack-usage")
