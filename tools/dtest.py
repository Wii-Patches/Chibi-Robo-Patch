"""Dolphin test lab: a private user folder, scripted pipe input, and a GDB-stub memory reader.

  from dtest import Lab
  lab = Lab('/path/to/game.rvz', mode='gc')     # mode: 'gc' | 'cc' | 'nunchuk'
  lab.start(gecko=ini_text)                       # boots the game paused at the GDB stub
  lab.run(seconds)                                # lets it run
  lab.read(0x8052b8e8, 0x40)                      # reads memory (halts, reads, resumes)
  lab.press('gc', 'A'); lab.stick('gc', 'MAIN', x, y)
"""
import os, socket, subprocess, time, shutil

APP = '/Applications/Dolphin.app/Contents/MacOS/Dolphin'
GDB_PORT = 24000 + (os.getpid() % 900)


def ini(sections):
    out = []
    for name, kv in sections.items():
        out.append('[%s]' % name)
        out += ['%s = %s' % (k, v) for k, v in kv.items()]
    return '\n'.join(out) + '\n'


class Gdb:
    def __init__(self, port=GDB_PORT, timeout=60):
        end = time.time() + timeout
        while True:
            try:
                self.s = socket.create_connection(('127.0.0.1', port), timeout=5)
                break
            except OSError:
                if time.time() > end:
                    raise
                time.sleep(0.3)
        self.s.settimeout(10)
        self.buf = b''

    def _send(self, data):
        cs = sum(data.encode()) & 0xFF
        self.s.sendall(('$%s#%02x' % (data, cs)).encode())

    def _recv(self):
        while True:
            i = self.buf.find(b'#')
            if i != -1 and len(self.buf) >= i + 3:
                pkt = self.buf[:i + 3]
                self.buf = self.buf[i + 3:]
                j = pkt.find(b'$')
                self.s.sendall(b'+')
                return pkt[j + 1:i].decode()
            self.buf += self.s.recv(65536)
            self.buf = self.buf.lstrip(b'+')

    def cmd(self, c):
        self._send(c)
        return self._recv()

    def read(self, addr, n):
        out = b''
        while n > 0:
            k = min(n, 0x400)
            r = self.cmd('m%x,%x' % (addr, k))
            out += bytes.fromhex(r)
            addr += k
            n -= k
        return out

    def write(self, addr, data):
        return self.cmd('M%x,%x:%s' % (addr, len(data), data.hex()))

    def cont(self):
        self._send('c')

    def _drain(self, quiet=0.6):
        """The stub follows a break with an empty packet and a repeat stop reply: eat them."""
        self.s.settimeout(quiet)
        try:
            while True:
                self._recv()
        except (socket.timeout, TimeoutError):
            pass
        self.s.settimeout(10)
        self.buf = b''

    def halt(self):
        """Interrupt the CPU and swallow the stop reply (and any stale packets)."""
        self.s.sendall(b'\x03')
        end = time.time() + 15
        while time.time() < end:
            try:
                r = self._recv()
            except socket.timeout:
                break
            if r[:1] in ('T', 'S'):
                self._drain()
                return
        raise RuntimeError('no stop reply from the GDB stub')


