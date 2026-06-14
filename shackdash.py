#!/usr/bin/env python3
"""
ShackDash - GTK WebKit wrapper with AppIndicator tray icon
Shack info loaded from ~/shack/shack.json — editable via menu.
"""
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
gi.require_version('AyatanaAppIndicator3', '0.1')
from gi.repository import Gtk, WebKit2, GLib, Gdk, AyatanaAppIndicator3 as AppIndicator3
import os
import subprocess
import threading
import json

PORT        = 7373
HTML        = os.path.expanduser('~/shack/shackdash_widget.html')
FETCHER     = os.path.expanduser('~/shack/shackdash_fetch.py')
SHACK_JSON  = os.path.expanduser('~/shack/shack.json')
SHACK_DIR   = os.path.expanduser('~/shack')
ICON        = os.path.expanduser('~/shack/shackdash_icon.png')
WIDTH       = 360
APP_VERSION = '0.1.3'
ABOUT_LINK_URL = 'https://go.frantik.it/m8twy'  # placeholder - update with your YOURLS short link

def detect_scale():
    """Auto-detect recommended scale factor based on screen DPI."""
    try:
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        if monitor:
            geo      = monitor.get_geometry()
            scale    = monitor.get_scale_factor()
            width_mm = monitor.get_width_mm()
            if width_mm > 0:
                dpi = geo.width * scale / (width_mm / 25.4)
                if dpi < 100:   return 0.8
                if dpi < 120:   return 1.0
                if dpi < 150:   return 1.25
                if dpi < 200:   return 1.5
                return 2.0
    except Exception as e:
        print(f"DPI detection failed: {e}")
    return 1.0

def get_scale():
    """Get scale from shack.json, or auto-detect and save it."""
    try:
        with open(SHACK_JSON) as f:
            data = json.load(f)
        if 'widget_scale' in data:
            return float(data['widget_scale'])
    except Exception:
        pass
    # Auto-detect and save
    scale = detect_scale()
    try:
        try:
            with open(SHACK_JSON) as f:
                data = json.load(f)
        except Exception:
            data = {}
        data['widget_scale'] = scale
        with open(SHACK_JSON, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Auto-detected scale: {scale}")
    except Exception as e:
        print(f"Could not save scale: {e}")
    return scale

def run_fetcher(callback=None):
    def _run():
        try:
            subprocess.run(['python3', FETCHER], timeout=20)
        except Exception as e:
            print(f"Fetch failed: {e}")
        if callback:
            GLib.idle_add(callback)
    threading.Thread(target=_run, daemon=True).start()

def load_shack():
    try:
        with open(SHACK_JSON) as f:
            return json.load(f)
    except Exception:
        return {}

def save_shack(data):
    with open(SHACK_JSON, 'w') as f:
        json.dump(data, f, indent=2)


class SetupWizardDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title='Station Setup Wizard', transient_for=parent, modal=True)
        self.set_default_size(400, -1)
        self.set_resizable(False)
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            'Look Up Location', Gtk.ResponseType.APPLY,
            'Save & Close',     Gtk.ResponseType.OK
        )
        # Save disabled until lookup done
        self.set_response_sensitive(Gtk.ResponseType.OK, False)

        box = self.get_content_area()
        box.set_spacing(6)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(14)
        box.set_margin_bottom(10)

        # Intro label
        intro = Gtk.Label()
        intro.set_markup("<b>Enter your details and we'll calculate your grid info automatically.</b>")
        intro.set_line_wrap(True)
        intro.set_halign(Gtk.Align.START)
        box.pack_start(intro, False, False, 0)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_top(4)
        sep.set_margin_bottom(4)
        box.pack_start(sep, False, False, 0)

        self.fields = {}

        def add_field(key, label, value='', placeholder=''):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            lbl = Gtk.Label(label=label)
            lbl.set_width_chars(20)
            lbl.set_halign(Gtk.Align.END)
            entry = Gtk.Entry()
            entry.set_text(value)
            if placeholder:
                entry.set_placeholder_text(placeholder)
            entry.set_hexpand(True)
            row.pack_start(lbl, False, False, 0)
            row.pack_start(entry, True, True, 0)
            box.pack_start(row, False, False, 0)
            self.fields[key] = entry

        # Load existing values if available
        existing = {}
        try:
            with open(os.path.expanduser('~/shack/shack.json')) as f:
                existing = json.load(f)
        except Exception:
            pass

        add_field('callsign', 'Callsign',  existing.get('callsign',''),  'e.g. M8TWY')
        add_field('name',     'Your name', existing.get('name',''),       'e.g. Toby')
        add_field('postcode', 'Postcode / Lat,Lon',  '',                 'UK: PE34 4QD  or  51.5,-0.1')
        add_field('qth',      'QTH',       existing.get('qth',''),        'Auto-filled from postcode/location')

        note = Gtk.Label()
        note.set_markup('<small><i>UK: enter postcode. Outside UK: enter lat,lon (e.g. 51.5,-0.1). QTH auto-filled.</i></small>')
        note.set_halign(Gtk.Align.START)
        note.set_margin_start(90)
        box.pack_start(note, False, False, 0)

        # Use My Location button
        loc_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        loc_row.set_margin_top(6)
        loc_btn = Gtk.Button(label='Use My Location')
        loc_btn.set_tooltip_text('Uses IP geolocation to find your approximate location')
        loc_btn.set_halign(Gtk.Align.START)
        loc_btn.set_margin_start(90)
        loc_row.pack_start(loc_btn, False, False, 0)
        box.pack_start(loc_row, False, False, 0)
        self.loc_btn = loc_btn

        # Status label for feedback
        self.status_lbl = Gtk.Label(label='')
        self.status_lbl.set_halign(Gtk.Align.CENTER)
        self.status_lbl.set_margin_top(6)
        box.pack_start(self.status_lbl, False, False, 0)

        self.show_all()

    def get_fields(self):
        return {k: v.get_text().strip() for k, v in self.fields.items()}

    def set_status(self, msg, colour='#f0c040'):
        self.status_lbl.set_markup(f'<span color="{colour}">{msg}</span>')


