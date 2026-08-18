# Model worker contracts

The production C++ application should launch isolated workers for Python/PyTorch
backends. This package deliberately does not pretend that TRELLIS 2, Hunyuan3D,
SAM 3D or ComfyUI are embedded when their runtime is not installed.

Each worker should expose:
START -> HEALTH -> READY -> EXECUTE -> PROGRESS -> ARTIFACT -> VERIFY -> SHUTDOWN

Recommended transport: stdio JSON-RPC or localhost RPC with a strict schema.
