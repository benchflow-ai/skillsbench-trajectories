import sys
import atheris
import unittest.mock

# Mock necessary modules before importing minisgl
sys.modules["torch"] = unittest.mock.MagicMock()
sys.modules["sgl_kernel"] = unittest.mock.MagicMock()
sys.modules["flashinfer"] = unittest.mock.MagicMock()
sys.modules["transformers"] = unittest.mock.MagicMock()

# Adjust path to find minisgl
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "python"))

from minisgl.tokenizer.detokenize import DetokenizeManager, find_printable_text
from minisgl.message import DetokenizeMsg

# Mock Tokenizer
class MockTokenizer:
    def __init__(self):
        self.eos_token_id = 2
    
    def batch_decode(self, token_ids_list, **kwargs):
        # Simple mock decoding: map int to char if possible, else '?'
        decoded = []
        for seq in token_ids_list:
            s = ""
            for t in seq:
                try:
                    # Map 0-255 to latin1 chars for simplicity, 
                    # larger to some placeholder or just unicode char if valid
                    if 0 <= t <= 1114111:
                         s += chr(t)
                    else:
                         s += "?"
                except:
                    s += "?"
            decoded.append(s)
        return decoded

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    
    # Fuzz find_printable_text
    try:
        text = fdp.ConsumeUnicode(100)
        find_printable_text(text)
    except Exception as e:
         pass

    # Fuzz DetokenizeManager
    tokenizer = MockTokenizer()
    manager = DetokenizeManager(tokenizer)
    
    # Create random msgs
    msgs = []
    num_msgs = fdp.ConsumeIntInRange(1, 10)
    for _ in range(num_msgs):
        uid = fdp.ConsumeIntInRange(0, 100)
        next_token = fdp.ConsumeIntInRange(0, 200) # Keep within ascii/printable range often
        finished = fdp.ConsumeBool()
        # Mock DetokenizeMsg object
        msg = unittest.mock.MagicMock()
        msg.uid = uid
        msg.next_token = next_token
        msg.finished = finished
        msgs.append(msg)
        
    try:
        manager.detokenize(msgs)
    except (UnicodeError, ValueError):
        pass
    except Exception as e:
        # Check if it's related to our mock
        pass

def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
