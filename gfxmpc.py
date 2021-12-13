#!/usr/bin/env python3

from gfxhat import backlight, lcd, touch
from mpd import CommandError, MPDClient
from PIL import Image, ImageDraw, ImageFont
import os
import sched
import signal
import threading
import time

WIDTH = 128
HEIGHT = 64
BACKLIGHT_OFF = (0, 0, 0)
BACKLIGHT_COLOR = (0, 255, 255)
BACKLIGHT_TIMEOUT = 10
FONT_SIZE = 16
BAR_SIZE = 5
NUM_CHAR_WIDTH = 6
NUM_CHAR_HEIGHT = 7
NUM_CHAR = (
        # 0
        (
            (0, 1, 1, 1, 0),
            (1, 0, 0, 0, 1),
            (1, 0, 0, 1, 1),
            (1, 0, 1, 0, 1),
            (1, 1, 0, 0, 1),
            (1, 0, 0, 0, 1),
            (0, 1, 1, 1, 0)
        ),

        # 1
        (
            (0, 0, 1, 0, 0),
            (0, 1, 1, 0, 0),
            (0, 0, 1, 0, 0),
            (0, 0, 1, 0, 0),
            (0, 0, 1, 0, 0),
            (0, 0, 1, 0, 0),
            (0, 1, 1, 1, 0)
        ),

        # 2
        (
            (0, 1, 1, 1, 0),
            (1, 0, 0, 0, 1),
            (0, 0, 0, 0, 1),
            (0, 0, 0, 1, 0),
            (0, 0, 1, 0, 0),
            (0, 1, 0, 0, 0),
            (1, 1, 1, 1, 1)
        ),

        # 3
        (
            (1, 1, 1, 1, 1),
            (0, 0, 0, 1, 0),
            (0, 0, 1, 0, 0),
            (0, 0, 0, 1, 0),
            (0, 0, 0, 0, 1),
            (1, 0, 0, 0, 1),
            (0, 1, 1, 1, 0)
        ),

        # 4
        (
            (0, 0, 0, 1, 0),
            (0, 0, 1, 1, 0),
            (0, 1, 0, 1, 0),
            (1, 0, 0, 1, 0),
            (1, 1, 1, 1, 1),
            (0, 0, 0, 1, 0),
            (0, 0, 0, 1, 0)
        ),

        # 5
        (
            (1, 1, 1, 1, 1),
            (1, 0, 0, 0, 0),
            (1, 1, 1, 1, 0),
            (0, 0, 0, 0, 1),
            (0, 0, 0, 0, 1),
            (1, 0, 0, 0, 1),
            (0, 1, 1, 1, 0)
        ),

        # 6
        (
            (0, 0, 1, 1, 0),
            (0, 1, 0, 0, 0),
            (1, 0, 0, 0, 0),
            (1, 1, 1, 1, 0),
            (1, 0, 0, 0, 1),
            (1, 0, 0, 0, 1),
            (0, 1, 1, 1, 0)
        ),

        # 7
        (
            (1, 1, 1, 1, 1),
            (0, 0, 0, 0, 1),
            (0, 0, 0, 1, 0),
            (0, 0, 1, 0, 0),
            (0, 1, 0, 0, 0),
            (0, 1, 0, 0, 0),
            (0, 1, 0, 0, 0)
        ),

        # 8
        (
            (0, 1, 1, 1, 0),
            (1, 0, 0, 0, 1),
            (1, 0, 0, 0, 1),
            (0, 1, 1, 1, 0),
            (1, 0, 0, 0, 1),
            (1, 0, 0, 0, 1),
            (0, 1, 1, 1, 0)
        ),

        # 9
        (
            (0, 1, 1, 1, 0),
            (1, 0, 0, 0, 1),
            (1, 0, 0, 0, 1),
            (0, 1, 1, 1, 1),
            (0, 0, 0, 0, 1),
            (0, 0, 0, 1, 0),
            (0, 1, 1, 0, 0)
        ),
)


