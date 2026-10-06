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
    def test_actual_acceptance_cue_has_priority_during_rf(self):
        main = (ROOT / 'src/standalone/pico/main.cpp').read_text()
        begin = main.index('#ifdef WSPRRY_PICO_GP14_RF_ACCEPTANCE',
                           main.index('indicator.softap_ready('))
        end = main.index('indicator.poll(field_now_ms);', begin)
        cue = main[begin:end]
        field = (ROOT / 'src/provisioning/field_runtime.cpp').read_text()
        elapsed_begin, elapsed_end = block(field, 'bool elapsed(')
        elapsed = field[field.index('bool elapsed('):elapsed_end]
        actual = field[field.index('IndicatorCode IndicatorController::identify('):
                       field.rindex('} // namespace')]
        program = r'''
#include "provisioning/field_runtime.hpp"
#include <array>
#include <stdexcept>
namespace wsprrypico::provisioning { ELAPSED ACTUAL }
using Pattern=wsprrypico::provisioning::IndicatorPattern;
struct Engine { bool active=false; bool output_active()const{return active;} } engine;
struct Output:wsprrypico::provisioning::IndicatorOutput {
 bool value=false; bool write(bool v)override{value=v;return true;}
} output;
wsprrypico::provisioning::IndicatorController indicator(output,"device");
void update(std::uint64_t field_now_ms){
CUE
 indicator.poll(field_now_ms);
}
int main(){
 engine.active=true;indicator.softap_ready(true);
 if(indicator.identify("cue","device",true,true,0)!=wsprrypico::provisioning::IndicatorCode::Ok)
  throw std::runtime_error("cue refused");
 for(auto tick:std::array<std::uint64_t,16>{0,149,150,299,300,449,450,599,600,749,750,1999,2000,9999,10000,10150}){
  update(tick);
#ifdef WSPRRY_PICO_GP14_RF_ACCEPTANCE
  const auto phase=tick%2000;
  const bool expected=tick>=10000||phase<150||(phase>=300&&phase<450)||(phase>=600&&phase<750);
#else
  const bool expected=true;
#endif
  if(output.value!=expected) throw std::runtime_error("acceptance cue masked or wrong edge");
 }
 engine.active=false;update(10600);
 if(output.value||indicator.status(10600).pattern!=Pattern::SoftApReady)
  throw std::runtime_error("expired cue did not return to setup pattern");
}
'''.replace('CUE', cue).replace('ELAPSED', elapsed).replace('ACTUAL', actual)
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory)
            (path / 'cue.cpp').write_text(program)
            for definitions in ([], ['-DWSPRRY_PICO_STANDALONE_RF=1'],
                                ['-DWSPRRY_PICO_STANDALONE_RF=1',
                                 '-DWSPRRY_PICO_GP14_RF_ACCEPTANCE=1']):
                built = subprocess.run(['c++', '-std=c++20', '-Wall', '-Wextra', '-Werror',
                                '-I' + str(ROOT / 'src'),
                                str(path / 'cue.cpp'), '-o', str(path / 'cue'), *definitions],
                               capture_output=True, text=True, timeout=60)
                self.assertEqual(built.returncode, 0, built.stderr)
                subprocess.run([str(path / 'cue')], check=True, capture_output=True, timeout=10)

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
#include <array>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
void check(bool v) { if (!v) throw std::runtime_error("adapter assertion"); }
struct Request { std::string path="/", method="GET"; std::string_view header(std::string_view)const{return "192.168.4.1";} };
struct Parser { Request value; bool failed()const{return false;} const Request& request()const{return value;} };
struct Response { unsigned status=200; std::string body; std::string wire_headers()const{return "headers";} };
Response http_error(unsigned n,std::string_view s){return {n,std::string(s)};}
Response json(std::string s){return {200,std::move(s)};}
unsigned time_us_64(){return 1;}
bool owner_public_get_admitted(const Request&,const std::string&){return true;}
Response bootstrap_http_response(const Request&,const std::string&,const std::string&,bool setup,bool,bool){return {200,setup?"setup":"identity"};}
struct Commit {bool allowed=true;bool cancellation_allowed()const{return allowed;}};
struct PicoBootstrapServer {
DEFAULT
 bool setup_admitted_=default_setup_admission,active_=true,mutation_safe_=true;
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
 server.setup_admitted_=false;server.dispatch();check(server.response_.body=="identity");
 for (auto path:{"/api/bootstrap/v1/status","/api/bootstrap/v1/submit","/api/owner/v1/claim/submit"}) {
  server.parser_.value.path=path;server.dispatch();check(server.response_.status==409);
 }
 server.parser_.value.path="/api/recovery/v1/status";server.dispatch();check(server.response_.body=="recovery");
 server.advance(true);check(server.advanced==0&&server.canceled==1&&server.owner_canceled==1&&!server.mutation_safe_);
 server.bootstrap_commit_.allowed=false;server.owner_reconcile_=true;
 server.advance(true);check(server.advanced==0&&server.canceled==1&&server.owner_canceled==1);
 server.setup_admitted_=true;server.parser_.value.path="/";server.dispatch();check(server.response_.body=="setup");
 server.parser_.value.path="/api/bootstrap/v1/status";server.dispatch();check(server.response_.body=="status");
 server.advance(true);check(server.advanced==1&&server.mutation_safe_);
 wsprrypico::usb::ConsoleReply console_reply;std::array<std::uint8_t,64> console_input{};
 const std::string input="FIRST\nSECOND\n";std::copy(input.begin(),input.end(),console_input.begin());
 std::size_t console_input_offset=0,console_input_size=input.size(),length=0;
 std::array<char,256> line{};bool overflow=false;unsigned reboot_at=0,calls=0;
 auto command=[&](std::string_view text){++calls;return std::string(text)+std::string(9000,'x')+"\n";};
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
                subprocess.run(args, check=True, capture_output=True, timeout=60)
                result = subprocess.run([str(path / 'adapter')], check=True,
                                        capture_output=True, text=True, timeout=10)
                self.assertIn('actual adapter branches passed', result.stdout)


if __name__ == '__main__':
    unittest.main()
