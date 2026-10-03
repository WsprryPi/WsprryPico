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
    PICO_STACK_SIZE=0x8000
    WSPRRY_PICO_RF_OUTPUT_DISABLED=1
    WSPRRY_PICO_RF_SAMPLE_RATE_HZ=${WSPRRY_PICO_RF_SAMPLE_RATE_HZ}
    PICO_PANIC_FUNCTION=wsprrypico_panic
)

# Finite fault fixtures affect only the inhibited target. A stage is selected at
# build time; no arbitrary memory corruption or remotely writable fault switch.
set(WSPRRY_PICO_PHASE12_FAULT_STAGE "0" CACHE STRING "Phase12 inhibited fault stage 0..10")
if(NOT WSPRRY_PICO_PHASE12_FAULT_STAGE MATCHES "^([0-9]|10)$")
    message(FATAL_ERROR "Phase12 fault stage must be 0..10")
endif()
if(NOT WSPRRY_PICO_PHASE12_FAULT_STAGE STREQUAL "0")
    target_sources(WsprryPico PRIVATE ../src/provisioning/pico/phase12_fault_fixture.cpp)
    target_compile_definitions(WsprryPico PRIVATE
        WSPRRY_PICO_PHASE12_FAULT_FIXTURE=1)
    set_source_files_properties(../src/provisioning/pico/phase12_fault_fixture.cpp PROPERTIES
        COMPILE_DEFINITIONS WSPRRY_PICO_PHASE12_FAULT_STAGE=${WSPRRY_PICO_PHASE12_FAULT_STAGE})
endif()

set(WSPRRY_PICO_CONSUMER_LAN_MODE "plain" CACHE STRING
    "Consumer LAN WTP mode: off, plain, or tls")
set_property(CACHE WSPRRY_PICO_CONSUMER_LAN_MODE PROPERTY STRINGS off plain tls)
if(NOT WSPRRY_PICO_CONSUMER_LAN_MODE MATCHES "^(off|plain|tls)$")
    message(FATAL_ERROR "WSPRRY_PICO_CONSUMER_LAN_MODE must be off, plain, or tls")
endif()
if(WSPRRY_PICO_CONSUMER_LAN_MODE STREQUAL "off")
    set(WSPRRY_PICO_CONSUMER_LAN_MODE_VALUE 0)
elseif(WSPRRY_PICO_CONSUMER_LAN_MODE STREQUAL "plain")
    set(WSPRRY_PICO_CONSUMER_LAN_MODE_VALUE 1)
else()
    set(WSPRRY_PICO_CONSUMER_LAN_MODE_VALUE 2)
endif()
target_compile_definitions(WsprryPico PRIVATE
    WSPRRY_PICO_CONSUMER_LAN_MODE=${WSPRRY_PICO_CONSUMER_LAN_MODE_VALUE})
option(WSPRRY_PICO_PHASE12_SESSION_DEADLINE_FIXTURE
    "RF-inhibited engineering session fixture: 15s inactivity/60s absolute" OFF)
if(WSPRRY_PICO_PHASE12_SESSION_DEADLINE_FIXTURE)
    target_compile_definitions(WsprryPico PRIVATE
        WSPRRY_PICO_PHASE12_SESSION_DEADLINE_FIXTURE=1)
endif()
option(WSPRRY_PICO_BOOTSEL_WINDOW_DIAGNOSTIC
    "Link the RF-inhibited USB BOOTSEL safe-zone window diagnostic" OFF)
option(WSPRRY_PICO_GP14_RUNTIME_BUTTON
    "Opt in to the unaccepted GP14 runtime button and PIO capture" OFF)
option(WSPRRY_PICO_GP14_FLASH_PROBE
    "Temporary RF-inhibited runtime variant with a guarded scratch flash probe" OFF)
option(WSPRRY_PICO_GP14_RF_ACCEPTANCE
    "Temporary RF worker variant with an identity-bound finite core-0 busy operation" OFF)
if(WSPRRY_PICO_GP14_RF_ACCEPTANCE AND NOT WSPRRY_PICO_GP14_RUNTIME_BUTTON)
    message(FATAL_ERROR "GP14 RF acceptance requires the runtime button")
endif()
if(WSPRRY_PICO_GP14_FLASH_PROBE AND NOT WSPRRY_PICO_GP14_RUNTIME_BUTTON)
    message(FATAL_ERROR "GP14 flash probe requires the opt-in runtime button")
