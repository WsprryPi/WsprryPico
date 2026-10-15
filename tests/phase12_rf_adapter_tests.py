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


@unittest.skipUnless(sys.platform.startswith('linux'), 'retained Linux C++ validation')
class AdapterTests(unittest.TestCase):
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

    def test_actual_dispatch_gate_and_console_batch(self):
        source = (ROOT / 'src/network/pico/bootstrap_server.cpp').read_text()
        header = (ROOT / 'src/network/pico/bootstrap_server.hpp').read_text()
        main = (ROOT / 'src/standalone/pico/main.cpp').read_text()
        start, end = block(source, 'void PicoBootstrapServer::dispatch(')
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
#include "network/consumer_radio.hpp"
#include <array>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
void check(bool v) { if (!v) throw std::runtime_error("adapter assertion"); }
using wsprrypico::network::ConsumerInterface;
using wsprrypico::network::WebAsset;
struct Request { std::string path="/", method="GET"; std::string_view header(std::string_view)const{return "192.168.4.1";} };
struct Parser { Request value; bool invalid=false; bool failed()const{return invalid;} const Request& request()const{return value;} };
struct HttpResponse {
 unsigned status; std::string body,type,etag,content_security_policy;
 std::string_view static_body; std::span<const std::string_view> static_parts;
 HttpResponse(unsigned code=200,std::string text={},std::string kind="application/json",std::string tag={})
  :status(code),body(std::move(text)),type(std::move(kind)),etag(std::move(tag)){}
 std::string wire_headers()const{return "headers";}
};
using Response=HttpResponse;
Response http_error(unsigned n,std::string_view s){return {n,std::string(s)};}
Response json(std::string s){return {200,std::move(s)};}
unsigned time_us_64(){return 1;}
bool owner_public_get_admitted(const Request&,const std::string&){return true;}
Response bootstrap_http_response(const Request&,const std::string&,const std::string&,bool setup,bool,bool){return {200,setup?"setup":"identity"};}
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
  ++handled;transaction=token;interface=source;handled_address=address;return {200,"radio-api"};
 }
};
struct Commit {bool allowed=true;bool cancellation_allowed()const{return allowed;}};
struct PicoBootstrapServer {
DEFAULT
 bool setup_admitted_=default_setup_admission,active_=true,mutation_safe_=true;
 bool ap_active_=false,station_active_=false,ap_setup_admitted_=false;
 ConsumerInterface client_interface_=ConsumerInterface::None;
 Radio* radio_=nullptr;Network* network_=nullptr;std::uint64_t radio_transaction_=17;
 bool pending=false;void (*setup_control_)(void*)=nullptr;void* setup_control_context_=nullptr;
 bool setup_pending()const{return pending;}
 bool owner_status_committed_reply_=false,owner_reconcile_=false,owner_restart_pending_=false;
 void* reset_begin_=nullptr; std::string device_="device",firmware_="firmware",headers_;
 Parser parser_;Response response_;Commit bootstrap_commit_;unsigned canceled=0,owner_canceled=0,advanced=0;
 Response recovery(const Request&){return {200,"recovery"};}
 Response status(){return {200,"status"};}
 Response mutation(const Request&){return {200,"mutation"};}
 Response owner_status(bool){return {200,"owner"};}
 Response owner_mutation(const Request&){return {200,"owner mutation"};}
 void cancel_slot(){++canceled;} void cancel_owner_slot(bool){++owner_canceled;}
 void dispatch() DISPATCH
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
 server.station_active_=true;server.parser_.invalid=true;server.dispatch();
 check(server.response_.status==400&&radio.handled==3);server.parser_.invalid=false;
 server.parser_.value.path="/";server.dispatch();check(server.response_.status==200);
 check(server.response_.static_body=="radio-inline"&&server.response_.static_parts.size()==2);
 check(server.response_.content_security_policy=="test-csp");
 radio.page_allowed=false;server.dispatch();check(server.response_.status==403);
 radio.page_allowed=true;radio.ready=false;server.dispatch();check(server.response_.status==403);
 radio.ready=true;asset_available=false;server.dispatch();check(server.response_.status==503);
 asset_available=true;server.client_interface_=ConsumerInterface::AccessPoint;
 server.parser_.value.path="/radio";server.dispatch();check(server.response_.status==200);
 server.parser_.value.path="/";server.dispatch();check(server.response_.body=="identity");
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
                        '-I' + str(ROOT / 'src'), str(path / 'adapter.cpp'),
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
