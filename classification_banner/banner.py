#
# Copyright (C) 2022 SecurityCentral Contributors. See LICENSE for license
#

"""Python Scritp to display classification level banner of a session"""

import sys
import os
import argparse
import time
import re
from ConfigParser import SafeConfigParser
from socket import gethostname

# Global Configuration File
CONF_FILE = "/etc/classification-banner/banner.conf"
MAX_ESC_TIMEOUT = 60
MIN_ESC_TIMEOUT = 1

# Check if DISPLAY variable is set
try:
    os.environ["DISPLAY"]
except OSError:
    print "Error: DISPLAY environment variable is not set."
    sys.exit(1)

try:
    import pygtk  # pylint: disable=unused-import
    import gtk  # pylint: disable=unused-import
except ImportError:
    try:
        import Gtk  # pylint: disable=unused-import
    except ImportError as err:
        raise err


# Returns Username
def get_user():
    """Returns Username"""
    try:
        user = os.getlogin()
    except OSError:
        user = ''

    return user


# Returns Hostname
def get_host():
    """Returns Hostname"""
    host = gethostname()
    host = host.split('.')[0]
    return host


# Classification Banner Class
class ClassificationBanner:  # pylint: disable=too-many-instance-attributes,old-style-class
    """Class to create and refresh the actual banner."""

    def __init__(self, message="UNCLASSIFIED", fgcolor="#000000",   # pylint: disable=invalid-name,too-many-arguments,too-many-statements
                 bgcolor="#00CC00", font="liberation-sans", size="small",
                 weight="bold", x=0, y=0, esc=True, esc_timeout=15,
                 opacity=0.75, sys_info=False):

        """Set up and display the main window

        Keyword arguments:
        message -- The classification level to display
        fgcolor -- Foreground color of the text to display
        bgcolor -- Background color of the banner the text is against
        font    -- Font type to use for the displayed text
        size    -- Size of font to use for text
        weight  -- Bold or normal
        hres    -- Horizontal Screen Resolution (int) [ requires vres ]
        vres    -- Vertical Screen Resolution (int) [ requires hres ]
        opacity -- Opacity of window (float) [0 .. 1, default 0.75]
        """

        if esc_timeout < MIN_ESC_TIMEOUT:
            sanitized_timeout = MIN_ESC_TIMEOUT
        elif esc_timeout > MAX_ESC_TIMEOUT:
            sanitized_timeout = MAX_ESC_TIMEOUT
        else:
            sanitized_timeout = esc_timeout

        self.hres = x
        self.vres = y
        self.esc_timeout = sanitized_timeout

        # Dynamic Resolution Scaling
        self.monitor = gtk.gdk.Screen()
        self.monitor.connect("size-changed", self.resize)

        # Newer versions of pygtk have this method
        try:
            self.monitor.connect("monitors-changed", self.resize)
        except AttributeError:
            pass

        # Create Main Window
        self.window = gtk.Window()
        self.window.set_position(gtk.WIN_POS_CENTER)
        self.window.connect("hide", self.restore)
        self.window.connect("key-press-event", self.keypress)
        self.window.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(bgcolor))
        self.window.set_property('skip-taskbar-hint', True)
        self.window.set_property('skip-pager-hint', True)
        self.window.set_property('destroy-with-parent', True)
        self.window.stick()
        self.window.set_decorated(False)
        self.window.set_keep_above(True)
        self.window.set_app_paintable(True)

        try:
            self.window.set_opacity(opacity)
        except AttributeError:  # nosec
            pass

        # Set the default window size
        self.window.set_default_size(int(self.hres), 5)

        # Create Main Horizontal Box to Populate
        self.hbox = gtk.HBox()

        # Create the Center Vertical Box
        self.vbox_center = gtk.VBox()
        self.center_label = gtk.Label(
            "<span font_family='%s' weight='%s' foreground='%s' size='%s'>%s</span>" %
            (font, weight, fgcolor, size, message))
        self.center_label.set_use_markup(True)
        self.center_label.set_justify(gtk.JUSTIFY_CENTER)
        self.vbox_center.pack_start(self.center_label, True, True, 0)

        # Create the Right-Justified Vertical Box to Populate for hostname
        self.vbox_right = gtk.VBox()
        self.host_label = gtk.Label(
            "<span font_family='%s' weight='%s' foreground='%s' size='%s'>%s</span>" %
            (font, weight, fgcolor, size, get_host()))
        self.host_label.set_use_markup(True)
        self.host_label.set_justify(gtk.JUSTIFY_RIGHT)
        self.host_label.set_width_chars(20)

        # Create the Left-Justified Vertical Box to Populate for user
        self.vbox_left = gtk.VBox()
        self.user_label = gtk.Label(
            "<span font_family='%s' weight='%s' foreground='%s' size='%s'>%s</span>" %
            (font, weight, fgcolor, size, get_user()))
        self.user_label.set_use_markup(True)
        self.user_label.set_justify(gtk.JUSTIFY_LEFT)
        self.user_label.set_width_chars(20)

        # Create the Right-Justified Vertical Box to Populate for ESC message
        self.vbox_esc_right = gtk.VBox()
        self.esc_label = gtk.Label(
            "<span font_family='liberation-sans' weight='normal' foreground='%s' size='xx-small'>  (ESC to hide temporarily)  </span>" %  # pylint: disable=line-too-long
            (fgcolor))
        self.esc_label.set_use_markup(True)
        self.esc_label.set_justify(gtk.JUSTIFY_RIGHT)
        self.esc_label.set_width_chars(20)

        # Empty Label for formatting purposes
        self.vbox_empty = gtk.VBox()
        self.empty_label = gtk.Label(
            "<span font_family='liberation-sans' weight='normal'>                 </span>")
        self.empty_label.set_use_markup(True)
        self.empty_label.set_width_chars(20)

        if not esc:
            if not sys_info:
                self.hbox.pack_start(self.vbox_center, True, True, 0)
            else:
                self.vbox_right.pack_start(self.host_label, True, True, 0)
                self.vbox_left.pack_start(self.user_label, True, True, 0)
                self.hbox.pack_start(self.vbox_right, False, True, 20)
                self.hbox.pack_start(self.vbox_center, True, True, 0)
                self.hbox.pack_start(self.vbox_left, False, True, 20)

        else:
            if esc and not sys_info:
                self.empty_label.set_justify(gtk.JUSTIFY_LEFT)
                self.vbox_empty.pack_start(self.empty_label, True, True, 0)
                self.vbox_esc_right.pack_start(self.esc_label, True, True, 0)
                self.hbox.pack_start(self.vbox_esc_right, False, True, 0)
                self.hbox.pack_start(self.vbox_center, True, True, 0)
                self.hbox.pack_start(self.vbox_empty, False, True, 0)

        if sys_info:
            self.vbox_right.pack_start(self.host_label, True, True, 0)
            self.vbox_left.pack_start(self.user_label, True, True, 0)
            self.hbox.pack_start(self.vbox_right, False, True, 20)
            self.hbox.pack_start(self.vbox_center, True, True, 0)
            self.hbox.pack_start(self.vbox_left, False, True, 20)

        self.window.add(self.hbox)
        self.window.show_all()
        self.width, self.height = self.window.get_size()

    # Restore Minimized Window
    def restore(self, widget, data=None):  # pylint: disable=unused-argument
        """Restore Minimized Window"""
        self.window.deiconify()
        self.window.present()

        return True

    # Destroy Classification Banner Window on Resize (Display Banner Will Relaunch)
    def resize(self, widget, data=None):  # pylint: disable=unused-argument
        """Destroy Classification Banner Window on Resize (Display Banner Will Relaunch)"""
        self.window.destroy()

        return True

    # Press ESC to hide window for 15 seconds
    def keypress(self, widget, event=None):  # pylint: disable=unused-argument
        """Press ESC to hide window for X seconds"""
        if event.keyval == 65307:
            if not gtk.events_pending():
                old_x, old_y = self.window.get_position()
                self.window.iconify()
                self.window.hide()
                time.sleep(self.esc_timeout)
                self.window.move(old_x, old_y)
                self.window.show()
                self.window.deiconify()
                self.window.present()

        return True


