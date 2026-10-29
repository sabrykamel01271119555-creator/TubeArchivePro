# 2.0.4 progress
Base 2.0.3. User report: (1) Settings buttons should read Apply & Save / Reset to Default / Cancel; (2) exit window Skip & Exit / Submit & Exit;
(3) console warning `QFont::setPointSize: Point size <= 0 (-1)` when running `python main.py`.
[x] 1,2 cause = Qt mnemonic '&' swallowed; fixed with widgets.mnemonic_safe on all buttons that can contain '&'
[x] 3 cannot reproduce (no Qt/PyPI in sandbox); main.py now logs the warning once with the Python stack to data/error.log (source unknown yet).
    NEXT: ask the user for data/error.log after running, then fix the source.

Update: user asked for 'and' wording as a safe alternative -> en.json MSG_081/082/297 = Skip and Exit / Submit and Exit / Apply and Save (Arabic already words). Qt install was tried at the user's request: pypi.org is denied (403) by the sandbox proxy -> no Qt here, do not retry.
Still open: QFont warning source -> ask user for data/error.log after running python main.py.
