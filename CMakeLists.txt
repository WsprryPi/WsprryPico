cmake_minimum_required(VERSION 3.24)

option(WSPRRY_PICO_BUILD_FIRMWARE "Build Pico 2 W firmware" OFF)

if(WSPRRY_PICO_BUILD_FIRMWARE)
    set(PICO_BOARD pico2_w CACHE STRING "Pico SDK board" FORCE)
    include(cmake/pico_sdk_import.cmake)
    project(WsprryPico LANGUAGES C CXX ASM)
    # SDK overlays contain diagnostic __FILE__ strings in the flashed image.
    # Normalize both roots so an independent build does not change .rodata,
    # relocate the image, or disclose a developer's filesystem layout.
    add_compile_options(
        "-ffile-prefix-map=${CMAKE_SOURCE_DIR}=wsprrypico-source"
        "-ffile-prefix-map=${CMAKE_BINARY_DIR}=wsprrypico-build"
        "-ffile-prefix-map=${PICO_SDK_PATH}=pico-sdk"
    )
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
add_subdirectory(src/microchrony)
if(WSPRRY_PICO_BUILD_FIRMWARE)
    include(cmake/cyw43_tx_overlay.cmake)
    wsprry_cyw43_tx_overlay()
endif()
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
    src/network/web/index.html src/network/web/style.css src/network/web/app.js src/network/web/udp-logging.js
    src/network/web/organization.js src/network/web/device-presentation.js src/network/web/config-validation.js
    src/network/web/saved-progress.js src/network/web/gpio-drive.js src/network/web/utc-datetime.js src/network/web/message-schedule.js
    src/network/web/rf-calibration.js src/network/web/amplifier-enable.js src/network/web/amplifier-timing.js src/network/web/filter-selector.js src/network/web/standalone-frequency.js
    src/network/bootstrap_web/index.html src/network/bootstrap_web/style.css
    src/network/bootstrap_web/bundle.js
    src/network/bootstrap_web/radio-bundle.js
    src/network/bootstrap_web/owner.html src/network/bootstrap_web/owner-bundle.js
    src/network/bootstrap_web/owner-key-bundle.js
    src/network/bootstrap_web/recovery.html src/network/bootstrap_web/recovery-bundle.js
    src/network/web/app.min.js src/network/web/config-validation.min.js
    src/network/web/device-presentation.min.js src/network/web/organization.min.js
    src/network/web/asset-build.json scripts/build_operator_assets.mjs
    scripts/generate_web_assets.py)
execute_process(COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/generate_web_assets.py
    ${CMAKE_SOURCE_DIR} ${CMAKE_CURRENT_BINARY_DIR}/generated/web_assets.cpp
    COMMAND_ERROR_IS_FATAL ANY)