endif()
if(WSPRRY_PICO_GP14_FLASH_PROBE)
    target_sources(WsprryPico PRIVATE ../src/provisioning/pico/gp14_flash_probe.cpp)
    target_compile_definitions(WsprryPico PRIVATE WSPRRY_PICO_GP14_FLASH_PROBE=1)
    set_source_files_properties(../src/provisioning/pico/gp14_flash_probe.cpp PROPERTIES
        COMPILE_OPTIONS "-Wall;-Wextra;-Wpedantic;-Werror;-fstack-usage")
    set_property(TARGET WsprryPico APPEND PROPERTY LINK_DEPENDS
                 ${CMAKE_SOURCE_DIR}/scripts/check_gp14_flash_probe_image.py)
endif()
if(WSPRRY_PICO_GP14_RUNTIME_BUTTON AND WSPRRY_PICO_BOOTSEL_WINDOW_DIAGNOSTIC)
    message(FATAL_ERROR "GP14 runtime input and the BOOTSEL window diagnostic are separate image modes")
endif()
if(WSPRRY_PICO_BOOTSEL_WINDOW_DIAGNOSTIC)
    target_compile_definitions(WsprryPico PRIVATE WSPRRY_PICO_BOOTSEL_WINDOW_DIAGNOSTIC=1
        PICO_CORE1_STACK_SIZE=0)
    target_link_libraries(WsprryPico PRIVATE pico_multicore)
endif()
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
    pico_flash
    pico_cyw43_arch_lwip_poll
    tinyusb_device
)

# The standard RF-inhibited image must have no runtime BOOTSEL sampler or
# linked core-1 launcher. The explicit diagnostic links only the bounded
# whole-gesture callback and its core-1 flash reader.
if(WSPRRY_PICO_BOOTSEL_WINDOW_DIAGNOSTIC)
    add_custom_command(TARGET WsprryPico POST_BUILD
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/check_bootsel_topology.py
                $<TARGET_FILE:WsprryPico> --expect-core1 VERBATIM)
else()
    add_custom_command(TARGET WsprryPico POST_BUILD
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/check_bootsel_topology.py
                $<TARGET_FILE:WsprryPico> VERBATIM)
endif()
set_property(TARGET WsprryPico APPEND PROPERTY LINK_DEPENDS
             ${CMAKE_SOURCE_DIR}/scripts/check_bootsel_topology.py)

# Reserve 32 KiB at the top of RP2350 main SRAM for the primary stack.
# Captive setup enters flash/crypto from an lwIP callback; 16 KiB overflowed
# during the first physical Wi-Fi setup attempt. The MSPLIM guard still reserves
# the bottom 4 KiB, leaving 28 KiB usable without overlapping heap or core 1.
target_link_options(WsprryPico PRIVATE
    "LINKER:--defsym=RAM_LENGTH=0x78000"
    "LINKER:--defsym=SCRATCH_Y_ORIGIN=0x20078000"
    "LINKER:--defsym=SCRATCH_Y_LENGTH=0x8000"
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
    WSPRRY_PICO_STANDALONE_RF=1 PICO_NO_BI_PROGRAM_BUILD_DATE=1 PICO_STACK_SIZE=0x8000
    WSPRRY_PICO_CONSUMER_LAN_MODE=${WSPRRY_PICO_CONSUMER_LAN_MODE_VALUE}
    PICO_PANIC_FUNCTION=wsprrypico_panic PICO_CORE1_STACK_SIZE=0)
target_sources(WsprryPico-StandaloneRF PRIVATE ../src/rf/pico/worker.cpp
    ../src/standalone/pico/net_trace.cpp)
if(WSPRRY_PICO_GP14_RF_ACCEPTANCE)
    target_compile_definitions(WsprryPico-StandaloneRF PRIVATE WSPRRY_PICO_GP14_RF_ACCEPTANCE=1)
endif()
target_link_libraries(WsprryPico-StandaloneRF PRIVATE
    wsprrypico_pico_rf pico_rand pico_time pico_unique_id hardware_flash pico_flash pico_multicore
    pico_cyw43_arch_lwip_poll tinyusb_device)
set_target_properties(WsprryPico-StandaloneRF PROPERTIES
    C_STANDARD 11 C_STANDARD_REQUIRED ON C_EXTENSIONS ON)
target_link_options(WsprryPico-StandaloneRF PRIVATE
    "LINKER:--defsym=RAM_LENGTH=0x78000"
    "LINKER:--defsym=SCRATCH_Y_ORIGIN=0x20078000"
    "LINKER:--defsym=SCRATCH_Y_LENGTH=0x8000")
