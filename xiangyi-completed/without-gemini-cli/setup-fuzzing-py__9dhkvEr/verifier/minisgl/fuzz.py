import sys
import atheris

try:
    from minisgl.message import TokenizeMsg
except ImportError:
    TokenizeMsg = None

def TestOneInput(data):
    if TokenizeMsg is None:
        return
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeString(sys.maxsize)
        TokenizeMsg(text=s)
    except Exception:
        pass

def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