add_library(wsprrypico_core
    src/logging/logger.cpp
    src/logging/udp_settings.cpp
    src/network/udp_logging.cpp
    src/application/config_update.cpp
    src/application/resources.cpp
    src/application/frequency_policy.cpp
    src/hardware/pins.cpp
    src/hardware/filter_settings.cpp
    src/rf/filter_selector.cpp
    src/provisioning/profile.cpp
    src/provisioning/network_profile.cpp
    src/provisioning/consumer_profile.cpp
    src/provisioning/consumer_claim.cpp
    src/provisioning/consumer_claim_commit.cpp
    src/provisioning/hostname.cpp
    src/provisioning/local_settings.cpp
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
    src/network/management.cpp
    src/network/consumer_radio.cpp
    src/network/softap_api.cpp
    ${CMAKE_CURRENT_BINARY_DIR}/generated/web_assets.cpp
    src/encoding/wspr.cpp
    src/encoding/wspr_plan.cpp
    src/standalone/dry_run_engine.cpp
    src/standalone/config.cpp
    src/standalone/frequency_policy_engine.cpp
    src/standalone/storage.cpp
    src/standalone/progress.cpp
    src/standalone/scheduler.cpp
    src/rf/calibration.cpp
    src/time/ntp_filter.cpp
    src/time/ntp_client.cpp
    src/time/controller_time.cpp
    src/time/utc_discipline.cpp
    src/time/usb_time_source.cpp
    src/usb/management_endpoint.cpp
    src/usb/time_exchange.cpp
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
target_link_libraries(wsprrypico_core PUBLIC microchrony)

if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    target_compile_options(wsprrypico_core PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

if(WSPRRY_PICO_BUILD_FIRMWARE)
    target_compile_options(microchrony PRIVATE -fstack-usage -fno-exceptions -fno-rtti
                           -ffunction-sections -fdata-sections)
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
if(DEFINED WSPRRY_PICO_STANDALONE_WSPR_BASE_FREQUENCY_HZ)
    message(FATAL_ERROR "Build-time standalone frequency selection was removed; configure frequency at runtime")
endif()
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
    add_executable(udp_logging_tests tests/udp_logging_tests.cpp)
    target_link_libraries(udp_logging_tests PRIVATE wsprrypico_core)
    target_compile_options(udp_logging_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME udp_logging_tests COMMAND udp_logging_tests)
    add_executable(logging_tests tests/logging_tests.cpp)
    target_link_libraries(logging_tests PRIVATE wsprrypico_core)
    target_compile_options(logging_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME logging_tests COMMAND logging_tests)
    add_executable(standalone_frequency_tests tests/standalone_frequency_tests.cpp)
    target_link_libraries(standalone_frequency_tests PRIVATE wsprrypico_core)
    target_compile_options(standalone_frequency_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME standalone_frequency COMMAND standalone_frequency_tests)
    add_test(NAME standalone_frequency_schema COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/standalone_frequency_schema_tests.py $<TARGET_FILE:standalone_frequency_tests>)
    find_program(WSPRRY_PICO_FREQUENCY_NODE node)
    if(WSPRRY_PICO_FREQUENCY_NODE)
        add_test(NAME standalone_frequency_browser COMMAND ${WSPRRY_PICO_FREQUENCY_NODE}
            ${CMAKE_SOURCE_DIR}/tests/standalone_frequency_browser_tests.js)
    endif()
    add_test(NAME operator_asset_build_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/operator_asset_build_tests.py)
    add_test(NAME application_image_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/application_image_tests.py)
    add_executable(usb_local_management_tests tests/usb_local_management_tests.cpp)
    target_link_libraries(usb_local_management_tests PRIVATE wsprrypico_core)
    target_compile_options(usb_local_management_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME usb_local_management_tests COMMAND usb_local_management_tests)
    add_executable(usb_maintenance_tests tests/usb_maintenance_tests.cpp)
    target_link_libraries(usb_maintenance_tests PRIVATE wsprrypico_core)
    target_compile_options(usb_maintenance_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME usb_maintenance_tests COMMAND usb_maintenance_tests)
    add_test(NAME usb_installer_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/usb_installer_tests.py)
    add_executable(usb_management_tests tests/usb_management_tests.cpp)
    target_link_libraries(usb_management_tests PRIVATE wsprrypico_core)
    target_compile_options(usb_management_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME usb_management_tests COMMAND usb_management_tests)
    add_executable(usb_management_driver tests/usb_management_driver.cpp)
    target_link_libraries(usb_management_driver PRIVATE wsprrypico_core)
    target_compile_options(usb_management_driver PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME usb_management_vectors COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/usb_management_vectors.py $<TARGET_FILE:usb_management_driver>
        ${CMAKE_SOURCE_DIR}/engineering/protocol/USB-Management-v1-vectors.json)
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
    add_test(NAME stack_guard_image_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/stack_guard_image_tests.py)
    add_test(NAME heap_hook_image_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/heap_hook_image_tests.py)
    add_executable(refill_metrics_tests tests/refill_metrics_tests.cpp)
    target_link_libraries(refill_metrics_tests PRIVATE wsprrypico_rf)
    target_compile_options(refill_metrics_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME refill_metrics_tests COMMAND refill_metrics_tests)
    add_test(NAME usb_inventory_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/usb_inventory_tests.py)
    add_test(NAME firmware_payload_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/firmware_payload_tests.py)
    add_test(NAME console_trace_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/console_trace_tests.py)
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
    add_executable(hostname_tests tests/hostname_tests.cpp)
    add_executable(progress_tests tests/progress_tests.cpp)
    target_link_libraries(progress_tests PRIVATE wsprrypico_core)
    target_compile_options(progress_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME progress_tests COMMAND progress_tests)
    target_link_libraries(hostname_tests PRIVATE wsprrypico_core)
    target_compile_options(hostname_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME hostname_tests COMMAND hostname_tests)
    add_executable(message_schedule_tests tests/message_schedule_tests.cpp)
    target_link_libraries(message_schedule_tests PRIVATE wsprrypico_core wsprrypico_rf)
    target_compile_options(message_schedule_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME message_schedule_tests COMMAND message_schedule_tests)
    add_executable(network_tests tests/network_tests.cpp)
    target_link_libraries(network_tests PRIVATE wsprrypico_core wsprrypico_rf)
    target_compile_options(network_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME network_tests COMMAND network_tests)
    add_executable(management_carrier_tests tests/management_carrier_tests.cpp)
    target_link_libraries(management_carrier_tests PRIVATE wsprrypico_core)
    target_compile_options(management_carrier_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME management_carrier_tests COMMAND management_carrier_tests)
    add_executable(consumer_radio_tests tests/consumer_radio_tests.cpp)
    target_link_libraries(consumer_radio_tests PRIVATE wsprrypico_core wsprrypico_rf)
    target_compile_options(consumer_radio_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME consumer_radio_tests COMMAND consumer_radio_tests)
    add_executable(http_response_lifetime_tests tests/http_response_lifetime_tests.cpp)
    target_link_libraries(http_response_lifetime_tests PRIVATE wsprrypico_core)
    target_compile_options(http_response_lifetime_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME http_response_lifetime_tests COMMAND http_response_lifetime_tests)
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
        add_test(NAME device_presentation_tests COMMAND ${WSPRRY_PICO_NODE_EXECUTABLE}
            ${CMAKE_SOURCE_DIR}/tests/device_presentation_tests.js)
        add_test(NAME saved_progress_browser_tests COMMAND ${WSPRRY_PICO_NODE_EXECUTABLE}
            ${CMAKE_SOURCE_DIR}/tests/saved_progress_tests.js)
        add_test(NAME operations_browser_tests COMMAND ${WSPRRY_PICO_NODE_EXECUTABLE}
            ${CMAKE_SOURCE_DIR}/tests/operations_browser_tests.js)
        add_test(NAME network_browser_tests COMMAND ${WSPRRY_PICO_NODE_EXECUTABLE}
            ${CMAKE_SOURCE_DIR}/tests/network_browser_tests.js)
        add_test(NAME logging_browser_tests COMMAND ${WSPRRY_PICO_NODE_EXECUTABLE}
            ${CMAKE_SOURCE_DIR}/tests/logging_browser_tests.js)
        add_test(NAME ui_access_browser_tests COMMAND ${WSPRRY_PICO_NODE_EXECUTABLE}
            ${CMAKE_SOURCE_DIR}/tests/ui_access_browser_tests.js)
        add_test(NAME ui_access_shipped_tests COMMAND ${CMAKE_COMMAND} -E env
            WSPRRY_PICO_BROWSER_SHIPPED=1 ${WSPRRY_PICO_NODE_EXECUTABLE}
            ${CMAKE_SOURCE_DIR}/tests/ui_access_browser_tests.js)
        add_test(NAME schedule_workflow_browser_tests COMMAND ${WSPRRY_PICO_NODE_EXECUTABLE}
            ${CMAKE_SOURCE_DIR}/tests/schedule_workflow_browser_tests.js)
        add_test(NAME message_frequency_browser_tests COMMAND ${WSPRRY_PICO_NODE_EXECUTABLE}
            ${CMAKE_SOURCE_DIR}/tests/message_frequency_browser_tests.js)
        add_test(NAME utc_datetime_browser_tests COMMAND ${WSPRRY_PICO_NODE_EXECUTABLE}
            ${CMAKE_SOURCE_DIR}/tests/utc_datetime_browser_tests.js)
    endif()
    add_executable(firmware_profile_tests tests/firmware_profile_tests.cpp)
    target_link_libraries(firmware_profile_tests PRIVATE wsprrypico_rf)
    target_compile_options(firmware_profile_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME firmware_profile_tests COMMAND firmware_profile_tests)
    add_executable(pin_allocation_tests tests/pin_allocation_tests.cpp)
    target_link_libraries(pin_allocation_tests PRIVATE wsprrypico_core)
    add_test(NAME pin_allocation COMMAND pin_allocation_tests)
    add_executable(microchrony_tests tests/microchrony_tests.cpp)
    target_link_libraries(microchrony_tests PRIVATE microchrony)
    target_compile_options(microchrony_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME microchrony COMMAND microchrony_tests)
    add_executable(microchrony_loop tests/reference/microchrony_loop.cpp)
    target_link_libraries(microchrony_loop PRIVATE microchrony)
    target_compile_options(microchrony_loop PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME microchrony_clock_loop COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/reference/test_microchrony_loop.py $<TARGET_FILE:microchrony_loop>)
    add_test(NAME independent_clock_measurement COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/clock_measurement_tests.py)
    add_test(NAME ntp_packet_evidence COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/ntp_packet_tests.py $<TARGET_FILE:ntp_work_tests>)
    add_executable(ntp_work_tests tests/ntp_work_tests.cpp)
    target_link_libraries(ntp_work_tests PRIVATE wsprrypico_rf)
    target_compile_options(ntp_work_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME ntp_work COMMAND ntp_work_tests)
    add_test(NAME ntp_replay COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/ntp_replay_tests.py $<TARGET_FILE:ntp_work_tests> $<TARGET_FILE:microchrony_tests>)
    if(WSPRRY_PICO_NODE_EXECUTABLE)
        add_test(NAME rf_calibration_browser COMMAND ${WSPRRY_PICO_NODE_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/rf_calibration_browser_tests.js)
    endif()
    add_executable(gpio_drive_tests tests/gpio_drive_tests.cpp)
    add_executable(ntp_timeout_tests tests/ntp_timeout_tests.cpp)
    target_link_libraries(ntp_timeout_tests PRIVATE wsprrypico_core)
    target_compile_options(ntp_timeout_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME ntp_timeout COMMAND ntp_timeout_tests)
    add_test(NAME ntp_timeout_schema COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/ntp_timeout_schema_tests.py $<TARGET_FILE:ntp_timeout_tests>)
    if(WSPRRY_PICO_NODE_EXECUTABLE)
        add_test(NAME ntp_timeout_browser COMMAND ${WSPRRY_PICO_NODE_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/ntp_timeout_browser_tests.js)
    endif()
    target_link_libraries(gpio_drive_tests PRIVATE wsprrypico_core)
    target_compile_options(gpio_drive_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME gpio_drive COMMAND gpio_drive_tests)
    add_test(NAME gpio_drive_schema COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/gpio_drive_schema_tests.py $<TARGET_FILE:gpio_drive_tests>)
    if(WSPRRY_PICO_NODE_EXECUTABLE)
        add_test(NAME gpio_drive_browser COMMAND ${WSPRRY_PICO_NODE_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/gpio_drive_browser_tests.js)
    endif()
    add_executable(application_resource_tests tests/application_resource_tests.cpp)
    target_link_libraries(application_resource_tests PRIVATE wsprrypico_core)
    target_compile_options(application_resource_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME application_resources COMMAND application_resource_tests)
    add_executable(config_update_tests tests/config_update_tests.cpp)
    target_link_libraries(config_update_tests PRIVATE wsprrypico_core)
    target_compile_options(config_update_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME config_updates COMMAND config_update_tests)
    add_test(NAME config_update_schema COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/config_update_schema_tests.py $<TARGET_FILE:config_update_tests>)
    set_tests_properties(config_update_schema PROPERTIES SKIP_RETURN_CODE 77)
    if(WSPRRY_PICO_NODE_EXECUTABLE)
        add_test(NAME config_update_legacy_pi COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_SOURCE_DIR}/tests/config_update_legacy_pi_test.py
            $<TARGET_FILE:config_update_tests> ${WSPRRY_PICO_NODE_EXECUTABLE})
    endif()
    add_test(NAME application_schema COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/application_schema_tests.py $<TARGET_FILE:application_resource_tests>)

    add_executable(standalone_tests tests/standalone_tests.cpp)
    target_link_libraries(standalone_tests PRIVATE wsprrypico_core)
    target_compile_definitions(standalone_tests PRIVATE WSPRRY_PICO_RF_SAMPLE_RATE_HZ=${WSPRRY_PICO_RF_SAMPLE_RATE_HZ})
    target_compile_options(standalone_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME standalone_tests COMMAND standalone_tests)
    add_executable(wspr_plan_tests tests/wspr_plan_tests.cpp)
    target_link_libraries(wspr_plan_tests PRIVATE wsprrypico_core)
    target_compile_options(wspr_plan_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME wspr_plan_tests COMMAND wspr_plan_tests)
    add_executable(wspr_resource_tests tests/wspr_resource_tests.cpp)
    target_link_libraries(wspr_resource_tests PRIVATE wsprrypico_core)
    target_compile_options(wspr_resource_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME wspr_resource_tests COMMAND wspr_resource_tests)
    add_test(NAME wspr_resource_schema_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/wspr_resource_schema_tests.py $<TARGET_FILE:wspr_resource_tests>)
    add_executable(frequency_policy_tests tests/frequency_policy_tests.cpp)
    target_link_libraries(frequency_policy_tests PRIVATE wsprrypico_core)
    target_compile_options(frequency_policy_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME frequency_policy_tests COMMAND frequency_policy_tests)
    add_executable(provisioning_tests tests/provisioning_tests.cpp)
    target_link_libraries(provisioning_tests PRIVATE wsprrypico_core)
    target_compile_options(provisioning_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME provisioning_tests COMMAND provisioning_tests)
    add_executable(provisioning_flash_fixture src/tools/provisioning_flash_fixture.cpp)
    target_link_libraries(provisioning_flash_fixture PRIVATE wsprrypico_core)
    target_compile_options(provisioning_flash_fixture PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME provisioning_flash_fixture_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/provisioning_flash_fixture_tests.py $<TARGET_FILE:provisioning_flash_fixture>
        $<TARGET_FILE:recovery_flash_inspector>)
    add_test(NAME populated_flash_fixture_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/populated_flash_fixture_tests.py $<TARGET_FILE:provisioning_flash_fixture>
        $<TARGET_FILE:recovery_flash_inspector>)
    add_executable(field_mode_fixture_tests tests/field_mode_fixture_tests.cpp)
    target_link_libraries(field_mode_fixture_tests PRIVATE wsprrypico_core)
    target_compile_options(field_mode_fixture_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME field_mode_fixture_tests COMMAND field_mode_fixture_tests
        $<TARGET_FILE:provisioning_flash_fixture>)
    add_executable(recovery_flash_inspector src/tools/recovery_flash_inspector.cpp)
    target_link_libraries(recovery_flash_inspector PRIVATE wsprrypico_core)
    target_compile_options(recovery_flash_inspector PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_executable(reset_storage_tests tests/reset_storage_tests.cpp)
    target_link_libraries(reset_storage_tests PRIVATE wsprrypico_core)
    target_compile_options(reset_storage_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME reset_storage_tests COMMAND reset_storage_tests)
    add_executable(field_access_tests tests/field_access_tests.cpp)
    target_link_libraries(field_access_tests PRIVATE wsprrypico_core)
    target_compile_options(field_access_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME field_access_tests COMMAND field_access_tests)
    add_executable(led_acceptance_tests tests/led_acceptance_tests.cpp
        src/provisioning/pico/indicator_output.cpp)
    target_include_directories(led_acceptance_tests PRIVATE tests/indicator_mock)
    target_compile_definitions(led_acceptance_tests PRIVATE WSPRRY_PICO_LED_ACCEPTANCE=1)
    target_link_libraries(led_acceptance_tests PRIVATE wsprrypico_core)
    target_compile_options(led_acceptance_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME led_acceptance_tests COMMAND led_acceptance_tests)
    add_executable(indicator_output_tests tests/indicator_output_tests.cpp
        src/provisioning/pico/indicator_output.cpp)
    target_include_directories(indicator_output_tests PRIVATE tests/indicator_mock)
    target_link_libraries(indicator_output_tests PRIVATE wsprrypico_core)
    target_compile_options(indicator_output_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME indicator_output_tests COMMAND indicator_output_tests)
    add_executable(amplifier_enable_tests tests/amplifier_enable_tests.cpp
        src/hardware/pico/amplifier_output.cpp)
    target_include_directories(amplifier_enable_tests PRIVATE tests/indicator_mock)
    target_link_libraries(amplifier_enable_tests PRIVATE wsprrypico_core)
    target_compile_options(amplifier_enable_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME amplifier_enable COMMAND amplifier_enable_tests)
    add_executable(filter_selector_tests tests/filter_selector_tests.cpp src/hardware/pico/filter_outputs.cpp)
    target_include_directories(filter_selector_tests PRIVATE tests/indicator_mock)
    target_link_libraries(filter_selector_tests PRIVATE wsprrypico_rf)
    target_compile_options(filter_selector_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME filter_selector COMMAND filter_selector_tests)
    add_test(NAME filter_selector_schema COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/filter_selector_schema_tests.py $<TARGET_FILE:filter_selector_tests>)
    if(WSPRRY_PICO_NODE_EXECUTABLE)
        add_test(NAME filter_selector_browser COMMAND ${WSPRRY_PICO_NODE_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/filter_selector_browser_tests.js)
    endif()
    add_test(NAME amplifier_timing_schema COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/amplifier_timing_schema_tests.py $<TARGET_FILE:amplifier_enable_tests>)
    add_test(NAME amplifier_enable_schema COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/amplifier_enable_schema_tests.py $<TARGET_FILE:amplifier_enable_tests>)
    if(WSPRRY_PICO_NODE_EXECUTABLE)
        add_test(NAME amplifier_timing_browser COMMAND ${WSPRRY_PICO_NODE_EXECUTABLE}
            ${CMAKE_SOURCE_DIR}/tests/amplifier_timing_browser_tests.js)
        add_test(NAME amplifier_enable_browser COMMAND ${WSPRRY_PICO_NODE_EXECUTABLE}
            ${CMAKE_SOURCE_DIR}/tests/amplifier_enable_browser_tests.js $<TARGET_FILE:amplifier_enable_tests>)
    endif()
    add_executable(button_diagnostic_tests tests/button_diagnostic_tests.cpp)
    target_link_libraries(button_diagnostic_tests PRIVATE wsprrypico_core)
    target_compile_options(button_diagnostic_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME button_diagnostic_tests COMMAND button_diagnostic_tests)
    add_test(NAME gp14_robustness_tests
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/gp14_robustness_tests.py)
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
        add_test(NAME rf_keyed_analysis_tests COMMAND ${WSPRRY_PICO_HARNESS_PYTHON}
                 ${CMAKE_CURRENT_SOURCE_DIR}/tests/rf_keyed_analysis_tests.py)
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
    add_executable(http_server_tests tests/http_server_tests.cpp src/network/pico/http_server.cpp)
    target_include_directories(http_server_tests PRIVATE tests/http_server_mock)
    target_link_libraries(http_server_tests PRIVATE wsprrypico_core)
    target_compile_options(http_server_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME http_server_tests COMMAND http_server_tests)
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
    add_test(NAME network_trace_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/network_trace_tests.py)
    add_test(NAME inhibited_network_acceptance_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/inhibited_network_acceptance_tests.py)
    add_test(NAME standalone_image_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/standalone_image_tests.py)
    add_test(NAME rf_renderer_image_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/rf_renderer_image_tests.py)
    add_test(NAME standalone_console_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/standalone_console_tests.py)
    if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
        add_test(NAME pico_application_adapter_tests COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_SOURCE_DIR}/tests/pico_application_adapter_tests.py)
        add_test(NAME journal_power_cut_tests COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_SOURCE_DIR}/tests/journal_power_cut_tests.py)
    endif()
    add_executable(wsprrypico_core_tests tests/core_tests.cpp)
    target_link_libraries(wsprrypico_core_tests PRIVATE wsprrypico_core)
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
        target_compile_options(wsprrypico_core_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()
    add_executable(endpoint_capacity_tests tests/endpoint_capacity_tests.cpp)
    target_link_libraries(endpoint_capacity_tests PRIVATE wsprrypico_core)
    target_compile_options(endpoint_capacity_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME endpoint_capacity_tests COMMAND endpoint_capacity_tests)
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
    add_test(NAME btstack_pool_hook_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/btstack_pool_hook_tests.py)
    add_test(NAME wtp_capacity_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/wtp_capacity_tests.py)
    set_tests_properties(wtp_capacity_tests PROPERTIES
        ENVIRONMENT "WTP_ENDPOINT_DRIVER=$<TARGET_FILE:endpoint_driver>")
    add_test(NAME console_info_format_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/console_info_format_tests.py)
    add_test(NAME firmware_fixture_options_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/firmware_fixture_options_tests.py)
    add_test(NAME radio_capture_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/radio_capture_tests.py)
    if(WSPRRY_PICO_HARNESS_PYTHON)
        add_test(NAME rf_analysis_jobs_tests COMMAND ${WSPRRY_PICO_HARNESS_PYTHON}
            ${CMAKE_SOURCE_DIR}/tests/rf_analysis_jobs_tests.py)
        add_test(NAME rf_abort_analysis_tests COMMAND ${WSPRRY_PICO_HARNESS_PYTHON}
            ${CMAKE_SOURCE_DIR}/tests/rf_abort_analysis_tests.py)
        add_test(NAME rf_presence_tests COMMAND ${WSPRRY_PICO_HARNESS_PYTHON}
            ${CMAKE_SOURCE_DIR}/tests/rf_presence_tests.py)
        add_test(NAME rf_drive_comparison_tests COMMAND ${WSPRRY_PICO_HARNESS_PYTHON}
            ${CMAKE_SOURCE_DIR}/tests/rf_drive_comparison_tests.py)
    endif()
    add_test(NAME wsprrypico_core_tests COMMAND wsprrypico_core_tests)
    add_test(NAME wtp_monitor_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/wtp_monitor_tests.py)
endif()

if(WSPRRY_PICO_BUILD_FIRMWARE)
    add_subdirectory(firmware)
endif()
