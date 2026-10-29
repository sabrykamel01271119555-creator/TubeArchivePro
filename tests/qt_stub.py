"""A tiny stand-in for PySide6 so the page LOGIC can be tested where Qt cannot be installed.
Only what the page needs is functional (combo boxes, line edits, labels, buttons, signals)."""
import sys
import types


class _Meta(type):
    def __getattr__(cls, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return Stub()


class Stub(metaclass=_Meta):
    def __init__(self, *a, **k):
        pass

    def __call__(self, *a, **k):
        return Stub()

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return Stub()

    def __or__(self, o): return Stub()
    __ror__ = __and__ = __rand__ = __or__
    def __int__(self): return 0
    def __iter__(self): return iter(())
    def width(self): return 100
    def height(self): return 100


class Signal:
    def __init__(self, *types): self.name = None
    def __set_name__(self, owner, name): self.name = name

    def __get__(self, inst, owner=None):
        if inst is None:
            return self
        key = "_sig_" + self.name
        if key not in inst.__dict__:
            inst.__dict__[key] = _Bound()
        return inst.__dict__[key]


class _Bound:
    def __init__(self): self.handlers = []
    def connect(self, f): self.handlers.append(f)
    def emit(self, *a):
        import inspect
        for h in list(self.handlers):
            try:
                params = list(inspect.signature(h).parameters.values())
            except (TypeError, ValueError):
                params = None
            if params is not None and not any(p.kind == p.VAR_POSITIONAL for p in params):
                n = len([p for p in params if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)])
                h(*a[:n])                      # like Qt: a slot may take fewer arguments than the signal sends
            else:
                h(*a)


class QObject(Stub): pass
class QWidget(Stub):
    def __init__(self, *a, **k): self._enabled = True
    def setEnabled(self, v): self._enabled = bool(v)
    def isEnabled(self): return self._enabled
    def window(self): return Stub()


class QLabel(QWidget):
    def __init__(self, text="", *a):
        super().__init__(); self._t = text if isinstance(text, str) else ""
    def setText(self, t): self._t = t
    def text(self): return self._t


class QLineEdit(QWidget):
    textChanged = Signal(str); returnPressed = Signal(); editingFinished = Signal()
    def __init__(self, text="", *a):
        super().__init__(); self._t = text if isinstance(text, str) else ""
    def setText(self, t):
        self._t = t; self.textChanged.emit(t)
    def text(self): return self._t


class QPushButton(QWidget):
    clicked = Signal()
    def __init__(self, text="", *a):
        super().__init__(); self._t = text if isinstance(text, str) else ""
    def setText(self, t): self._t = t
    def text(self): return self._t


class QProgressBar(QWidget):
    def __init__(self, *a): super().__init__(); self._v = 0
    def setValue(self, v): self._v = v
    def value(self): return self._v


class QPlainTextEdit(QWidget):
    def __init__(self, *a): super().__init__(); self.lines = []
    def appendHtml(self, h): self.lines.append(h)
    def toPlainText(self):
        import re
        return "\n".join(re.sub(r"<[^>]+>", "", l) for l in self.lines)


class QCheckBox(QPushButton):
    def isChecked(self): return False


class QComboBox(QWidget):
    currentIndexChanged = Signal(int)
    def __init__(self, *a):
        super().__init__(); self.items = []; self._i = -1; self._block = False
    def blockSignals(self, b): self._block = b
    def clear(self): self.items = []; self._i = -1
    def addItem(self, text, data=None): self.items.append((text, data))
    def insertSeparator(self, i): self.items.insert(i, ("---", None))
    def count(self): return len(self.items)
    def findData(self, d):
        for i, (_t, v) in enumerate(self.items):
            if v is not None and v == d:
                return i
        return -1
    def itemData(self, i): return self.items[i][1] if 0 <= i < len(self.items) else None
    def currentIndex(self): return self._i
    def currentData(self): return self.items[self._i][1] if 0 <= self._i < len(self.items) else None
    def setCurrentIndex(self, i):
        changed = i != self._i
        self._i = i
        if changed and not self._block:
            self.currentIndexChanged.emit(i)
    def labels(self): return [t for t, v in self.items if v is not None]


class QTimer(QObject):
    timeout = Signal()
    def start(self, *a): pass
    def stop(self): pass
    @staticmethod
    def singleShot(ms, fn): fn()


class QPixmap(Stub):
    def loadFromData(self, b): return False


class _Mod(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        cls = type(name, (Stub,), {})
        setattr(self, name, cls)
        return cls


def install():
    core, gui, widgets = _Mod("PySide6.QtCore"), _Mod("PySide6.QtGui"), _Mod("PySide6.QtWidgets")
    core.QObject, core.Signal, core.QTimer = QObject, Signal, QTimer
    gui.QPixmap = QPixmap
    for c in (QWidget, QLabel, QLineEdit, QPushButton, QProgressBar, QPlainTextEdit, QCheckBox, QComboBox):
        setattr(widgets, c.__name__, c)
    pkg = _Mod("PySide6")
    pkg.QtCore, pkg.QtGui, pkg.QtWidgets = core, gui, widgets
    sys.modules.update({"PySide6": pkg, "PySide6.QtCore": core, "PySide6.QtGui": gui,
                        "PySide6.QtWidgets": widgets})
