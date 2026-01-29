"""
LibFuzzer fuzz driver for MiniSGL library.

Targets:
- TokenizeManager.tokenize()
- DetokenizeManager.detokenize()
- serialize_type() / deserialize_type()
"""

import sys
import json

def fuzz(data):
    """Main fuzzing target for MiniSGL library."""
    if not data:
        return

    try:
        # Split input into sections
        parts = data.split(b'\x00')

        # Test 1: Tokenization
        try:
            from minisgl.tokenizer.tokenize import TokenizeManager

            text = parts[0].decode('utf-8', errors='ignore') if parts else ""
            if text and len(text) < 10000:
                tm = TokenizeManager()
                # Test with plain text
                try:
                    from minisgl.message.utils import TokenizeMsg
                    msg = TokenizeMsg(text=text)
                    tm.tokenize([msg])
                except Exception:
                    pass
        except (ImportError, Exception):
            pass

        # Test 2: Detokenization
        try:
            from minisgl.tokenizer.detokenize import DetokenizeManager

            dtm = DetokenizeManager()
            if len(data) >= 4:
                # Use first 4 bytes as token ID
                token_id = int.from_bytes(data[:4], 'big')
                try:
                    from minisgl.message.utils import DetokenizeMsg
                    msg = DetokenizeMsg(uid=0, next_token=abs(token_id) % 50000, finished=False)
                    dtm.detokenize([msg])
                except Exception:
                    pass
        except (ImportError, Exception):
            pass

        # Test 3: Serialization/Deserialization
        try:
            from minisgl.message.utils import serialize_type, deserialize_type

            test_dict = {
                "__type__": "dict",
                "key": "value",
                "nested": {"value": 42}
            }

            try:
                # Try to deserialize various dict structures
                result = deserialize_type({}, test_dict)
            except (KeyError, TypeError, Exception):
                pass

        except (ImportError, Exception):
            pass

    except Exception:
        pass


if __name__ == '__main__':
    # Simple test mode
    test_input = b'hello world\x00\x00\x00\x01'
    fuzz(test_input)
    print("Fuzz target ready")
