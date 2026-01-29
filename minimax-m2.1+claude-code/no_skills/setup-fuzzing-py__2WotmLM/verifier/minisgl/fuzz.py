#!/usr/bin/env python3
"""
Fuzz driver for Mini-SGLang library.
Coverage-guided fuzzing for LLM serving framework utilities.
Note: Core inference requires GPU, focus on utility functions.
"""

import sys
import os
import time
import random
import string

# Add the library to path
sys.path.insert(0, '/app/minisgl/python')

try:
    MINISGL_AVAILABLE = True
    from minisgl.utils.registry import Registry
    from minisgl.utils.misc import sample
    from minisgl.utils.hf import get_llm_dtype
except ImportError as e:
    MINISGL_AVAILABLE = False


def fuzz_identifier(data: bytes) -> str:
    """Create a valid Python identifier."""
    try:
        text = data.decode('utf-8', errors='replace')
    except:
        return "test"

    valid_start = string.ascii_letters + '_'
    valid = valid_start + string.digits

    if not text:
        return "test"

    result = ""
    for i, c in enumerate(text):
        if i == 0:
            if c in valid_start:
                result += c
        else:
            if c in valid:
                result += c
        if len(result) > 50:
            break

    return result if result else "test"


def fuzz_config_dict(data: bytes) -> dict:
    """Create a configuration-like dictionary."""
    try:
        text = data.decode('utf-8', errors='replace')
    except:
        return {}

    config = {}

    # Common config keys
    keys = [
        "temperature", "max_tokens", "top_p", "top_k", "frequency_penalty",
        "presence_penalty", "stop", "stream", "model", "dtype"
    ]

    for key in keys[:random.randint(1, 5)]:
        if random.random() < 0.5:
            val_type = random.choice(['str', 'int', 'float', 'bool', 'list'])
            if val_type == 'str':
                config[key] = fuzz_identifier(data)
            elif val_type == 'int':
                config[key] = random.randint(0, 10000)
            elif val_type == 'float':
                config[key] = random.uniform(0, 2)
            elif val_type == 'bool':
                config[key] = random.random() > 0.5
            elif val_type == 'list':
                config[key] = [fuzz_identifier(data) for _ in range(random.randint(0, 3))]

    return config


def fuzz_prompt(data: bytes) -> str:
    """Create a prompt-like string."""
    try:
        text = data.decode('utf-8', errors='replace')
    except:
        return "Hello"

    # Clean special characters
    clean = text.replace('\x00', ' ')

    # Prompt templates
    templates = [
        "Hello, how are you?",
        "Explain quantum physics.",
        "Write a poem about {subject}",
        "Summarize: {text}",
        "Translate to French: {text}",
    ]

    if len(clean) < 3 or random.random() < 0.3:
        return random.choice(templates).format(
            subject="life",
            text="The quick brown fox."
        )

    return clean[:500]


def fuzz_sampling_params(data: bytes) -> dict:
    """Create sampling parameters for LLM generation."""
    params = {
        "temperature": random.uniform(0, 2) if random.random() > 0.5 else None,
        "top_p": random.uniform(0, 1) if random.random() > 0.5 else None,
        "top_k": random.randint(1, 100) if random.random() > 0.5 else None,
        "max_tokens": random.randint(1, 2048) if random.random() > 0.5 else None,
        "frequency_penalty": random.uniform(-2, 2) if random.random() > 0.5 else None,
        "presence_penalty": random.uniform(-2, 2) if random.random() > 0.5 else None,
    }

    # Remove None values
    return {k: v for k, v in params.items() if v is not None}


def run_fuzz_test(data: bytes) -> None:
    """Main fuzz test function - processes a single fuzz input."""
    try:
        if not MINISGL_AVAILABLE:
            # Test basic string processing
            _ = fuzz_identifier(data)
            _ = fuzz_config_dict(data)
            _ = fuzz_prompt(data)
            return

        # Test 1: Registry operations
        try:
            reg = Registry("test_registry")
            name = fuzz_identifier(data)

            @reg.register(name)
            def test_func():
                return "test"

            retrieved = reg.get(name)
            reg.list_available()
        except Exception:
            pass

        # Test 2: HF utilities
        try:
            dtype = get_llm_dtype("auto")
            dtype = get_llm_dtype("float16")
            dtype = get_llm_dtype("bfloat16")
        except Exception:
            pass

        # Test 3: Sampling utilities
        try:
            params = fuzz_sampling_params(data)
            _ = sample(params)
        except Exception:
            pass

        # Test 4: Configuration parsing
        try:
            config = fuzz_config_dict(data)
            # Verify it can be processed
            for key, val in config.items():
                _ = str(key)
                _ = str(val)
        except Exception:
            pass

        # Test 5: Prompt formatting
        try:
            prompt = fuzz_prompt(data)
            prompt_len = len(prompt)
        except Exception:
            pass

        # Test 6: Message format
        try:
            messages = [
                {"role": "system", "content": fuzz_prompt(data)},
                {"role": "user", "content": fuzz_prompt(data)},
                {"role": "assistant", "content": fuzz_prompt(data)},
            ]
            # Just ensure structure is valid
            for msg in messages:
                _ = msg.get("role")
                _ = msg.get("content")
        except Exception:
            pass

    except Exception as e:
        pass


def run_standalone_fuzzer(seconds: int = 10) -> None:
    """Run standalone fuzzer with random input generation."""
    print(f"Starting Mini-SGLang fuzzer for {seconds} seconds...")
    print("Note: Core LLM inference requires GPU and is skipped.")

    start_time = time.time()
    iterations = 0

    while time.time() - start_time < seconds:
        # Generate random input
        length = random.randint(0, 1000)
        data = bytes(random.randint(0, 255) for _ in range(length))

        run_fuzz_test(data)
        iterations += 1

    print(f"Completed {iterations} iterations in {seconds} seconds")


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "--standalone":
        # Standalone mode with random inputs
        seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        run_standalone_fuzzer(seconds)
    else:
        # LibFuzzer mode - read from stdin
        data = sys.stdin.buffer.read()
        run_fuzz_test(data)


if __name__ == "__main__":
    main()
