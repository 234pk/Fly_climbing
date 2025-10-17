#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cv2
import numpy as np
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QImage, QPixmap


class VideoPlayer(QObject):
    """视频播放器类，处理视频的加载、播放和帧提取"""
    
    # 定义信号
    frame_updated = pyqtSignal(np.ndarray)  # 帧更新信号
    video_loaded = pyqtSignal(int, int)     # 视频加载信号(总帧数, fps)
    video_finished = pyqtSignal()           # 视频播放完成信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 视频相关属性
        self.video_capture = None
        self.total_frames = 0
        self.current_frame = 0
        self.fps = 0
        self.is_playing_flag = False
        
        # 播放控制
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame)
        self.playback_speed = 1.0  # 播放速度倍率
        
        # 当前帧
        self.current_frame_image = None
        
    def load_video(self, video_path):
        """
        加载视频文件
        
        参数:
            video_path: 视频文件路径
            
        返回:
            是否成功加载视频
        """
        # 释放之前的视频
        if self.video_capture is not None:
            self.video_capture.release()
            
        # 尝试打开新视频
        self.video_capture = cv2.VideoCapture(video_path)
        
        if not self.video_capture.isOpened():
            return False
            
        # 获取视频信息
        self.total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.video_capture.get(cv2.CAP_PROP_FPS)
        self.current_frame = 0
        
        # 设置定时器间隔(毫秒)
        self.timer.setInterval(int(1000 / (self.fps * self.playback_speed)))
        
        # 读取第一帧
        ret, frame = self.video_capture.read()
        if ret:
            self.current_frame_image = frame.copy()
            self.frame_updated.emit(frame)
            
        # 发送视频加载信号
        self.video_loaded.emit(self.total_frames, self.fps)
        
        return True
        
    def play(self):
        """开始播放视频"""
        if self.video_capture is not None and not self.is_playing_flag:
            self.is_playing_flag = True
            self.timer.start()
            
    def pause(self):
        """暂停视频播放"""
        if self.is_playing_flag:
            self.is_playing_flag = False
            self.timer.stop()
            
    def stop(self):
        """停止视频播放并重置到开始位置"""
        self.pause()
        if self.video_capture is not None:
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.current_frame = 0
            ret, frame = self.video_capture.read()
            if ret:
                self.current_frame_image = frame.copy()
                self.frame_updated.emit(frame)
                
    def set_playback_speed(self, speed):
        """
        设置播放速度
        
        参数:
            speed: 播放速度倍率
        """
        self.playback_speed = speed
        if self.fps > 0:
            self.timer.setInterval(int(1000 / (self.fps * self.playback_speed)))
            
    def next_frame(self):
        """播放下一帧"""
        if self.video_capture is None:
            return
            
        ret, frame = self.video_capture.read()
        if ret:
            self.current_frame += 1
            self.current_frame_image = frame.copy()
            self.frame_updated.emit(frame)
        else:
            # 视频播放完成
            self.pause()
            self.video_finished.emit()
            
    def seek_frame(self, frame_number):
        """
        跳转到指定帧
        
        参数:
            frame_number: 帧编号
        """
        if self.video_capture is None or frame_number < 0 or frame_number >= self.total_frames:
            return False
            
        self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        self.current_frame = frame_number
        
        ret, frame = self.video_capture.read()
        if ret:
            self.current_frame_image = frame.copy()
            self.frame_updated.emit(frame)
            return True
        return False
        
    def get_current_frame(self):
        """获取当前帧图像"""
        return self.current_frame_image
        
    def get_current_frame_number(self):
        """获取当前帧编号"""
        return self.current_frame
        
    def get_total_frames(self):
        """获取总帧数"""
        return self.total_frames
        
    def get_fps(self):
        """获取视频帧率"""
        return self.fps
        
    def is_video_loaded(self):
        """检查视频是否已加载"""
        return self.video_capture is not None and self.video_capture.isOpened()
        
    def is_playing(self):
        """检查视频是否正在播放"""
        return self.is_playing_flag
        
    def is_video_playing(self):
        """检查视频是否正在播放（别名方法）"""
        return self.is_playing_flag
        
    def get_frame_at(self, frame_number):
        """
        获取指定帧的图像
        
        参数:
            frame_number: 帧编号
            
        返回:
            指定帧的图像，如果获取失败返回None
        """
        if self.video_capture is None or frame_number < 0 or frame_number >= self.total_frames:
            return None
            
        # 保存当前位置
        current_pos = self.video_capture.get(cv2.CAP_PROP_POS_FRAMES)
        
        # 跳转到指定帧
        self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.video_capture.read()
        
        # 恢复原来的位置
        self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, current_pos)
        
        if ret:
            return frame.copy()
        return None
        
    def get_playback_speed(self):
        """获取播放速度倍率"""
        return self.playback_speed
        
    def unload_video(self):
        """卸载当前视频"""
        if self.video_capture is not None:
            self.video_capture.release()
            self.video_capture = None
            
        # 重置状态
        self.total_frames = 0
        self.current_frame = 0
        self.fps = 0
        self.is_playing_flag = False
        self.current_frame_image = None
        
    def previous_frame(self):
        """播放上一帧"""
        if self.video_capture is None or self.current_frame <= 0:
            return
            
        self.current_frame -= 1
        self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.video_capture.read()
        if ret:
            self.current_frame_image = frame.copy()
            self.frame_updated.emit(frame)
            
    def play_one_frame(self):
        """播放一帧（用于测试）"""
        self.next_frame()
        
    def release(self):
        """释放视频资源"""
        if self.video_capture is not None:
            self.timer.stop()
            self.video_capture.release()
            self.video_capture = None
            self.is_playing_flag = False