class EditShackDialog(Gtk.Dialog):
    def __init__(self, parent, shack):
        super().__init__(title='Edit Shack Info', transient_for=parent, modal=True)
        self.set_default_size(440, 520)
        self.set_resizable(True)
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE,   Gtk.ResponseType.OK
        )

        # ── Scrolled container ───────────────────────────────────────────
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        inner.set_margin_start(16)
        inner.set_margin_end(16)
        inner.set_margin_top(10)
        inner.set_margin_bottom(10)

        scroll.add(inner)

        # Add scrolled window to dialog content area
        content = self.get_content_area()
        content.pack_start(scroll, True, True, 0)

        self.fields = {}

        def add_section(label):
            lbl = Gtk.Label()
            lbl.set_markup(f'<b>{label}</b>')
            lbl.set_halign(Gtk.Align.START)
            lbl.set_margin_top(10)
            inner.pack_start(lbl, False, False, 0)
            sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            sep.set_margin_bottom(4)
            inner.pack_start(sep, False, False, 0)

        def add_field(key, label, value):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.set_margin_bottom(2)
            lbl = Gtk.Label(label=label)
            lbl.set_width_chars(16)
            lbl.set_halign(Gtk.Align.END)
            lbl.set_valign(Gtk.Align.CENTER)
            entry = Gtk.Entry()
            entry.set_text(str(value or ''))
            entry.set_hexpand(True)
            row.pack_start(lbl, False, False, 0)
            row.pack_start(entry, True, True, 0)
            inner.pack_start(row, False, False, 0)
            self.fields[key] = entry

        add_section('Station')
        add_field('callsign',  'Callsign',      shack.get('callsign', ''))
        add_field('name',      'Name',           shack.get('name', ''))
        add_field('licence',   'Licence class',  shack.get('licence', ''))
        add_field('qrz',       'QRZ page',       shack.get('qrz', ''))
        add_field('qsl',       'QSL method',     shack.get('qsl', ''))
        # Modes — toggle checkboxes
        modes_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        modes_lbl = Gtk.Label(label='Modes')
        modes_lbl.set_width_chars(20)
        modes_lbl.set_halign(Gtk.Align.END)
        modes_wrap = Gtk.FlowBox()
        modes_wrap.set_max_children_per_line(4)
        modes_wrap.set_selection_mode(Gtk.SelectionMode.NONE)
        current_modes = [m.strip() for m in shack.get('modes', '').split(',') if m.strip()]
        self.mode_checks = {}
        for mode in ['FM', 'SSB', 'CW', 'AM', 'FT8', 'FT4', 'DMR', 'C4FM', 'D-STAR', 'RTTY', 'PSK31']:
            cb = Gtk.CheckButton(label=mode)
            cb.set_active(mode in current_modes)
            self.mode_checks[mode] = cb
            modes_wrap.add(cb)
        modes_row.pack_start(modes_lbl, False, False, 0)
        modes_row.pack_start(modes_wrap, True, True, 0)
        inner.pack_start(modes_row, False, False, 0)

        add_section('Location')
        add_field('qth',        'QTH',           shack.get('qth', ''))
        add_field('county',     'County',        shack.get('county', ''))
        add_field('country',    'Country',       shack.get('country', ''))
        add_field('maidenhead', 'Maidenhead',    shack.get('maidenhead', ''))
        add_field('wab',        'WAB square',    shack.get('wab', ''))
        add_field('os_grid',    'OS grid ref',   shack.get('os_grid', ''))
        add_field('lat',        'Latitude',      shack.get('lat', ''))
        add_field('lon',        'Longitude',     shack.get('lon', ''))
        add_field('cq_zone',    'CQ Zone',       shack.get('cq_zone', ''))
        add_field('itu_zone',   'ITU Zone',      shack.get('itu_zone', ''))

        add_section('Equipment')
        rigs = shack.get('rigs', [{}, {}])
        while len(rigs) < 3:
            rigs.append({})
        for i, rig in enumerate(rigs[:3]):
            add_field(f'rig{i}_label', f'Rig {i+1} label', rig.get('label', ''))
            add_field(f'rig{i}_value', f'Rig {i+1} value', rig.get('value', ''))

        add_field('antenna',       'Antenna',      shack.get('antenna', ''))
        add_field('antenna2',      'Antenna 2',    shack.get('antenna2', ''))

        self.show_all()

    def get_values(self, original):
        data = dict(original)
        for key, entry in self.fields.items():
            if not key.startswith('rig'):
                data[key] = entry.get_text().strip()
        rigs = []
        for i in range(3):
            lbl = self.fields[f'rig{i}_label'].get_text().strip()
            val = self.fields[f'rig{i}_value'].get_text().strip()
            if lbl or val:
                rigs.append({'label': lbl, 'value': val})
        data['rigs'] = rigs
        # Collect modes from checkboxes
        if hasattr(self, 'mode_checks'):
            data['modes'] = ', '.join(m for m, cb in self.mode_checks.items() if cb.get_active())
        return data


