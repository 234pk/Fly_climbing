#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
from cx_Freeze import setup, Executable

# 添加video_player模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'video_player'))

# 构建选项
build_exe_options = {
    "packages": ["os", "sys", "cv2", "numpy", "PyQt5", "PyQt5.QtCore", "PyQt5.QtGui", "PyQt5.QtWidgets", "matplotlib", "PIL", "PIL.Image"],
    "include_files": [
        ("video_player", "video_player"),
        ("example", "example"),
    ],
    "excludes": ["tkinter", "unittest"],
    "zip_include_packages": ["*"],
    "zip_exclude_packages": [],
}

# 基础信息
base = None
if sys.platform == "win32":
    base = "Win32GUI"  # 用于Windows GUI应用程序

setup(
    name="FlyClimbingAnalyzer",
    version="1.0",
    description="Fly Climbing 多管子实验视频分析器",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            "main.py",
            base=base,
            target_name="FlyClimbingAnalyzer.exe",
            icon=None,
        )
    ],
)