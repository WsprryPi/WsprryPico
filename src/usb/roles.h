#pragma once

// CDC instance indices differ from the USB control/data interface numbers.
enum { USB_CDC_CONSOLE = 0, USB_CDC_WTP = 1, USB_CDC_MANAGEMENT = 2, USB_CDC_COUNT = 3 };
enum { USB_ITF_CONSOLE = 0, USB_ITF_WTP = 2, USB_ITF_MANAGEMENT = 4, USB_ITF_COUNT = 6 };
