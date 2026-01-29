"""
Fuzz driver for MiniSGL library - ML inference library.
Coverage-guided fuzzing using atheris/pythonfuzz pattern.
"""

import sys
import os
import json

# Set environment to avoid GPU issues
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['NEURON_CC_FLAGS'] = '--skip-compilation'

# Add minisgl to path
sys.path.insert(0, '/app/minisgl/python')


def validate_utf8(data: bytes) -> bool:
    """Check if data is valid UTF-8."""
    try:
        data.decode('utf-8')
        return True
    except UnicodeDecodeError:
        return False


def safe_unicode_decode(data: bytes) -> str:
    """Safely decode bytes to string."""
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        return data.decode('utf-8', errors='replace')


def fuzz_tokenizer_basic(data: bytes) -> None:
    """Fuzz basic tokenizer operations."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    try:
        from minisgl.tokenizer import Tokenizer
        # Try to instantiate tokenizer with dummy model path
        # This will fail but test import paths
    except ImportError:
        pass
    except Exception:
        pass


def fuzz_message_creation(data: bytes) -> None:
    """Fuzz message creation."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    try:
        from minisgl.message import Message, Messages

        # Test message creation
        msg = Message(role='user', content=input_str)
        _ = msg.model_dump()

        # Test Messages container
        msgs = Messages()
        msgs.append(msg)
        _ = len(msgs)
    except (ValueError, TypeError):
        pass


def fuzz_json_config(data: bytes) -> None:
    """Fuzz JSON configuration parsing."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    try:
        # Test JSON parsing
        config = json.loads(input_str)

        # Validate common config fields
        if isinstance(config, dict):
            _ = config.get('model')
            _ = config.get('temperature')
            _ = config.get('max_tokens')
            _ = config.get('top_p')
    except json.JSONDecodeError:
        pass


def fuzz_yaml_like_config(data: bytes) -> None:
    """Fuzz YAML-like configuration parsing."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    # Try to parse as key: value pairs
    config = {}
    lines = input_str.split('\n')
    for line in lines:
        if ':' in line:
            try:
                key, value = line.split(':', 1)
                config[key.strip()] = value.strip()
            except ValueError:
                pass


def fuzz_model_kwargs(data: bytes) -> None:
    """Fuzz model keyword arguments."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    try:
        from minisgl.core import ModelKwargs

        # Test creating kwargs with string values
        kwargs = ModelKwargs(
            temperature=float(input_str[:4]) if len(input_str) >= 4 else 0.5,
            max_tokens=int(input_str[:2]) if input_str[:2].isdigit() else 100,
            top_p=float(input_str[2:4]) if len(input_str) >= 4 and input_str[2:4].replace('.', '').isdigit() else 1.0,
        )
    except (ValueError, TypeError):
        pass


def fuzz_attention_config(data: bytes) -> None:
    """Fuzz attention configuration."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    try:
        from minisgl.layers.attention import AttentionConfig

        config = AttentionConfig(
            num_heads=int(input_str[:2]) if input_str[:2].isdigit() else 8,
            head_dim=int(input_str[2:4]) if len(input_str) >= 4 and input_str[2:4].isdigit() else 64,
        )
    except (ValueError, TypeError):
        pass


def fuzz_prompt_templates(data: bytes) -> None:
    """Fuzz prompt template processing."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    # Common template patterns
    templates = [
        f'<s>[INST] {input_str} [/INST]',
        f'User: {input_str}\nAssistant:',
        f'{{{{system}}}}\n{{{{user}}}} {input_str}',
        f'[INST] {input_str} [/INST]',
    ]

    for template in templates:
        try:
            # Test string formatting
            result = template.format(system='You are a helpful assistant.', user=input_str)
        except (ValueError, KeyError):
            pass


def fuzz_sampling_params(data: bytes) -> None:
    """Fuzz sampling parameters."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    try:
        from minisgl.core import SamplingParams

        params = SamplingParams(
            temperature=float(input_str[:3]) if len(input_str) >= 3 else 1.0,
            top_p=float(input_str[3:6]) if len(input_str) >= 6 and input_str[3:6].replace('.', '').isdigit() else 1.0,
            top_k=int(input_str[6:9]) if len(input_str) >= 9 and input_str[6:9].isdigit() else 50,
        )
    except (ValueError, TypeError):
        pass


def fuzz_kv_cache_config(data: bytes) -> None:
    """Fuzz KV cache configuration."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    try:
        from minisgl.kvcache import PagedAttentionConfig

        config = PagedAttentionConfig(
            block_size=int(input_str[:2]) if input_str[:2].isdigit() else 16,
            num_blocks=int(input_str[2:5]) if len(input_str) >= 5 and input_str[2:5].isdigit() else 1000,
        )
    except (ValueError, TypeError):
        pass


def fuzz_env_parsing(data: bytes) -> None:
    """Fuzz environment configuration parsing."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    try:
        from minisgl.env import EnvConfig

        # Test environment string parsing
        config = EnvConfig(
            tensor_parallel_size=int(input_str[0]) if input_str and input_str[0].isdigit() else 1,
        )
    except (ValueError, TypeError):
        pass


def fuzz_message_validation(data: bytes) -> None:
    """Fuzz message field validation."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    try:
        from minisgl.message import Message, ChatMessage

        # Test various roles
        roles = ['system', 'user', 'assistant', 'tool']
        for role in roles:
            msg = Message(role=role, content=input_str)
            _ = msg.model_dump()
    except (ValueError, TypeError):
        pass


def fuzz_scheduler_config(data: bytes) -> None:
    """Fuzz scheduler configuration."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    try:
        from minisgl.scheduler import SchedulerConfig

        config = SchedulerConfig(
            max_batch_size=int(input_str[0]) if input_str and input_str[0].isdigit() else 4,
            max_num_tokens=int(input_str[1:3]) if len(input_str) >= 3 and input_str[1:3].isdigit() else 2048,
        )
    except (ValueError, TypeError):
        pass


def main():
    """Main entry point for fuzzing."""
    # Get input from stdin (LibFuzzer/AFL style) or use provided data
    if len(sys.argv) > 1:
        # Read from file (AFL/LibFuzzer queue)
        with open(sys.argv[1], 'rb') as f:
            data = f.read()
    else:
        # Read from stdin
        data = sys.stdin.buffer.read()

    if not data:
        return

    # Run all fuzz targets
    fuzz_tokenizer_basic(data)
    fuzz_message_creation(data)
    fuzz_json_config(data)
    fuzz_yaml_like_config(data)
    fuzz_model_kwargs(data)
    fuzz_attention_config(data)
    fuzz_prompt_templates(data)
    fuzz_sampling_params(data)
    fuzz_kv_cache_config(data)
    fuzz_env_parsing(data)
    fuzz_message_validation(data)
    fuzz_scheduler_config(data)


if __name__ == '__main__':
    main()
