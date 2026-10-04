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
    src/network/bootstrap_web/index.html src/network/bootstrap_web/style.css
    src/network/bootstrap_web/bundle.js
    src/network/bootstrap_web/owner.html src/network/bootstrap_web/owner-bundle.js
    src/network/bootstrap_web/owner-key-bundle.js
    src/network/bootstrap_web/recovery.html src/network/bootstrap_web/recovery-bundle.js
    scripts/generate_web_assets.py)
execute_process(COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/generate_web_assets.py
    ${CMAKE_SOURCE_DIR} ${CMAKE_CURRENT_BINARY_DIR}/generated/web_assets.cpp
    COMMAND_ERROR_IS_FATAL ANY)

add_library(wsprrypico_core
    src/application/resources.cpp
    src/hardware/pins.cpp
    src/provisioning/profile.cpp
    src/provisioning/network_profile.cpp
    src/provisioning/consumer_profile.cpp
    src/provisioning/consumer_claim.cpp
    src/provisioning/consumer_claim_commit.cpp
    src/provisioning/access.cpp
    src/provisioning/ble_session.cpp
    src/provisioning/field_runtime.cpp
    src/provisioning/gatt_framing.cpp
    src/provisioning/local_access.cpp
    src/provisioning/reset.cpp
    src/provisioning/reset_storage.cpp
    src/provisioning/softap_http.cpp
    src/provisioning/activation.cpp
    src/provisioning/storage.cpp
    src/provisioning/manager.cpp
    src/provisioning/command.cpp
    src/provisioning/runtime.cpp
    src/network/mdns.cpp
    src/network/http.cpp
    src/network/bootstrap_http.cpp
    src/network/bootstrap_codec.cpp
    src/network/bootstrap_join.cpp
    src/network/bootstrap_slot.cpp
    src/network/bootstrap_wire.cpp
    src/network/owner_wire.cpp
    src/network/owner_challenge.cpp
    src/network/owner_claim_http.cpp
    src/network/api.cpp
    src/network/softap_api.cpp
    ${CMAKE_CURRENT_BINARY_DIR}/generated/web_assets.cpp
    src/encoding/wspr.cpp
    src/standalone/dry_run_engine.cpp
    src/standalone/config.cpp
    src/standalone/storage.cpp
    src/standalone/scheduler.cpp
    src/time/sntp.cpp
    src/time/controller_time.cpp
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
set(WSPRRY_PICO_STANDALONE_WSPR_BASE_FREQUENCY_HZ "3570100" CACHE STRING
    "Autonomous standalone WSPR base frequency in whole Hz")
if(NOT WSPRRY_PICO_STANDALONE_WSPR_BASE_FREQUENCY_HZ MATCHES "^[0-9]+$")
    message(FATAL_ERROR "Standalone WSPR base frequency must be whole Hz")
endif()
math(EXPR WSPRRY_PICO_STANDALONE_WSPR_MAX_BASE_HZ
     "${WSPRRY_PICO_RF_SAMPLE_RATE_HZ} / 2 - 5")
if(WSPRRY_PICO_STANDALONE_WSPR_BASE_FREQUENCY_HZ LESS 100000 OR
   WSPRRY_PICO_STANDALONE_WSPR_BASE_FREQUENCY_HZ GREATER
   WSPRRY_PICO_STANDALONE_WSPR_MAX_BASE_HZ)
    message(FATAL_ERROR "Standalone WSPR base frequency is outside the RF profile")
endif()
target_compile_definitions(wsprrypico_core PUBLIC
    WSPRRY_PICO_STANDALONE_WSPR_BASE_FREQUENCY_HZ=${WSPRRY_PICO_STANDALONE_WSPR_BASE_FREQUENCY_HZ})
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
    add_executable(acl_credit_tests tests/acl_credit_tests.cpp src/runtime/pico/btstack_acl_metrics.cpp)
    target_include_directories(acl_credit_tests PRIVATE tests/acl_mock src)
    target_compile_options(acl_credit_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME acl_credit_tests COMMAND acl_credit_tests)

    add_executable(activity_trace_tests tests/activity_trace_tests.cpp)
    target_include_directories(activity_trace_tests PRIVATE src)
    target_compile_options(activity_trace_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME activity_trace_tests COMMAND activity_trace_tests)
    add_test(NAME phase12_engineering_flash_status_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase12_engineering_flash_status_tests.py)
    add_test(NAME phase12_engineering_flash_status_dispatch_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase12_engineering_flash_status_dispatch_tests.py)
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
    add_test(NAME phase12_candidate_manifest_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase12_candidate_manifest_tests.py)
    add_test(NAME phase11_5_network_fixture_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_network_fixture_tests.py)
    add_test(NAME phase11_5_package8_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_package8_tests.py)
    add_test(NAME phase11_5_package9_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_package9_tests.py)
    add_test(NAME phase11_5_package10_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_package10_tests.py)
    add_test(NAME phase11_5_package11_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_package11_tests.py)
    add_test(NAME phase11_6_plan_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_6_plan_tests.py)
    add_test(NAME phase11_6_audit_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_6_audit_tests.py)
    add_test(NAME phase11_6_attempt_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_6_attempt_tests.py)
    add_test(NAME phase11_7_closure_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_7_closure_tests.py)
    set_tests_properties(phase11_7_closure_tests PROPERTIES WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})
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
    add_executable(bootstrap_http_tests tests/bootstrap_http_tests.cpp)
    target_link_libraries(bootstrap_http_tests PRIVATE wsprrypico_core)
    target_compile_options(bootstrap_http_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME bootstrap_http_tests COMMAND bootstrap_http_tests)
    add_executable(bootstrap_slot_tests tests/bootstrap_slot_tests.cpp)
    target_link_libraries(bootstrap_slot_tests PRIVATE wsprrypico_core)
    target_compile_options(bootstrap_slot_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME bootstrap_slot_tests COMMAND bootstrap_slot_tests)
    add_executable(bootstrap_join_tests tests/bootstrap_join_tests.cpp)
    target_link_libraries(bootstrap_join_tests PRIVATE wsprrypico_core)
    target_compile_options(bootstrap_join_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME bootstrap_join_tests COMMAND bootstrap_join_tests)
    add_executable(bootstrap_wire_tests tests/bootstrap_wire_tests.cpp)
    target_link_libraries(bootstrap_wire_tests PRIVATE wsprrypico_core)
    target_compile_options(bootstrap_wire_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME bootstrap_wire_tests COMMAND bootstrap_wire_tests)
    find_program(WSPRRY_PICO_NODE_EXECUTABLE node)
    if(WSPRRY_PICO_NODE_EXECUTABLE)
        add_test(NAME network_browser_tests COMMAND ${WSPRRY_PICO_NODE_EXECUTABLE}
            ${CMAKE_SOURCE_DIR}/tests/network_browser_tests.js)
    endif()
    add_executable(firmware_profile_tests tests/firmware_profile_tests.cpp)
    target_link_libraries(firmware_profile_tests PRIVATE wsprrypico_rf)
    target_compile_options(firmware_profile_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME firmware_profile_tests COMMAND firmware_profile_tests)
    add_executable(pin_allocation_tests tests/pin_allocation_tests.cpp)
    target_link_libraries(pin_allocation_tests PRIVATE wsprrypico_core)
    add_test(NAME pin_allocation COMMAND pin_allocation_tests)
    add_executable(application_resource_tests tests/application_resource_tests.cpp)
    target_link_libraries(application_resource_tests PRIVATE wsprrypico_core)
    target_compile_options(application_resource_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME application_resources COMMAND application_resource_tests)
    add_test(NAME application_schema COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/application_schema_tests.py $<TARGET_FILE:application_resource_tests>)

    add_executable(standalone_tests tests/standalone_tests.cpp)
    target_link_libraries(standalone_tests PRIVATE wsprrypico_core)
    target_compile_definitions(standalone_tests PRIVATE WSPRRY_PICO_RF_SAMPLE_RATE_HZ=${WSPRRY_PICO_RF_SAMPLE_RATE_HZ})
    target_compile_options(standalone_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME standalone_tests COMMAND standalone_tests)
    add_executable(provisioning_tests tests/provisioning_tests.cpp)
    target_link_libraries(provisioning_tests PRIVATE wsprrypico_core)
    target_compile_options(provisioning_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME provisioning_tests COMMAND provisioning_tests)
    add_executable(phase12_flash_fixture src/tools/phase12_flash_fixture.cpp)
    target_link_libraries(phase12_flash_fixture PRIVATE wsprrypico_core)
    target_compile_options(phase12_flash_fixture PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME phase12_flash_fixture_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase12_flash_fixture_tests.py $<TARGET_FILE:phase12_flash_fixture>
        $<TARGET_FILE:recovery_flash_inspector>)
    add_test(NAME phase12_populated_fixture_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase12_populated_fixture_tests.py $<TARGET_FILE:phase12_flash_fixture>
        $<TARGET_FILE:recovery_flash_inspector>)
    add_executable(phase12_field_mode_fixture_tests tests/phase12_field_mode_fixture_tests.cpp)
    target_link_libraries(phase12_field_mode_fixture_tests PRIVATE wsprrypico_core)
    target_compile_options(phase12_field_mode_fixture_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME phase12_field_mode_fixture_tests COMMAND phase12_field_mode_fixture_tests
        $<TARGET_FILE:phase12_flash_fixture>)
    add_executable(recovery_flash_inspector src/tools/recovery_flash_inspector.cpp)
    target_link_libraries(recovery_flash_inspector PRIVATE wsprrypico_core)
    target_compile_options(recovery_flash_inspector PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME phase12_recovery_orchestration_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase12_recovery_orchestration_tests.py $<TARGET_FILE:recovery_flash_inspector>)
    add_executable(reset_storage_tests tests/reset_storage_tests.cpp)
    target_link_libraries(reset_storage_tests PRIVATE wsprrypico_core)
    target_compile_options(reset_storage_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME reset_storage_tests COMMAND reset_storage_tests)
    add_executable(field_access_tests tests/field_access_tests.cpp)
    target_link_libraries(field_access_tests PRIVATE wsprrypico_core)
    target_compile_options(field_access_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME field_access_tests COMMAND field_access_tests)
    add_executable(button_diagnostic_tests tests/button_diagnostic_tests.cpp)
    target_link_libraries(button_diagnostic_tests PRIVATE wsprrypico_core)
    target_compile_options(button_diagnostic_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME button_diagnostic_tests COMMAND button_diagnostic_tests)
    add_test(NAME gp14_robustness_tests
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/gp14_robustness_tests.py)
    add_test(NAME gp14_rf_orchestration_tests
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/gp14_rf_orchestration_tests.py)
    add_test(NAME gp14_ap_proof_tests
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/gp14_ap_proof_tests.py)
    add_executable(consumer_profile_tests tests/consumer_profile_tests.cpp)
    target_link_libraries(consumer_profile_tests PRIVATE wsprrypico_core)
    target_compile_options(consumer_profile_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME consumer_profile_tests COMMAND consumer_profile_tests)
    add_executable(consumer_storage_tests tests/consumer_storage_tests.cpp)
    target_link_libraries(consumer_storage_tests PRIVATE wsprrypico_core)
    target_compile_options(consumer_storage_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME consumer_storage_tests COMMAND consumer_storage_tests)
    add_executable(consumer_claim_tests tests/consumer_claim_tests.cpp)
    target_link_libraries(consumer_claim_tests PRIVATE wsprrypico_core)
    target_compile_options(consumer_claim_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME consumer_claim_tests COMMAND consumer_claim_tests)
    add_executable(consumer_claim_commit_tests tests/consumer_claim_commit_tests.cpp)
    target_link_libraries(consumer_claim_commit_tests PRIVATE wsprrypico_core)
    target_compile_options(consumer_claim_commit_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME consumer_claim_commit_tests COMMAND consumer_claim_commit_tests)
    add_executable(owner_wire_tests tests/owner_wire_tests.cpp)
    target_link_libraries(owner_wire_tests PRIVATE wsprrypico_core)
    target_compile_options(owner_wire_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME owner_wire_tests COMMAND owner_wire_tests)
    add_executable(owner_challenge_tests tests/owner_challenge_tests.cpp)
    target_link_libraries(owner_challenge_tests PRIVATE wsprrypico_core)
    target_compile_options(owner_challenge_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME owner_challenge_tests COMMAND owner_challenge_tests)
    add_executable(owner_claim_http_tests tests/owner_claim_http_tests.cpp)
    target_link_libraries(owner_claim_http_tests PRIVATE wsprrypico_core)
    target_compile_options(owner_claim_http_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME owner_claim_http_tests COMMAND owner_claim_http_tests)
    add_executable(softap_api_tests tests/softap_api_tests.cpp)
    target_link_libraries(softap_api_tests PRIVATE wsprrypico_core)
    target_compile_options(softap_api_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME softap_api_tests COMMAND softap_api_tests)
    add_executable(flash_layout_tests tests/flash_layout_tests.cpp)
    target_include_directories(flash_layout_tests PRIVATE src)
    target_compile_options(flash_layout_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME flash_layout_tests COMMAND flash_layout_tests)
    if(WSPRRY_PICO_NODE_EXECUTABLE)
        add_test(NAME recovery_web_tests COMMAND ${WSPRRY_PICO_NODE_EXECUTABLE}
            ${CMAKE_SOURCE_DIR}/src/network/bootstrap_web/recovery-app.test.mjs)
        add_test(NAME provisioning_web_tests COMMAND ${WSPRRY_PICO_NODE_EXECUTABLE}
            ${CMAKE_SOURCE_DIR}/tests/provisioning_web_tests.js)
    endif()
    add_test(NAME provisioning_contract_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/provisioning_contract_tests.py)
    add_test(NAME capacity_pending_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/capacity_pending_tests.py)
    add_test(NAME raspberry_pi_ble_client_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/raspberry_pi_ble_client_tests.py)
    add_test(NAME network_transport_contract_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/network_transport_contract_tests.py)
    add_test(NAME bluefy_release_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/bluefy_release_tests.py)
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
    add_test(NAME network_certificate_strict_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/network_certificate_strict_tests.py)
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
    add_test(NAME phase11_5_r3_tests COMMAND ${Python3_EXECUTABLE} -m unittest discover
        -s ${CMAKE_SOURCE_DIR}/tests -p "phase11_5_r3*tests.py")
    set_tests_properties(phase11_5_r3_tests PROPERTIES WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})
    add_test(NAME phase11_5_package4_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_package4_tests.py)
    set_tests_properties(phase11_5_package4_tests PROPERTIES WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})
    add_test(NAME phase11_5_package5_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_package5_tests.py)
    set_tests_properties(phase11_5_package5_tests PROPERTIES WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})
    add_test(NAME phase11_5_package6_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_package6_tests.py)
    set_tests_properties(phase11_5_package6_tests PROPERTIES WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})
    add_test(NAME phase11_5_package7_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_package7_tests.py)
    set_tests_properties(phase11_5_package7_tests PROPERTIES WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})
    add_executable(wsprrypico_core_tests tests/core_tests.cpp)
    target_link_libraries(wsprrypico_core_tests PRIVATE wsprrypico_core)
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
        target_compile_options(wsprrypico_core_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()
    add_executable(endpoint_driver tests/endpoint_driver.cpp)
    add_executable(gatt_write_admission_tests tests/gatt_write_admission_tests.cpp)
    target_link_libraries(gatt_write_admission_tests PRIVATE wsprrypico_core)
    target_compile_options(gatt_write_admission_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME gatt_write_admission_tests COMMAND gatt_write_admission_tests)
    set(WSPRRY_PICO_BTSTACK_TEST_ROOT "" CACHE PATH
        "Optional existing pinned BTstack root for hardware-free delayed ATT runtime checks")
    if(WSPRRY_PICO_BTSTACK_TEST_ROOT)
        # Compile the original pinned SDK server and upstream host mock in
        # place. No SDK download, installation, or CppUTest dependency.
        set(_gatt_sdk_hashes
            "src/ble/att_db.c|7675e6f2063d3d12ac6f35e652a142c1295cdfd66ba222c235a1f7b67de28c8f"
            "src/ble/att_server.c|e4b0b07745feef9b803d23bd7d5f32d2253e4421a8add3b72ae4559d74bc2c25"
            "src/hci.h|2fd4f3169783a306d6bb10f1c0f68748fd95670a56fb014bf282e1530d2aba5a"
            "test/gatt_server/mock.c|6bf6ad80fcb46517ed18e36d73880730f94e1ed21ce9aa56b428589363c40770"
            "test/include/coverage-ble/btstack_config.h|6ecabbe390b84aeb27fe34f9ef1fcdd4d27ebef4d470e1d4bf13c6efbf653b64")
        foreach(_gatt_binding IN LISTS _gatt_sdk_hashes)
            string(REPLACE "|" ";" _gatt_binding "${_gatt_binding}")
            list(GET _gatt_binding 0 _gatt_file)
            list(GET _gatt_binding 1 _gatt_expected)
            file(SHA256 "${WSPRRY_PICO_BTSTACK_TEST_ROOT}/${_gatt_file}" _gatt_actual)
            if(NOT _gatt_actual STREQUAL _gatt_expected)
                message(FATAL_ERROR "Delayed ATT runtime test requires pinned SDK source: ${_gatt_file}")
            endif()
        endforeach()
        enable_language(C)
        set(_gatt_sdk_sources
            test/gatt_server/mock.c test/mock/mock_btstack_tlv.c
            src/ad_parser.c src/ble/att_db.c src/ble/att_db_util.c src/ble/att_server.c
            src/ble/le_device_db_memory.c src/btstack_crypto.c src/btstack_linked_list.c
            src/btstack_memory.c src/btstack_memory_pool.c src/btstack_tlv.c
            src/btstack_util.c src/hci_cmd.c src/hci_dump.c
            3rd-party/rijndael/rijndael.c 3rd-party/micro-ecc/uECC.c)
        list(TRANSFORM _gatt_sdk_sources PREPEND "${WSPRRY_PICO_BTSTACK_TEST_ROOT}/")
        add_executable(gatt_delayed_sdk_tests tests/gatt_delayed_sdk_tests.cpp ${_gatt_sdk_sources})
        set_target_properties(gatt_delayed_sdk_tests PROPERTIES C_STANDARD 11 C_STANDARD_REQUIRED YES)
        target_include_directories(gatt_delayed_sdk_tests PRIVATE
            "${WSPRRY_PICO_BTSTACK_TEST_ROOT}/test/include/coverage-ble"
            "${WSPRRY_PICO_BTSTACK_TEST_ROOT}/test/mock"
            "${WSPRRY_PICO_BTSTACK_TEST_ROOT}/src"
            "${WSPRRY_PICO_BTSTACK_TEST_ROOT}/3rd-party/rijndael"
            "${WSPRRY_PICO_BTSTACK_TEST_ROOT}/3rd-party/micro-ecc"
            "${WSPRRY_PICO_BTSTACK_TEST_ROOT}/platform/posix")
        target_link_libraries(gatt_delayed_sdk_tests PRIVATE wsprrypico_core)
        add_test(NAME gatt_delayed_sdk_tests COMMAND gatt_delayed_sdk_tests)
    endif()
    add_executable(event_storage_tests tests/event_storage_tests.cpp)
    target_link_libraries(event_storage_tests PRIVATE wsprrypico_core)
    target_compile_options(event_storage_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME event_storage_tests COMMAND event_storage_tests)
    add_executable(load_reply_driver tests/load_reply_driver.cpp)
    target_link_libraries(load_reply_driver PRIVATE wsprrypico_rf)
    target_compile_options(load_reply_driver PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME load_reply_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/load_reply_tests.py $<TARGET_FILE:load_reply_driver>)
    add_test(NAME load_reply_target_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase11_5_load_reply_target_tests.py)
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
    add_executable(pool_metrics_tests tests/pool_metrics_tests.cpp)
    target_link_libraries(pool_metrics_tests PRIVATE wsprrypico_core)
    if(MSVC)
        target_compile_options(pool_metrics_tests PRIVATE /UNDEBUG)
    else()
        target_compile_options(pool_metrics_tests PRIVATE -UNDEBUG)
    endif()
    add_test(NAME pool_metrics_tests COMMAND pool_metrics_tests)
    add_test(NAME phase12_composition_audit_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase12_composition_audit_tests.py)
    add_test(NAME phase12_composition_capture_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase12_composition_capture_tests.py)
    add_test(NAME phase12_consumer_composition_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/test_phase12_consumer_composition.py)
    add_test(NAME phase12_consumer_dispatch_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/test_phase12_consumer_dispatch.py)
    add_test(NAME phase12_engineering_setup_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase12_engineering_setup_tests.py)
    add_test(NAME phase12_independent_orchestrator_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase12_independent_orchestrator_tests.py)
    add_test(NAME phase12_engineering_composition_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase12_engineering_composition_tests.py)
    add_test(NAME phase12_engineering_sessions_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase12_engineering_sessions_tests.py)
    add_test(NAME phase12_engineering_time_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/phase12_engineering_time_tests.py)
    foreach(phase12_python_test IN ITEMS
            phase12_authority_capture phase12_serial_observer
            phase12_engineering_orchestrator phase12_engineering_scope phase12_engineering_fixture
            phase12_fixture_roles phase12_virtual_observer phase12_beacon_scan
            phase12_final_collection phase12_target_ap_proof phase12_status_poll
            phase12_station_trial phase12_consumer_fallback
            phase12_engineering_staging
            phase12_engineering_bond_refusal
            phase12_engineering_time_jobs phase12_engineering_time_invalidation
            phase12_time_jobs_sampling phase12_engineering_cookie_grace
            phase12_engineering_stage_dispatch phase12_engineering_network
            phase12_engineering_network_dispatch phase12_consumer_negative
            phase12_consumer_negative_dispatch phase12_consumer_negative_orchestrator
            phase12_consumer_flash_status
            phase12_consumer_busy_claim
            phase12_resource_capture_review phase12_populated phase12_engineering_journal
            phase12_engineering_repairs phase12_consumer_readiness)
        add_test(NAME ${phase12_python_test}_tests COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_SOURCE_DIR}/tests/${phase12_python_test}_tests.py)
    endforeach()
    add_test(NAME btstack_pool_hook_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/btstack_pool_hook_tests.py)
    add_test(NAME wsprrypico_core_tests COMMAND wsprrypico_core_tests)
    add_test(NAME wtp_monitor_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/wtp_monitor_tests.py)
endif()

if(WSPRRY_PICO_BUILD_FIRMWARE)
    add_subdirectory(firmware)
endif()
