set(WSPRRY_PICO_REQUIRED_SDK_VERSION "2.3.0")
set(WSPRRY_PICO_REQUIRED_SDK_COMMIT "98a542c1a62fb549ffb5d66a3e5892b06276b670")
set(WSPRRY_PICO_REQUIRED_ARM_GCC_VERSION "15.3.1")

if(NOT PICO_SDK_VERSION_STRING STREQUAL WSPRRY_PICO_REQUIRED_SDK_VERSION)
    message(FATAL_ERROR
        "Pico SDK ${WSPRRY_PICO_REQUIRED_SDK_VERSION} is required; found ${PICO_SDK_VERSION_STRING}")
endif()

execute_process(
    COMMAND git -C "${PICO_SDK_PATH}" rev-parse HEAD
    OUTPUT_VARIABLE WSPRRY_PICO_ACTUAL_SDK_COMMIT
    OUTPUT_STRIP_TRAILING_WHITESPACE
    RESULT_VARIABLE WSPRRY_PICO_SDK_GIT_RESULT
)
if(NOT WSPRRY_PICO_SDK_GIT_RESULT EQUAL 0 OR
   NOT WSPRRY_PICO_ACTUAL_SDK_COMMIT STREQUAL WSPRRY_PICO_REQUIRED_SDK_COMMIT)
    message(FATAL_ERROR
        "Pico SDK commit ${WSPRRY_PICO_REQUIRED_SDK_COMMIT} is required; found ${WSPRRY_PICO_ACTUAL_SDK_COMMIT}")
endif()

execute_process(
    COMMAND git -C "${PICO_SDK_PATH}" status --porcelain --untracked-files=no
    OUTPUT_VARIABLE WSPRRY_PICO_SDK_STATUS
    OUTPUT_STRIP_TRAILING_WHITESPACE
    RESULT_VARIABLE WSPRRY_PICO_SDK_STATUS_RESULT
)
if(NOT WSPRRY_PICO_SDK_STATUS_RESULT EQUAL 0 OR NOT WSPRRY_PICO_SDK_STATUS STREQUAL "")
    message(FATAL_ERROR "The pinned Pico SDK checkout or its submodules contain local changes")
endif()

execute_process(
    COMMAND git -C "${PICO_SDK_PATH}/lib/tinyusb" rev-parse HEAD
    OUTPUT_VARIABLE WSPRRY_PICO_ACTUAL_TINYUSB_COMMIT
    OUTPUT_STRIP_TRAILING_WHITESPACE
    RESULT_VARIABLE WSPRRY_PICO_TINYUSB_GIT_RESULT
)
if(NOT WSPRRY_PICO_TINYUSB_GIT_RESULT EQUAL 0 OR
   NOT WSPRRY_PICO_ACTUAL_TINYUSB_COMMIT STREQUAL "86ad6e56c1700e85f1c5678607a762cfe3aa2f47")
    message(FATAL_ERROR "The Pico SDK TinyUSB submodule does not match the pinned revision")
endif()

if(NOT CMAKE_C_COMPILER_ID STREQUAL "GNU" OR
   NOT CMAKE_C_COMPILER_VERSION STREQUAL WSPRRY_PICO_REQUIRED_ARM_GCC_VERSION)
    message(FATAL_ERROR
        "Arm GNU Toolchain ${WSPRRY_PICO_REQUIRED_ARM_GCC_VERSION} is required; found ${CMAKE_C_COMPILER_ID} ${CMAKE_C_COMPILER_VERSION}")
endif()

# New linked networking components must match the SDK's recorded submodules.
foreach(component lwip cyw43-driver mbedtls)
    if(component STREQUAL "lwip")
        set(expected_revision "77dcd25a72509eb83f72b033d219b1d40cd8eb95")
    elseif(component STREQUAL "mbedtls")
        set(expected_revision "0bebf8b8c7f07abe3571ded48a11aa907a1ffb20")
    else()
        set(expected_revision "055d64274b014dd7b1c2fc94d26e8a18face7124")
    endif()
    set(component_path "${PICO_SDK_PATH}/lib/${component}")
    if(component STREQUAL "mbedtls")
        # The SDK permits an environment/cache override. Verify the linked input.
        set(component_path "${PICO_MBEDTLS_PATH}")
        execute_process(COMMAND git -C "${component_path}" status --porcelain --untracked-files=no
            OUTPUT_VARIABLE tls_status OUTPUT_STRIP_TRAILING_WHITESPACE RESULT_VARIABLE tls_status_result)
        if(NOT tls_status_result EQUAL 0 OR NOT tls_status STREQUAL "")
            message(FATAL_ERROR "The linked Mbed TLS checkout contains local changes")
        endif()
    endif()
    execute_process(COMMAND git -C "${component_path}" rev-parse HEAD
        OUTPUT_VARIABLE actual_revision OUTPUT_STRIP_TRAILING_WHITESPACE
        RESULT_VARIABLE revision_result)
    if(NOT revision_result EQUAL 0 OR NOT actual_revision STREQUAL expected_revision)
        message(FATAL_ERROR "The Pico SDK ${component} submodule does not match the pinned revision")
    endif()
endforeach()