pico_enable_stdio_uart(WsprryPico-StandaloneRF 0)
pico_enable_stdio_usb(WsprryPico-StandaloneRF 0)
pico_set_program_name(WsprryPico-StandaloneRF "WsprryPico-StandaloneRF")
pico_set_program_version(WsprryPico-StandaloneRF "${WSPRRY_PICO_FIRMWARE_VERSION}")
pico_set_program_description(WsprryPico-StandaloneRF "Standalone GP2 integration ${WSPRRY_PICO_GIT_REVISION}")
pico_add_extra_outputs(WsprryPico-StandaloneRF)

if(WSPRRY_PICO_GP14_RUNTIME_BUTTON)
    foreach(image WsprryPico WsprryPico-StandaloneRF)
        target_sources(${image} PRIVATE ../src/provisioning/pico/gp14_capture.cpp)
        target_include_directories(${image} PRIVATE ${CMAKE_SOURCE_DIR}/src)
        target_compile_definitions(${image} PRIVATE WSPRRY_PICO_GP14_RUNTIME_BUTTON=1)
        target_link_libraries(${image} PRIVATE hardware_pio hardware_dma)
        pico_generate_pio_header(${image}
            ${CMAKE_SOURCE_DIR}/src/provisioning/pico/gp14_sampler.pio)
    endforeach()
    set(gp14_rf_check_args)
    if(WSPRRY_PICO_GP14_RF_ACCEPTANCE)
        list(APPEND gp14_rf_check_args --acceptance)
    endif()
    add_custom_command(TARGET WsprryPico-StandaloneRF POST_BUILD
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/check_gp14_rf_image.py
            $<TARGET_FILE:WsprryPico-StandaloneRF> ${gp14_rf_check_args} VERBATIM)
    set_property(TARGET WsprryPico-StandaloneRF APPEND PROPERTY LINK_DEPENDS
        ${CMAKE_SOURCE_DIR}/scripts/check_gp14_rf_image.py)
    set_source_files_properties(../src/provisioning/pico/gp14_capture.cpp PROPERTIES
        COMPILE_OPTIONS "-Wall;-Wextra;-Werror;-fstack-usage")
endif()

# Explicit GP14 input diagnostic. It links no RF engine, Wi-Fi, or storage
# writer, and never performs the actions that it reports.
option(WSPRRY_PICO_GP14_BUTTON_DIAGNOSTIC "Enable the opt-in GP14 button image" OFF)
option(WSPRRY_PICO_GP14_DIAG_INJECT_WATCHDOG
       "Inject one watchdog reset 15 seconds after the diagnostic's first boot" OFF)
if(WSPRRY_PICO_GP14_BUTTON_DIAGNOSTIC)
    add_executable(WsprryPico-GP14ButtonDiag EXCLUDE_FROM_ALL
        ${CMAKE_SOURCE_DIR}/src/provisioning/pico/gp14_button_diagnostic.cpp
        ${CMAKE_SOURCE_DIR}/src/runtime/pico/stack_guard.c)
    target_include_directories(WsprryPico-GP14ButtonDiag PRIVATE ${CMAKE_SOURCE_DIR}/src)
    target_compile_features(WsprryPico-GP14ButtonDiag PRIVATE cxx_std_20)
    # pico_multicore compiles SDK C sources in this target. Keep warnings as
    # errors on our diagnostic source without imposing them on SDK sources.
    set_source_files_properties(
        ${CMAKE_SOURCE_DIR}/src/provisioning/pico/gp14_button_diagnostic.cpp
        PROPERTIES COMPILE_OPTIONS "-Wall;-Wextra;-Wpedantic;-Werror;-fstack-usage")
    target_compile_definitions(WsprryPico-GP14ButtonDiag PRIVATE
        WSPRRY_GP14_DIAG_INJECT_WATCHDOG=$<BOOL:${WSPRRY_PICO_GP14_DIAG_INJECT_WATCHDOG}>
        PICO_NO_BI_PROGRAM_BUILD_DATE=1 PICO_STACK_SIZE=0x4000 PICO_CORE1_STACK_SIZE=0
        PICO_STDIO_USB_STDOUT_TIMEOUT_US=1000
        PICO_STDIO_DEADLOCK_TIMEOUT_MS=2
        PICO_ENABLE_USB_RESET_VIA_BAUD_RATE=0
        PICO_ENABLE_USB_RESET_VIA_VENDOR_INTERFACE=0
        PICO_RUNTIME_SKIP_INIT_PER_CORE_INSTALL_STACK_GUARD=0
        PICO_RUNTIME_NO_INIT_PER_CORE_INSTALL_STACK_GUARD=1)
    target_link_libraries(WsprryPico-GP14ButtonDiag PRIVATE
        pico_stdlib pico_multicore hardware_watchdog hardware_exception)
    target_link_options(WsprryPico-GP14ButtonDiag PRIVATE
        "LINKER:--defsym=RAM_LENGTH=0x7c000"
        "LINKER:--defsym=SCRATCH_Y_ORIGIN=0x2007c000"
        "LINKER:--defsym=SCRATCH_Y_LENGTH=0x4000")
    pico_enable_stdio_uart(WsprryPico-GP14ButtonDiag 0)
    pico_enable_stdio_usb(WsprryPico-GP14ButtonDiag 1)
    pico_set_program_name(WsprryPico-GP14ButtonDiag "WsprryPico-GP14ButtonDiag")
    pico_set_program_version(WsprryPico-GP14ButtonDiag "${WSPRRY_PICO_FIRMWARE_VERSION}")
    pico_set_program_description(WsprryPico-GP14ButtonDiag
        "RF-inhibited GP14 input diagnostic ${WSPRRY_PICO_GIT_REVISION}")
    pico_add_extra_outputs(WsprryPico-GP14ButtonDiag)
    add_custom_command(TARGET WsprryPico-GP14ButtonDiag POST_BUILD
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/check_stack_guards.py
                $<TARGET_FILE:WsprryPico-GP14ButtonDiag> --physical
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/check_gp14_button_image.py
                $<TARGET_FILE:WsprryPico-GP14ButtonDiag> VERBATIM)
