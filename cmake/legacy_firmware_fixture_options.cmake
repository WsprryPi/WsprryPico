# An old diagnostic request must never silently become an ordinary RF build.
# Disabled defaults may remain in an existing CMake cache.
if(DEFINED WSPRRY_PICO_PHASE12_FAULT_STAGE AND
   NOT "${WSPRRY_PICO_PHASE12_FAULT_STAGE}" STREQUAL "0")
    message(FATAL_ERROR
        "Active obsolete WSPRRY_PICO_PHASE12_FAULT_STAGE: use WSPRRY_PICO_JOURNAL_FAULT_STAGE and remove the old cache setting")
endif()

foreach(_wsprry_fixture_mapping IN ITEMS
        "WSPRRY_PICO_PHASE12_INDICATOR_FAULT_FIXTURE|WSPRRY_PICO_INDICATOR_FAULT_FIXTURE"
        "WSPRRY_PICO_PHASE12_PHYSICAL_CUT_FIXTURE|WSPRRY_PICO_JOURNAL_POWER_CUT_FIXTURE"
        "WSPRRY_PICO_PHASE12_SESSION_DEADLINE_FIXTURE|WSPRRY_PICO_SESSION_DEADLINE_FIXTURE")
    string(REPLACE "|" ";" _wsprry_fixture_mapping "${_wsprry_fixture_mapping}")
    list(GET _wsprry_fixture_mapping 0 _wsprry_fixture_legacy)
    list(GET _wsprry_fixture_mapping 1 _wsprry_fixture_current)
    if(DEFINED ${_wsprry_fixture_legacy} AND ${_wsprry_fixture_legacy})
        message(FATAL_ERROR
            "Active obsolete ${_wsprry_fixture_legacy}: use ${_wsprry_fixture_current} and remove the old cache setting")
    endif()
endforeach()
unset(_wsprry_fixture_mapping)
unset(_wsprry_fixture_legacy)
unset(_wsprry_fixture_current)