class Lab:
    def __init__(self, game, mode='gc', root=None):
        here = os.path.dirname(os.path.abspath(__file__))
        self.game = game
        self.mode = mode
        self.root = root or os.path.join(here, '..', 'work', 'du')
        self.root = os.path.abspath(self.root)
        self.proc = None
        self.gdb = None
        self.pipes = {}

    # -- user folder ------------------------------------------------------
    def setup(self, gecko=''):
        r = self.root
        shutil.rmtree(r, ignore_errors=True)
        for d in ('Config', 'GameSettings', 'Pipes', 'Logs', 'ScreenShots', 'Wii', 'GC'):
            os.makedirs(os.path.join(r, d))
        open(os.path.join(r, 'Config', 'Dolphin.ini'), 'w').write(ini({
            'General': {'GDBPort': GDB_PORT},
            'Interface': {'ConfirmStop': 'False', 'UsePanicHandlers': 'False', 'OnScreenDisplayMessages': 'False'},
            'Input': {'BackgroundInput': 'True'},
            'Analytics': {'Enabled': 'False', 'PermissionAsked': 'True'},
            'Core': {'CPUCore': 4, 'MMU': 'False', 'EnableCheats': 'True', 'WiiSDCard': 'False',
                     'SIDevice0': 6 if self.mode == 'gc' else 0, 'SIDevice1': 0, 'SIDevice2': 0, 'SIDevice3': 0,
                     'EmulationSpeed': '1.0', 'AudioBackend': 'No Audio Output'},
            'DSP': {'Backend': 'No Audio Output'},
        }))
        open(os.path.join(r, 'Config', 'GFX.ini'), 'w').write(ini({
            'Settings': {'ShowFPS': 'False'}, 'Hardware': {'VSync': 'False'}}))
        for name in ('gc1', 'w1', 'w2'):
            p = os.path.join(r, 'Pipes', name)
            if not os.path.exists(p):
                os.mkfifo(p)
        self._pad_cfg()
        self._wiimote_cfg()
        if gecko:
            open(os.path.join(r, 'GameSettings', 'R24J01.ini'), 'w').write(gecko)

    def _pad_cfg(self):
        m = {'Device': 'Pipe/0/gc1'}
        for b in ('A', 'B', 'X', 'Y', 'Z', 'START'):
            m['Buttons/%s' % ('Start' if b == 'START' else b)] = '`Pipe/0/gc1:Button %s`' % b
        for d in ('UP', 'DOWN', 'LEFT', 'RIGHT'):
            m['D-Pad/%s' % d.capitalize()] = '`Pipe/0/gc1:Button D_%s`' % d
        for s, n in (('Main Stick', 'MAIN'), ('C-Stick', 'C')):
            for d, ax in (('Up', 'Y -'), ('Down', 'Y +'), ('Left', 'X -'), ('Right', 'X +')):
                m['%s/%s' % (s, d)] = '`Pipe/0/gc1:Axis %s %s`' % (n, ax)
        m['Triggers/L'] = '`Pipe/0/gc1:Button L`'
        m['Triggers/R'] = '`Pipe/0/gc1:Button R`'
        m['Triggers/L-Analog'] = '`Pipe/0/gc1:Axis L +`'
        m['Triggers/R-Analog'] = '`Pipe/0/gc1:Axis R +`'
        sect = {'GCPad1': m}
        open(os.path.join(self.root, 'Config', 'GCPadNew.ini'), 'w').write(ini(sect))

    def _wiimote_cfg(self):
        # Wii Remote 1: the remote on pipe w1 (buttons), extension on pipe w2
        m = {'Device': 'Pipe/0/w1', 'Source': 1}
        m['Buttons/A'] = '`Pipe/0/w1:Button A`'; m['Buttons/B'] = '`Pipe/0/w1:Button B`'
        m['Buttons/1'] = '`Pipe/0/w1:Button X`'; m['Buttons/2'] = '`Pipe/0/w1:Button Y`'
        m['Buttons/-'] = '`Pipe/0/w1:Button L`'; m['Buttons/+'] = '`Pipe/0/w1:Button R`'
        m['Buttons/Home'] = '`Pipe/0/w1:Button Z`'
        for d in ('Up', 'Down', 'Left', 'Right'):
            m['D-Pad/%s' % d] = '`Pipe/0/w1:Button D_%s`' % d.upper()
        for d, ax in (('Up', 'Y -'), ('Down', 'Y +'), ('Left', 'X -'), ('Right', 'X +')):
            m['IR/%s' % d] = '`Pipe/0/w1:Axis MAIN %s`' % ax        # the remote's pointer, for baselines
        if self.mode == 'cc':
            m['Extension'] = 'Classic'
            for k, v in (('A', 'A'), ('B', 'B'), ('X', 'X'), ('Y', 'Y'), ('ZL', 'L'), ('ZR', 'R'), ('+', 'START')):
                m['Classic/Buttons/%s' % k] = '`Pipe/0/w2:Button %s`' % v
            for d in ('Up', 'Down', 'Left', 'Right'):
                m['Classic/D-Pad/%s' % d] = '`Pipe/0/w2:Button D_%s`' % d.upper()
            for s, n in (('Left Stick', 'MAIN'), ('Right Stick', 'C')):
                for d, ax in (('Up', 'Y -'), ('Down', 'Y +'), ('Left', 'X -'), ('Right', 'X +')):
                    m['Classic/%s/%s' % (s, d)] = '`Pipe/0/w2:Axis %s %s`' % (n, ax)
            m['Classic/Triggers/L'] = '`Pipe/0/w2:Button L`'
            m['Classic/Triggers/R'] = '`Pipe/0/w2:Button R`'
        elif self.mode == 'nunchuk':
            m['Extension'] = 'Nunchuk'
            m['Nunchuk/Buttons/C'] = '`Pipe/0/w2:Button A`'
            m['Nunchuk/Buttons/Z'] = '`Pipe/0/w2:Button B`'
            for d, ax in (('Up', 'Y -'), ('Down', 'Y +'), ('Left', 'X -'), ('Right', 'X +')):
                m['Nunchuk/Stick/%s' % d] = '`Pipe/0/w2:Axis MAIN %s`' % ax
        else:
            m['Extension'] = 'None'
        w = {'Wiimote1': m,
             'Wiimote2': {'Source': 0}, 'Wiimote3': {'Source': 0}, 'Wiimote4': {'Source': 0},
             'BalanceBoard': {'Source': 0}}
        open(os.path.join(self.root, 'Config', 'WiimoteNew.ini'), 'w').write(ini(w))

    # -- running ----------------------------------------------------------
    def start(self, gecko='', gdb=True):
        self.setup(gecko)
        args = [APP, '-u', self.root, '-b', '-e', self.game]
        self.log = open(os.path.join(self.root, 'dolphin.out'), 'w')
        self.proc = subprocess.Popen(args, stdout=self.log, stderr=subprocess.STDOUT)
        for name in ('gc1', 'w1', 'w2'):     # open our end of each pipe (Dolphin opens read, non-blocking)
            pass
        for name in ('gc1', 'w1', 'w2'):     # Dolphin opens its (read) end once the controller interface is up
            p = os.path.join(self.root, 'Pipes', name)
            end = time.time() + 90
            while True:
                try:
                    self.pipes[name] = os.open(p, os.O_WRONLY | os.O_NONBLOCK)
                    break
                except OSError:
                    if time.time() > end:
                        raise
                    time.sleep(0.5)
        if gdb:
            self.gdb = Gdb()
            self.gdb.cont()

    def send(self, pipe, line):
        os.write(self.pipes[pipe], (line + '\n').encode())

    def run(self, seconds):
        time.sleep(seconds)

    def read(self, addr, n):
        self.gdb.halt()
        try:
            return self.gdb.read(addr, n)
        finally:
            self.gdb.cont()

    def stop(self):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except Exception:
                self.proc.kill()
            self.proc = None


def window_id(pid):
    """CGWindowID of the game window (title mentions Dolphin) belonging to `pid`, so we never capture other apps."""
    import Quartz
    for w in Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionAll, Quartz.kCGNullWindowID):
        if w.get('kCGWindowOwnerPID') == pid and 'Dolphin' in (w.get('kCGWindowName') or '') and w.get('kCGWindowIsOnscreen'):
            return w['kCGWindowNumber']
    return None


def shot(lab, path):
    wid = window_id(lab.proc.pid)
    if wid is None:
        return False
    return subprocess.call(['screencapture', '-x', '-l', str(wid), path]) == 0