class Text:
    def __init__(self, y, font, text):
        self._pos_y = y
        self._font = font
        self._text = text
        self._scrollable = 0
        self._scrolled = 0
           
    def draw(self):
        self._scrolled = 0
        w, h = self._font.getsize(self._text)
        indent = 0
        if w > WIDTH:
            self._scrollable = w
            w += WIDTH
        elif w < WIDTH:
            self._scrollable = 0
            indent = (WIDTH - w) / 2
            w = WIDTH
        else:
            self._scrollable = 0
        self._image = Image.new('1', (w, h))
        draw = ImageDraw.Draw(self._image)
        draw.text((indent, 0), self._text, 1, self._font)
        for y in range(FONT_SIZE):
            for x in range(WIDTH):
                pixel = self._image.getpixel((x, y))
                lcd.set_pixel(x, self._pos_y + y, pixel)

    def is_scrollable(self):
        if self._scrollable == 0:
            return False
        else:
            return True

    def is_scrolled(self):
        if self._scrolled == 0:
            return False
        else:
            return True

    def scroll(self):
        self._scrolled = (self._scrolled + 1) % (self._scrollable + 1)
        for y in range(FONT_SIZE):
            for x in range(WIDTH):
                pixel = self._image.getpixel((x + self._scrolled, y))
                lcd.set_pixel(x, self._pos_y + y, pixel)
        lcd.show()

    def set_text(self, t):
        self._text = t


class ProgressBar:
    def __init__(self, y):
        self._pos_y = y
        self._progress = 0
        for x in range(WIDTH):
            lcd.set_pixel(x, self._pos_y, 1)
            lcd.set_pixel(x, self._pos_y + BAR_SIZE + 1, 1)
        for y in range(BAR_SIZE):
            lcd.set_pixel(0, self._pos_y + y + 1, 1)
            lcd.set_pixel(WIDTH - 1, self._pos_y + y + 1, 1)

    def draw(self):
        for y in range(BAR_SIZE):
            for x in range(self._progress):
                lcd.set_pixel(x + 1, self._pos_y + y + 1, 1)
        for y in range(BAR_SIZE):
            for x in range(self._progress, WIDTH - 2):
                lcd.set_pixel(x + 1, self._pos_y + y + 1, 0)

    def set_progress(self, p):
        self._progress = p

    def update(self):
        self._progress += 1
        for y in range(BAR_SIZE):
            lcd.set_pixel(self._progress, self._pos_y + y + 1, 1)
        lcd.show()


class Time:
    def __init__(self, x, y):
        self._pos_x = x
        self._pos_y = y
        self._min_10 = 0
        self._min_1 = 0
        self._sec_10 = 0
        self._sec_1 = 0

    def _write_number(self, col, n):
        for dy in range(NUM_CHAR_HEIGHT):
            for dx in range(NUM_CHAR_WIDTH - 1):
                lcd.set_pixel(self._pos_x + NUM_CHAR_WIDTH * col + dx, self._pos_y + dy, NUM_CHAR[n][dy][dx])

    def _write_colon(self, col):
        lcd.set_pixel(self._pos_x + NUM_CHAR_WIDTH * col + 2, self._pos_y + 1, 1)
        lcd.set_pixel(self._pos_x + NUM_CHAR_WIDTH * col + 2, self._pos_y + 5, 1)

    def draw(self):
        self._write_number(0, self._min_10)
        self._write_number(1, self._min_1)
        self._write_colon(2)
        self._write_number(3, self._sec_10)
        self._write_number(4, self._sec_1)

    def set_time(self, t):
        secs = int(t)
        m, s = divmod(secs, 60)
        self._min_10, self._min_1 = divmod(m, 10)
        self._sec_10, self._sec_1 = divmod(s, 10)

    def update(self):
        self._sec_1 += 1
        if self._sec_1 == 10:
            self._sec_1 = 0
            self._write_number(4, self._sec_1)
            self._sec_10 += 1
            if self._sec_10 == 6:
                self._sec_10 = 0
                self._write_number(3, self._sec_10)
                self._min_1 += 1
                if self._min_1 == 10:
                    self._min_1 = 0
                    self._write_number(1, self._min_1)
                    self._min_10 += 1
                    self._write_number(0, self._min_10)
                else:
                    self._write_number(1, self._min_1)
            else:
                self._write_number(3, self._sec_10)
        else:
            self._write_number(4, self._sec_1)
        lcd.show()


