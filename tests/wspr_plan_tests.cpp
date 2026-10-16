#include "encoding/wspr.hpp"
#include "wspr_oracle_vectors.hpp"
#include "wspr_plan_vectors.hpp"

#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <string>
using namespace wsprrypico::encoding;
#define CHECK(condition)                                                                           \
    do {                                                                                           \
        if (!(condition)) {                                                                        \
            std::cerr << __LINE__ << ": " #condition "\n";                                         \
            std::exit(1);                                                                          \
        }                                                                                          \
    } while (false)
int main() {
    for (const auto& v : vectors) {
        const auto plan = wspr_plan(v.call, v.grid, v.power);
        CHECK(plan && plan->count == 1 && unsigned(plan->frames[0].type) == v.type);
        CHECK(plan->frames[0].payload < (1ULL << 50));
        CHECK(wspr_channel(plan->frames[0].payload) == plan->frames[0].symbols);
        for (unsigned i = 0; i < 162; ++i)
            CHECK(plan->frames[0].symbols[i] == unsigned(v.symbols[i] - '0'));
    }
    for (const auto call : {"AA0NT/1", "AA0NT/12", "W0/AA0NT", "PJ4/AA0NT", "AA0NT/P", "AA0NT/M"}) {
        const auto single = wspr_plan(call, "EM18", 37), pair = wspr_plan(call, "EM18IG", 37);
        const auto hashed = wspr_plan("<" + std::string(call) + ">", "EM18IG", 37);
        CHECK(single && single->count == 1 && single->frames[0].type == WsprType::Type2);
        CHECK(pair && pair->count == 2 && pair->frames[0].symbols == single->frames[0].symbols);
        CHECK(hashed && hashed->count == 1 && hashed->frames[0].type == WsprType::Type3);
        CHECK(pair->frames[1].symbols == hashed->frames[0].symbols);
    }
    CHECK(wspr_plan("AA0NT", "EM18IG", 20)->frames[0].symbols == *wspr_type1("AA0NT", "EM18", 20));
    for (const auto call :
         {"", "<>", "<AA0NT", "AA0NT>", "<<AA0NT>>", "<AA0NT>/P", "AA0NT//P", "AA0NT/", "/AA0NT",
          "AA0NT/P/M", "AA0NT/ABC", "ABCD/AA0NT", "NOTACALL", "AA0NT/p", "AA0NT P", "AA0NT\n",
          "<AA0NT/P/M>", "PJ4/AA0NTXXX", "<PJ4/AA0NTXXX>"})
        CHECK(!wspr_plan(call, "EM18IG", 20));
    CHECK(!wspr_plan(std::string_view("AA0NT\0X", 7), "EM18IG", 20));
    for (const auto grid : {"", "EM1", "EM18I", "EM18IGX", "SM18IG", "EM18IY", "EM18ig", "EMAAIG"})
        CHECK(!wspr_plan("AA0NT/P", grid, 20));
    CHECK(!wspr_plan("<AA0NT>", "EM18", 20));
    CHECK(wspr_plan("AA0NT/Z", "EM18", 20));
    CHECK(wspr_plan("AA0NT/00", "EM18", 20));
    const auto zero9 = wspr_plan("AA0NT/09", "EM18IG", 20), z = wspr_plan("AA0NT/Z", "EM18IG", 20);
    CHECK(zero9 && z && zero9->type2_ambiguous && z->type2_ambiguous);
    CHECK(zero9->frames[0].symbols == z->frames[0].symbols);
    CHECK(zero9->frames[1].symbols != z->frames[1].symbols);
    CHECK(std::string_view(zero9->alternate_call.data(), zero9->alternate_length) == "AA0NT/Z");
    CHECK(std::string_view(z->alternate_call.data(), z->alternate_length) == "AA0NT/09");
    for (const auto power : {1U, 21U, 61U, std::numeric_limits<unsigned>::max()})
        CHECK(!wspr_plan("AA0NT/P", "EM18IG", power));
    CHECK(valid_station_details("AA0NT/P/M", "EM18IG", 20)); // Legacy storage, unsupported plan.
    CHECK(valid_station_details("<PJ4/AA0NT>", "EM18IG", 20));
    CHECK(wspr_plan("<PJ4/AA0NT>", "EM18IG", 20));
    for (const auto& v : oracle_vectors) {
        const auto plan = wspr_plan(v.call, v.grid, v.power);
        if (!v.accepted) {
            CHECK(!plan);
            continue;
        }
        CHECK(plan && unsigned(plan->frames[0].type) == v.type);
        CHECK(plan->frames[0].payload == v.payload);
        for (unsigned i = 0; i < 162; ++i)
            CHECK(plan->frames[0].symbols[i] == unsigned(v.symbols[i] - '0'));
    }
    for (const auto& h : hash_vectors)
        CHECK(wspr_hash(h.text) == h.hash);
    // Every hash tail/alignment, including exact-allocation string views.
    for (unsigned length = 0; length <= 32; ++length) {
        const std::string call = std::string("A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6").substr(0, length);
        const auto expected = wspr_hash(call);
        for (unsigned offset = 0; offset < 8; ++offset) {
            const auto storage = std::string(offset, '!') + call;
            CHECK(wspr_hash(std::string_view(storage).substr(offset)) == expected);
        }
    }
    // Stateless reuse across long/short calls and all formats.
    for (unsigned i = 0; i < 100; ++i)
        for (const auto& v : vectors) {
            const auto plan = wspr_plan(v.call, v.grid, v.power);
            for (unsigned j = 0; j < 162; ++j)
                CHECK(plan->frames[0].symbols[j] == unsigned(v.symbols[j] - '0'));
        }
    std::cout
        << "WSPR planner: fixed symbols, complete plans, refusal, hash tails and reuse passed\n";
}
