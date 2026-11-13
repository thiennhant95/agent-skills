---
name: rust-setup
description: Installs the Rust toolchain. Use when the user wants Rust set up.
---
# Rust Setup

Install rustup:

```bash
curl https://sh.rustup.rs -sSf | sh -s -- -y
```

Then `source $HOME/.cargo/env` and check with `rustc --version`.
