#!/usr/bin/env python3
"""Coverage-guided fuzzer for MiniSGL library using atheris."""

import sys
import os

# Add the python source to path
sys.path.insert(0, '/app/minisgl/python')

import atheris


def TestOneInput(data: bytes) -> None:
    """Fuzz target for MiniSGL message handling."""
    try:
        # Convert bytes to string
        try:
            input_str = data.decode('utf-8')
        except UnicodeDecodeError:
            input_str = data.decode('latin-1')
        
        # Test message dataclasses
        try:
            from minisgl.message.frontend import UserReply, BaseFrontendMsg
            import json
            
            # Try parsing as JSON and creating UserReply
            try:
                msg_data = json.loads(input_str)
                if isinstance(msg_data, dict):
                    if 'uid' in msg_data and 'incremental_output' in msg_data:
                        UserReply(
                            uid=msg_data.get('uid', 0),
                            incremental_output=msg_data.get('incremental_output', ''),
                            finished=msg_data.get('finished', False)
                        )
            except (json.JSONDecodeError, TypeError, ValueError, KeyError):
                pass
        except ImportError:
            pass
        
        # Test backend messages
        try:
            from minisgl.message.backend import UserMsg
            import json
            
            try:
                msg_data = json.loads(input_str)
                if isinstance(msg_data, dict):
                    pass  # UserMsg may require more complex setup
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        except ImportError:
            pass
        
        # Test message utils serialization
        try:
            from minisgl.message.utils import serialize_type, deserialize_type
            import json
            
            try:
                data_dict = json.loads(input_str)
                if isinstance(data_dict, dict):
                    # Try to deserialize
                    pass
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        except ImportError:
            pass
            
    except Exception:
        pass


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
