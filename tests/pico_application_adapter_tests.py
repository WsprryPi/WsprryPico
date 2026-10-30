"""Exercise actual adapter branches with Linux dependency doubles, no hardware."""
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def block(source, anchor):
    # Preserve offsets while ignoring braces in strings/comments.
    clean = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\\n])\'|//[^\n]*|/\*.*?\*/',
                   lambda m: ' ' * len(m[0]), source, flags=re.S)
    start = clean.index('{', source.index(anchor))
    depth = 1
    end = start + 1
    while depth:
        depth += (clean[end] == '{') - (clean[end] == '}')
        end += 1
    return start, end


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux C++ validation')
class AdapterTests(unittest.TestCase):
    def test_softap_association_cache_and_driver_error(self):
        source = (ROOT / 'src/provisioning/pico/field_platform.cpp').read_text()
        begin, end = block(source, 'bool PicoSoftAp::client_connected(')
        program = r'''
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
std::uint64_t now_ms=0;
std::uint64_t time_us_64(){return now_ms*1000;}
int cyw43_state=0, calls=0, result=0;
void cyw43_wifi_ap_get_stas(int*,int* count,std::uint8_t* mac){
 assert(*count==1);++calls;
 if(result<0)return; // SDK ensure-up error leaves input capacity untouched.
 *count=result;
 if(result)mac[0]=2;
}
struct PicoSoftAp {
 bool running_=false,clients_sampled_=false,client_connected_=false;
 std::uint64_t clients_sampled_ms_=0;
 bool client_connected(bool refresh=false) ACTUAL
};
int main(){
 PicoSoftAp ap;
 assert(!ap.client_connected()&&calls==0);
 ap.running_=true;
 assert(!ap.client_connected()&&calls==1);
 result=1;now_ms=999;
 assert(!ap.client_connected()&&calls==1);
 now_ms=1000;
 assert(ap.client_connected()&&calls==2);
 result=0;
 assert(!ap.client_connected(true)&&calls==3);
 result=-1;
 assert(!ap.client_connected(true)&&calls==4);
 ap.running_=false;
 assert(!ap.client_connected(true)&&calls==4);
}
'''.replace('ACTUAL', source[begin:end])
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory)
            (path / 'softap.cpp').write_text(program)
            built = subprocess.run(['c++', '-std=c++20', '-Wall', '-Wextra', '-Werror',
                                    str(path / 'softap.cpp'), '-o', str(path / 'softap')],
                                   capture_output=True, text=True, timeout=60)
            self.assertEqual(built.returncode, 0, built.stderr)
            subprocess.run([str(path / 'softap')], check=True, capture_output=True, timeout=10)

    def test_console_status_observation_precedes_profile_control_guard(self):
        source = (ROOT / 'src/standalone/pico/main.cpp').read_text()
        start = source.index('        if (text == "STATUS")')
        end = source.index('        if (text.starts_with("HEAP PROBE "))', start)
        actual = source[start:end]
        # Compile the actual target routing and guard, including all combinations
        # of consumer selection, pending ownership and absent runtime authority.
        program = r'''
#include <string>
#include <string_view>
#include <stdexcept>
struct Scheduler { unsigned reads=0; std::string status(){++reads;return "observed";} } scheduler;
struct Bootstrap { bool pending=false; bool owner_claim_pending(){return pending;} } bootstrap;
bool consumer=false, ready=false;
bool consumer_source_selected(){return consumer;}
bool runtime_profile_ready(){return ready;}
std::string command(std::string_view text) { ACTUAL return "control"; }
int main() {
 for(unsigned flags=0;flags<8;++flags) {
  consumer=flags&1; bootstrap.pending=flags&2; ready=flags&4;
  if(command("STATUS")!="observed") return 1;
  const bool blocked=consumer||bootstrap.pending||!ready;
  for(auto text:{"STOP","CONFIG {}","WIFI OFF","STATUS extra"}) {
   const auto result=command(text);
   if(blocked ? result.find("profile_runtime_unavailable")==std::string::npos : result!="control") return 2;
  }
  for(auto text:{"ABORT","REBOOT","BOOTSEL","ACCESS SOFTAP device"})
   if(command(text)!="control") return 3;
 }
 if(scheduler.reads!=8) return 4;
}
'''.replace('ACTUAL', actual)
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory)
            (path / 'status.cpp').write_text(program)
            subprocess.run(['c++', '-std=c++20', '-Wall', '-Wextra', '-Werror',
                            str(path / 'status.cpp'), '-o', str(path / 'status')],
                           check=True, capture_output=True, timeout=60)
            subprocess.run([str(path / 'status')], check=True, capture_output=True, timeout=10)
        command_start = source.index('    auto command =')
        self.assertLess(source.index('if (reset_coordinator.blocks_admission()', command_start), start)

    def test_actual_indicator_poll_selects_transmit_gate_only_for_rf(self):
        main = (ROOT / 'src/standalone/pico/main.cpp').read_text()
        begin, end = block(main, 'const auto poll_indicator =')
        actual = main[begin:end]
        # The adapter now routes RF indication through the already tested
        # TransmitIndicatorGate. Compile its actual branch rather than the
        # removed inline acceptance-cue branch; no hardware assertion changes.
        program = r'''
#include <cstdint>
#include <stdexcept>
std::uint64_t time_us_64(){return 123000;}
int tx_indicator_gate=7;
struct Indicator {
 unsigned rf=0, dry=0, polled=0;
 void poll_transmit(int gate,std::uint64_t now){if(gate!=7||now!=123)throw std::runtime_error("gate");++rf;}
 void transmitting(bool active){if(active)throw std::runtime_error("dry TX");++dry;}
 void poll(std::uint64_t now){if(now!=123)throw std::runtime_error("time");++polled;}
} indicator;
int main(){
 auto poll_indicator=[&]() ACTUAL;
 poll_indicator();
#ifdef WSPRRY_PICO_STANDALONE_RF
 if(indicator.rf!=1||indicator.dry||indicator.polled) return 1;
#else
 if(indicator.rf||indicator.dry!=1||indicator.polled!=1) return 2;
#endif
}
'''.replace('ACTUAL', actual)
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory)
            (path / 'indicator.cpp').write_text(program)
            for definitions in ([], ['-DWSPRRY_PICO_STANDALONE_RF=1'],
                                ['-DWSPRRY_PICO_STANDALONE_RF=1',
                                 '-DWSPRRY_PICO_GP14_RF_ACCEPTANCE=1']):
                built = subprocess.run(['c++', '-std=c++20', '-Wall', '-Wextra', '-Werror',
                                str(path / 'indicator.cpp'), '-o', str(path / 'indicator'), *definitions],
                               capture_output=True, text=True, timeout=60)
                self.assertEqual(built.returncode, 0, built.stderr)
                subprocess.run([str(path / 'indicator')], check=True, capture_output=True, timeout=10)

    def test_radio_context_refresh_without_http_dispatch(self):
        source = (ROOT / 'src/network/pico/bootstrap_server.cpp').read_text()
        poll_start = source.index('void PicoBootstrapServer::poll(')
        begin, end = block(source[poll_start:], 'if (radio_)')
        actual = source[poll_start:][begin:end]
        program = r'''
#include <cstdint>
#include <string>
#include <stdexcept>
std::uint64_t time_us_64(){return 1000;}
struct Network {
 std::string address="192.168.1.53", name="pico.local";
 std::string ipv4(){return address;} std::string configured_hostname(){return name;}
};
struct Radio {
 unsigned refreshes=0, polls=0, closed=0; bool ap=true; std::string ip,host;
 void listeners(bool a,std::string i,std::string h){++refreshes;ap=a;ip=i;host=h;}
 void poll(std::uint64_t){if(refreshes!=polls+1)throw std::runtime_error("stale context");++polls;}
 void close(){++closed;}
};
int main(){
 Radio radio;Network network;auto* radio_=&radio;auto* network_=&network;
 bool ap_active_=false,station_active_=true,active_=true;
 const auto poll=[&]() ACTUAL;
 poll(); if(radio.ap||radio.ip!=network.address||radio.host!=network.name||radio.closed)return 1;
 ap_active_=true;network.address="192.168.1.54";poll();
 if(!radio.ap||radio.ip!=network.address||radio.closed)return 2;
 station_active_=false;active_=false;poll();
 if(!radio.ip.empty()||radio.closed!=1)return 3;
}
'''.replace('ACTUAL', actual)
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory)
            (path / 'contexts.cpp').write_text(program)
            built = subprocess.run(['c++', '-std=c++20', '-Wall', '-Wextra', '-Werror',
                                    str(path / 'contexts.cpp'), '-o', str(path / 'contexts')],
                                   capture_output=True, text=True, timeout=60)
            self.assertEqual(built.returncode, 0, built.stderr)
            subprocess.run([str(path / 'contexts')], check=True, capture_output=True, timeout=10)

    def test_actual_setup_receipts_are_transaction_scoped(self):
        source = (ROOT / 'src/network/pico/bootstrap_server.cpp').read_text()
        methods = []
        for anchor in ('void PicoBootstrapServer::setup_delivered(',
                       'void PicoBootstrapServer::remember_setup_reply('):
            start, end = block(source, anchor)
            methods.append(source[start:end])
        conditions = []
        for anchor in ('if (bootstrap_trial_start_pending_ && bootstrap_submit_delivered_',
                       'if (owner_trial_start_pending_ &&',
                       'if (!setup_transaction_ && bootstrap_restart_pending_',
                       'if (!setup_transaction_ && owner_restart_pending_'):
            start = source.index('(', source.index(anchor))
            end, depth = start + 1, 1
            while depth:
                depth += (source[end] == '(') - (source[end] == ')')
                end += 1
            conditions.append(source[start:end])
        program = r"""
#include <cstdint>
#include <stdexcept>
#include <string>
struct HttpRequest {std::string path;};
unsigned time_us_64(){return 123000;}
void check(bool v){if(!v)throw std::runtime_error("receipt isolation");}
struct Server {
 std::string setup_reply_path_;
 std::uint64_t setup_transaction_=0,bootstrap_submit_delivered_ms_=0;
 bool setup_owner_status_committed_=false,owner_status_committed_reply_=false;
 bool bootstrap_trial_start_pending_=true,bootstrap_submit_delivered_=false;
 bool owner_trial_start_pending_=true,owner_submit_delivered_=false,bootstrap_ack_delivered_=false;
 unsigned canceled=0,owner_canceled=0;
 struct Restart {
  unsigned calls=0;void delivered(bool ok,unsigned now){check(ok&&now==123);++calls;}
  bool ready(unsigned)const{return true;}
 } owner_result_restart_;
 struct Commit {bool reconcile()const{return false;}bool restart_due(unsigned)const{return true;}} bootstrap_commit_;
 bool bootstrap_restart_pending_=true,owner_restart_pending_=true,restart_=true;
 unsigned bootstrap_committed_ms_=0,now_ms=5000,restart_now_ms=65000;
 // No TCP connection state exists in this fixture. Unrelated sockets cannot gate these actions.
 bool trial_ready()const{return TRIAL;}
 bool owner_ready()const{return OWNER;}
 bool restart_ready()const{return RESTART;}
 bool owner_restart_ready()const{return OWNER_RESTART;}
 void cancel_slot(){++canceled;}void cancel_owner_slot(bool restore){check(restore);++owner_canceled;}
 void setup_delivered(std::uint64_t transaction,bool apply) DELIVER
 void remember_setup_reply(const HttpRequest& request,std::uint64_t transaction) REMEMBER
};
int main(){
 Server s;
 s.remember_setup_reply({"/api/bootstrap/v1/status"},11);check(s.setup_transaction_==0);
 s.remember_setup_reply({"/api/bootstrap/v1/submit"},12);
 s.setup_delivered(0,true);s.setup_delivered(11,true);s.setup_delivered(13,false);
 check(!s.bootstrap_submit_delivered_&&s.canceled==0&&s.setup_transaction_==12);
 s.setup_delivered(12,true);check(s.bootstrap_submit_delivered_&&s.bootstrap_submit_delivered_ms_==123);
 s.setup_delivered(12,false);check(s.canceled==0&&s.setup_transaction_==0);
 s.remember_setup_reply({"/api/bootstrap/v1/submit"},14);s.setup_delivered(14,false);
 check(s.canceled==1&&s.setup_transaction_==0);
 s.remember_setup_reply({"/api/owner/v1/claim/submit"},15);s.setup_delivered(16,true);
 check(!s.owner_submit_delivered_);s.setup_delivered(15,false);check(s.owner_canceled==1);
 s.remember_setup_reply({"/api/owner/v1/claim/submit"},17);s.setup_delivered(17,true);
 check(s.owner_submit_delivered_);
 s.remember_setup_reply({"/api/bootstrap/v1/ack"},18);s.setup_delivered(19,true);
 check(!s.bootstrap_ack_delivered_);s.setup_delivered(18,true);check(s.bootstrap_ack_delivered_);
 s.owner_status_committed_reply_=true;s.remember_setup_reply({"/api/owner/v1/claim/status"},20);
 s.owner_status_committed_reply_=false; // Another tab dispatches an unrelated static page.
 s.setup_delivered(19,true);check(s.owner_result_restart_.calls==0);
 s.setup_delivered(20,true);check(s.owner_result_restart_.calls==1);
 s.setup_delivered(20,true);check(s.owner_result_restart_.calls==1);
 s.remember_setup_reply({"/api/owner/v1/claim/status"},21);check(s.setup_transaction_==0);
 check(s.trial_ready()&&s.owner_ready()&&s.restart_ready()&&s.owner_restart_ready());
 s.setup_transaction_=22;
 check(!s.trial_ready()&&!s.owner_ready()&&!s.restart_ready()&&!s.owner_restart_ready());
}
""".replace('DELIVER', methods[0]).replace('REMEMBER', methods[1])
        # Replace the longer marker first, keeping OWNER out of OWNER_RESTART.
        for key, condition in zip(('TRIAL', 'OWNER', 'RESTART', 'OWNER_RESTART'), conditions):
            program = program.replace('return ' + key + ';', 'return ' + condition + ';')
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory)
            (path / 'receipts.cpp').write_text(program)
            built = subprocess.run(['c++', '-std=c++20', '-Wall', '-Wextra', '-Werror',
                                    str(path / 'receipts.cpp'), '-o', str(path / 'receipts')],
                                   capture_output=True, text=True, timeout=60)
            self.assertEqual(built.returncode, 0, built.stderr)
            subprocess.run([str(path / 'receipts')], check=True, capture_output=True, timeout=10)

    def test_actual_dispatch_gate_and_console_batch(self):
        source = (ROOT / 'src/network/pico/bootstrap_server.cpp').read_text()
        header = (ROOT / 'src/network/pico/bootstrap_server.hpp').read_text()
        main = (ROOT / 'src/standalone/pico/main.cpp').read_text()
        start, end = block(source, 'HttpResponse PicoBootstrapServer::dispatch(')
        dispatch = source[start:end]
        default = re.search(r'#ifdef WSPRRY_PICO_STANDALONE_RF\s+'
                            r'static constexpr bool default_setup_admission = false;.*?#endif',
                            header, re.S)[0]
        begin, finish = block(source, 'if (!setup_admitted_)')
        denied = source[begin:finish]
        # Locate the else adjacent to this exact admission check, not an
        # unrelated branch elsewhere in the server.
        clean_tail = source[finish:]
        self.assertRegex(clean_tail, r'^\s*else\s*\{')
        relative_begin, relative_end = block(clean_tail, 'else')
        allowed = clean_tail[relative_begin:relative_end]
        poll_begin, poll_end = block(source, 'void PicoBootstrapServer::poll(')
        poll = source[poll_begin:poll_end]
        for action in ('bootstrap_commit_.commit(', 'commit_consumer_claim(',
                       'start_bootstrap_trial(', 'restart_(restart_context_)'):
            self.assertIn(action, allowed)
            self.assertTrue(action not in poll.replace(allowed, ''), action + ' outside gate')
        read_anchor = 'while (!reboot_at && !console_reply.pending()'
        _, read_end = block(main, read_anchor)
        reader = '{\n' + main[main.index(read_anchor):read_end] + '\n}'
        program = r'''
#include "usb/console_reply.hpp"
#include "network/assets.hpp"
#include "network/control.hpp"
#include "network/consumer_radio.hpp"
#include "wtp/json.hpp"
#include <array>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
void check_at(bool v,int line) { if (!v) throw std::runtime_error("adapter assertion line " + std::to_string(line)); }
#define check(v) check_at((v),__LINE__)
using wsprrypico::network::ConsumerInterface;
using wsprrypico::network::WebAsset;
namespace wtp = wsprrypico::wtp;
struct Request { std::string path="/", method="GET"; std::string_view header(std::string_view)const{return "192.168.4.1";} };
struct Parser { Request value; bool invalid=false; bool failed()const{return invalid;} const Request& request()const{return value;} };
using wsprrypico::network::HttpResponse;
using wsprrypico::network::control_response;
using wsprrypico::network::http_error;
using Response=HttpResponse;
namespace wsprrypico::network { std::string_view web_csp(){return "test-csp";} }
Response json(std::string s){return {200,std::move(s),"application/json",{}};}
unsigned time_us_64(){return 1;}
bool owner_public_get_admitted(const Request&,const std::string&){return true;}
Response bootstrap_http_response(const Request&,const std::string&,const std::string&,bool setup,bool,bool){return {200,setup?"setup":"identity","application/json",{}};}
bool asset_available=true;
std::array<std::string_view,2> radio_parts={"radio-","page"};
std::optional<WebAsset> consumer_radio_asset(){
 if(!asset_available)return {};
 return WebAsset{"radio-inline","text/html",radio_parts};
}
std::string_view consumer_radio_csp(){return "test-csp";}
struct Network {
 std::string address="192.0.2.10",hostname="pico-test.local";
 const std::string& ipv4()const{return address;}
 const std::string& configured_hostname()const{return hostname;}
};
struct Radio {
 bool ready=true,page_allowed=true,seen_ap=false;
 unsigned refreshed=0,handled=0; std::uint64_t transaction=0;
 ConsumerInterface interface=ConsumerInterface::None;
 std::string address,hostname,handled_address;
 void listeners(bool ap,std::string_view ip,std::string_view name){
  ++refreshed;seen_ap=ap;address=ip;hostname=name;
 }
 bool available()const{return ready;}
 bool page_admitted(const Request&,ConsumerInterface)const{return page_allowed;}
 Response handle(const Request&,std::uint64_t,std::uint64_t token,ConsumerInterface source){
  ++handled;transaction=token;interface=source;handled_address=address;return {200,"radio-api","application/json",{}};
 }
};
struct Commit {bool allowed=true;bool cancellation_allowed()const{return allowed;}};
struct Progress {
 bool station_only=false,drive=false,amplifier=false;
 Response progress_readback(bool station,bool gpio,bool amp){
  station_only=station;drive=gpio;amplifier=amp;
  return {200,R"({"schema":"progress"})","application/json",{}};
 }
};
struct PicoBootstrapServer {
DEFAULT
 bool setup_admitted_=default_setup_admission,active_=true,mutation_safe_=true;
 bool ap_active_=false,station_active_=false,ap_setup_admitted_=false;
 ConsumerInterface client_interface_=ConsumerInterface::None;
 Radio* radio_=nullptr;Network* network_=nullptr;std::uint64_t radio_transaction_=17;
 bool pending=false;void (*setup_control_)(void*)=nullptr;void* setup_control_context_=nullptr;
 bool setup_pending()const{return pending;}
 bool owner_status_committed_reply_=false,owner_reconcile_=false,owner_restart_pending_=false;
 void* reset_begin_=nullptr; std::string device_="device",boot_id_="boot",firmware_="firmware",headers_;
 Progress* progress_api_=nullptr;bool owner_claimable()const{return true;}
 Parser parser_;Response response_;Commit bootstrap_commit_;unsigned canceled=0,owner_canceled=0,advanced=0;
 Response recovery(const Request&){return {200,"recovery","application/json",{}};}
 Response status(){return {200,"status","application/json",{}};}
 Response mutation(const Request&){return {200,"mutation","application/json",{}};}
 Response owner_status(bool){return {200,"owner","application/json",{}};}
 Response owner_mutation(const Request&){return {200,"owner mutation","application/json",{}};}
 void cancel_slot(){++canceled;} void cancel_owner_slot(bool){++owner_canceled;}
 std::uint64_t setup_transaction_=0;
 void remember_setup_reply(const Request&,std::uint64_t){}
 Response dispatch_request(const Request& request,ConsumerInterface client_interface_,std::uint64_t radio_transaction_) DISPATCH
 void dispatch(){response_=dispatch_request(parser_.request(),client_interface_,radio_transaction_);}

 void advance(bool mutation_safe) {
  mutation_safe_=mutation_safe&&setup_admitted_;
  if (!setup_admitted_) DENIED else {++advanced;}
 }
};
int main() {
 PicoBootstrapServer server;
#ifdef WSPRRY_PICO_STANDALONE_RF
 check(!server.setup_admitted_);
#else
 check(server.setup_admitted_);
#endif
 server.client_interface_=ConsumerInterface::AccessPoint;server.ap_active_=true;
 server.setup_admitted_=false;server.dispatch();check(server.response_.body=="identity");
 for (auto path:{"/api/bootstrap/v1/status","/api/bootstrap/v1/submit","/api/owner/v1/claim/submit"}) {
  server.parser_.value.path=path;server.dispatch();check(server.response_.status==409);
 }
 server.parser_.value.path="/api/recovery/v1/status";server.dispatch();check(server.response_.body=="recovery");
 server.advance(true);check(server.advanced==0&&server.canceled==1&&server.owner_canceled==1&&!server.mutation_safe_);
 server.bootstrap_commit_.allowed=false;server.owner_reconcile_=true;
 server.advance(true);check(server.advanced==0&&server.canceled==1&&server.owner_canceled==1);
 server.setup_admitted_=true;server.ap_setup_admitted_=true;
 server.parser_.value.path="/";server.dispatch();check(server.response_.body=="setup");
 server.parser_.value.path="/api/bootstrap/v1/status";server.dispatch();check(server.response_.body=="status");
 server.advance(true);check(server.advanced==1&&server.mutation_safe_);
 // Station availability must not admit AP-only provisioning or recovery.
 server.ap_setup_admitted_=false;server.station_active_=true;
 server.parser_.value.path="/api/bootstrap/v1/submit";server.dispatch();check(server.response_.status==409);
 server.client_interface_=ConsumerInterface::Station;
 for(auto path:{"/api/bootstrap/v1/status","/api/owner/v1/public-status","/api/recovery/v1/status","/"}){
  server.parser_.value.path=path;server.dispatch();check(server.response_.status==403);
 }
 Radio radio;Network network;server.radio_=&radio;server.network_=&network;
 server.parser_.value.path="/api/consumer/v1/identity";server.dispatch();
 check(server.response_.body=="radio-api"&&radio.handled==1&&radio.transaction==17);
 check(radio.interface==ConsumerInterface::Station&&radio.seen_ap&&radio.address==network.address);
 check(radio.hostname==network.hostname&&radio.handled_address==network.address);
 network.address="192.0.2.20";server.dispatch();
 check(radio.handled_address==network.address);
 server.station_active_=false;server.dispatch();check(radio.handled_address.empty());
 server.station_active_=true;
 server.parser_.value.path="/";server.dispatch();check(server.response_.status==200);
 check(server.response_.static_body=="radio-inline"&&server.response_.static_parts.size()==2);
 check(server.response_.content_security_policy=="test-csp");
 radio.page_allowed=false;server.dispatch();check(server.response_.status==403);
 radio.page_allowed=true;radio.ready=false;server.dispatch();check(server.response_.status==403);
 radio.ready=true;asset_available=false;server.dispatch();check(server.response_.status==503);
 asset_available=true;server.client_interface_=ConsumerInterface::AccessPoint;
 server.parser_.value.path="/radio";server.dispatch();check(server.response_.status==200);
 server.parser_.value.path="/";server.dispatch();
 check(server.response_.status==302&&server.response_.location=="/wifi-host");
 server.setup_transaction_=31;server.parser_.value.path="/api/bootstrap/v1/status";
 server.dispatch();check(server.response_.status==409&&server.response_.body==R"({"error":{"code":"setup_response_pending"}})");
 server.parser_.value.path="/radio";server.dispatch();check(server.response_.status==200);
 server.parser_.value.path="/api/consumer/v1/identity";server.dispatch();check(server.response_.body=="radio-api");
 server.setup_transaction_=0;
 server.ap_setup_admitted_=true;
 Progress progress;server.progress_api_=&progress;
 server.parser_.value.path="/api/owner/v1/progress";server.dispatch();
 check(server.response_.status==200&&progress.station_only&&progress.drive&&progress.amplifier);
 check(server.response_.body==R"({"contract":"Wsprry-Control/1","schema":"progress"})");
 server.parser_.value.path="/api/consumer/v1/identity";
 server.pending=true;unsigned paused=0;server.setup_control_context_=&paused;
 server.setup_control_=[](void* context){++*static_cast<unsigned*>(context);};
 server.dispatch();check(paused==1);
 wsprrypico::usb::ConsoleReply console_reply;std::array<std::uint8_t,64> console_input{};
 const std::string input="FIRST\nSECOND\n";std::copy(input.begin(),input.end(),console_input.begin());
 std::size_t console_input_offset=0,console_input_size=input.size(),length=0;
 std::array<char,256> line{};bool overflow=false;unsigned reboot_at=0,calls=0;
 auto command=[&](std::string_view text)->wsprrypico::usb::ConsoleResponse{++calls;return std::string(text)+std::string(9000,'x')+"\n";};
 auto consume=[&]() READER;
 consume();check(calls==1&&console_input_offset==6&&console_reply.pending());
 consume();check(calls==1&&console_input_offset==6);
 while(console_reply.pending()) console_reply.poll([](std::string_view){return true;});
 consume();check(calls==2&&console_input_offset==input.size());
 console_reply.reset();check(!console_reply.pending());
 std::cout<<"actual adapter branches passed\n";
}
'''
        for name, value in [('DEFAULT', default), ('DISPATCH', dispatch), ('DENIED', denied),
                            ('READER', reader)]:
            program = program.replace(name, value)
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory)
            (path / 'adapter.cpp').write_text(program)
            for rf in (False, True):
                args = ['c++', '-std=c++20', '-Wall', '-Wextra', '-Werror',
                        '-I' + str(ROOT / 'src/microchrony'),
                        '-I' + str(ROOT / 'src'), str(path / 'adapter.cpp'),
                        str(ROOT / 'src/wtp/json.cpp'), str(ROOT / 'src/network/http.cpp'),
                        '-o', str(path / 'adapter')]
                if rf:
                    args.append('-DWSPRRY_PICO_STANDALONE_RF=1')
                built = subprocess.run(args, capture_output=True, text=True, timeout=60)
                self.assertEqual(built.returncode, 0, built.stderr)
                result = subprocess.run([str(path / 'adapter')],
                                        capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('actual adapter branches passed', result.stdout)


if __name__ == '__main__':
    unittest.main()