class ShackDashWidget:
    def __init__(self):
        self.window_visible  = True
        self.current_view    = 'both'
        self._drag_start     = None
        self.always_on_top   = True  # on by default
        self._page_ready     = True  # Always ready - js() guards internally
        self._spots_done      = False
        self.scale           = get_scale()
        # Load saved theme
        try:
            with open(SHACK_JSON) as f:
                d = json.load(f)
            self.theme = d.get('widget_theme', 'dark')
        except Exception:
            self.theme = 'dark'
        print(f"Widget scale: {self.scale}")

        # Set app icon before window creation so taskbar picks it up
        icon_path = os.path.expanduser('~/shack/m8twy-icon.png')
        if os.path.exists(icon_path):
            Gtk.Window.set_default_icon_from_file(icon_path)
        self._resize_attempts = 0

        # ── Window ──────────────────────────────────────────────────────
        self.window = Gtk.Window(title='ShackDash')
        self.window.set_resizable(True)
        self.window.set_decorated(False)
        self.window.set_keep_above(True)
        self.window.move(5, 25)
        self.window.connect('delete-event', self.on_delete_event)
        self.window.connect('configure-event', self.on_window_configure)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_skip_pager_hint(True)
        self.window.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        # RGBA visual for transparency (graceful fallback if not available)
        try:
            screen = self.window.get_screen()
            visual = screen.get_rgba_visual()
            if visual and screen.is_composited():
                self.window.set_visual(visual)
        except Exception:
            pass

        # Set taskbar/window icon at app level
        icon_path = os.path.expanduser('~/shack/m8twy-icon.png')
        if os.path.exists(icon_path):
            self.window.set_icon_from_file(icon_path)
            Gtk.Window.set_default_icon_from_file(icon_path)

        # ── WebKit ───────────────────────────────────────────────────────
        self.webview = WebKit2.WebView()
        settings = self.webview.get_settings()
        settings.set_allow_file_access_from_file_urls(True)
        settings.set_allow_universal_access_from_file_urls(True)
        settings.set_enable_write_console_messages_to_stdout(True)
        settings.set_enable_developer_extras(True)
        self.webview.connect('load-changed', self.on_load_changed)
        self.webview.connect('button-press-event', self.on_button_press)
        self.webview.connect('button-release-event', self.on_button_release)
        self.webview.connect('motion-notify-event', self.on_motion)
        self.webview.connect('context-menu', lambda *a: True)
        self.webview.connect('decide-policy', self.on_decide_policy)
        # Watch for title changes used to signal resize from JS
        self.webview.connect('notify::title', self.on_title_changed)
        self.webview.load_uri('file://' + HTML)

        self.box = Gtk.Box()
        self.box.pack_start(self.webview, True, True, 0)
        self.window.add(self.box)
        scaled_width = int(WIDTH * self.scale)
        # Start tall enough to cover full content behind loading overlay
        self.webview.set_size_request(scaled_width, 260)
        self.window.set_default_size(scaled_width, 260)
        # Apply zoom level to WebKit so text/layout scales too
        self.webview.set_zoom_level(self.scale)
        self.window.show_all()

        # ── AppIndicator ─────────────────────────────────────────────────
        self.indicator = AppIndicator3.Indicator.new(
            'shackdash', ICON,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_title('ShackDash')
        self.indicator.set_menu(self.build_menu())

        def on_startup_fetch_done():
            # Small delay to ensure page JS is ready before calling loadData
            GLib.timeout_add(800, lambda: self.js(
                "loadData(); showStatus('Solar data updated', 'ok');"
            ) or False)
        run_fetcher(callback=on_startup_fetch_done)
    def on_load_changed(self, webview, event):
        if event == WebKit2.LoadEvent.FINISHED:
            self._page_ready = True
            self._resize_attempts = 0
            GLib.timeout_add(2500, self._try_initial_resize)  # after loading dismisses at 1500ms
            GLib.timeout_add(3000, self._fetch_spots)
            # Set up recurring spots refresh ONCE
            if not getattr(self, '_spots_timer_set', False):
                self._spots_timer_set = True
                GLib.timeout_add(5 * 60 * 1000, self._spots_refresh_timer)
            GLib.timeout_add(200, lambda: self.js(f"setTheme('{self.theme}');") or False)
            # Inject callsign into loading screen
            try:
                with open(SHACK_JSON) as _f:
                    _cs = json.load(_f).get('callsign', '') or 'ShackDash'
                GLib.timeout_add(100, lambda cs=_cs: self.js(
                    f"var lc=document.getElementById('loading-callsign');"
                    f"if(lc)lc.textContent='{cs}';"
                ) or False)
            except Exception:
                pass
            # First run — launch setup wizard if no shack.json or no callsign
            try:
                with open(SHACK_JSON) as _f:
                    _d = json.load(_f)
                if not _d.get('callsign'):
                    GLib.timeout_add(1000, lambda: self.on_setup_wizard(None) or False)
            except FileNotFoundError:
                GLib.timeout_add(1000, lambda: self.on_setup_wizard(None) or False)
            except Exception:
                pass
            # Update menu label
            if hasattr(self, 'theme_item'):
                self.theme_item.set_label(
                    'Switch to Dark Mode' if self.theme == 'light' else 'Switch to Light Mode'
                )

    def _try_initial_resize(self):
        self._resize_attempts += 1
        def got_height(h):
            if h and h > 200:
                self._apply_resize(h)
                GLib.timeout_add(800, self._final_resize)
                GLib.timeout_add(500, self._check_location_consistency)
            elif self._resize_attempts < 5:
                GLib.timeout_add(1000, self._try_initial_resize)
        self.js_get_height(got_height)
        return False

    def _final_resize(self):
        def got_height(h):
            if h and h > 200:
                self._apply_resize(h)
        self.js_get_height(got_height)
        return False

    def _apply_resize(self, h):
        actual_w = int(WIDTH * self.scale)
        max_h = 9999
        try:
            display = Gdk.Display.get_default()
            monitor = None
            # Prefer the monitor the window is actually on
            if self.window and self.window.get_window():
                monitor = display.get_monitor_at_window(self.window.get_window())
            if not monitor:
                monitor = display.get_primary_monitor()
            if not monitor:
                monitor = display.get_monitor(0)
            if monitor:
                screen_h = monitor.get_geometry().height
                workarea = monitor.get_workarea()
                screen_h = workarea.height if workarea.height > 0 else screen_h
                max_h = screen_h - 40  # Account for top panel and taskbar
            else:
                screen = Gdk.Screen.get_default()
                if screen:
                    max_h = screen.get_height() - 35
        except Exception as e:
            max_h = 9999
        buffered_h = h + 2
        capped_h = min(buffered_h, max_h)
        is_capped = buffered_h > max_h
        overflow = 'auto' if is_capped else 'hidden'
        self.js(f"document.body.style.overflowY = '{overflow}';")
        self.webview.set_size_request(actual_w, capped_h)
        self.window.resize(actual_w, capped_h)

    def _spots_refresh_timer(self):
        self._fetch_spots()
        return True  # keep repeating

    def _fetch_spots(self):
        def _run():
            import urllib.request as _ur, json as _js
            try:
                with _ur.urlopen('http://127.0.0.1:7373/spots', timeout=8) as r:
                    spots = _js.loads(r.read())
                GLib.idle_add(lambda: self.js(f"renderSpots({_js.dumps(spots)});") or False)
            except Exception as e:
                print(f"Spots fetch error: {e}")
        threading.Thread(target=_run, daemon=True).start()
        return False

    def _start_spots_polling(self):
        # Keep trying until _page_ready is True
        if self._spots_done:
            return False
        if getattr(self, '_page_ready', False):
            self._spots_done = True
            self._fetch_spots()
            return False
        return True  # Try again in 1 second

    def _check_location_consistency(self):
        shack = load_shack()
        qth    = shack.get('qth', '').strip()
        county = shack.get('county', '').strip()
        # Only warn if county and qth both have content AND share no common words
        # This catches obvious mismatches (e.g. Northampton vs Norfolk)
        # but ignores normal cases where QTH is a village in that county
        qth_words    = set(qth.lower().split())
        county_words = set(county.lower().split())
        # Check maidenhead prefix too — if first 2 chars differ significantly
        maidenhead = shack.get('maidenhead', '')
        # Only flag if county and qth share zero words AND county is non-empty
        no_overlap = not qth_words.intersection(county_words)
        # Extra check: see if qth appears to be a known alias for county
        # e.g. "Terrington St Clement" is in "Norfolk" — no overlap but not a mismatch
        # So we need a second signal: check if os_grid prefix matches county
        os_grid = shack.get('os_grid', '')
        os_prefix = os_grid[:2] if os_grid else ''
        # Norfolk OS prefixes: TF, TG — West Northants: SP
        # If os_prefix is consistent with county name we trust it's fine
        county_grid_map = {
            'norfolk': ['TF', 'TG'], 'suffolk': ['TL', 'TM'],
            'northamptonshire': ['SP'], 'west northamptonshire': ['SP'],
            'lincolnshire': ['TF', 'SK'], 'cambridgeshire': ['TL'],
            'yorkshire': ['SE', 'TA', 'NY'], 'lancashire': ['SD'],
        }
        expected_prefixes = county_grid_map.get(county.lower(), [])
        grid_mismatch = bool(expected_prefixes) and os_prefix not in expected_prefixes
        if grid_mismatch:
            warn = Gtk.MessageDialog(
                transient_for=self.window,
                modal=False,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.NONE,
                text='Location data may be inconsistent'
            )
            warn.format_secondary_text(
                'QTH is set to "' + qth + '" but county shows "' + county + '".\n\n'
                'This may mean your location data is out of date. '
                'Run the Setup Wizard to update all location fields.'
            )
            warn.add_buttons(
                'Ignore',      Gtk.ResponseType.CANCEL,
                'Open Wizard', Gtk.ResponseType.OK,
            )
            def on_warn_response(dialog, response):
                dialog.destroy()
                if response == Gtk.ResponseType.OK:
                    self.on_setup_wizard(None)
            warn.connect('response', on_warn_response)
            warn.show()
        return False

    def build_menu(self):
        menu = Gtk.Menu()

        title = Gtk.MenuItem(label='ShackDash')
        title.set_sensitive(False)
        menu.append(title)

        about_item = Gtk.MenuItem(label='About ShackDash…')
        about_item.connect('activate', self.on_about)
        menu.append(about_item)

        menu.append(Gtk.SeparatorMenuItem())

        self.toggle_item = Gtk.MenuItem(label='Hide Widget')
        self.toggle_item.connect('activate', self.on_toggle_window)
        menu.append(self.toggle_item)
        menu.append(Gtk.SeparatorMenuItem())

        # Scale submenu near top so it has room to open
        scale_item = Gtk.MenuItem(label='Widget Scale')
        scale_menu = Gtk.Menu()
        self.scale_items = {}
        for label, val in [('Small (0.8×)', 0.8), ('Normal (1.0×)', 1.0),
                           ('Large (1.25×)', 1.25), ('Extra Large (1.5×)', 1.5),
                           ('HiDPI (2.0×)', 2.0)]:
            prefix = '✓ ' if abs(val - self.scale) < 0.01 else '  '
            item = Gtk.MenuItem(label=prefix + label)
            item.connect('activate', self.on_set_scale, val)
            scale_menu.append(item)
            self.scale_items[val] = (item, label)
        scale_menu.show_all()
        scale_item.set_submenu(scale_menu)
        menu.append(scale_item)
        menu.append(Gtk.SeparatorMenuItem())

        view_item = Gtk.MenuItem(label='View')
        view_menu = Gtk.Menu()
        self.view_checks = {}
        for label, key in [('Location & Grid', 'loc'), ('Shack Info', 'shack'),
                            ('Propagation', 'prop'), ('Spots', 'spots')]:
            ci = Gtk.CheckMenuItem(label=label)
            ci.set_active(True)  # all on by default
            ci.connect('toggled', self.on_view_toggle)
            self.view_checks[key] = ci
            view_menu.append(ci)
        view_menu.append(Gtk.SeparatorMenuItem())
        show_all = Gtk.MenuItem(label='Show All')
        show_all.connect('activate', self.on_view_show_all)
        view_menu.append(show_all)
        view_menu.show_all()
        view_item.set_submenu(view_menu)
        menu.append(view_item)

        menu.append(Gtk.SeparatorMenuItem())

        setup_item = Gtk.MenuItem(label='Setup Wizard…')
        setup_item.connect('activate', self.on_setup_wizard)
        menu.append(setup_item)

        reset_item = Gtk.MenuItem(label='Reset ShackDash…')
        reset_item.connect('activate', self.on_reset)
        menu.append(reset_item)


        self.aot_item = Gtk.MenuItem(label='✓ Always on Top')
        self.aot_item.connect('activate', self.on_toggle_always_on_top)
        menu.append(self.aot_item)

        self.theme_item = Gtk.MenuItem(label='Switch to Light Mode')
        self.theme_item.connect('activate', self.on_toggle_theme)
        menu.append(self.theme_item)

        menu.append(Gtk.SeparatorMenuItem())

        edit_item = Gtk.MenuItem(label='Edit Shack Info…')
        edit_item.connect('activate', self.on_edit_shack)
        menu.append(edit_item)

        refresh_item = Gtk.MenuItem(label='Refresh Solar Data')
        refresh_item.connect('activate', self.on_refresh)
        menu.append(refresh_item)

        reload_item = Gtk.MenuItem(label='Reload Widget')
        reload_item.connect('activate', self.on_reload)
        menu.append(reload_item)

        about_item = Gtk.MenuItem(label='About ShackDash…')
        about_item.connect('activate', self.on_about)
        menu.append(about_item)

        menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label='Quit')
        quit_item.connect('activate', self.on_quit)
        menu.append(quit_item)

        menu.show_all()
        return menu

    def js(self, script):
        self.webview.run_javascript(script, None, None, None)
    def js_get_height(self, callback):
        def on_result(webview, result, user_data):
            try:
                js_result = webview.run_javascript_finish(result)
                value = js_result.get_js_value()
                # scrollHeight * scale = GTK window px
                actual_height = int(value.to_double() * self.scale)
                GLib.idle_add(lambda: callback(actual_height))
            except Exception as e:
                print(f"Height query failed: {e}")
                GLib.idle_add(lambda: callback(None))
        # scrollHeight in CSS px * scale = GTK window px
        self.webview.run_javascript(
            "document.querySelector('.widget').scrollHeight;",
            None, on_result, None
        )
    def on_window_configure(self, widget, event):
        # Detect monitor change and re-apply resize cap
        try:
            display = Gdk.Display.get_default()
            monitor = display.get_monitor_at_window(self.window.get_window())
            if monitor != getattr(self, '_last_monitor', None):
                self._last_monitor = monitor
                if hasattr(self, '_monitor_resize_timer') and self._monitor_resize_timer:
                    GLib.source_remove(self._monitor_resize_timer)
                self._monitor_resize_timer = GLib.timeout_add(300, self._on_monitor_changed)
        except Exception:
            pass
        return False

    def _on_monitor_changed(self):
        self._monitor_resize_timer = None
        self.resize_to_content(delay=50)
        return False

    def resize_to_content(self, delay=120):
        def measure():
            def apply_height(h):
                if h and h > 100:
                    self._apply_resize(h)
            self.js_get_height(apply_height)
            return False
        GLib.timeout_add(delay, measure)

    def on_view_toggle(self, _):
        visible = [k for k, ci in self.view_checks.items() if ci.get_active()]
        self.js(f"setPanels({str(visible).replace(chr(39), chr(34))});")
        self.resize_to_content()
        if not self.window_visible:
            self.show_window()

    def on_view_show_all(self, _):
        for ci in self.view_checks.values():
            ci.set_active(True)

    def set_view(self, view):
        # Legacy - map old view names to checkbox state
        mapping = {'both': None, 'loc': 'loc', 'shack': 'shack', 'prop': 'prop', 'spots': 'spots'}
        if view == 'both':
            self.on_view_show_all(None)
        else:
            for k, ci in self.view_checks.items():
                ci.set_active(k == view)

    def on_reset(self, _):
        dlg = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text='Reset ShackDash?'
        )
        dlg.format_secondary_text(
            'This will clear all your station settings and relaunch the Setup Wizard.\n'
            'Your solar data will not be affected.'
        )
        dlg.add_button('Cancel', Gtk.ResponseType.CANCEL)
        dlg.add_button('Reset', Gtk.ResponseType.OK)
        dlg.set_default_response(Gtk.ResponseType.CANCEL)
        response = dlg.run()
        dlg.destroy()
        if response == Gtk.ResponseType.OK:
            try:
                os.remove(SHACK_JSON)
                print(f"Reset: deleted {SHACK_JSON}")
            except FileNotFoundError:
                print(f"Reset: {SHACK_JSON} not found, proceeding anyway")
            except Exception as e:
                print(f"Reset error: {e}")
            # Clear widget display and show empty state
            self.js("loadShack({});")
            GLib.timeout_add(200, lambda: self.resize_to_content() or False)
            self.on_setup_wizard(None)
            # Resize again after wizard closes
            GLib.timeout_add(500, lambda: self.resize_to_content() or False)

    def on_about(self, _):
        dlg = Gtk.Dialog(title='About ShackDash', transient_for=self.window, modal=True)
        dlg.set_default_size(320, 0)
        box = dlg.get_content_area()
        box.set_spacing(8)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(16)
        box.set_margin_bottom(10)

        # Icon
        try:
            icon = Gtk.Image.new_from_file(os.path.expanduser('~/shack/shackdash_icon.png'))
            icon.set_pixel_size(48)
            box.pack_start(icon, False, False, 4)
        except Exception:
            pass

        title = Gtk.Label()
        title.set_markup('<b><big>ShackDash</big></b>')
        box.pack_start(title, False, False, 0)

        version = Gtk.Label(label=f'Version {APP_VERSION}')
        version.get_style_context().add_class('dim-label')
        box.pack_start(version, False, False, 0)

        desc = Gtk.Label(label='Amateur radio station desktop widget')
        desc.set_line_wrap(True)
        box.pack_start(desc, False, False, 4)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(sep, False, False, 4)

        def add_link(label_text, url):
            link = Gtk.LinkButton.new_with_label(url, label_text)
            link.set_halign(Gtk.Align.START)
            box.pack_start(link, False, False, 0)

        add_link('GitHub repository', 'https://github.com/tobyw7/shackdash')
        add_link('Report an issue', 'https://github.com/tobyw7/shackdash/issues')
        add_link('More from M8TWY', ABOUT_LINK_URL)

        footer = Gtk.Label()
        footer.set_markup('<small>73 de M8TWY</small>')
        footer.set_margin_top(8)
        box.pack_start(footer, False, False, 0)

        dlg.add_button('Close', Gtk.ResponseType.CLOSE)
        dlg.show_all()
        dlg.run()
        dlg.destroy()

    def on_setup_wizard(self, _):
        import sys
        sys.path.insert(0, os.path.expanduser('~/shack'))
        try:
            import shackdash_setup as setup
        except ImportError:
            self.js("showStatus('Setup module not found in ~/shack/', 'err');")
            return

        dialog = SetupWizardDialog(self.window)

        result_data = [None]   # store lookup result across threads
        expected_qth = [None]  # QTH returned by postcode lookup

        def do_lookup(btn=None):
            fields = dialog.get_fields()
            if not fields['postcode']:
                dialog.set_status('Please enter a postcode or lat,lon coordinates.', '#e05050')
                return
            dialog.set_status('Looking up location…', '#f0c040')
            dialog.set_response_sensitive(Gtk.ResponseType.OK, False)
            dialog.set_response_sensitive(Gtk.ResponseType.APPLY, False)

            def _run():
                try:
                    data = setup.calculate_all(
                        fields['callsign'],
                        fields['name'],
                        fields['postcode'],
                        fields.get('qth', '')
                    )
                    result_data[0] = data
                    expected_qth[0] = data.get('qth', '')
                    def _done():
                        # Update dialog UI while still open
                        qth_entry = dialog.fields.get('qth')
                        if qth_entry and data.get('qth'):
                            qth_entry.set_text(data['qth'])
                        dialog.set_status(
                            f"✓ {data['maidenhead']} · {data['wab']} · {data['os_grid']}",
                            '#4de090'
                        )
                        dialog.set_response_sensitive(Gtk.ResponseType.OK, True)
                        dialog.set_response_sensitive(Gtk.ResponseType.APPLY, True)
                    GLib.idle_add(_done)
                except Exception as e:
                    def _err():
                        dialog.set_status(f'Error: {e}', '#e05050')
                        dialog.set_response_sensitive(Gtk.ResponseType.OK, True)
                    GLib.idle_add(_err)

            threading.Thread(target=_run, daemon=True).start()

        # Clear QTH when postcode changes so user knows it'll be auto-filled
        def on_postcode_changed(entry):
            dialog.fields['qth'].set_text('')
            dialog.set_status('Enter postcode (UK) or lat,lon, then click Look Up', '#4a6a8a')
        dialog.fields['postcode'].connect('changed', on_postcode_changed)

        def do_locate(_btn=None):
            dialog.set_status('Finding your location via IP…', '#f0c040')
            dialog.loc_btn.set_sensitive(False)

            def _run():
                try:
                    import urllib.request as ur, json as js
                    req = ur.Request('https://ipapi.co/json/',
                        headers={'User-Agent': 'ShackDash/1.0'})
                    with ur.urlopen(req, timeout=10) as r:
                        geo = js.loads(r.read())
                    lat = geo.get('latitude')
                    lon = geo.get('longitude')
                    city = geo.get('city', 'Unknown')
                    if not lat or not lon:
                        raise ValueError('No coordinates returned')

                    req2 = ur.Request(
                        f'https://api.postcodes.io/postcodes?lon={lon}&lat={lat}&limit=1',
                        headers={'User-Agent': 'ShackDash/1.0'})
                    with ur.urlopen(req2, timeout=10) as r:
                        pc_data = js.loads(r.read())

                    postcode = ''
                    if pc_data.get('result'):
                        postcode = pc_data['result'][0].get('postcode', '')

                    def _done():
                        dialog.loc_btn.set_sensitive(True)
                        if postcode:
                            dialog.fields['postcode'].set_text(postcode)
                            dialog.set_status(
                                f'Found {city} → {postcode} — verify and click Look Up Location',
                                '#f0c040'
                            )
                        else:
                            dialog.set_status(
                                f'IP location found {city} (approx.) — enter postcode or lat,lon above',
                                '#f0c040'
                            )
                    GLib.idle_add(_done)

                except Exception as e:
                    def _err():
                        dialog.loc_btn.set_sensitive(True)
                        dialog.set_status(f'Location failed: {e}', '#e05050')
                    GLib.idle_add(_err)

            threading.Thread(target=_run, daemon=True).start()

        dialog.loc_btn.connect('clicked', do_locate)

        for entry in dialog.fields.values():
            entry.connect('activate', do_lookup)

        # Keep dialog open so user can review results before saving
        while True:
            response = dialog.run()
            if response == Gtk.ResponseType.APPLY:
                # Look Up button — run the postcode lookup
                do_lookup()
                continue
            elif response == Gtk.ResponseType.OK:
                # Save & Close — validate then save
                if result_data[0] is not None:
                    data = result_data[0]
                    entered_qth = dialog.fields['qth'].get_text().strip()
                    # Check if QTH was manually changed from postcode result
                    if (expected_qth[0] and entered_qth and
                            entered_qth.lower() != expected_qth[0].lower()):
                        warn = Gtk.MessageDialog(
                            transient_for=dialog,
                            modal=True,
                            message_type=Gtk.MessageType.WARNING,
                            buttons=Gtk.ButtonsType.YES_NO,
                            text='QTH mismatch'
                        )
                        sec = ('Entered: ' + entered_qth + '\n'
                               'Postcode result: ' + str(expected_qth[0]) + '\n\n'
                               'Save anyway with your custom QTH?')
                        warn.format_secondary_text(sec)
                        warn_response = warn.run()
                        warn.destroy()
                        if warn_response != Gtk.ResponseType.YES:
                            dialog.fields['qth'].set_text(expected_qth[0])
                            continue
                    # Update data with whatever QTH the user confirmed
                    data['qth'] = entered_qth
                    # Auto-derive QRZ URL from callsign
                    if data.get('callsign'):
                        data['qrz'] = f"https://qrz.com/db/{data['callsign'].upper()}"
                    setup.save_shack(data)
                    dialog.destroy()
                    self.js(f"loadShack({json.dumps(data)});")
                    self.js("showStatus('Station setup complete!', 'ok');")
                    self.resize_to_content(delay=200)
                    break
            else:
                dialog.destroy()
                break

    def on_edit_shack(self, _):
        shack = load_shack()
        dialog = EditShackDialog(self.window, shack)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            new_data = dialog.get_values(shack)

            # Warn if QTH changed without location data being updated
            old_qth = shack.get('qth', '').lower().strip()
            new_qth = new_data.get('qth', '').lower().strip()
            location_fields = ['maidenhead', 'wab', 'os_grid', 'lat', 'lon']
            location_changed = any(
                new_data.get(f) != shack.get(f) for f in location_fields
            )

            if new_qth != old_qth and not location_changed:
                warn = Gtk.MessageDialog(
                    transient_for=self.window,
                    modal=True,
                    message_type=Gtk.MessageType.WARNING,
                    buttons=Gtk.ButtonsType.NONE,
                    text='QTH changed without location update'
                )
                warn.format_secondary_text(
                    'You changed the QTH to "' + new_data.get('qth', '') +
                    '" but the grid, coordinates and locator still point to '
                    'the old location.\n\nUse the Setup Wizard to update '
                    'all location data together.'
                )
                warn.add_buttons(
                    'Save Anyway', Gtk.ResponseType.ACCEPT,
                    'Open Wizard', Gtk.ResponseType.HELP,
                    'Cancel',      Gtk.ResponseType.CANCEL,
                )
                warn_response = warn.run()
                warn.destroy()
                if warn_response == Gtk.ResponseType.CANCEL:
                    dialog.destroy()
                    return
                elif warn_response == Gtk.ResponseType.HELP:
                    dialog.destroy()
                    self.on_setup_wizard(None)
                    return

            # Auto-derive QRZ URL from callsign
            if new_data.get('callsign'):
                new_data['qrz'] = f"https://qrz.com/db/{new_data['callsign'].upper()}"
            save_shack(new_data)
            self.js(f"loadShack({json.dumps(new_data)});")
            self.resize_to_content(delay=200)
            self.js("showStatus('Shack info updated!', 'ok');")
        dialog.destroy()

    def on_set_scale(self, _, scale):
        self.scale = scale
        # Update checkmarks
        if hasattr(self, 'scale_items'):
            for val, (item, label) in self.scale_items.items():
                prefix = '✓ ' if abs(val - scale) < 0.01 else '  '
                item.set_label(prefix + label)
        # Save to shack.json
        try:
            with open(SHACK_JSON) as f:
                data = json.load(f)
            data['widget_scale'] = scale
            with open(SHACK_JSON, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Could not save scale: {e}")
        # Cancel any pending resize, apply zoom then do one clean resize
        self.webview.set_zoom_level(scale)
        # Debounce — wait 400ms after last scale change before measuring
        if hasattr(self, '_scale_timer') and self._scale_timer:
            GLib.source_remove(self._scale_timer)
        self._scale_timer = GLib.timeout_add(400, self._apply_scale_resize)
        self.js(f"showStatus('Scale set to {scale}×', 'ok');")

    def _apply_scale_resize(self):
        self._scale_timer = None
        # Single resize pass with enough delay for WebKit to fully re-render at new zoom
        self.resize_to_content(delay=500)
        return False

    def on_toggle_theme(self, _):
        self.theme = 'light' if self.theme == 'dark' else 'dark'
        self.js(f"setTheme('{self.theme}');")
        self.theme_item.set_label(
            'Switch to Dark Mode' if self.theme == 'light' else 'Switch to Light Mode'
        )
        # Save to shack.json
        try:
            with open(SHACK_JSON) as f:
                data = json.load(f)
            data['widget_theme'] = self.theme
            with open(SHACK_JSON, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
        self.resize_to_content(delay=200)

    def on_toggle_always_on_top(self, _):
        import os
        self.always_on_top = not self.always_on_top
        self.window.set_keep_above(self.always_on_top)
        self.aot_item.set_label('✓ Always on Top' if self.always_on_top else '  Always on Top')
        # Warn on Wayland where this has no effect
        if os.environ.get('XDG_SESSION_TYPE', '').lower() == 'wayland':
            if not getattr(self, '_aot_warned', False):
                self._aot_warned = True
                info = Gtk.MessageDialog(
                    transient_for=self.window,
                    modal=True,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    text='Always on Top unavailable on Wayland'
                )
                info.format_secondary_text(
                    'This feature works on X11 but Wayland does not allow '
                    'apps to control their own window stacking order.\n\n'
                    'The setting is saved for X11 sessions.'
                )
                info.run()
                info.destroy()

    def on_toggle_window(self, _):
        if self.window_visible:
            self.hide_window()
        else:
            self.show_window()

    def show_window(self):
        self.window.show_all()
        self.window.present()
        self.window_visible = True
        self.toggle_item.set_label('Hide Widget')

    def hide_window(self):
        self.window.hide()
        self.window_visible = False
        self.toggle_item.set_label('Show Widget')

    def on_delete_event(self, window, event):
        self.hide_window()
        return True

    def on_refresh(self, _):
        self.js("showStatus('Refreshing solar data…', 'pending');")
        def done():
            self.js("loadData(); showStatus('Solar data refreshed!', 'ok');")
            # ResizeObserver handles any resize needed
        run_fetcher(callback=done)

    def on_button_press(self, widget, event):
        if event.button == 1:
            # Store press position — only start drag if mouse actually moves
            self._drag_start = (event.x_root, event.y_root, event.time)
        return False

    def on_button_release(self, widget, event):
        self._drag_start = None
        return False

    def on_motion(self, widget, event):
        if self._drag_start and event.state & 0x100:  # button 1 held
            sx, sy, stime = self._drag_start
            if abs(event.x_root - sx) > 5 or abs(event.y_root - sy) > 5:
                self._drag_start = None
                self.window.begin_move_drag(
                    1, int(sx), int(sy), stime)
        return False

    def on_reload(self, _):
        # Just reload data from existing files - no subprocess fetch
        self.js("fetchShack(); loadData(); showStatus('Widget refreshed!', 'ok');")
        GLib.timeout_add(500, self._fetch_spots)

    def on_decide_policy(self, webview, decision, decision_type):
        import subprocess
        if decision_type.value_nick == 'navigation-action':
            nav = decision.get_navigation_action()
            url = nav.get_request().get_uri()
            if url.startswith('http') and not url.startswith('file://'):
                # Open URL directly in running browser to get focus
                GLib.timeout_add(100, lambda: self._raise_browser(url))
                decision.ignore()
                return True
        return False

    def _raise_browser(self, url):
        import subprocess
        try:
            # On Wayland, open the URL directly in the running browser
            # Firefox supports -new-tab to raise and focus
            procs = subprocess.run(['pgrep', '-x', 'firefox'],
                capture_output=True, text=True)
            if procs.stdout.strip():
                subprocess.Popen(['firefox', '--new-tab', url])
                return False
            procs = subprocess.run(['pgrep', '-x', 'chromium-browser'],
                capture_output=True, text=True)
            if procs.stdout.strip():
                subprocess.Popen(['chromium-browser', url])
                return False
            # Fallback
            subprocess.Popen(['xdg-open', url])
        except Exception as e:
            print(f"Browser raise failed: {e}")
        return False

    def on_title_changed(self, webview, _):
        # Title changes used to signal resize from section toggles
        title = webview.get_title() or ''
        if title.startswith('page-ready:'):
            self._page_ready = True
            return
        if title.startswith('open-wizard:'):
            self.on_setup_wizard(None)
            return
        if title.startswith('open-edit:'):
            self.on_edit_shack(None)
            return
        if title.startswith('solar-refresh:'):
            print("Stale solar data detected — refreshing")
            threading.Thread(target=lambda: run_fetcher(
                callback=lambda: GLib.idle_add(
                    lambda: self.js("loadData(); showStatus('Solar data refreshed!', 'ok');") or False
                )
            ), daemon=True).start()
            return
        if title.startswith('resize:'):
            # Only resize for section toggles, not scale changes
            # Use a generous debounce to ignore noise
            if hasattr(self, '_title_resize_timer') and self._title_resize_timer:
                GLib.source_remove(self._title_resize_timer)
            self._title_resize_timer = GLib.timeout_add(300, self._do_title_resize)

    def _do_title_resize(self):
        self._title_resize_timer = None
        # Only resize if not in middle of a scale change
        if not getattr(self, '_scale_timer', None):
            self.resize_to_content(delay=100)
        return False

    def on_quit(self, _):
        Gtk.main_quit()

app = ShackDashWidget()
Gtk.main()
