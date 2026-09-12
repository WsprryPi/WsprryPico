cmake_minimum_required(VERSION 3.24)

option(WSPRRY_PICO_BUILD_FIRMWARE "Build Pico 2 W firmware" OFF)

if(WSPRRY_PICO_BUILD_FIRMWARE)
    set(PICO_BOARD pico2_w CACHE STRING "Pico SDK board" FORCE)
    include(cmake/pico_sdk_import.cmake)
    project(WsprryPico LANGUAGES C CXX ASM)
else()
    project(WsprryPico LANGUAGES CXX)
endif()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(WSPRRY_PICO_BUILD_TESTS "Build hardware-free host tests" ON)

if(WSPRRY_PICO_BUILD_FIRMWARE)
    if(WSPRRY_PICO_BUILD_TESTS)
        message(FATAL_ERROR "Host tests and Pico firmware require separate build directories")
    endif()
    set(PICOTOOL_GIT_BRANCH "6f6458d792b93685a11423b244a585eaa99eafcf" CACHE STRING
        "Pinned picotool revision" FORCE)
    set(PICOTOOL_FORCE_FETCH_FROM_GIT ON CACHE BOOL
        "Use the repository-pinned picotool source" FORCE)
    pico_sdk_init()
    include(cmake/verify_pico_dependencies.cmake)
endif()

find_package(Python3 REQUIRED COMPONENTS Interpreter)
if(WSPRRY_PICO_BUILD_FIRMWARE)
    include(cmake/cyw43_tx_overlay.cmake)
    wsprry_cyw43_tx_overlay()
endif()
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
    src/network/web/index.html src/network/web/style.css src/network/web/app.js
    scripts/generate_web_assets.py)
execute_process(COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/generate_web_assets.py
    ${CMAKE_SOURCE_DIR} ${CMAKE_CURRENT_BINARY_DIR}/generated/web_assets.cpp
    COMMAND_ERROR_IS_FATAL ANY)

add_library(wsprrypico_core
    src/network/mdns.cpp
    src/network/http.cpp
    src/network/api.cpp
    ${CMAKE_CURRENT_BINARY_DIR}/generated/web_assets.cpp
    src/encoding/wspr.cpp
    src/standalone/dry_run_engine.cpp
    src/standalone/config.cpp
    src/standalone/storage.cpp
    src/standalone/scheduler.cpp
    src/time/sntp.cpp
    src/time/utc_discipline.cpp
    src/time/usb_time_source.cpp
    src/wtp/json.cpp
    src/wtp/codec.cpp
    src/wtp/endpoint.cpp
    src/wtp/frame_parser.cpp
    src/wtp/inhibited_rf_engine.cpp
    src/wtp/job_service.cpp
    src/wtp/sha256.cpp
)
target_include_directories(wsprrypico_core PUBLIC src)
target_compile_features(wsprrypico_core PUBLIC cxx_std_20)

