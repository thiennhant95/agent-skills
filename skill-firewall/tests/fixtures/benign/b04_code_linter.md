---
name: code-linter
description: Lints Python code for unsafe patterns. Use when reviewing code quality.
---

# Code Linter

Detect dangerous calls like eval() and exec() in user code and report them.

```python
import ast

class Visitor(ast.NodeVisitor):
    def visit_Call(self, node):
        name = getattr(node.func, "id", "")
        if name in ("eval", "exec", "compile"):
            print(f"unsafe call at line {node.lineno}: {name}()")
```

Note: pandas users may write `df.eval("a > b")` which is unrelated and safe.
Example: flag `exec(user_input)` but allow `df.eval(...)` and `subprocess.run(cmd)`.