endif()
foreach(image WsprryPico WsprryPico-StandaloneRF)
    target_sources(${image} PRIVATE ${CMAKE_SOURCE_DIR}/src/provisioning/pico/bootsel_sampler.cpp
        ${CMAKE_SOURCE_DIR}/src/runtime/pico/heap_metrics.c
        ${CMAKE_SOURCE_DIR}/src/runtime/pico/stack_guard.c)
    target_sources(${image} PRIVATE ${CMAKE_SOURCE_DIR}/src/runtime/pico/btstack_pool_metrics.cpp
        ${CMAKE_SOURCE_DIR}/src/runtime/pico/btstack_acl_metrics.cpp)
    target_link_options(${image} PRIVATE "LINKER:--wrap=hci_transport_cyw43_instance"
        "LINKER:--undefined=__wrap_hci_transport_cyw43_instance")
    foreach(pool hci_connection l2cap_channel l2cap_service sm_lookup_entry whitelist_entry)
        foreach(operation get free)
            target_link_options(${image} PRIVATE "LINKER:--wrap=btstack_memory_${pool}_${operation}")
            target_link_options(${image} PRIVATE "LINKER:--undefined=__wrap_btstack_memory_${pool}_${operation}")
        endforeach()
    endforeach()
    target_compile_definitions(${image} PRIVATE WSPRRY_PICO_HEAP_METRICS=1
        PICO_RUNTIME_SKIP_INIT_PER_CORE_INSTALL_STACK_GUARD=0
        PICO_RUNTIME_NO_INIT_PER_CORE_INSTALL_STACK_GUARD=1)
    target_compile_options(${image} PRIVATE -fstack-usage)
    foreach(function _malloc_r _calloc_r _realloc_r _free_r mallinfo)
        target_link_options(${image} PRIVATE "LINKER:--wrap=${function}")
    endforeach()
    add_custom_command(TARGET ${image} POST_BUILD
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/check_btstack_pool_hooks.py
                $<TARGET_FILE:${image}> VERBATIM)
    set_property(TARGET ${image} APPEND PROPERTY LINK_DEPENDS
                 ${CMAKE_SOURCE_DIR}/scripts/check_btstack_pool_hooks.py)
    add_custom_command(TARGET ${image} POST_BUILD
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/check_heap_hooks.py
                $<TARGET_FILE:${image}> VERBATIM)
    set_property(TARGET ${image} APPEND PROPERTY LINK_DEPENDS
                 ${CMAKE_SOURCE_DIR}/scripts/check_heap_hooks.py)
    if(image STREQUAL "WsprryPico-StandaloneRF" OR
       (image STREQUAL "WsprryPico" AND WSPRRY_PICO_BOOTSEL_WINDOW_DIAGNOSTIC))
        set(stack_guard_arguments --physical)
    else()
        set(stack_guard_arguments)
    endif()
    add_custom_command(TARGET ${image} POST_BUILD
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/check_stack_guards.py
                $<TARGET_FILE:${image}> ${stack_guard_arguments} VERBATIM)
    set_property(TARGET ${image} APPEND PROPERTY LINK_DEPENDS
                 ${CMAKE_SOURCE_DIR}/scripts/check_stack_guards.py)
