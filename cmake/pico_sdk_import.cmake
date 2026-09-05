# Resolve a developer-provided Pico SDK without downloading dependencies.
if(NOT PICO_SDK_PATH)
    if(DEFINED ENV{PICO_SDK_PATH} AND NOT "$ENV{PICO_SDK_PATH}" STREQUAL "")
        set(PICO_SDK_PATH "$ENV{PICO_SDK_PATH}")
    elseif(EXISTS "${CMAKE_CURRENT_LIST_DIR}/../../pico-sdk/pico_sdk_init.cmake")
        get_filename_component(PICO_SDK_PATH "${CMAKE_CURRENT_LIST_DIR}/../../pico-sdk" ABSOLUTE)
    else()
        message(FATAL_ERROR
            "Set PICO_SDK_PATH to the pinned Pico SDK checkout; automatic downloads are disabled")
    endif()
endif()

get_filename_component(PICO_SDK_PATH "${PICO_SDK_PATH}" ABSOLUTE)
if(NOT EXISTS "${PICO_SDK_PATH}/pico_sdk_init.cmake")
    message(FATAL_ERROR "PICO_SDK_PATH does not contain pico_sdk_init.cmake: ${PICO_SDK_PATH}")
endif()
include("${PICO_SDK_PATH}/pico_sdk_init.cmake")