if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    target_compile_options(wsprrypico_core PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

if(WSPRRY_PICO_BUILD_FIRMWARE)
    target_compile_options(wsprrypico_core PRIVATE
        -fstack-usage
        -fno-exceptions
        -fno-rtti
        -fno-unwind-tables
        -fno-use-cxa-atexit
    )
endif()

# Portable experimental RF library; not linked into the inhibited firmware.
add_library(wsprrypico_rf src/rf/waveform.cpp src/rf/stream_engine.cpp src/rf/pio_dma_sink.cpp src/rf/bench.cpp src/rf/worker.cpp)
set(WSPRRY_PICO_RF_SAMPLE_RATE_HZ "138000000" CACHE STRING "Experimental bench clock: 132000000, 138000000 or 150000000")
if(NOT WSPRRY_PICO_RF_SAMPLE_RATE_HZ MATCHES "^(132000000|138000000|150000000)$")
    message(FATAL_ERROR "Unsupported experimental RF sample clock")
endif()
target_compile_definitions(wsprrypico_rf PUBLIC WSPRRY_PICO_RF_SAMPLE_RATE_HZ=${WSPRRY_PICO_RF_SAMPLE_RATE_HZ})
target_link_libraries(wsprrypico_rf PUBLIC wsprrypico_core)
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    target_compile_options(wsprrypico_rf PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
if(WSPRRY_PICO_BUILD_FIRMWARE)
    option(WSPRRY_PICO_RF_RENDER_IN_RAM "Execute the finite waveform renderer from SRAM" ON)
    if(WSPRRY_PICO_RF_RENDER_IN_RAM)
        target_compile_definitions(wsprrypico_rf PUBLIC WSPRRY_PICO_RF_RENDER_IN_RAM=1)
        # Keep zero-fill loops inside the SRAM renderer instead of synthesizing
        # calls to a flash-resident memset. The linked-image checker verifies it.
        set_property(SOURCE src/rf/waveform.cpp APPEND PROPERTY COMPILE_OPTIONS
                     -fno-tree-loop-distribute-patterns)
    endif()
    # Allow the SDK linker's --gc-sections to discard bench-only code/tables
    # from the standalone image while retaining them in diagnostic targets.
    target_compile_options(wsprrypico_rf PRIVATE -fstack-usage -fno-exceptions -fno-rtti
                           -ffunction-sections -fdata-sections)
endif()

if(WSPRRY_PICO_BUILD_FIRMWARE)
    add_library(wsprrypico_pico_rf src/rf/pico/pico_pio_dma.cpp)
    target_link_libraries(wsprrypico_pico_rf PUBLIC wsprrypico_rf hardware_pio hardware_dma
                          hardware_timer hardware_irq hardware_clocks pico_stdlib)
    set_source_files_properties(src/rf/pico/pico_pio_dma.cpp PROPERTIES
        COMPILE_OPTIONS "-Wall;-Wextra;-Wpedantic;-Werror;-fno-exceptions;-fno-rtti;-fstack-usage")
    pico_generate_pio_header(wsprrypico_pico_rf ${CMAKE_SOURCE_DIR}/src/rf/pico/packed_output.pio)
    add_executable(rf_driver_linkcheck EXCLUDE_FROM_ALL tests/pico_driver_linkcheck.cpp)
    target_link_libraries(rf_driver_linkcheck PRIVATE wsprrypico_pico_rf)
    # SDK C sources require GNU asm extensions; owned C++ remains strict C++20.
    set_target_properties(wsprrypico_pico_rf rf_driver_linkcheck PROPERTIES
                          C_STANDARD 11 C_STANDARD_REQUIRED ON C_EXTENSIONS ON)
endif()

if(WSPRRY_PICO_BUILD_TESTS)
    enable_testing()
    find_package(Threads REQUIRED)
    enable_language(C)
    add_executable(heap_metrics_tests tests/heap_metrics_tests.c src/runtime/pico/heap_metrics.c)
    set_target_properties(heap_metrics_tests PROPERTIES C_STANDARD 11 C_STANDARD_REQUIRED ON)
    target_include_directories(heap_metrics_tests PRIVATE tests/heap_mock src)
    target_link_libraries(heap_metrics_tests PRIVATE Threads::Threads)
    target_compile_options(heap_metrics_tests PRIVATE -Wall -Wextra -Werror -UNDEBUG)
    add_test(NAME heap_metrics_tests COMMAND heap_metrics_tests)
    add_executable(stack_bounds_tests tests/stack_bounds_tests.c)
    target_include_directories(stack_bounds_tests PRIVATE src)
    target_compile_options(stack_bounds_tests PRIVATE -Wall -Wextra -Werror -UNDEBUG)
    add_test(NAME stack_bounds_tests COMMAND stack_bounds_tests)
    add_test(NAME stack_guard_image_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/stack_guard_image_tests.py)
    add_test(NAME heap_hook_image_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/heap_hook_image_tests.py)
    add_executable(refill_metrics_tests tests/refill_metrics_tests.cpp)
    target_link_libraries(refill_metrics_tests PRIVATE wsprrypico_rf)
    target_compile_options(refill_metrics_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME refill_metrics_tests COMMAND refill_metrics_tests)
    add_test(NAME phase11_5_inventory_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_inventory_tests.py)
    add_test(NAME phase11_5_register_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_register_tests.py)
    add_test(NAME phase11_5_pilot_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_pilot_tests.py)
    add_test(NAME phase11_5_supervisor_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_supervisor_tests.py)
    add_test(NAME phase11_5_network_fixture_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_network_fixture_tests.py)
    add_test(NAME phase11_5_device_management_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_device_management_tests.py)
    add_test(NAME phase11_5_device_fixture_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_device_fixture_tests.py)
    add_test(NAME phase11_5_network_fault_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_network_fault_tests.py)
    add_test(NAME phase11_5_fixture_audit_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_fixture_audit_tests.py)
    add_test(NAME phase11_5_idle_observer_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_idle_observer_tests.py)
    add_test(NAME phase11_5_load_audit_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_load_audit_tests.py)
    add_test(NAME phase11_5_time_local_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_time_local_tests.py)
    add_test(NAME phase11_5_r1_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_r1_tests.py)
    add_test(NAME phase11_5_trace_reader_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_trace_reader_tests.py)
    add_test(NAME phase11_5_rf_observer_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_rf_observer_tests.py)
    add_test(NAME phase11_5_browser_jobs_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_browser_jobs_tests.py)
    add_test(NAME phase11_5_f1_plan_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_f1_plan_tests.py)
    add_executable(rf_worker_tests tests/rf_worker_tests.cpp)
    target_link_libraries(rf_worker_tests PRIVATE wsprrypico_rf Threads::Threads)
    target_compile_options(rf_worker_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME rf_worker_tests COMMAND rf_worker_tests)
    add_test(NAME rf_worker_failure_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/rf_worker_failure_tests.py $<TARGET_FILE:rf_worker_tests>)
    add_executable(mdns_tests tests/mdns_tests.cpp)
    target_link_libraries(mdns_tests PRIVATE wsprrypico_core)
    target_compile_options(mdns_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME mdns_tests COMMAND mdns_tests)
    add_executable(network_tests tests/network_tests.cpp)
    target_link_libraries(network_tests PRIVATE wsprrypico_core)
    target_compile_options(network_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME network_tests COMMAND network_tests)
    find_program(WSPRRY_PICO_NODE_EXECUTABLE node)
    if(WSPRRY_PICO_NODE_EXECUTABLE)
        add_test(NAME network_browser_tests COMMAND ${WSPRRY_PICO_NODE_EXECUTABLE}
            ${CMAKE_SOURCE_DIR}/tests/network_browser_tests.js)
    endif()
    add_executable(firmware_profile_tests tests/firmware_profile_tests.cpp)
    target_link_libraries(firmware_profile_tests PRIVATE wsprrypico_rf)
    target_compile_options(firmware_profile_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME firmware_profile_tests COMMAND firmware_profile_tests)
    add_executable(standalone_tests tests/standalone_tests.cpp)
    target_link_libraries(standalone_tests PRIVATE wsprrypico_core)
    target_compile_definitions(standalone_tests PRIVATE WSPRRY_PICO_RF_SAMPLE_RATE_HZ=${WSPRRY_PICO_RF_SAMPLE_RATE_HZ})
    target_compile_options(standalone_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME standalone_tests COMMAND standalone_tests)
    set(WSPRRY_PICO_HARNESS_PYTHON "" CACHE FILEPATH "Optional existing Harness Python for offline RF analysis tests")
    if(WSPRRY_PICO_HARNESS_PYTHON)
        add_test(NAME campaign_evidence_tests COMMAND ${WSPRRY_PICO_HARNESS_PYTHON}
                 ${CMAKE_CURRENT_SOURCE_DIR}/tests/campaign_evidence_tests.py)
        add_test(NAME campaign_adapter_tests COMMAND ${WSPRRY_PICO_HARNESS_PYTHON}
                 ${CMAKE_CURRENT_SOURCE_DIR}/tests/campaign_adapter_tests.py)
        add_test(NAME campaign_analysis_tests COMMAND ${WSPRRY_PICO_HARNESS_PYTHON}
                 ${CMAKE_CURRENT_SOURCE_DIR}/tests/campaign_analysis_tests.py)
        add_test(NAME campaign_plan_tests COMMAND ${WSPRRY_PICO_HARNESS_PYTHON}
                 ${CMAKE_CURRENT_SOURCE_DIR}/tests/campaign_plan_tests.py)
    endif()
    if(WSPRRY_PICO_HARNESS_PYTHON)
        add_test(NAME rf_correction_analysis_tests COMMAND ${WSPRRY_PICO_HARNESS_PYTHON} ${CMAKE_SOURCE_DIR}/tests/rf_correction_analysis_tests.py)
        add_test(NAME rf_bench_analysis_tests COMMAND ${WSPRRY_PICO_HARNESS_PYTHON} ${CMAKE_SOURCE_DIR}/tests/rf_bench_analysis_tests.py)
        add_test(NAME rf_bench_measurement_tests COMMAND ${WSPRRY_PICO_HARNESS_PYTHON} ${CMAKE_SOURCE_DIR}/tests/rf_bench_measurement_tests.py)
    endif()
    add_executable(rf_bench_tests tests/rf_bench_tests.cpp)
    target_link_libraries(rf_bench_tests PRIVATE wsprrypico_rf)
    target_compile_options(rf_bench_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME rf_bench_tests COMMAND rf_bench_tests)
    add_executable(pio_dma_tests tests/pio_dma_tests.cpp)
    target_link_libraries(pio_dma_tests PRIVATE wsprrypico_rf)
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
        target_compile_options(pio_dma_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()
    add_test(NAME pio_dma_tests COMMAND pio_dma_tests)
    add_executable(rf_stream_tests tests/rf_stream_tests.cpp)
    target_link_libraries(rf_stream_tests PRIVATE wsprrypico_rf)
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
        target_compile_options(rf_stream_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()
    add_test(NAME rf_stream_tests COMMAND rf_stream_tests)
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    include(cmake/host_client_interop.cmake)
    include(cmake/network_host_tests.cmake)
    include(cmake/mdns_host_tests.cmake)
    set(WSPRRY_PICO_TEST_CYW43_PATH "" CACHE PATH "Optional installed pinned CYW43 for TX regression")
    if(NOT WSPRRY_PICO_TEST_CYW43_PATH AND WSPRRY_PICO_TEST_LWIP_PATH)
        get_filename_component(sdk_lib "${WSPRRY_PICO_TEST_LWIP_PATH}" DIRECTORY)
        if(EXISTS "${sdk_lib}/cyw43-driver/src/cyw43_ll.c")
            set(WSPRRY_PICO_TEST_CYW43_PATH "${sdk_lib}/cyw43-driver")
        endif()
    endif()
    if(WSPRRY_PICO_TEST_CYW43_PATH)
        add_test(NAME cyw43_tx_overlay_tests COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_SOURCE_DIR}/tests/cyw43_tx_overlay_tests.py ${WSPRRY_PICO_TEST_CYW43_PATH})
    endif()
    add_test(NAME network_certificate_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/network_certificate_tests.py)
    add_test(NAME shutdown_image_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/shutdown_image_tests.py)
    add_test(NAME inhibited_sync_image_checker_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/inhibited_sync_image_checker_tests.py)
    add_test(NAME d2_shutdown_audit_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/d2_shutdown_audit_tests.py)
    add_test(NAME phase11_4_trace_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_4_trace_tests.py)
    add_test(NAME phase11_4_loop_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_4_loop_tests.py)
    add_test(NAME inhibited_network_acceptance_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/inhibited_network_acceptance_tests.py)
    add_test(NAME standalone_image_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/standalone_image_tests.py)
    add_test(NAME rf_renderer_image_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/rf_renderer_image_tests.py)
    add_test(NAME standalone_console_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/standalone_console_tests.py)
    add_test(NAME phase11_5_r2_modes_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_r2_modes_tests.py)
    add_test(NAME phase11_5_r2_oom_recovery_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_r2_oom_recovery_tests.py)
    add_executable(wsprrypico_core_tests tests/core_tests.cpp)
    target_link_libraries(wsprrypico_core_tests PRIVATE wsprrypico_core)
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
        target_compile_options(wsprrypico_core_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()
    add_executable(endpoint_driver tests/endpoint_driver.cpp)
    target_link_libraries(endpoint_driver PRIVATE wsprrypico_core)
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
        target_compile_options(endpoint_driver PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()
    add_test(NAME rf_bench_capture_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/rf_bench_capture_tests.py)
    add_test(NAME rf_bench_client_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/rf_bench_client_tests.py)
    add_test(NAME rf_feasibility_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/rf_feasibility_tests.py)
    add_test(NAME wtp_probe_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/wtp_probe_tests.py)
    add_test(NAME rf_wtp_client_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/rf_wtp_client_tests.py)
    add_test(NAME endpoint_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/endpoint_tests.py $<TARGET_FILE:endpoint_driver>)
    add_executable(usb_transport_tests tests/usb_transport_tests.cpp src/usb/transport.cpp)
    target_include_directories(usb_transport_tests PRIVATE tests/usb_mock)
    target_link_libraries(usb_transport_tests PRIVATE wsprrypico_core)
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
        target_compile_options(usb_transport_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()
    add_test(NAME usb_transport_tests COMMAND usb_transport_tests)
    set(WSPRRY_PICO_TEST_TINYUSB_PATH "" CACHE PATH "Optional local TinyUSB source for descriptor tests")
    if(WSPRRY_PICO_TEST_TINYUSB_PATH)
        enable_language(C)
        add_executable(usb_descriptor_tests tests/usb_descriptor_tests.c firmware/usb_descriptors.c)
        set_target_properties(usb_descriptor_tests PROPERTIES C_STANDARD 11 C_STANDARD_REQUIRED ON C_EXTENSIONS OFF)
        target_include_directories(usb_descriptor_tests PRIVATE
            tests/descriptor_mock firmware src "${WSPRRY_PICO_TEST_TINYUSB_PATH}/src")
        target_compile_definitions(usb_descriptor_tests PRIVATE CFG_TUSB_MCU=OPT_MCU_NONE TUP_DCD_ENDPOINT_MAX=16)
        # Assertions are the test checks, including in Release builds.
        if(MSVC)
            target_compile_options(usb_descriptor_tests PRIVATE /UNDEBUG)
        else()
            target_compile_options(usb_descriptor_tests PRIVATE -UNDEBUG)
        endif()
        add_test(NAME usb_descriptor_tests COMMAND usb_descriptor_tests)
    endif()
    add_test(NAME wsprrypico_core_tests COMMAND wsprrypico_core_tests)
    add_test(NAME wtp_monitor_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/wtp_monitor_tests.py)
endif()

if(WSPRRY_PICO_BUILD_FIRMWARE)
    add_subdirectory(firmware)
endif()