endforeach()
set_source_files_properties(${CMAKE_SOURCE_DIR}/src/runtime/pico/heap_metrics.c
    ${CMAKE_SOURCE_DIR}/src/runtime/pico/stack_guard.c PROPERTIES
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

# Reserve the access journal, SDK BTstack bank, all remaining journals and the RP2350-E10 boot
# sector on every maintained image. PICO_FLASH_SIZE_BYTES retains the physical
# capacity; these definitions also pin the SDK flash-bank implementation to the
# project-owned, non-overlapping region.
set(WSPRRY_PICO_BTSTACK_FLASH_OFFSET 0x3f5000)
set(WSPRRY_PICO_BTSTACK_FLASH_SIZE 0x2000)
function(wsprry_configure_flash_layout image)
    target_compile_definitions(${image} PRIVATE
        PICO_FLASH_BANK_STORAGE_OFFSET=${WSPRRY_PICO_BTSTACK_FLASH_OFFSET}
        PICO_FLASH_BANK_TOTAL_SIZE=${WSPRRY_PICO_BTSTACK_FLASH_SIZE})
    if(image STREQUAL "WsprryPico" AND WSPRRY_PICO_GP14_FLASH_PROBE)
        pico_add_linker_script_override_path(${image}
            ${CMAKE_SOURCE_DIR}/cmake/gp14_robustness_link FILES memory_flash.incl)
    else()
        pico_add_linker_script_override_path(${image}
            ${CMAKE_SOURCE_DIR}/cmake/standalone_link FILES memory_flash.incl)
    endif()
endfunction()
foreach(image WsprryPico WsprryPico-RFBench WsprryPico-RFWTP WsprryPico-StandaloneRF
              rf_driver_linkcheck)
    wsprry_configure_flash_layout(${image})
endforeach()
if(WSPRRY_PICO_GP14_BUTTON_DIAGNOSTIC)
    wsprry_configure_flash_layout(WsprryPico-GP14ButtonDiag)
endif()

include(${CMAKE_SOURCE_DIR}/cmake/mbedtls_alert_overlay.cmake)
wsprry_mbedtls_alert_overlay(pico_mbedtls_tls INTERFACE_SOURCES "${PICO_MBEDTLS_PATH}")
include(${CMAKE_SOURCE_DIR}/cmake/network.cmake)

# Hardware-free Arm link evidence for the provisioning boundary. This target is
# never a radio/runtime integration claim: it retains the transport-neutral
# manager/command/activation code plus the Pico credential/shared-PSA adapter.
add_executable(provisioning_pico_linkcheck EXCLUDE_FROM_ALL
    ${CMAKE_SOURCE_DIR}/tests/provisioning_pico_linkcheck.cpp
    ${CMAKE_SOURCE_DIR}/src/network/pico/psa_lifetime.cpp
    ${CMAKE_SOURCE_DIR}/src/provisioning/pico/credential_validator.cpp)
target_link_libraries(provisioning_pico_linkcheck PRIVATE
    wsprrypico_core pico_mbedtls pico_stdlib)
target_include_directories(provisioning_pico_linkcheck PRIVATE
    ${CMAKE_SOURCE_DIR}/src/network/pico)
target_compile_features(provisioning_pico_linkcheck PRIVATE cxx_std_20)
target_compile_options(provisioning_pico_linkcheck PRIVATE
    "$<$<COMPILE_LANGUAGE:CXX>:-Wall;-Wextra;-Wpedantic;-Werror;-fstack-usage>"
    "$<$<COMPILE_LANGUAGE:CXX>:-fno-exceptions;-fno-rtti;-fno-unwind-tables;-fno-use-cxa-atexit>")
target_compile_definitions(provisioning_pico_linkcheck PRIVATE
    PICO_NO_BI_PROGRAM_BUILD_DATE=1)
set_target_properties(provisioning_pico_linkcheck PROPERTIES
    C_STANDARD 11 C_STANDARD_REQUIRED ON C_EXTENSIONS ON)
wsprry_configure_flash_layout(provisioning_pico_linkcheck)
pico_add_extra_outputs(provisioning_pico_linkcheck)

# P12.3 hardware-free target proof. The adapter is linked only when the exact
# pinned BTstack source is supplied at configure time; it is not enabled in a
# production image and this target is never executed as a hardware test.
if(TARGET pico_btstack_ble AND TARGET pico_btstack_cyw43)
    set(WSPRRY_PICO_PINNED_BTSTACK_REVISION
        eb0bb8b5ea6d234ccb940313b47f7a5c3b4e20ec)
    find_program(WSPRRY_PICO_GIT_EXECUTABLE git REQUIRED)
    execute_process(
        COMMAND ${WSPRRY_PICO_GIT_EXECUTABLE} -C ${PICO_BTSTACK_PATH} rev-parse HEAD
        OUTPUT_VARIABLE WSPRRY_PICO_BTSTACK_REVISION
        OUTPUT_STRIP_TRAILING_WHITESPACE
        RESULT_VARIABLE WSPRRY_PICO_BTSTACK_REVISION_RESULT)
    execute_process(
        COMMAND ${WSPRRY_PICO_GIT_EXECUTABLE} -C ${PICO_BTSTACK_PATH}
                status --porcelain --untracked-files=all
        OUTPUT_VARIABLE WSPRRY_PICO_BTSTACK_DIRTY
        OUTPUT_STRIP_TRAILING_WHITESPACE
        RESULT_VARIABLE WSPRRY_PICO_BTSTACK_DIRTY_RESULT)
    if(NOT WSPRRY_PICO_BTSTACK_REVISION_RESULT EQUAL 0 OR
       NOT WSPRRY_PICO_BTSTACK_REVISION STREQUAL WSPRRY_PICO_PINNED_BTSTACK_REVISION OR
       NOT WSPRRY_PICO_BTSTACK_DIRTY_RESULT EQUAL 0 OR
       NOT WSPRRY_PICO_BTSTACK_DIRTY STREQUAL "")
        message(FATAL_ERROR
            "P12.3 requires clean BTstack ${WSPRRY_PICO_PINNED_BTSTACK_REVISION}; "
            "found ${WSPRRY_PICO_BTSTACK_REVISION} at ${PICO_BTSTACK_PATH}")
    endif()

    # Both maintained standalone variants use this common main and the single
    # CYW43 owner. Bench/diagnostic images retain their separate dependencies.
    foreach(image WsprryPico WsprryPico-StandaloneRF)
        target_sources(${image} PRIVATE
            ${CMAKE_SOURCE_DIR}/src/network/pico/bootstrap_crypto.cpp
            ${CMAKE_SOURCE_DIR}/src/network/pico/recovery_crypto.cpp
            ${CMAKE_SOURCE_DIR}/src/network/pico/owner_claim_crypto.cpp
            ${CMAKE_SOURCE_DIR}/src/provisioning/pico/activation_platform.cpp
            ${CMAKE_SOURCE_DIR}/src/provisioning/pico/captive_dns.c
            ${CMAKE_SOURCE_DIR}/src/provisioning/pico/dhcp_server.c
            ${CMAKE_SOURCE_DIR}/src/provisioning/pico/field_platform.cpp
            ${CMAKE_SOURCE_DIR}/src/provisioning/pico/gatt_transport.cpp)
        target_include_directories(${image} PRIVATE
            ${CMAKE_SOURCE_DIR}/src/provisioning/pico
            ${CMAKE_SOURCE_DIR}/src/network/pico
            ${CMAKE_SOURCE_DIR}/src/standalone/pico)
        target_link_libraries(${image} PRIVATE pico_btstack_ble pico_btstack_cyw43)
        pico_btstack_make_gatt_header(${image} PRIVATE
            ${CMAKE_SOURCE_DIR}/src/provisioning/pico/field_access.gatt)
    endforeach()
    set_source_files_properties(
        ${CMAKE_SOURCE_DIR}/src/provisioning/pico/activation_platform.cpp
        ${CMAKE_SOURCE_DIR}/src/provisioning/pico/captive_dns.c
        ${CMAKE_SOURCE_DIR}/src/provisioning/pico/dhcp_server.c
        ${CMAKE_SOURCE_DIR}/src/provisioning/pico/field_platform.cpp
        ${CMAKE_SOURCE_DIR}/src/provisioning/pico/gatt_transport.cpp
        PROPERTIES COMPILE_OPTIONS "-Wall;-Wextra;-Wpedantic;-Werror;-fstack-usage")

    add_executable(field_access_pico_linkcheck EXCLUDE_FROM_ALL
        ${CMAKE_SOURCE_DIR}/tests/field_access_pico_linkcheck.cpp
        ${CMAKE_SOURCE_DIR}/src/provisioning/pico/captive_dns.c
        ${CMAKE_SOURCE_DIR}/src/provisioning/pico/dhcp_server.c
        ${CMAKE_SOURCE_DIR}/src/provisioning/pico/field_platform.cpp
        ${CMAKE_SOURCE_DIR}/src/provisioning/pico/gatt_transport.cpp)
    target_link_libraries(field_access_pico_linkcheck PRIVATE
        wsprrypico_core pico_stdlib pico_rand pico_btstack_ble pico_btstack_cyw43
        pico_cyw43_arch_lwip_poll)
    target_include_directories(field_access_pico_linkcheck PRIVATE
        ${CMAKE_SOURCE_DIR}/src/provisioning/pico
        ${CMAKE_SOURCE_DIR}/src/network/pico
        ${CMAKE_SOURCE_DIR}/src/standalone/pico)
    target_compile_features(field_access_pico_linkcheck PRIVATE cxx_std_20)
    target_compile_options(field_access_pico_linkcheck PRIVATE
        "$<$<COMPILE_LANGUAGE:CXX>:-Wall;-Wextra;-Wpedantic;-Werror;-fstack-usage>"
        "$<$<COMPILE_LANGUAGE:CXX>:-fno-exceptions;-fno-rtti;-fno-unwind-tables;-fno-use-cxa-atexit>")
    target_compile_definitions(field_access_pico_linkcheck PRIVATE
        PICO_NO_BI_PROGRAM_BUILD_DATE=1)
    set_target_properties(field_access_pico_linkcheck PROPERTIES
        C_STANDARD 11 C_STANDARD_REQUIRED ON C_EXTENSIONS ON)
    pico_btstack_make_gatt_header(field_access_pico_linkcheck PRIVATE
        ${CMAKE_SOURCE_DIR}/src/provisioning/pico/field_access.gatt)
    wsprry_configure_flash_layout(field_access_pico_linkcheck)
    pico_add_extra_outputs(field_access_pico_linkcheck)
else()
    message(STATUS "P12.3 BTstack linkcheck unavailable: configure PICO_BTSTACK_PATH at the pinned revision")
endif()


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

# The common bootstrap adapter uses these reset-surviving shutdown breadcrumbs.
foreach(image WsprryPico WsprryPico-StandaloneRF)
    target_sources(${image} PRIVATE ../src/standalone/pico/shutdown_trace.cpp)
    foreach(operation cyw43_cb_tcpip_deinit dhcp_stop netif_remove igmp_stop
                      cyw43_wifi_update_multicast_filter cyw43_wifi_leave)
        target_link_options(${image} PRIVATE "LINKER:--wrap=${operation}")
    endforeach()
endforeach()
set_source_files_properties(../src/standalone/pico/shutdown_trace.cpp PROPERTIES
    COMPILE_OPTIONS "-Wall;-Wextra;-Werror;-fstack-usage")

if(WSPRRY_PICO_GP14_FLASH_PROBE)
    # Run after pico_add_extra_outputs has generated the UF2 to inspect.
    add_custom_command(TARGET WsprryPico POST_BUILD
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/check_gp14_flash_probe_image.py
                $<TARGET_FILE:WsprryPico> VERBATIM)
endif()

# Standalone unattended capture campaign. No network/RF/settings adapter is linked.
option(WSPRRY_PICO_GP14_ROBUSTNESS "Build the opt-in GP14 robustness test image" OFF)
if(WSPRRY_PICO_GP14_ROBUSTNESS)
    add_executable(WsprryPico-GP14Robustness EXCLUDE_FROM_ALL
        ${CMAKE_SOURCE_DIR}/src/provisioning/pico/gp14_robustness.cpp
        ${CMAKE_SOURCE_DIR}/src/provisioning/pico/gp14_capture.cpp
        ${CMAKE_SOURCE_DIR}/src/runtime/pico/stack_guard.c)
    target_include_directories(WsprryPico-GP14Robustness PRIVATE
        ${CMAKE_SOURCE_DIR}/src ${CMAKE_CURRENT_BINARY_DIR}/generated)
    target_compile_features(WsprryPico-GP14Robustness PRIVATE cxx_std_20)
    set_target_properties(WsprryPico-GP14Robustness PROPERTIES
        C_STANDARD 11 C_STANDARD_REQUIRED ON C_EXTENSIONS ON)
    set_source_files_properties(
        ${CMAKE_SOURCE_DIR}/src/provisioning/pico/gp14_robustness.cpp
        ${CMAKE_SOURCE_DIR}/src/provisioning/pico/gp14_capture.cpp
        PROPERTIES COMPILE_OPTIONS "-Wall;-Wextra;-Wpedantic;-Werror;-fstack-usage")
    # A 1 ms host scheduling gap can discard a chunk of a JSON status record.
    # Allow ordinary USB scheduling latency. A host making no read progress
    # times out each chunk; the watchdog still bounds a wedged foreground loop.
    target_compile_definitions(WsprryPico-GP14Robustness PRIVATE
        WSPRRY_PICO_GP14_ROBUSTNESS=1 PICO_NO_BI_PROGRAM_BUILD_DATE=1
        PICO_STACK_SIZE=0x4000 PICO_CORE1_STACK_SIZE=0
        PICO_STDIO_USB_STDOUT_TIMEOUT_US=100000 PICO_STDIO_DEADLOCK_TIMEOUT_MS=2
        PICO_ENABLE_USB_RESET_VIA_BAUD_RATE=0 PICO_ENABLE_USB_RESET_VIA_VENDOR_INTERFACE=0
        PICO_RUNTIME_SKIP_INIT_PER_CORE_INSTALL_STACK_GUARD=0
        PICO_RUNTIME_NO_INIT_PER_CORE_INSTALL_STACK_GUARD=1)
    target_link_libraries(WsprryPico-GP14Robustness PRIVATE
        pico_stdlib pico_multicore pico_unique_id pico_rand pico_flash hardware_flash
        hardware_watchdog hardware_exception hardware_pio hardware_dma)
    target_link_options(WsprryPico-GP14Robustness PRIVATE
        "LINKER:--defsym=RAM_LENGTH=0x7c000"
        "LINKER:--defsym=SCRATCH_Y_ORIGIN=0x2007c000"
        "LINKER:--defsym=SCRATCH_Y_LENGTH=0x4000")
    pico_add_linker_script_override_path(WsprryPico-GP14Robustness
        ${CMAKE_SOURCE_DIR}/cmake/gp14_robustness_link FILES memory_flash.incl)
    pico_generate_pio_header(WsprryPico-GP14Robustness
        ${CMAKE_SOURCE_DIR}/src/provisioning/pico/gp14_sampler.pio)
    pico_enable_stdio_uart(WsprryPico-GP14Robustness 0)
    pico_enable_stdio_usb(WsprryPico-GP14Robustness 1)
    pico_set_program_name(WsprryPico-GP14Robustness "WsprryPico-GP14Robustness")
    pico_set_program_description(WsprryPico-GP14Robustness
        "RF-inhibited GP14 robustness ${WSPRRY_PICO_GIT_REVISION}")
    pico_add_extra_outputs(WsprryPico-GP14Robustness)
    add_custom_command(TARGET WsprryPico-GP14Robustness POST_BUILD
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/check_stack_guards.py
                $<TARGET_FILE:WsprryPico-GP14Robustness> --physical
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/check_gp14_robustness_image.py
                $<TARGET_FILE:WsprryPico-GP14Robustness>
        VERBATIM)
    set_property(TARGET WsprryPico-GP14Robustness APPEND PROPERTY LINK_DEPENDS
        ${CMAKE_SOURCE_DIR}/scripts/check_gp14_robustness_image.py
        ${CMAKE_SOURCE_DIR}/scripts/check_standalone_image.py)
endif()

# Fault cases are isolated from other deliberate reset/flash experiments.
if(NOT WSPRRY_PICO_PHASE12_FAULT_STAGE STREQUAL "0" AND
   (WSPRRY_PICO_BOOTSEL_WINDOW_DIAGNOSTIC OR WSPRRY_PICO_GP14_RUNTIME_BUTTON OR
    WSPRRY_PICO_GP14_FLASH_PROBE OR WSPRRY_PICO_GP14_RF_ACCEPTANCE OR
    WSPRRY_PICO_GP14_BUTTON_DIAGNOSTIC OR WSPRRY_PICO_GP14_DIAG_INJECT_WATCHDOG OR
    WSPRRY_PICO_GP14_ROBUSTNESS OR WSPRRY_PICO_PHASE12_SESSION_DEADLINE_FIXTURE))
    message(FATAL_ERROR "Phase12 fault fixture requires an isolated inhibited configuration")
endif()
