#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

# 添加video_player模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'video_player'))

from video_player.multi_tube_ui import MultiTubeUI


def main():
    """主函数，启动Fly Climbing多管子实验视频分析器"""
    # 创建QApplication实例
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName("Fly Climbing 多管子实验视频分析器")
    app.setApplicationVersion("1.0")
    
    # 创建主窗口
    window = MultiTubeUI()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()