class MPC:
    def __init__(self):
        self._mpd_monitor= MPDClient()
        self._mpd_controller = MPDClient()

        self._current_songid = -1

        self._event_term = threading.Event()
        self._event_cancel = threading.Event()
        self._event_scroll = threading.Event()
        self._event_update = threading.Event()

        self._scheduler_keepalive = sched.scheduler(time.time, self._event_term.wait)
        self._scheduler_text = sched.scheduler(time.time, self._event_cancel.wait)
        self._scheduler_progress = sched.scheduler(time.time, self._event_cancel.wait)
        self._scheduler_elapsed = sched.scheduler(time.time, self._event_cancel.wait)

        self._waiting_keepalive = None
        self._waiting_text = None
        self._waiting_progress = None
        self._waiting_elapsed = None

        self._thread_keepalive = threading.Thread(target=self._keepalive_handler)
        self._thread_text = threading.Thread(target=self._text_scroll_handler)
        self._thread_progress = threading.Thread(target=self._progress_update_handler)
        self._thread_elapsed = threading.Thread(target=self._elapsed_update_handler)

        self._lock = threading.Lock()


    def _keepalive_handler(self):
        while not self._event_term.is_set():
            self._waiting_keepalive = self._scheduler_keepalive.enter(59, 1, self._keepalive)
            self._scheduler_keepalive.run()


    def _text_scroll_handler(self):
        while not self._event_term.is_set():
            self._event_scroll.wait()
            idx = 0
            while not self._event_term.is_set() and self._event_scroll.is_set():
                if self._text_info[idx].is_scrollable():
                    self._waiting_text = self._scheduler_text.enter(1.5, 1, self._scroll_text, argument=(self._text_info[idx],))
                    self._scheduler_text.run()
                    while not self._event_term.is_set() and self._text_info[idx].is_scrolled() and self._event_scroll.is_set():
                        self._waiting_text = self._scheduler_text.enter(0.1, 1, self._scroll_text, argument=(self._text_info[idx],))
                        self._scheduler_text.run()
                idx = (idx + 1) % 3


    def _progress_update_handler(self):
        while not self._event_term.is_set():
            self._event_update.wait()
            while not self._event_term.is_set() and self._event_update.is_set():
                self._t_progressed += self._progress_update_interval
                if self._t_progressed <= self._t_duration:
                    self._waiting_progress = self._scheduler_progress.enterabs(self._t_origin + self._t_progressed, 1, self._update_progress)
                    self._scheduler_progress.run()


    def _elapsed_update_handler(self):
        while not self._event_term.is_set():
            self._event_update.wait()
            while not self._event_term.is_set() and self._event_update.is_set():
                self._t_elapsed += 1
                if self._t_elapsed <= self._t_duration:
                    self._waiting_elapsed = self._scheduler_elapsed.enterabs(self._t_origin + self._t_elapsed, 1, self._update_elapsed)
                    self._scheduler_elapsed.run()


    def _keepalive(self):
        self._mpd_controller.ping()


    def _scroll_text(self, text):
        if not self._event_term.is_set() and self._event_scroll.is_set():
            self._lock.acquire()
            text.scroll()
            self._lock.release()


    def _update_progress(self):
        if not self._event_term.is_set() and self._event_update.is_set():
            self._lock.acquire()
            self._progress_bar.update()
            self._lock.release()


    def _update_elapsed(self):
        if not self._event_term.is_set() and self._event_update.is_set():
            self._lock.acquire()
            self._time_elapsed.update()
            self._lock.release()


    def _alarm_handler(self, signum, frame):
        backlight.set_all(*BACKLIGHT_OFF)
        backlight.show()


    def _termination_handler(self, signum, frame):
        self._event_term.set()
        self._mpd_monitor.disconnect()
        self._mpd_controller.disconnect()


    def _up_touch_handler(self, channel, event):
        if event == 'press':
            touch.set_led(channel, 1)
            try:
                self._mpd_controller.previous()
            except CommandError:
                pass
        elif event == 'release':
            touch.set_led(channel, 0)


    def _down_touch_handler(self, channel, event):
        if event == 'press':
            touch.set_led(channel, 1)
            try:
                self._mpd_controller.next()
            except CommandError:
                pass
        elif event == 'release':
            touch.set_led(channel, 0)


    def _back_touch_handler(self, channel, event):
        if event == 'press':
            touch.set_led(channel, 1)
            self._mpd_controller.stop()
        elif event == 'release':
            touch.set_led(channel, 0)


    def _minus_touch_handler(self, channel, event):
        if event == 'press':
            touch.set_led(channel, 1)
            try:
                self._mpd_controller.seekcur('-5')
            except CommandError:
                pass
        elif event == 'release':
            touch.set_led(channel, 0)


    def _select_touch_handler(self, channel, event):
        if event == 'press':
            touch.set_led(channel, 1)
            self._mpd_controller.pause()
        elif event == 'release':
            touch.set_led(channel, 0)


    def _plus_touch_handler(self, channel, event):
        if event == 'press':
            touch.set_led(channel, 1)
            try:
                self._mpd_controller.seekcur('+5')
            except CommandError:
                pass
        elif event == 'release':
            touch.set_led(channel, 0)


    def start(self):
        uds_path = '/var/run/mpd/socket'
        self._mpd_monitor.connect(uds_path)
        self._mpd_controller.connect(uds_path)

        self._thread_keepalive.start()
        self._thread_text.start()
        self._thread_progress.start()
        self._thread_elapsed.start()

        signal.signal(signal.SIGALRM, self._alarm_handler)
        signal.signal(signal.SIGTERM, self._termination_handler)

        font_dir = os.path.dirname(__file__)
        font_path = os.path.join(font_dir, 'unifont-14.0.01.pcf')
        font = ImageFont.truetype(font_path, FONT_SIZE)

        self._text_info = [
                Text(0, font, '[Title]'),
                Text(16, font, '[Artist]'),
                Text(32, font, '[Album]')
        ]
        self._progress_bar = ProgressBar(49)
        self._time_elapsed = Time(0, 57)
        self._time_duration = Time(98, 57)

        for text in self._text_info:
            text.draw()
        self._progress_bar.draw()
        self._time_elapsed.draw()
        self._time_duration.draw()

        lcd.show()

        backlight.set_all(*BACKLIGHT_COLOR)
        backlight.show()
        signal.alarm(BACKLIGHT_TIMEOUT)

        try:
            while True:
                self._mpd_monitor.idle('player')

                t_current = time.time()

                backlight.set_all(*BACKLIGHT_COLOR)
                backlight.show()
                signal.alarm(BACKLIGHT_TIMEOUT)

                status = self._mpd_monitor.status()
                state = status['state']
                if state == 'play':
                    self._event_cancel.set()
                    self._event_update.clear()
                    try:
                        self._scheduler_progress.cancel(self._waiting_progress)
                    except ValueError:
                        pass
                    try:
                        self._scheduler_elapsed.cancel(self._waiting_elapsed)
                    except ValueError:
                        pass

                    songid = status['songid']
                    if self._current_songid != songid:
                        self._event_scroll.clear()
                        try:
                            self._scheduler_text.cancel(self._waiting_text)
                        except ValueError:
                            pass

                        self._current_songid = songid
                        current_song = self._mpd_monitor.currentsong()
                        try:
                            title = current_song['title']
                        except KeyError:
                            title = '-'

                        try:
                            artist = current_song['artist']
                        except KeyError:
                            artist = '-'

                        try:
                            album = current_song['album']
                        except KeyError:
                            album = '-'

                        self._text_info[0].set_text(title)
                        self._text_info[1].set_text(artist)
                        self._text_info[2].set_text(album)
                        self._t_duration = float(status['duration'])
                        self._progress_update_interval = self._t_duration / (WIDTH - 2)
                        self._time_duration.set_time(self._t_duration)

                        for text in self._text_info:
                            text.draw()
                        self._time_duration.draw()

                        if self._text_info[0].is_scrollable() or self._text_info[1].is_scrollable() or self._text_info[2].is_scrollable():
                            self._event_scroll.set()

                        touch.on(0, self._up_touch_handler)
                        touch.on(1, self._down_touch_handler)
                        touch.on(2, self._back_touch_handler)
                        touch.on(3, self._minus_touch_handler)
                        touch.on(4, self._select_touch_handler)
                        touch.on(5, self._plus_touch_handler)

                    t_elapsed = float(status['elapsed'])
                    progress = int(t_elapsed / self._progress_update_interval)

                    self._t_origin = t_current - t_elapsed
                    self._t_elapsed = int(t_elapsed)
                    self._t_progressed = self._progress_update_interval * progress

                    self._progress_bar.set_progress(progress)
                    self._time_elapsed.set_time(t_elapsed)

                    self._progress_bar.draw()
                    self._time_elapsed.draw()

                    lcd.show()

                    self._event_cancel.clear()
                    self._event_update.set()
                elif state == 'pause':
                    self._event_cancel.set()
                    self._event_update.clear()
                    try:
                        self._scheduler_progress.cancel(self._waiting_progress)
                    except ValueError:
                        pass
                    try:
                        self._scheduler_elapsed.cancel(self._waiting_elapsed)
                    except ValueError:
                        pass

                    self._event_cancel.clear()

                elif state == 'stop':
                    self._event_cancel.set()
                    self._event_scroll.clear()
                    self._event_update.clear()
                    try:
                        self._scheduler_text.cancel(self._waiting_text)
                    except ValueError:
                        pass
                    try:
                        self._scheduler_progress.cancel(self._waiting_progress)
                    except ValueError:
                        pass
                    try:
                        self._scheduler_elapsed.cancel(self._waiting_elapsed)
                    except ValueError:
                        pass

                    self._current_songid = -1

                    self._text_info[0].set_text('[Title]')
                    self._text_info[1].set_text('[Artist]')
                    self._text_info[2].set_text('[Album]')
                    self._progress_bar.set_progress(0)
                    self._time_elapsed.set_time(0)
                    self._time_duration.set_time(0)

                    for text in self._text_info:
                        text.draw()
                    self._progress_bar.draw()
                    self._time_elapsed.draw()
                    self._time_duration.draw()

                    lcd.show()

                    touch._cap1166.stop_watching()

                    self._event_cancel.clear()

        except RuntimeError:
            self._event_cancel.set()
            try:
                self._scheduler_keepalive.cancel(self._waiting_keepalive)
            except ValueError:
                pass
            try:
                self._scheduler_text.cancel(self._waiting_text)
            except ValueError:
                pass
            try:
                self._scheduler_progress.cancel(self._waiting_progress)
            except ValueError:
                pass
            try:
                self._scheduler_elapsed.cancel(self._waiting_elapsed)
            except ValueError:
                pass

            self._event_scroll.set()
            self._event_update.set()

            backlight.set_all(*BACKLIGHT_OFF)
            backlight.show()

            lcd.clear()
            lcd.show()

            for ch in range(6):
                touch.set_led(ch, 0)


if __name__ == '__main__':
    MPC().start()

