#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试ROI区域选择和管子自动划分功能
"""

import sys
import os
import cv2
import numpy as np

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from video_player.multi_tube_ui import VideoPlayerApp
from video_player.multi_tube_detector import MultiTubeFlyDetector

def test_roi_and_tube_division():
    """测试ROI区域选择和管子自动划分功能"""
    print("开始测试ROI区域选择和管子自动划分功能...")
    
    # 创建一个简单的测试图像
    test_image = np.zeros((480, 640, 3), dtype=np.uint8)
    # 在图像上画一些内容以便观察
    cv2.rectangle(test_image, (100, 100), (500, 400), (255, 255, 255), 2)
    cv2.putText(test_image, "Test Video", (250, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # 保存测试图像
    cv2.imwrite("test_frame.jpg", test_image)
    
    print("已创建测试图像: test_frame.jpg")
    print("请在GUI中执行以下操作:")
    print("1. 点击'选择ROI区域'按钮")
    print("2. 在图像上拖拽选择一个区域")
    print("3. 观察状态栏是否显示ROI区域坐标和自动划分的管子区域")
    print("4. 关闭窗口完成测试")
    
    # 启动GUI应用
    app = VideoPlayerApp()
    
    # 如果需要加载测试图像，可以在这里添加代码
    # 这里我们依赖用户手动选择视频或使用现有功能
    
    return app

if __name__ == '__main__':
    app = test_roi_and_tube_division()
    # 注意: GUI应用需要在main.py中运行，这里只是提供测试逻辑说明
    print("\n测试说明:")
    print("请运行main.py启动应用程序，然后:")
    print("1. 加载一个视频文件或使用测试图像")
    print("2. 点击'选择ROI区域'按钮")
    print("3. 在显示的图像上拖拽选择一个区域")
    print("4. 应用会自动根据指定的管子数量划分管子区域")
    print("5. 检查状态栏是否正确显示ROI区域和管子区域信息")