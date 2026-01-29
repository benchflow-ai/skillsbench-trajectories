"""
LibFuzzer fuzz driver for IPython library.

Targets:
- InputTransformerManager.transform_cell()
- InputTransformerManager.check_complete()
- PrefilterManager.prefilter_line()
"""

import sys
from IPython.core.inputtransformer2 import TransformerManager
from IPython.core.prefilter import PrefilterManager
from IPython.core.interactiveshell import InteractiveShell

def fuzz(data):
    """Main fuzzing target for IPython library."""
    if not data:
        return

    try:
        # Decode input as UTF-8, ignoring errors
        cell_content = data.decode('utf-8', errors='ignore')

        if not cell_content or len(cell_content) > 100000:
            return

        # Initialize transformer and prefilter managers
        try:
            # Test 1: Transform cell
            tm = TransformerManager()
            try:
                result = tm.transform_cell(cell_content)
                if result:
                    pass
            except Exception:
                pass

            # Test 2: Check complete
            try:
                status, indent = tm.check_complete(cell_content)
                if status:
                    pass
            except Exception:
                pass

            # Test 3: Prefilter line (split into lines and test)
            lines = cell_content.split('\n')
            if lines:
                pm = PrefilterManager(shell=None)
                for line in lines[:10]:  # Limit lines to test
                    try:
                        pm.prefilter_line(line)
                    except Exception:
                        pass

        except Exception:
            pass

    except Exception:
        pass


if __name__ == '__main__':
    # Simple test mode
    test_input = b'x = 1\nprint(x)'
    fuzz(test_input)
    print("Fuzz target ready")
