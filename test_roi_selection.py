#!/usr/bin/env python
"""
测试ROI选择功能
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from video_player.multi_tube_ui import MultiTubeUI

def test_roi_selection():
    """测试ROI选择功能"""
    app = QApplication(sys.argv)
    window = MultiTubeUI()
    window.show()
    
    # 检查是否有"选择ROI区域"按钮
    roi_button = window.select_roi_btn
    if roi_button:
        print("✓ ROI选择按钮已添加到UI中")
        print(f"  按钮文本: {roi_button.text()}")
    else:
        print("✗ ROI选择按钮未找到")
        return False
        
    # 检查VideoDisplayWidget是否有ROI相关方法
    video_display = window.video_display
    if hasattr(video_display, 'start_roi_selection'):
        print("✓ VideoDisplayWidget有start_roi_selection方法")
    else:
        print("✗ VideoDisplayWidget缺少start_roi_selection方法")
        return False
        
    if hasattr(video_display, 'get_roi'):
        print("✓ VideoDisplayWidget有get_roi方法")
    else:
        print("✗ VideoDisplayWidget缺少get_roi方法")
        return False
        
    if hasattr(video_display, 'roi_selected'):
        print("✓ VideoDisplayWidget有roi_selected信号")
    else:
        print("✗ VideoDisplayWidget缺少roi_selected信号")
        return False
        
    # 检查MultiTubeUI是否有ROI相关方法
    if hasattr(window, 'start_roi_selection'):
        print("✓ MultiTubeUI有start_roi_selection方法")
    else:
        print("✗ MultiTubeUI缺少start_roi_selection方法")
        return False
        
    if hasattr(window, 'on_roi_selected'):
        print("✓ MultiTubeUI有on_roi_selected方法")
    else:
        print("✗ MultiTubeUI缺少on_roi_selected方法")
        return False
        
    print("\n所有ROI选择功能组件检查通过!")
    print("\n使用说明:")
    print("1. 加载视频文件")
    print("2. 播放视频或跳转到有内容的帧")
    print("3. 点击'选择ROI区域'按钮")
    print("4. 在视频显示区域拖动鼠标选择ROI")
    print("5. 选择完成后，ROI区域将用于管子检测")
    
    return app, window

if __name__ == "__main__":
    app, window = test_roi_selection()
    sys.exit(app.exec_())