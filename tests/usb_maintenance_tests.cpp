#include "network_support.hpp"
#include "usb/maintenance.hpp"

using namespace wsprrypico;
using namespace network_test;

int main() {
    Fixture f;
    const std::string device(32, 'a'), boot = f.service.status().boot_id;
    std::string revision = "\"1\"", watermark = "0";
    bool ready = true, scheduled = false, accept = true;
    usb::Maintenance maintenance(
        f.service, device, boot, [&] { return ready; }, [&] { return f.scheduler.idle(); },
        [&] { return revision; }, [&] { return watermark; },
        [&] { scheduled = true; return accept; });
    network::HttpRequest r;
    r.method = "POST";
    r.path = "/api/usb/v1/maintenance";
    r.headers["if-match"] = revision;
    r.body = "{\"schema\":\"transmitter-usb-maintenance/1\",\"target\":{\"scope\":\"member\","
             "\"device_id\":\"" + device + "\",\"boot_id\":\"" + boot +
             "\"},\"confirmed\":true,\"watermark_utc_ns\":\"0\"}";
    const auto original_flash = f.flash.bytes;
    REQUIRE(maintenance.handle(r, 7).status == 202);
    REQUIRE(f.service.maintenance() && !f.scheduler.idle());
    f.scheduler.poll();
    REQUIRE(f.flash.bytes == original_flash && !scheduled);
    maintenance.finish(8, true); // A different transaction cannot cause reset.
    REQUIRE(!scheduled && f.service.maintenance());
    maintenance.finish(7, false); // Disconnection/cancel releases admission.
    REQUIRE(!scheduled && !f.service.maintenance() && f.scheduler.idle());
    REQUIRE(maintenance.handle(r, 9).status == 202);
    revision = "\"2\"";
    maintenance.finish(9, true);
    REQUIRE(!scheduled && !f.service.maintenance());
    r.headers["if-match"] = revision;
    REQUIRE(maintenance.handle(r, 10).status == 202);
    watermark = "1";
    maintenance.finish(10, true);
    REQUIRE(!scheduled && !f.service.maintenance());
    watermark = "0";
    ready = false;
    REQUIRE(maintenance.handle(r, 11).status == 409);
    ready = true;
    REQUIRE(maintenance.handle(r, 12).status == 202);
    f.clock.now += 16'000'000'000ULL;
    maintenance.finish(12, true); // An expired transaction never resets.
    REQUIRE(!scheduled && !f.service.maintenance());
    REQUIRE(maintenance.handle(r, 13).status == 202);
    maintenance.finish(13, true);
    REQUIRE(scheduled && f.service.maintenance()); // Hold through ACK drain.
    {
        Fixture stopped;
        bool reset_requested = false;
        usb::Maintenance pending(
            stopped.service, device, boot, [] { return true; }, [&] { return stopped.scheduler.idle(); },
            [&] { return revision; }, [&] { return watermark; },
            [&] { reset_requested = true; return true; });
        REQUIRE(pending.handle(r, 20).status == 202);
        pending.finish(20, true);
        REQUIRE(reset_requested && stopped.service.verification_safe());
        REQUIRE(stopped.service.local_inhibit_output());
        REQUIRE(stopped.service.maintenance() && !stopped.service.verification_safe());
    }
    f.service.end_maintenance();
    f.scheduler.command("STOP");
    REQUIRE(f.scheduler.suspended());
    REQUIRE(f.flash.bytes == original_flash);
    // A flash-update boot holds admission independently of the expiring ACK hold.
    f.service.hold_update_verification();
    f.clock.now += 60'000'000'000ULL;
    REQUIRE(f.service.maintenance() && !f.scheduler.idle());
    f.scheduler.poll();
    REQUIRE(f.flash.bytes == original_flash);
    REQUIRE(maintenance.handle(r, 14).status == 409);
    r.path = "/api/usb/v1/maintenance/finish";
    REQUIRE(maintenance.handle(r, 15).status == 202);
    maintenance.finish(15, false);
    REQUIRE(f.service.update_verification()); // Disconnect never releases the hold.
    REQUIRE(maintenance.handle(r, 16).status == 202);
    revision = "\"3\"";
    maintenance.finish(16, true);
    REQUIRE(f.service.update_verification());
    r.headers["if-match"] = revision;
    REQUIRE(maintenance.handle(r, 17).status == 202);
    maintenance.finish(17, true);
    REQUIRE(!f.service.maintenance() && f.scheduler.suspended());
    REQUIRE(f.flash.bytes == original_flash);
    f.service.hold_update_verification();
    REQUIRE(f.service.local_inhibit_output());
    REQUIRE(maintenance.handle(r, 18).status == 409);
    REQUIRE(f.service.update_verification());
    std::cout << "USB maintenance delivery, verification hold and storage checks passed\n";
}
