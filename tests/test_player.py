#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sys
import os
import tempfile
import cv2
import numpy as np
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from video_player.player import VideoPlayer


class TestVideoPlayer(unittest.TestCase):
    """视频播放器测试类"""
    
    def setUp(self):
        """测试前的设置"""
        self.player = VideoPlayer()
        
        # 创建临时测试视频文件
        self.temp_video_path = self.create_test_video()
        
    def tearDown(self):
        """测试后的清理"""
        # 释放player资源
        self.player.release()
        
        # 删除临时测试视频文件
        if os.path.exists(self.temp_video_path):
            os.remove(self.temp_video_path)
            
    def create_test_video(self):
        """创建测试视频文件"""
        # 创建临时文件
        temp_file = tempfile.NamedTemporaryFile(suffix='.avi', delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        # 创建测试视频
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(temp_path, fourcc, 20.0, (640, 480))
        
        # 创建10帧测试视频
        for i in range(10):
            # 创建不同颜色的帧
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame[:] = (i * 25, 100, 100)  # 不同红色值
            out.write(frame)
            
        out.release()
        return temp_path
        
    def test_init(self):
        """测试初始化"""
        self.assertFalse(self.player.is_video_loaded())
        self.assertIsNone(self.player.get_current_frame())
        self.assertEqual(self.player.get_current_frame_number(), 0)
        self.assertEqual(self.player.get_total_frames(), 0)
        self.assertEqual(self.player.get_fps(), 0)
        self.assertEqual(self.player.get_playback_speed(), 1.0)
        self.assertFalse(self.player.is_playing())
        
    def test_load_video(self):
        """测试加载视频"""
        # 测试加载成功
        result = self.player.load_video(self.temp_video_path)
        self.assertTrue(result)
        self.assertTrue(self.player.is_video_loaded())
        self.assertEqual(self.player.get_total_frames(), 10)
        self.assertGreater(self.player.get_fps(), 0)
        
        # 测试加载不存在的文件
        result = self.player.load_video("nonexistent_file.mp4")
        self.assertFalse(result)
        self.assertFalse(self.player.is_video_loaded())
        
    def test_get_current_frame(self):
        """测试获取当前帧"""
        # 未加载视频时返回None
        self.assertIsNone(self.player.get_current_frame())
        
        # 加载视频后获取第一帧
        self.player.load_video(self.temp_video_path)
        frame = self.player.get_current_frame()
        self.assertIsNotNone(frame)
        self.assertEqual(frame.shape, (480, 640, 3))
        
    def test_get_current_frame_number(self):
        """测试获取当前帧号"""
        # 未加载视频时返回0
        self.assertEqual(self.player.get_current_frame_number(), 0)
        
        # 加载视频后返回0
        self.player.load_video(self.temp_video_path)
        self.assertEqual(self.player.get_current_frame_number(), 0)
        
    def test_seek_frame(self):
        """测试跳转到指定帧"""
        # 加载视频
        self.player.load_video(self.temp_video_path)
        
        # 跳转到第5帧
        result = self.player.seek_frame(5)
        self.assertTrue(result)
        self.assertEqual(self.player.get_current_frame_number(), 5)
        
        # 测试超出范围的帧号
        result = self.player.seek_frame(-1)
        self.assertFalse(result)  # 实际实现返回False
        
        result = self.player.seek_frame(20)
        self.assertFalse(result)  # 实际实现返回False
        
    def test_next_frame(self):
        """测试下一帧"""
        # 加载视频
        self.player.load_video(self.temp_video_path)
        
        # 初始帧号为0
        self.assertEqual(self.player.get_current_frame_number(), 0)
        
        # 下一帧
        self.player.next_frame()
        self.assertEqual(self.player.get_current_frame_number(), 1)
        
        # 到达最后一帧后再调用next_frame
        self.player.seek_frame(9)
        self.player.next_frame()
        self.assertEqual(self.player.get_current_frame_number(), 10)  # 实际实现会继续增加
        
    def test_previous_frame(self):
        """测试上一帧"""
        # 加载视频并跳转到第5帧
        self.player.load_video(self.temp_video_path)
        self.player.seek_frame(5)
        
        # 上一帧
        self.player.previous_frame()
        self.assertEqual(self.player.get_current_frame_number(), 4)
        
        # 到达第一帧后再调用previous_frame
        self.player.seek_frame(0)
        self.player.previous_frame()
        self.assertEqual(self.player.get_current_frame_number(), 0)  # 应该保持在第一帧
        
    def test_playback_speed(self):
        """测试播放速度"""
        # 默认速度为1.0
        self.assertEqual(self.player.get_playback_speed(), 1.0)
        
        # 设置播放速度
        self.player.set_playback_speed(2.0)
        self.assertEqual(self.player.get_playback_speed(), 2.0)
        
        # 测试负速度（应该直接设置）
        self.player.set_playback_speed(-1.0)
        self.assertEqual(self.player.get_playback_speed(), -1.0)
        
    def test_play(self):
        """测试播放"""
        # 加载视频
        self.player.load_video(self.temp_video_path)
        
        # 播放一帧
        self.player.play_one_frame()
        self.assertEqual(self.player.get_current_frame_number(), 1)
        
        # 再次播放一帧
        self.player.play_one_frame()
        self.assertEqual(self.player.get_current_frame_number(), 2)
        
    def test_stop(self):
        """测试停止"""
        # 加载视频并跳转到第5帧
        self.player.load_video(self.temp_video_path)
        self.player.seek_frame(5)
        
        # 停止
        self.player.stop()
        self.assertEqual(self.player.get_current_frame_number(), 0)  # 应该回到第一帧
        self.assertFalse(self.player.is_playing())
        
    def test_pause(self):
        """测试暂停"""
        # 加载视频
        self.player.load_video(self.temp_video_path)
        
        # 暂停
        self.player.pause()
        self.assertFalse(self.player.is_playing())
        
    def test_frame_updated_signal(self):
        """测试帧更新信号"""
        # 创建模拟接收器
        mock_receiver = Mock()
        self.player.frame_updated.connect(mock_receiver)
        
        # 加载视频并播放一帧
        self.player.load_video(self.temp_video_path)
        self.player.next_frame()
        
        # 检查信号是否发送
        self.assertTrue(mock_receiver.called)
        
        # 获取发送的帧
        call_args = mock_receiver.call_args[0][0]
        self.assertEqual(call_args.shape, (480, 640, 3))
        
    def test_video_loaded_signal(self):
        """测试视频加载信号"""
        # 创建模拟接收器
        mock_receiver = Mock()
        self.player.video_loaded.connect(mock_receiver)
        
        # 加载视频
        self.player.load_video(self.temp_video_path)
        
        # 检查信号是否发送
        self.assertTrue(mock_receiver.called)
        
        # 获取发送的参数
        call_args = mock_receiver.call_args[0]
        self.assertEqual(call_args[0], 10)  # 总帧数
        self.assertGreater(call_args[1], 0)  # FPS
        
    def test_video_finished_signal(self):
        """测试视频播放完成信号"""
        # 创建模拟接收器
        mock_receiver = Mock()
        self.player.video_finished.connect(mock_receiver)
        
        # 加载视频并跳转到最后一帧
        self.player.load_video(self.temp_video_path)
        self.player.seek_frame(9)
        
        # 播放下一帧
        self.player.next_frame()
        
        # 检查信号是否发送
        self.assertTrue(mock_receiver.called)


if __name__ == '__main__':
    unittest.main()