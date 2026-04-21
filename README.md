---
title: Reachy Assistant
emoji: 👋
colorFrom: red
colorTo: blue
sdk: static
pinned: false
short_description: Write your description here
tags:
 - reachy_mini
 - reachy_mini_python_app
---

# Reach Assistant

![Reachy Assistant](./docs/Reachy%20Mini_gatech.png)

## Project Setup

uv venv to create a virtual environment and install the dependencies:

```bash
uv venv
uv pip install "reachy-mini[mujoco]"
reachy-mini-app-assistant create
```


# Fix the gstreamer-python library to use the correct Python framework on macOS:
install_name_tool -change \
  /Library/Frameworks/Python.framework/Versions/3.12/Python \
  /opt/homebrew/opt/python@3.12/Frameworks/Python.framework/Versions/3.12/Python \
  .venv/lib/python3.12/site-packages/gstreamer_python/lib/gstreamer-1.0/libgstpython.dylib