class DisplayBanner:  # pylint: disable=old-style-class,too-many-instance-attributes
    """Display Classification Banner Message"""

    def __init__(self):
        # Dynamic Resolution Scaling
        self.monitor = gtk.gdk.Screen()
        self.monitor.connect("size-changed", self.resize)

        # Newer versions of pygtk have this method
        try:
            self.monitor.connect("monitors-changed", self.resize)
        except AttributeError:
            pass

        # Launch Banner
        self.config = self.configure()
        self.execute(self.config)

    # Read Global configuration
    def configure(self):  # pylint: disable=no-self-use
        """Read Global configuration"""
        defaults = {}
        defaults["message"] = "UNCLASSIFIED"
        defaults["foreground"] = "#FFFFFF"
        defaults["background"] = "#007A33"
        defaults["font"] = "liberation-sans"
        defaults["size"] = "small"
        defaults["weight"] = "bold"
        defaults["show_top"] = True
        defaults["show_bottom"] = True
        defaults["horizontal_resolution"] = 0
        defaults["vertical_resolution"] = 0
        defaults["sys_info"] = False
        defaults["opacity"] = 0.75
        defaults["esc"] = True
        defaults["esc_timeout"] = 15
        defaults["spanning"] = False

        conf = SafeConfigParser()
        conf.read(CONF_FILE)
        for key, val in conf.items("global"):
            if re.match(r"^[0-9]+$", val):
                defaults[key] = conf.getint("global", key)
            elif re.match(r"^[0-9]+.[0-9]+$", val):
                defaults[key] = conf.getfloat("global", key)
            elif re.match(r"^(true|false|yes|no)$", val, re.IGNORECASE):
                defaults[key] = conf.getboolean("global", key)
            else:
                defaults[key] = val


        # Use the global config to set defaults for command line options
        parser = argparse.ArgumentParser()
        parser.add_argument("-m", "--message", default=defaults["message"],
                            help="Set the Classification message")
        parser.add_argument("-f", "--fgcolor", default=defaults["foreground"],
                            help="Set the Foreground (text) color")
        parser.add_argument("-b", "--bgcolor", default=defaults["background"],
                            help="Set the Background color")
        parser.add_argument("-x", "--hres", default=defaults["horizontal_resolution"], type=int,
                            help="Set the Horizontal Screen Resolution")
        parser.add_argument("-y", "--vres", default=defaults["vertical_resolution"], type=int,
                            help="Set the Vertical Screen Resolution")
        parser.add_argument("-o", "--opacity", default=defaults["opacity"],
                            type=float, dest="opacity",
                            help="Set the window opacity for composted window managers")
        parser.add_argument("--font", default=defaults["font"], help="Font type")
        parser.add_argument("--size", default=defaults["size"], help="Font size")
        parser.add_argument("--weight", default=defaults["weight"],
                            help="Set the Font weight")
        parser.add_argument("--disable-esc", default=defaults["esc"],
                            dest="esc", action="store_false",
                            help="Disable the 'ESC to hide' message")
        parser.add_argument("--esc-timeout", default=defaults["esc_timeout"], type=int,
                            help="Configure how long 'ESC' will hide the classification bar")
        parser.add_argument("--hide-top", default=defaults["show_top"],
                            dest="show_top", action="store_false",
                            help="Disable the top banner")
        parser.add_argument("--hide-bottom", default=defaults["show_bottom"],
                            dest="show_bottom", action="store_false",
                            help="Disable the bottom banner")
        parser.add_argument("--system-info", default=defaults["sys_info"],
                            dest="sys_info", action="store_true",
                            help="Show user and hostname in the top banner")
        parser.add_argument("--enable-spanning", default=defaults["spanning"],
                            dest="spanning", action="store_true",
                            help="Enable banner(s) to span across screens as a single banner")

        args = parser.parse_args()

        return args

    # Launch the Classification Banner Window(s)
    def execute(self, options):
        """Launch the Classification Banner Window(s)"""
        self.num_monitor = int(os.popen("xrandr | grep ' connected ' | wc -l").readlines()[0])

        if options.hres == 0 or options.vres == 0:
            self.display = gtk.gdk.display_get_default()
            self.screen = self.display.get_default_screen()

            if not options.spanning and self.num_monitor > 1:
                for monitor in range(self.num_monitor):
                    mon_geo = self.screen.get_monitor_geometry(monitor)
                    self.x_location, self.y_location, self.x, self.y = (mon_geo.x, mon_geo.y, mon_geo.width, mon_geo.height)  # pylint: disable=invalid-name
                    self.banners(options)
                return

            self.x = self.screen.get_width()
            self.y = self.screen.get_height()
        else:
            # Resolution Set Staticly
            self.x = options.hres
            self.y = options.vres

        self.x_location = 0
        self.y_location = 0
        self.banners(options)

    def banners(self, options):
        """Set banner configuration"""
        if options.show_top:
            top = ClassificationBanner(
                options.message,
                options.fgcolor,
                options.bgcolor,
                options.font,
                options.size,
                options.weight,
                self.x,
                self.y,
                options.esc,
                options.esc_timeout,
                options.opacity,
                options.sys_info)
            top.window.move(self.x_location, self.y_location)

        if options.show_bottom:
            bottom = ClassificationBanner(
                options.message,
                options.fgcolor,
                options.bgcolor,
                options.font,
                options.size,
                options.weight,
                self.x,
                self.y,
                options.esc,
                options.esc_timeout,
                options.opacity)
            bottom.window.move(self.x_location, int(bottom.vres))

    # Relaunch the Classification Banner on Screen Resize
    def resize(self, widget, data=None):  # pylint: disable=unused-argument
        """Relaunch the Classification Banner on Screen Resize"""
        self.config = self.configure()
        self.execute(self.config)

        return True


def main():
    """Display Banner"""
    DisplayBanner()
    gtk.main()
