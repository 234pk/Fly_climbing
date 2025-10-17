#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import json
from datetime import datetime
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QSlider, QSpinBox,
                            QTableWidget, QTableWidgetItem, QFileDialog, QGroupBox,
                            QGridLayout, QMessageBox, QHeaderView, QSplitter,
                            QTabWidget, QTextEdit, QComboBox, QCheckBox, QProgressBar,
                            QDialog, QLineEdit, QDialogButtonBox, QListWidget, QAbstractItemView, QAction)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QRect
from PyQt5.QtGui import QImage, QPixmap, QFont, QIcon, QPainter, QClipboard

from video_player.player import VideoPlayer
from video_player.multi_tube_detector import MultiTubeFlyDetector


class VideoListWidget(QListWidget):
    """支持拖放视频文件的视频列表控件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.parent_ui = None  # 用于引用父UI
        
    def set_parent_ui(self, parent_ui):
        """设置父UI引用"""
        self.parent_ui = parent_ui
        
    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            # 检查是否是视频文件
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                if file_path and self.is_video_file(file_path):
                    event.acceptProposedAction()
                    return
        event.ignore()
        
    def dragMoveEvent(self, event):
        """拖拽移动事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        """拖放事件"""
        if event.mimeData().hasUrls() and self.parent_ui:
            urls = event.mimeData().urls()
            video_files = []
            
            for url in urls:
                file_path = url.toLocalFile()
                if file_path and self.is_video_file(file_path):
                    video_files.append(file_path)
            
            if video_files:
                # 添加视频到列表
                self.parent_ui.add_videos_to_list(video_files)
                event.acceptProposedAction()
                
        event.ignore()
        
    def is_video_file(self, file_path):
        """检查文件是否是视频文件"""
        video_extensions = ['.avi', '.mp4', '.mov', '.mkv', '.mts', '.wmv', '.flv', '.webm']
        _, ext = os.path.splitext(file_path.lower())
        return ext in video_extensions


class VideoDisplayWidget(QWidget):
    """视频显示控件"""
    
    # 自定义信号
    roi_selected = pyqtSignal(tuple)  # ROI选择完成信号
    tube_region_moved = pyqtSignal(int, tuple)  # 管子区域移动信号 (索引, 新区域)
    fly_selected = pyqtSignal(int, tuple)  # 果蝇选择完成信号 (管子索引, 点击位置)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(640, 480)
        self.current_frame = None
        self.scale_factor = 1.0
        
        # ROI选择相关
        self.selecting_roi = False
        self.roi_start_point = None
        self.roi_end_point = None
        self.roi_rect = None
        
        # 管子区域相关
        self.tube_regions = []
        self.genotype_names = []
        
        # 管子区域拖动相关
        self.dragging_tube = False
        self.dragged_tube_index = -1
        self.drag_start_point = None
        self.drag_start_region = None
        
        # 手动选择果蝇相关
        self.manual_selecting = False  # 是否处于手动选择模式
        
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.current_frame is not None:
            # 计算缩放比例，使图像适应控件大小
            widget_width = self.width()
            widget_height = self.height()
            
            img_height, img_width, _ = self.current_frame.shape
            
            # 计算缩放比例，保持宽高比
            scale_x = widget_width / img_width
            scale_y = widget_height / img_height
            self.scale_factor = min(scale_x, scale_y)
            
            # 计算居中位置
            scaled_width = int(img_width * self.scale_factor)
            scaled_height = int(img_height * self.scale_factor)
            offset_x = (widget_width - scaled_width) // 2
            offset_y = (widget_height - scaled_height) // 2
            
            # 转换为QImage并显示
            height, width, channel = self.current_frame.shape
            bytes_per_line = 3 * width
            q_image = QImage(self.current_frame.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
            
            # 缩放图像
            scaled_pixmap = QPixmap.fromImage(q_image).scaled(scaled_width, scaled_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # 绘制图像
            painter.drawPixmap(offset_x, offset_y, scaled_pixmap)
            
            # 绘制ROI选择矩形
            if self.roi_start_point and self.roi_end_point:
                painter.setPen(Qt.red)
                painter.drawRect(QRect(self.roi_start_point, self.roi_end_point))
                
            # 绘制管子区域
            if self.tube_regions:
                painter.setPen(Qt.green)
                font = painter.font()
                font.setPointSize(12)
                font.setBold(True)
                painter.setFont(font)
                
                for i, region in enumerate(self.tube_regions):
                    if region is not None:
                        x, y, w, h = region
                        
                        # 转换为显示坐标
                        display_x = int(x * self.scale_factor) + offset_x
                        display_y = int(y * self.scale_factor) + offset_y
                        display_w = int(w * self.scale_factor)
                        display_h = int(h * self.scale_factor)
                        
                        # 如果正在拖动此管子，使用不同的颜色和样式
                        if self.dragging_tube and i == self.dragged_tube_index:
                            painter.setPen(Qt.yellow)  # 使用黄色表示正在拖动
                            painter.setBrush(Qt.NoBrush)
                            # 绘制虚线边框
                            painter.setPen(Qt.yellow)
                            painter.drawRect(display_x, display_y, display_w, display_h)
                        else:
                            painter.setPen(Qt.green)  # 正常状态使用绿色
                            painter.drawRect(display_x, display_y, display_w, display_h)
                        
                        # 绘制管子编号和基因型名称
                        genotype_name = self.genotype_names[i] if i < len(self.genotype_names) else f"管子{i+1}"
                        text = f"{genotype_name}"
                        painter.drawText(display_x + 5, display_y + 20, text)
                
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            # 检查是否点击了管子区域
            if not self.selecting_roi and self.tube_regions:
                tube_index = self.get_tube_at_position(event.pos())
                if tube_index >= 0:
                    # 开始拖动管子区域
                    self.dragging_tube = True
                    self.dragged_tube_index = tube_index
                    self.drag_start_point = event.pos()
                    self.drag_start_region = self.tube_regions[tube_index]
                    return
            
            # 原有的ROI选择逻辑
            if self.selecting_roi:
                self.roi_start_point = event.pos()
                self.roi_end_point = event.pos()
            
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        # 处理管子区域拖动
        if self.dragging_tube and self.dragged_tube_index >= 0:
            # 计算偏移量（转换为图像坐标）
            offset = self.calculate_image_offset(self.drag_start_point, event.pos())
            
            # 更新管子区域
            if self.drag_start_region:
                x, y, w, h = self.drag_start_region
                new_x = max(0, x + offset[0])
                new_y = max(0, y + offset[1])
                self.tube_regions[self.dragged_tube_index] = (new_x, new_y, w, h)
                
                # 发送信号通知管子区域已更新
                self.tube_region_moved.emit(self.dragged_tube_index, self.tube_regions[self.dragged_tube_index])
                
            self.update()
            return
            
        # 原有的ROI选择逻辑
        if self.selecting_roi and self.roi_start_point:
            self.roi_end_point = event.pos()
            self.update()
            
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            # 处理手动选择果蝇
            if self.manual_selecting:
                # 获取点击位置对应的管子
                tube_index = self.get_tube_at_position(event.pos())
                if tube_index >= 0:
                    # 转换为图像坐标
                    image_pos = self.display_to_image_coords(event.pos())
                    if image_pos:
                        # 发送果蝇选择信号
                        self.fly_selected.emit(tube_index, image_pos)
                return
                
            # 处理管子区域拖动结束
            if self.dragging_tube:
                self.dragging_tube = False
                self.dragged_tube_index = -1
                self.drag_start_point = None
                self.drag_start_region = None
                return
                
            # 原有的ROI选择逻辑
            if self.selecting_roi and self.roi_start_point:
                self.roi_end_point = event.pos()
                
                # 计算ROI区域
                if self.roi_start_point and self.roi_end_point:
                    # 转换为图像坐标
                    roi = self.calculate_roi()
                    if roi:
                        self.roi_rect = roi
                        self.roi_selected.emit(roi)
                        
                # 结束ROI选择
                self.selecting_roi = False
                self.roi_start_point = None
                self.roi_end_point = None
                self.update()
            
    def calculate_roi(self):
        """计算ROI区域（转换为图像坐标）"""
        if not self.roi_start_point or not self.roi_end_point or self.current_frame is None:
            return None
            
        # 获取图像显示区域
        widget_width = self.width()
        widget_height = self.height()
        
        img_height, img_width, _ = self.current_frame.shape
        
        # 计算缩放比例
        scale_x = widget_width / img_width
        scale_y = widget_height / img_height
        scale_factor = min(scale_x, scale_y)
        
        # 计算居中位置
        scaled_width = int(img_width * scale_factor)
        scaled_height = int(img_height * scale_factor)
        offset_x = (widget_width - scaled_width) // 2
        offset_y = (widget_height - scaled_height) // 2
        
        # 获取鼠标选择的矩形
        rect = QRect(self.roi_start_point, self.roi_end_point).normalized()
        
        # 转换为图像坐标
        x = max(0, int((rect.x() - offset_x) / scale_factor))
        y = max(0, int((rect.y() - offset_y) / scale_factor))
        w = min(img_width - x, int(rect.width() / scale_factor))
        h = min(img_height - y, int(rect.height() / scale_factor))
        
        # 确保ROI有效
        if w <= 0 or h <= 0:
            return None
            
        return (x, y, w, h)
        
    def start_roi_selection(self):
        """开始ROI选择"""
        self.selecting_roi = True
        self.roi_start_point = None
        self.roi_end_point = None
        self.roi_rect = None
        self.update()
        
    def get_roi(self):
        """获取当前ROI区域"""
        return self.roi_rect
        
    def update_frame(self, frame):
        """更新显示的帧"""
        self.current_frame = frame.copy()
        self.update()
        
    def get_scale_factor(self):
        """获取当前缩放比例"""
        return self.scale_factor
        
    def set_tube_regions(self, tube_regions, genotype_names=None):
        """
        设置管子区域用于显示
        
        参数:
            tube_regions: 管子区域列表，每个元素为 (x, y, width, height)
            genotype_names: 基因型名称列表
        """
        self.tube_regions = tube_regions or []
        self.genotype_names = genotype_names or [f"管子{i+1}" for i in range(len(tube_regions or []))]
        self.update()
        
    def get_tube_at_position(self, pos):
        """
        获取指定位置处的管子索引
        
        参数:
            pos: 鼠标位置 (QPoint)
            
        返回:
            管子索引，如果没有管子则返回-1
        """
        if not self.tube_regions or self.current_frame is None:
            return -1
            
        # 获取图像显示区域
        widget_width = self.width()
        widget_height = self.height()
        
        img_height, img_width, _ = self.current_frame.shape
        
        # 计算缩放比例
        scale_x = widget_width / img_width
        scale_y = widget_height / img_height
        scale_factor = min(scale_x, scale_y)
        
        # 计算居中位置
        scaled_width = int(img_width * scale_factor)
        scaled_height = int(img_height * scale_factor)
        offset_x = (widget_width - scaled_width) // 2
        offset_y = (widget_height - scaled_height) // 2
        
        # 检查每个管子区域
        for i, region in enumerate(self.tube_regions):
            if region is not None:
                x, y, w, h = region
                
                # 转换为显示坐标
                display_x = int(x * scale_factor) + offset_x
                display_y = int(y * scale_factor) + offset_y
                display_w = int(w * scale_factor)
                display_h = int(h * scale_factor)
                
                # 检查鼠标是否在管子区域内
                rect = QRect(display_x, display_y, display_w, display_h)
                if rect.contains(pos):
                    return i
                    
        return -1
        
    def calculate_image_offset(self, start_pos, end_pos):
        """
        计算鼠标移动的图像坐标偏移量
        
        参数:
            start_pos: 起始位置 (QPoint)
            end_pos: 结束位置 (QPoint)
            
        返回:
            图像坐标偏移量 (dx, dy)
        """
        if self.current_frame is None:
            return (0, 0)
            
        # 获取图像显示区域
        widget_width = self.width()
        widget_height = self.height()
        
        img_height, img_width, _ = self.current_frame.shape
        
        # 计算缩放比例
        scale_x = widget_width / img_width
        scale_y = widget_height / img_height
        scale_factor = min(scale_x, scale_y)
        
        # 计算偏移量（转换为图像坐标）
        dx = int((end_pos.x() - start_pos.x()) / scale_factor)
        dy = int((end_pos.y() - start_pos.y()) / scale_factor)
        
        return (dx, dy)
        
    def display_to_image_coords(self, display_pos):
        """
        将显示坐标转换为图像坐标
        
        参数:
            display_pos: 显示坐标 (QPoint)
            
        返回:
            图像坐标 (x, y) 或 None
        """
        if self.current_frame is None:
            return None
            
        # 获取图像显示区域
        widget_width = self.width()
        widget_height = self.height()
        
        img_height, img_width, _ = self.current_frame.shape
        
        # 计算缩放比例
        scale_x = widget_width / img_width
        scale_y = widget_height / img_height
        scale_factor = min(scale_x, scale_y)
        
        # 计算居中位置
        scaled_width = int(img_width * scale_factor)
        scaled_height = int(img_height * scale_factor)
        offset_x = (widget_width - scaled_width) // 2
        offset_y = (widget_height - scaled_height) // 2
        
        # 转换为图像坐标
        image_x = int((display_pos.x() - offset_x) / scale_factor)
        image_y = int((display_pos.y() - offset_y) / scale_factor)
        
        # 确保坐标在图像范围内
        if 0 <= image_x < img_width and 0 <= image_y < img_height:
            return (image_x, image_y)
        return None
        
    def start_manual_selection(self):
        """开始手动选择果蝇"""
        self.manual_selecting = True
        self.update()
        
    def stop_manual_selection(self):
        """停止手动选择果蝇"""
        self.manual_selecting = False
        self.update()


class MultiTubeUI(QMainWindow):
    """多管子果蝇检测主界面"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化组件
        self.video_player = VideoPlayer()
        self.detector = MultiTubeFlyDetector()
        
        # 初始化背景帧
        self.background_frame = None
        
        # 初始化初始帧和最终帧
        self.start_frame = 0
        self.end_frame = 0
        
        # ROI偏移相关
        self.roi_x_offset = 0
        self.roi_y_offset = 0
        self.original_tube_regions = []  # 保存原始的管子区域
        
        # 手动选择相关
        self.manual_selection_history = []  # 存储手动选择的历史记录
        self.manual_selecting = False  # 是否处于手动选择模式
        
        # 视频相关
        self.video_path = None
        self.background_frame = None
        
        # 视频列表相关
        self.video_list = []  # 存储视频路径列表
        self.current_video_index = -1  # 当前选中的视频索引
        
        # 记忆上次打开的文件夹路径
        self.last_opened_folder = ""  # 上次打开视频的文件夹路径
        
        # 初始化UI
        self.init_ui()
        self.connect_signals()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("Fly Climbing 多管子实验视频分析器")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧：视频列表和显示区域
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 视频列表区域
        video_list_group = QGroupBox("视频列表")
        video_list_layout = QVBoxLayout()
        
        # 视频导入按钮
        self.import_videos_btn = QPushButton("导入视频")
        video_list_layout.addWidget(self.import_videos_btn)
        
        # 视频列表控件
        self.video_list_widget = VideoListWidget()
        self.video_list_widget.setSelectionMode(QListWidget.SingleSelection)
        # 设置父UI引用，以便处理拖放事件
        self.video_list_widget.set_parent_ui(self)
        video_list_layout.addWidget(self.video_list_widget)
        
        # 视频操作按钮
        video_btn_layout = QHBoxLayout()
        self.remove_video_btn = QPushButton("移除视频")
        self.clear_videos_btn = QPushButton("清空列表")
        video_btn_layout.addWidget(self.remove_video_btn)
        video_btn_layout.addWidget(self.clear_videos_btn)
        video_list_layout.addLayout(video_btn_layout)
        
        video_list_group.setLayout(video_list_layout)
        left_layout.addWidget(video_list_group)
        
        # 视频显示控件
        self.video_display = VideoDisplayWidget()
        left_layout.addWidget(self.video_display)
        
        # 视频控制区域
        control_group = QGroupBox("视频控制")
        control_layout = QHBoxLayout()
        
        # 视频控制按钮
        self.open_btn = QPushButton("打开视频")
        self.play_pause_btn = QPushButton("播放")
        self.stop_btn = QPushButton("停止")
        
        control_layout.addWidget(self.open_btn)
        control_layout.addWidget(self.play_pause_btn)
        control_layout.addWidget(self.stop_btn)
        
        control_group.setLayout(control_layout)
        left_layout.addWidget(control_group)
        
        # 进度条
        progress_group = QGroupBox("视频进度")
        progress_layout = QVBoxLayout()
        
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_label = QLabel("0 / 0")
        
        progress_layout.addWidget(self.progress_slider)
        progress_layout.addWidget(self.progress_label)
        
        # 初始帧和最终帧设置
        frame_control_layout = QHBoxLayout()
        
        # 初始帧设置
        frame_control_layout.addWidget(QLabel("初始帧:"))
        self.start_frame_spin = QSpinBox()
        self.start_frame_spin.setRange(0, 1000000)
        self.start_frame_spin.setValue(0)
        frame_control_layout.addWidget(self.start_frame_spin)
        
        # 设置当前帧为初始帧按钮
        self.set_current_as_start_btn = QPushButton("设为初始帧")
        frame_control_layout.addWidget(self.set_current_as_start_btn)
        
        # 最终帧设置
        frame_control_layout.addWidget(QLabel("最终帧:"))
        self.end_frame_spin = QSpinBox()
        self.end_frame_spin.setRange(0, 1000000)
        self.end_frame_spin.setValue(0)
        frame_control_layout.addWidget(self.end_frame_spin)
        
        # 时间间隔设置
        frame_control_layout.addWidget(QLabel("时间间隔(s):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 30)
        self.interval_spin.setValue(5)
        frame_control_layout.addWidget(self.interval_spin)
        
        progress_layout.addLayout(frame_control_layout)
        
        progress_group.setLayout(progress_layout)
        left_layout.addWidget(progress_group)
        
        splitter.addWidget(left_widget)
        
        # 右侧：检测控制区域
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 检测控制选项卡
        tab_widget = QTabWidget()
        
        # 管子设置选项卡
        tube_tab = QWidget()
        tube_layout = QVBoxLayout()
        
        # 管子数量设置
        tube_count_group = QGroupBox("管子设置")
        tube_count_layout = QHBoxLayout()
        
        tube_count_layout.addWidget(QLabel("管子数量:"))
        self.tube_count_spin = QSpinBox()
        self.tube_count_spin.setRange(1, 10)
        self.tube_count_spin.setValue(5)
        tube_count_layout.addWidget(self.tube_count_spin)
        
        self.select_roi_btn = QPushButton("选择ROI区域")
        tube_count_layout.addWidget(self.select_roi_btn)
        
        tube_count_group.setLayout(tube_count_layout)
        tube_layout.addWidget(tube_count_group)
        
        # 管子信息表格
        tube_table_group = QGroupBox("管子信息")
        tube_table_layout = QVBoxLayout()
        
        self.tube_table = QTableWidget()
        self.tube_table.setColumnCount(3)
        self.tube_table.setHorizontalHeaderLabels(["管子编号", "基因型", "操作"])
        self.tube_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        tube_table_layout.addWidget(self.tube_table)
        tube_table_group.setLayout(tube_table_layout)
        tube_layout.addWidget(tube_table_group)
        
        tube_tab.setLayout(tube_layout)
        tab_widget.addTab(tube_tab, "管子设置")
        
        # 检测参数选项卡
        param_tab = QWidget()
        param_layout = QVBoxLayout()
        
        # 检测参数设置
        param_group = QGroupBox("检测参数")
        param_form_layout = QGridLayout()
        
        param_form_layout.addWidget(QLabel("背景减法阈值:"), 0, 0)
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(1, 100)
        self.threshold_spin.setValue(15)
        param_form_layout.addWidget(self.threshold_spin, 0, 1)
        
        param_form_layout.addWidget(QLabel("最小果蝇面积:"), 1, 0)
        self.min_area_spin = QSpinBox()
        self.min_area_spin.setRange(10, 500)
        self.min_area_spin.setValue(50)
        param_form_layout.addWidget(self.min_area_spin, 1, 1)
        
        param_form_layout.addWidget(QLabel("最大果蝇面积:"), 2, 0)
        self.max_area_spin = QSpinBox()
        self.max_area_spin.setRange(100, 2000)
        self.max_area_spin.setValue(500)
        param_form_layout.addWidget(self.max_area_spin, 2, 1)
        
        self.apply_param_btn = QPushButton("应用参数")
        param_form_layout.addWidget(self.apply_param_btn, 3, 0, 1, 2)
        
        # 添加优化按钮
        self.optimize_btn = QPushButton("优化最小面积")
        param_form_layout.addWidget(self.optimize_btn, 4, 0, 1, 2)
        
        param_group.setLayout(param_form_layout)
        param_layout.addWidget(param_group)
        param_tab.setLayout(param_layout)
        tab_widget.addTab(param_tab, "检测参数")
        
        # 检测结果选项卡
        result_tab = QWidget()
        result_layout = QVBoxLayout()
        
        # 实时检测结果
        result_group = QGroupBox("实时检测结果")
        result_table_layout = QVBoxLayout()
        
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels(["基因型", "当前高度", "最大高度", "平均高度", "排名"])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # 启用表格选择功能
        self.result_table.setSelectionMode(QAbstractItemView.ContiguousSelection)
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectItems)
        
        # 添加复制快捷键
        self.result_table.setContextMenuPolicy(Qt.ActionsContextMenu)
        copy_action = QAction("复制", self.result_table)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.copy_selected_cells)
        self.result_table.addAction(copy_action)
        
        result_table_layout.addWidget(self.result_table)
        result_group.setLayout(result_table_layout)
        result_layout.addWidget(result_group)
        
        # 检测控制按钮
        detection_control_layout = QHBoxLayout()
        
        self.final_frame_detection_btn = QPushButton("最终帧检测")
        self.reset_data_btn = QPushButton("重置数据")
        self.export_data_btn = QPushButton("导出数据")
        
        detection_control_layout.addWidget(self.final_frame_detection_btn)
        detection_control_layout.addWidget(self.reset_data_btn)
        detection_control_layout.addWidget(self.export_data_btn)
        
        result_layout.addLayout(detection_control_layout)
        
        # 手动选择果蝇区域
        manual_select_group = QGroupBox("手动选择果蝇")
        manual_select_layout = QVBoxLayout()
        
        # 手动选择说明
        manual_info_label = QLabel("点击按钮后，在视频上点击果蝇位置，系统将自动记录果蝇高度并添加到对应管子的数据表格中")
        manual_info_label.setWordWrap(True)
        manual_select_layout.addWidget(manual_info_label)
        
        # 手动选择按钮
        manual_button_layout = QHBoxLayout()
        
        self.manual_select_btn = QPushButton("开始手动选择")
        self.manual_select_btn.setEnabled(False)  # 初始状态禁用
        self.undo_last_select_btn = QPushButton("撤销上一次选择")
        self.undo_last_select_btn.setEnabled(False)  # 初始状态禁用
        
        manual_button_layout.addWidget(self.manual_select_btn)
        manual_button_layout.addWidget(self.undo_last_select_btn)
        
        manual_select_layout.addLayout(manual_button_layout)
        
        manual_select_group.setLayout(manual_select_layout)
        result_layout.addWidget(manual_select_group)
        
        result_tab.setLayout(result_layout)
        tab_widget.addTab(result_tab, "检测结果")
        
        right_layout.addWidget(tab_widget)
        
        # 状态栏
        self.status_label = QLabel("就绪")
        right_layout.addWidget(self.status_label)
        
        splitter.addWidget(right_widget)
        
        # 设置分割器比例
        splitter.setSizes([800, 400])
        
        # 初始化管子表格
        self.update_tube_table()
        
    def connect_signals(self):
        """连接信号和槽"""
        # 视频列表相关
        self.import_videos_btn.clicked.connect(self.import_videos)
        self.video_list_widget.itemClicked.connect(self.on_video_selected)
        self.remove_video_btn.clicked.connect(self.remove_video)
        self.clear_videos_btn.clicked.connect(self.clear_videos)
        
        # 视频控制按钮
        self.open_btn.clicked.connect(self.open_video)
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        self.stop_btn.clicked.connect(self.stop_video)
        
        # 视频播放器信号
        self.video_player.frame_updated.connect(self.on_frame_updated)
        self.video_player.video_loaded.connect(self.on_video_loaded)
        self.video_player.video_finished.connect(self.on_video_finished)
        
        # 进度条
        self.progress_slider.sliderMoved.connect(self.seek_frame)
        
        # 初始帧和最终帧设置
        self.set_current_as_start_btn.clicked.connect(self.set_current_as_start_frame)
        self.start_frame_spin.valueChanged.connect(self.on_start_frame_changed)
        self.end_frame_spin.valueChanged.connect(self.on_end_frame_changed)
        self.interval_spin.valueChanged.connect(self.on_interval_changed)
        
        # 管子设置
        self.tube_count_spin.valueChanged.connect(self.on_tube_count_changed)
        self.select_roi_btn.clicked.connect(self.start_roi_selection)
        
        # 连接视频显示控件的ROI选择信号
        self.video_display.roi_selected.connect(self.on_roi_selected)
        
        # 连接视频显示控件的管子区域移动信号
        self.video_display.tube_region_moved.connect(self.on_tube_region_moved)
        
        # 连接视频显示控件的果蝇选择信号
        self.video_display.fly_selected.connect(self.on_fly_selected)
        
        # 检测参数
        self.apply_param_btn.clicked.connect(self.apply_detection_params)
        self.optimize_btn.clicked.connect(self.optimize_min_area)
        
        # 检测控制
        self.final_frame_detection_btn.clicked.connect(self.final_frame_detection)
        self.reset_data_btn.clicked.connect(self.reset_detection_data)
        self.export_data_btn.clicked.connect(self.export_detection_data)
        
        # 手动选择控制
        self.manual_select_btn.clicked.connect(self.start_manual_selection)
        self.undo_last_select_btn.clicked.connect(self.undo_last_selection)
        
    def open_video(self):
        """打开视频文件（单视频模式，兼容原有功能）"""
        # 使用上次打开的文件夹路径作为默认路径
        start_folder = self.last_opened_folder if self.last_opened_folder else ""
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", start_folder, "视频文件 (*.avi *.mp4 *.mov *.mkv *.mts)"
        )
        
        if file_path:
            # 记录这次打开的文件夹路径
            self.last_opened_folder = os.path.dirname(file_path)
            
            # 清空当前列表
            self.video_list.clear()
            self.video_list.append(file_path)
            self.current_video_index = 0
            
            # 更新显示
            self.update_video_list()
            self.video_list_widget.setCurrentRow(0)
            
            # 加载视频
            self.load_current_video()
                
    def play_video(self):
        """播放当前视频"""
        if self.video_player.is_video_loaded():
            self.video_player.play()
            self.play_pause_btn.setText("暂停")
            self.status_label.setText("播放中...")
        else:
            QMessageBox.information(self, "提示", "请先选择一个视频")
            
    def pause_video(self):
        """暂停视频"""
        self.video_player.pause()
        self.status_label.setText("已暂停")
        
    def toggle_play_pause(self):
        """切换播放/暂停状态"""
        if self.video_player.is_video_loaded():
            if self.video_player.is_playing():
                self.video_player.pause()
                self.play_pause_btn.setText("播放")
                self.status_label.setText("已暂停")
            else:
                self.video_player.play()
                self.play_pause_btn.setText("暂停")
                self.status_label.setText("播放中...")
        else:
            QMessageBox.warning(self, "警告", "请先加载视频")
        
    def stop_video(self):
        """停止当前视频"""
        if self.video_player.is_video_loaded():
            self.video_player.stop()
            self.play_pause_btn.setText("播放")
            self.status_label.setText("已停止")
        
    def set_background_frame(self):
        """设置背景帧，根据初始帧和最终帧之间的大约15帧计算得到"""
        if not self.video_player.is_video_loaded():
            QMessageBox.warning(self, "警告", "请先加载视频")
            return
            
        if self.start_frame >= self.end_frame:
            QMessageBox.warning(self, "警告", "请先设置有效的初始帧和最终帧范围")
            return
            
        try:
            # 计算要采样的帧数（大约15帧）
            total_frames = self.end_frame - self.start_frame + 1
            sample_count = min(15, total_frames)
            
            # 计算采样间隔
            step = max(1, total_frames // sample_count)
            
            # 收集采样帧
            frames = []
            for i in range(sample_count):
                frame_number = self.start_frame + i * step
                if frame_number > self.end_frame:
                    break
                    
                # 获取指定帧
                frame = self.video_player.get_frame_at(frame_number)
                if frame is not None:
                    frames.append(frame)
                    
            if not frames:
                QMessageBox.warning(self, "警告", "无法获取指定范围内的帧")
                return
                
            # 计算平均背景帧
            if len(frames) == 1:
                self.background_frame = frames[0]
            else:
                # 将所有帧转换为float类型进行计算
                float_frames = [frame.astype(np.float32) for frame in frames]
                # 计算平均值
                avg_frame = np.mean(float_frames, axis=0)
                # 转换回uint8类型
                self.background_frame = np.clip(avg_frame, 0, 255).astype(np.uint8)
                
            # 设置背景帧
            self.detector.set_background(self.background_frame)
            self.status_label.setText(f"背景帧已设置（基于 {len(frames)} 帧的平均值）")
            self.statusBar().showMessage(f"背景帧已设置，采样了 {len(frames)} 帧")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"设置背景帧失败: {str(e)}")
            
    def seek_frame(self, position):
        """跳转到指定帧"""
        if self.video_player.is_video_loaded():
            self.video_player.seek_frame(position)
            
    def set_current_as_start_frame(self):
        """设置当前帧为初始帧"""
        if self.video_player.is_video_loaded():
            current_frame = self.video_player.get_current_frame_number()
            self.start_frame = current_frame
            self.start_frame_spin.setValue(current_frame)
            self.statusBar().showMessage(f"已将当前帧 {current_frame} 设置为初始帧")
            # 调用on_start_frame_changed方法来触发自动背景帧计算
            self.on_start_frame_changed(current_frame)
        else:
            QMessageBox.warning(self, "警告", "请先加载视频")
            
    def on_start_frame_changed(self, value):
        """处理初始帧变化"""
        self.start_frame = value
        # 确保初始帧不超过最终帧
        if self.end_frame > 0 and value > self.end_frame:
            self.start_frame_spin.setValue(self.end_frame)
            self.start_frame = self.end_frame
            self.statusBar().showMessage("初始帧不能大于最终帧")
        else:
            # 根据时间间隔自动更新最终帧
            self.update_end_frame_from_interval()
            
        # 自动计算并设置背景帧
        self.auto_set_background_frame()
    
    def auto_set_background_frame(self):
        """自动设置背景帧，根据初始帧和最终帧之间的大约15帧计算得到"""
        if not self.video_player.is_video_loaded():
            return
            
        if self.start_frame >= self.end_frame:
            return
            
        try:
            # 计算要采样的帧数（大约15帧）
            total_frames = self.end_frame - self.start_frame + 1
            sample_count = min(15, total_frames)
            
            # 计算采样间隔
            step = max(1, total_frames // sample_count)
            
            # 收集采样帧
            frames = []
            for i in range(sample_count):
                frame_number = self.start_frame + i * step
                if frame_number > self.end_frame:
                    break
                    
                # 获取指定帧
                frame = self.video_player.get_frame_at(frame_number)
                if frame is not None:
                    frames.append(frame)
                    
            if not frames:
                return
                
            # 计算平均背景帧
            if len(frames) == 1:
                self.background_frame = frames[0]
            else:
                # 将所有帧转换为float类型进行计算
                float_frames = [frame.astype(np.float32) for frame in frames]
                # 计算平均值
                avg_frame = np.mean(float_frames, axis=0)
                # 转换回uint8类型
                self.background_frame = np.clip(avg_frame, 0, 255).astype(np.uint8)
                
            # 设置背景帧
            self.detector.set_background(self.background_frame)
            self.status_label.setText(f"背景帧已自动设置（基于 {len(frames)} 帧的平均值）")
            self.statusBar().showMessage(f"背景帧已自动设置，采样了 {len(frames)} 帧")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"自动设置背景帧失败: {str(e)}")
            
    def on_end_frame_changed(self, value):
        """处理最终帧变化"""
        self.end_frame = value
        # 确保最终帧不小于初始帧
        if value < self.start_frame:
            self.end_frame_spin.setValue(self.start_frame)
            self.end_frame = self.start_frame
            self.statusBar().showMessage("最终帧不能小于初始帧")
            
        # 如果视频已加载，设置默认最终帧为初始帧+5秒的帧数
        if self.video_player.is_video_loaded() and self.start_frame == 0 and value == 0:
            fps = self.video_player.get_fps()
            if fps > 0:
                default_end_frame = min(int(self.start_frame + 5 * fps), self.video_player.get_total_frames() - 1)
                self.end_frame_spin.setValue(default_end_frame)
                self.end_frame = default_end_frame
        
    def on_frame_updated(self, frame):
        """处理帧更新信号"""
        # 更新视频显示
        self.video_display.update_frame(frame)
        
        # 传递管子区域信息给VideoDisplayWidget用于绘制
        self.video_display.set_tube_regions(self.detector.tube_regions, self.detector.genotype_names)
        
        # 更新进度条
        current = self.video_player.get_current_frame_number()
        total = self.video_player.get_total_frames()
        self.progress_slider.setMaximum(total - 1)
        self.progress_slider.setValue(current)
        self.progress_label.setText(f"{current} / {total}")
            
    def on_video_loaded(self, total_frames, fps):
        """处理视频加载完成信号"""
        self.progress_slider.setMaximum(total_frames - 1)
        self.progress_slider.setValue(0)
        self.progress_label.setText(f"0 / {total_frames}")
        
        # 设置初始帧和最终帧的范围
        self.start_frame_spin.setRange(0, total_frames - 1)
        self.end_frame_spin.setRange(0, total_frames - 1)
        
        # 视频加载时默认将最终帧设置为初始帧+5秒对应的帧数
        if fps > 0:
            # 计算初始帧+5秒对应的帧数
            default_end_frame = min(int(self.start_frame + 5 * fps), total_frames - 1)
            self.end_frame_spin.setValue(default_end_frame)
            self.end_frame = default_end_frame
            
        # 更新状态标签，显示当前视频信息
        if self.current_video_index >= 0 and self.current_video_index < len(self.video_list):
            video_path = self.video_list[self.current_video_index]
            self.status_label.setText(f"已加载视频: {os.path.basename(video_path)}")
        
    def on_video_finished(self):
        """处理视频播放完成信号"""
        self.status_label.setText("视频播放完成")
        
    def on_detection_completed(self, result):
        """处理检测完成信号"""
        # 更新检测结果表格
        self.update_result_table()
        
        # 检测完成后，启用手动选择按钮
        self.manual_select_btn.setEnabled(True)
        self.status_label.setText("检测完成，现在可以使用手动选择功能补充果蝇数据")
        
    def on_tube_count_changed(self, value):
        """处理管子数量变化"""
        self.detector.set_tube_count(value)
        self.update_tube_table()
        
    def update_tube_table(self):
        """更新管子表格"""
        tube_count = self.tube_count_spin.value()
        self.tube_table.setRowCount(tube_count)
        
        for i in range(tube_count):
            # 管子编号
            self.tube_table.setItem(i, 0, QTableWidgetItem(f"管子 {i+1}"))
            
            # 基因型名称
            genotype = self.detector.genotype_names[i] if i < len(self.detector.genotype_names) else f"管子{i+1}"
            self.tube_table.setItem(i, 1, QTableWidgetItem(genotype))
            
            # 操作按钮
            btn = QPushButton("设置基因型")
            btn.clicked.connect(lambda checked, idx=i: self.set_genotype(idx))
            self.tube_table.setCellWidget(i, 2, btn)
            
    def set_genotype(self, tube_index):
        """设置管子的基因型"""
        dialog = QDialog(self)
        dialog.setWindowTitle("设置基因型")
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("基因型名称:"))
        line_edit = QLineEdit()
        line_edit.setText(self.detector.genotype_names[tube_index])
        layout.addWidget(line_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            genotype = line_edit.text()
            if genotype:
                self.detector.set_genotype_name(tube_index, genotype)
                self.update_tube_table()
                
    def start_roi_selection(self):
        """开始ROI选择"""
        if not self.video_player.is_video_loaded():
            QMessageBox.warning(self, "警告", "请先加载视频")
            return
            
        if self.video_player.get_current_frame() is None:
            QMessageBox.warning(self, "警告", "请先播放视频或跳转到有内容的帧")
            return
            
        # 开始ROI选择
        self.video_display.start_roi_selection()
        self.statusBar().showMessage("请在视频上拖动鼠标选择ROI区域")
        
    def on_roi_selected(self, roi):
        """ROI选择完成处理"""
        if roi:
            x, y, w, h = roi
            self.statusBar().showMessage(f"ROI区域已选择: ({x}, {y}, {w}, {h})")
            
            # 自动划分管子区域
            try:
                # 获取当前帧
                frame = self.video_player.get_current_frame()
                if frame is not None:
                    # 获取管子数量
                    tube_count = self.tube_count_spin.value()
                    
                    # 使用检测器自动划分管子区域
                    tube_regions = self.detector.auto_detect_tubes(frame, roi, tube_count)
                    
                    if tube_regions:
                        # 设置管子区域到显示控件
                        self.video_display.set_tube_regions(tube_regions, self.detector.genotype_names)
                        
                        # 更新管子表格
                        self.update_tube_table()
                        self.statusBar().showMessage(f"ROI区域已选择并自动划分了 {len(tube_regions)} 个管子区域")
                    else:
                        self.statusBar().showMessage("ROI区域已选择，但未能划分管子区域")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"自动划分管子区域失败: {str(e)}")
        else:
            self.statusBar().showMessage("ROI选择无效，请重试")
        
    def apply_detection_params(self):
        """应用检测参数"""
        threshold = self.threshold_spin.value()
        min_area = self.min_area_spin.value()
        max_area = self.max_area_spin.value()
        
        self.detector.set_threshold(threshold)
        self.detector.min_area = min_area
        self.detector.max_area = max_area
        
        self.status_label.setText("检测参数已更新")
        
    def optimize_min_area(self):
        """优化最小果蝇面积参数"""
        if not self.video_player.is_video_loaded():
            QMessageBox.warning(self, "警告", "请先加载视频")
            return
            
        if self.background_frame is None:
            QMessageBox.warning(self, "警告", "请先设置背景帧")
            return
            
        # 检查是否所有管子都已设置区域
        all_set = True
        for i in range(self.detector.tube_count):
            if self.detector.tube_regions[i] is None:
                all_set = False
                break
                
        if not all_set:
            QMessageBox.warning(self, "警告", "请先设置所有管子的区域")
            return
        
        try:
            # 获取当前帧
            current_frame = self.video_player.get_current_frame()
            if current_frame is None:
                QMessageBox.warning(self, "警告", "无法获取当前帧")
                return
                
            # 获取所有果蝇的面积
            areas = self.detector.get_fly_areas(current_frame)
            
            if not areas:
                QMessageBox.warning(self, "警告", "未检测到果蝇，无法优化最小面积参数")
                return
                
            # 计算平均面积
            avg_area = sum(areas) / len(areas)
            
            # 计算优化后的最小面积（平均值的70%）
            optimized_min_area = int(avg_area * 0.7)
            
            # 确保优化后的最小面积在合理范围内
            optimized_min_area = max(10, min(optimized_min_area, 200))
            
            # 更新UI中的最小面积值
            self.min_area_spin.setValue(optimized_min_area)
            
            # 应用新的参数
            self.apply_detection_params()
            
            self.status_label.setText(f"最小果蝇面积已优化为: {optimized_min_area} (基于{len(areas)}个果蝇，平均面积: {avg_area:.1f})")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"优化最小面积失败: {str(e)}")
        
    def final_frame_detection(self):
        """执行最终帧检测，在最终帧前后十帧中找到最清晰的一帧，然后合并该帧及其前后两帧的检测结果"""
        if not self.video_player.is_video_loaded():
            QMessageBox.warning(self, "警告", "请先加载视频")
            return
            
        if self.background_frame is None:
            QMessageBox.warning(self, "警告", "请先设置背景帧")
            return
            
        # 检查是否所有管子都已设置区域
        all_set = True
        for i in range(self.detector.tube_count):
            if self.detector.tube_regions[i] is None:
                all_set = False
                break
                
        if not all_set:
            QMessageBox.warning(self, "警告", "请先设置所有管子的区域")
            return
        
        # 重置检测数据，避免多次检测导致数据累积
        self.detector.reset_data()
        
        try:
            self.status_label.setText("正在分析最终帧前后十帧，寻找最清晰的一帧...")
            
            # 获取最清晰的一帧及其前后两帧
            best_frames, best_frame_numbers, sharpness_scores = self.get_top_3_sharpest_frames()
            
            if not best_frames:
                QMessageBox.warning(self, "警告", "无法获取清晰的帧")
                return
                
            # 对每一帧执行果蝇检测
            all_detection_results = []
            for i, frame in enumerate(best_frames):
                self.status_label.setText(f"正在分析第{i+1}帧（第{best_frame_numbers[i]}帧）...")
                detection_results = self.detector.detect_all_tubes(frame)
                all_detection_results.append(detection_results)
            
            # 合并三帧的检测结果，查缺补漏
            merged_results = self.merge_detection_results(all_detection_results, best_frame_numbers, sharpness_scores)
            
            # 更新检测器的结果为合并后的结果
            self.detector.detection_results = merged_results
            
            # 更新结果表格
            self.update_result_table()
            
            # 在视频上标注合并后的果蝇位置
            self.annotate_flies(best_frames[0], merged_results)
            
            # 显示合并后的统计信息
            self.show_merge_statistics(all_detection_results, merged_results, best_frame_numbers, sharpness_scores)
            
            # 分析完成后，启用手动选择按钮
            self.manual_select_btn.setEnabled(True)
            self.status_label.setText("分析完成，现在可以使用手动选择功能补充果蝇数据")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"最终帧检测失败: {str(e)}")
            
    def get_top_3_sharpest_frames(self):
        """在最终帧前后十帧中找到最清晰的一帧，然后选择该帧及其前后两帧"""
        # 确定帧范围
        start_frame = max(0, self.end_frame - 10)
        end_frame = min(self.video_player.get_total_frames() - 1, self.end_frame + 10)
        
        frame_scores = []
        
        # 遍历范围内的每一帧，计算清晰度分数
        for frame_num in range(start_frame, end_frame + 1):
            # 获取当前帧
            self.video_player.seek_frame(frame_num)
            frame = self.video_player.get_current_frame()
            
            if frame is None:
                continue
                
            # 计算清晰度分数（使用拉普拉斯方差）
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            sharpness_score = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # 保存帧信息
            frame_scores.append({
                'frame': frame.copy(),
                'frame_number': frame_num,
                'sharpness_score': sharpness_score
            })
        
        # 按清晰度分数排序，选择最清晰的一帧
        frame_scores.sort(key=lambda x: x['sharpness_score'], reverse=True)
        sharpest_frame = frame_scores[0]
        sharpest_frame_num = sharpest_frame['frame_number']
        
        # 确定三帧的帧号：最清晰帧及其前后一帧
        frame_numbers = []
        # 确保不超出视频范围
        prev_frame = max(start_frame, sharpest_frame_num - 1)
        next_frame = min(end_frame, sharpest_frame_num + 1)
        
        # 添加前一帧、最清晰帧、后一帧（按顺序）
        frame_numbers = [prev_frame, sharpest_frame_num, next_frame]
        # 如果前一帧等于最清晰帧（即最清晰帧是第一帧），则调整为最清晰帧和后两帧
        if prev_frame == sharpest_frame_num:
            frame_numbers = [sharpest_frame_num, next_frame, min(end_frame, next_frame + 1)]
        # 如果后一帧等于最清晰帧（即最清晰帧是最后一帧），则调整为前两帧和最清晰帧
        elif next_frame == sharpest_frame_num:
            frame_numbers = [max(start_frame, prev_frame - 1), prev_frame, sharpest_frame_num]
        
        # 获取这三帧的图像和清晰度分数
        best_frames = []
        best_frame_numbers = []
        sharpness_scores = []
        
        for frame_num in frame_numbers:
            # 从已计算的帧分数中找到对应帧
            frame_info = next((item for item in frame_scores if item['frame_number'] == frame_num), None)
            if frame_info:
                best_frames.append(frame_info['frame'])
                best_frame_numbers.append(frame_info['frame_number'])
                sharpness_scores.append(frame_info['sharpness_score'])
        
        # 跳转到最清晰的帧位置
        self.video_player.seek_frame(sharpest_frame_num)
        
        # 显示使用了哪几帧
        frame_info = []
        for i, frame_num in enumerate(best_frame_numbers):
            frame_offset = frame_num - self.end_frame
            if frame_offset == 0:
                offset_text = "（原始最终帧）"
            elif frame_offset > 0:
                offset_text = f"（最终帧后{frame_offset}帧）"
            else:
                offset_text = f"（最终帧前{abs(frame_offset)}帧）"
            
            # 标记最清晰的帧
            if frame_num == sharpest_frame_num:
                offset_text += " [最清晰]"
            
            frame_info.append(f"第{frame_num}帧{offset_text}")
        
        self.statusBar().showMessage(f"已选择最清晰帧及其前后帧: {', '.join(frame_info)}")
        
        return best_frames, best_frame_numbers, sharpness_scores
    
    def merge_detection_results(self, all_detection_results, frame_numbers, sharpness_scores):
        """合并多帧的检测结果，查缺补漏"""
        # 初始化合并后的结果
        merged_results = []
        
        # 获取管子数量
        tube_count = len(all_detection_results[0]) if all_detection_results else 0
        
        # 对每个管子进行合并处理
        for tube_idx in range(tube_count):
            tube_flies = []
            fly_positions = {}  # 用于存储位置相近的果蝇
            
            # 遍历每一帧的检测结果
            for frame_idx, detection_results in enumerate(all_detection_results):
                frame_flies = detection_results[tube_idx]
                if frame_flies is None:
                    continue
                    
                # 处理当前帧中的每个果蝇
                for fly in frame_flies:
                    if fly is None:
                        continue
                        
                    fly_x, fly_y, fly_height = fly
                    
                    # 查找位置相近的果蝇（距离阈值：10像素）
                    found_similar = False
                    for pos_key, existing_fly in fly_positions.items():
                        existing_x, existing_y = pos_key
                        distance = ((fly_x - existing_x) ** 2 + (fly_y - existing_y) ** 2) ** 0.5
                        
                        if distance < 10:  # 如果距离小于10像素，认为是同一个果蝇
                            found_similar = True
                            # 更新果蝇信息：保留高度值较大的（更可能是完整的果蝇）
                            if fly_height > existing_fly['height']:
                                fly_positions[pos_key] = {
                                    'x': fly_x,
                                    'y': fly_y,
                                    'height': fly_height,
                                    'frame_idx': frame_idx,
                                    'frame_number': frame_numbers[frame_idx],
                                    'sharpness': sharpness_scores[frame_idx]
                                }
                            break
                    
                    # 如果没有找到相近的果蝇，添加新果蝇
                    if not found_similar:
                        fly_positions[(fly_x, fly_y)] = {
                            'x': fly_x,
                            'y': fly_y,
                            'height': fly_height,
                            'frame_idx': frame_idx,
                            'frame_number': frame_numbers[frame_idx],
                            'sharpness': sharpness_scores[frame_idx]
                        }
            
            # 将合并后的果蝇信息转换为列表格式
            for fly_info in fly_positions.values():
                tube_flies.append([fly_info['x'], fly_info['y'], fly_info['height']])
            
            merged_results.append(tube_flies if tube_flies else None)
        
        return merged_results
    
    def show_merge_statistics(self, all_detection_results, merged_results, frame_numbers, sharpness_scores):
        """显示合并结果的统计信息"""
        # 统计每帧检测到的果蝇数量
        frame_fly_counts = []
        for detection_results in all_detection_results:
            total_flies = 0
            for tube_flies in detection_results:
                if tube_flies:
                    total_flies += len(tube_flies)
            frame_fly_counts.append(total_flies)
        
        # 统计合并后的果蝇数量
        merged_total = 0
        for tube_flies in merged_results:
            if tube_flies:
                merged_total += len(tube_flies)
        
        # 创建统计信息文本
        stats_text = "多帧分析统计:\n"
        for i, (frame_num, count, sharpness) in enumerate(zip(frame_numbers, frame_fly_counts, sharpness_scores)):
            stats_text += f"第{frame_num}帧: 检测到{count}只果蝇 (清晰度: {sharpness:.2f})\n"
        
        stats_text += f"合并后: 共{merged_total}只果蝇\n"
        
        # 计算增量
        if frame_fly_counts:
            max_single_frame = max(frame_fly_counts)
            if merged_total > max_single_frame:
                stats_text += f"相比最佳单帧增加了{merged_total - max_single_frame}只果蝇"
            else:
                stats_text += "与最佳单帧检测数量相同"
        
        # 显示统计信息
        self.statusBar().showMessage(stats_text.replace('\n', ' | '))
        
        # 也可以使用对话框显示更详细的信息
        QMessageBox.information(self, "多帧分析统计", stats_text)
        
        # 分析完成后，启用手动选择按钮
        self.manual_select_btn.setEnabled(True)
        
    def on_tube_region_moved(self, tube_index, new_region):
        """处理管子区域移动事件"""
        # 更新检测器中的管子区域
        self.detector.tube_regions[tube_index] = new_region
        
        # 如果当前有视频帧，更新显示
        if self.video_player.is_video_loaded():
            current_frame = self.video_player.get_current_frame()
            if current_frame is not None:
                # 重新标注果蝇位置（使用当前检测结果）
                if hasattr(self.detector, 'detection_results'):
                    self.annotate_flies(current_frame, self.detector.detection_results)
        
        # 更新状态栏
        genotype_name = self.detector.genotype_names[tube_index] if tube_index < len(self.detector.genotype_names) else f"管子{tube_index+1}"
        self.status_label.setText(f"已移动{genotype_name}区域到新位置")
        
    def start_manual_selection(self):
        """开始或取消手动选择果蝇模式"""
        if not self.video_player.is_video_loaded():
            QMessageBox.warning(self, "警告", "请先加载视频")
            return
            
        # 切换手动选择模式
        if self.manual_selecting:
            # 取消手动选择模式
            self.video_display.stop_manual_selection()
            self.manual_selecting = False
            self.manual_select_btn.setText("开始手动选择")
            
            # 禁用撤销按钮（如果没有选择历史）
            if not self.manual_selection_history:
                self.undo_last_select_btn.setEnabled(False)
            
            # 更新状态栏
            self.status_label.setText("已取消手动选择模式")
        else:
            # 启用手动选择模式
            self.video_display.start_manual_selection()
            self.manual_selecting = True
            
            # 启用撤销按钮
            self.undo_last_select_btn.setEnabled(True)
            
            # 更新按钮文本
            self.manual_select_btn.setText("取消选择果蝇")
            
            # 更新状态栏
            self.status_label.setText("手动选择模式已启动，请在视频上点击果蝇位置")
        
    def undo_last_selection(self):
        """撤销上一次手动选择"""
        if not self.manual_selection_history:
            QMessageBox.information(self, "提示", "没有可撤销的选择")
            return
            
        # 移除最后一次选择
        last_selection = self.manual_selection_history.pop()
        tube_index, fly_x, fly_y, fly_height = last_selection
        
        # 从检测结果中移除对应的果蝇
        if hasattr(self.detector, 'detection_results') and self.detector.detection_results[tube_index] is not None:
            # 查找并移除匹配的果蝇
            flies = self.detector.detection_results[tube_index]
            for i, fly in enumerate(flies):
                if fly is not None:
                    fx, fy, fh = fly
                    # 检查位置是否匹配（允许一定误差）
                    if abs(fx - fly_x) < 5 and abs(fh - fly_height) < 3:
                        flies.pop(i)
                        break
        
        # 更新表格和显示
        self.update_result_table()
        
        # 如果当前有视频帧，更新显示
        if self.video_player.is_video_loaded():
            current_frame = self.video_player.get_current_frame()
            if current_frame is not None:
                if hasattr(self.detector, 'detection_results'):
                    self.annotate_flies(current_frame, self.detector.detection_results)
        
        # 更新状态栏
        genotype_name = self.detector.genotype_names[tube_index] if tube_index < len(self.detector.genotype_names) else f"管子{tube_index+1}"
        self.status_label.setText(f"已撤销{genotype_name}中的一次选择")
        
    def on_fly_selected(self, tube_index, image_pos):
        """处理果蝇选择事件"""
        if not self.manual_selecting:
            return
            
        # 获取点击位置
        fly_x, fly_y = image_pos
        
        # 获取管子区域
        tube_region = self.detector.tube_regions[tube_index]
        if tube_region is None:
            return
            
        x, y, w, h = tube_region
        
        # 计算果蝇高度（从管子底部算起）
        fly_height = y + h - fly_y
        
        # 确保高度在合理范围内
        if fly_height < 0:
            fly_height = 0
        elif fly_height > h:
            fly_height = h
        
        # 初始化检测结果（如果需要）
        if not hasattr(self.detector, 'detection_results'):
            self.detector.detection_results = [None] * self.detector.tube_count
            
        if self.detector.detection_results[tube_index] is None:
            self.detector.detection_results[tube_index] = []
            
        # 添加果蝇到检测结果
        self.detector.detection_results[tube_index].append((fly_x, fly_y, fly_height))
        
        # 记录到选择历史
        self.manual_selection_history.append((tube_index, fly_x, fly_y, fly_height))
        
        # 更新表格
        self.update_result_table()
        
        # 更新显示
        if self.video_player.is_video_loaded():
            current_frame = self.video_player.get_current_frame()
            if current_frame is not None:
                if hasattr(self.detector, 'detection_results'):
                    self.annotate_flies(current_frame, self.detector.detection_results)
        
        # 更新状态栏
        genotype_name = self.detector.genotype_names[tube_index] if tube_index < len(self.detector.genotype_names) else f"管子{tube_index+1}"
        self.status_label.setText(f"已在{genotype_name}中选择果蝇，高度: {int(fly_height)}像素")
        
    def on_roi_offset_changed(self):
        """处理ROI偏移值变化"""
        self.roi_x_offset = self.roi_x_offset_spin.value()
        self.roi_y_offset = self.roi_y_offset_spin.value()
        
    def apply_roi_offset(self):
        """应用ROI偏移，更新管子区域显示"""
        if not self.original_tube_regions:
            # 如果没有保存原始区域，先保存当前区域
            self.original_tube_regions = [region.copy() if region else None for region in self.detector.tube_regions]
            
        # 应用偏移到管子区域
        for i, region in enumerate(self.original_tube_regions):
            if region is not None:
                x, y, w, h = region
                # 应用偏移
                new_x = max(0, x + self.roi_x_offset)
                new_y = max(0, y + self.roi_y_offset)
                # 更新检测器中的管子区域
                self.detector.tube_regions[i] = (new_x, new_y, w, h)
        
        # 更新显示
        self.video_display.set_tube_regions(self.detector.tube_regions, self.detector.genotype_names)
        
        # 如果当前有视频帧，更新显示
        if self.video_player.is_video_loaded():
            current_frame = self.video_player.get_current_frame()
            if current_frame is not None:
                # 重新标注果蝇位置（使用当前检测结果）
                if hasattr(self.detector, 'detection_results'):
                    self.annotate_flies(current_frame, self.detector.detection_results)
        
        self.status_label.setText(f"已应用ROI偏移: X={self.roi_x_offset}, Y={self.roi_y_offset}")
        
    def reset_roi_offset(self):
        """重置ROI偏移"""
        self.roi_x_offset_spin.setValue(0)
        self.roi_y_offset_spin.setValue(0)
        self.roi_x_offset = 0
        self.roi_y_offset = 0
        
        # 恢复原始管子区域
        if self.original_tube_regions:
            self.detector.tube_regions = [region.copy() if region else None for region in self.original_tube_regions]
            self.video_display.set_tube_regions(self.detector.tube_regions, self.detector.genotype_names)
            
            # 如果当前有视频帧，更新显示
            if self.video_player.is_video_loaded():
                current_frame = self.video_player.get_current_frame()
                if current_frame is not None:
                    # 重新标注果蝇位置（使用当前检测结果）
                    if hasattr(self.detector, 'detection_results'):
                        self.annotate_flies(current_frame, self.detector.detection_results)
        
        self.status_label.setText("已重置ROI偏移")
        
    def reanalyze_with_roi_offset(self):
        """应用ROI偏移并重新分析"""
        if not self.video_player.is_video_loaded():
            QMessageBox.warning(self, "警告", "请先加载视频")
            return
            
        if self.background_frame is None:
            QMessageBox.warning(self, "警告", "请先设置背景帧")
            return
            
        # 检查是否所有管子都已设置区域
        all_set = True
        for i in range(self.detector.tube_count):
            if self.detector.tube_regions[i] is None:
                all_set = False
                break
                
        if not all_set:
            QMessageBox.warning(self, "警告", "请先设置所有管子的区域")
            return
            
        # 保存原始区域（如果尚未保存）
        if not self.original_tube_regions:
            self.original_tube_regions = [region.copy() if region else None for region in self.detector.tube_regions]
            
        # 应用ROI偏移
        self.apply_roi_offset()
        
        try:
            self.status_label.setText("正在使用偏移后的ROI进行分析...")
            
            # 获取最清晰的三帧及其检测结果
            best_frames, best_frame_numbers, sharpness_scores = self.get_top_3_sharpest_frames()
            
            if not best_frames:
                QMessageBox.warning(self, "警告", "无法获取清晰的帧")
                return
                
            # 对每一帧执行果蝇检测
            all_detection_results = []
            for i, frame in enumerate(best_frames):
                self.status_label.setText(f"正在分析第{i+1}帧（第{best_frame_numbers[i]}帧）...")
                detection_results = self.detector.detect_all_tubes(frame)
                all_detection_results.append(detection_results)
            
            # 合并三帧的检测结果，查缺补漏
            merged_results = self.merge_detection_results(all_detection_results, best_frame_numbers, sharpness_scores)
            
            # 更新检测器的结果为合并后的结果
            self.detector.detection_results = merged_results
            
            # 更新结果表格
            self.update_result_table()
            
            # 在视频上标注合并后的果蝇位置
            self.annotate_flies(best_frames[0], merged_results)
            
            # 显示合并后的统计信息
            self.show_merge_statistics(all_detection_results, merged_results, best_frame_numbers, sharpness_scores)
            
            # 添加ROI偏移信息到统计
            offset_info = f"\nROI偏移: X={self.roi_x_offset}, Y={self.roi_y_offset}"
            self.status_label.setText(self.status_label.text() + offset_info)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"使用偏移ROI重新分析失败: {str(e)}")
            
    def annotate_flies(self, frame, detection_results):
        """在视频上标注果蝇位置"""
        annotated_frame = frame.copy()
        
        # 遍历所有管子的检测结果
        for tube_idx, flies in enumerate(detection_results):
            if flies is None:
                continue
                
            # 获取管子区域
            tube_region = self.detector.tube_regions[tube_idx]
            if tube_region is None:
                continue
                
            x, y, w, h = tube_region
            
            # 绘制管子区域
            cv2.rectangle(annotated_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # 绘制管子标签
            genotype_name = self.detector.genotype_names[tube_idx] if tube_idx < len(self.detector.genotype_names) else f"管子{tube_idx+1}"
            cv2.putText(annotated_frame, genotype_name, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # 绘制果蝇位置
            for fly in flies:
                if fly is None:
                    continue
                    
                # 获取果蝇位置和高度
                fly_x, fly_y, fly_height = fly
                
                # 计算果蝇在管子中的相对位置
                relative_y = y + h - fly_height  # 从管子底部计算高度
                
                # 绘制果蝇位置
                cv2.circle(annotated_frame, (fly_x, int(relative_y)), 8, (0, 0, 255), 1)
                
                # 绘制果蝇高度标注
                cv2.putText(annotated_frame, f"{int(fly_height)}", (fly_x-20, int(relative_y)-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        
        # 更新显示
        self.video_display.update_frame(annotated_frame)

    def on_interval_changed(self, value):
        """处理时间间隔变化"""
        # 如果视频已加载，根据时间间隔自动计算最终帧
        if self.video_player.is_video_loaded():
            self.update_end_frame_from_interval()
            
    def update_end_frame_from_interval(self):
        """根据时间间隔更新最终帧"""
        if self.video_player.is_video_loaded():
            fps = self.video_player.get_fps()
            if fps > 0:
                # 获取当前时间间隔（秒）
                interval = self.interval_spin.value()
                # 计算最终帧：初始帧 + 时间间隔 * 帧率
                calculated_end_frame = int(self.start_frame + interval * fps)
                # 确保最终帧不超过视频总帧数
                total_frames = self.video_player.get_total_frames()
                final_end_frame = min(calculated_end_frame, total_frames - 1)
                # 更新最终帧
                self.end_frame = final_end_frame
                self.end_frame_spin.setValue(final_end_frame)

    def update_result_table(self):
        """更新检测结果表格，转置显示并将高度表示为百分比"""
        # 获取管子数量
        tube_count = self.detector.tube_count
        
        # 获取每个管子的所有果蝇高度
        all_fly_heights = []
        max_fly_count = 0
        tube_heights = []  # 存储每个管子的高度
        
        for i in range(tube_count):
            # 直接从detection_results获取果蝇高度数据
            fly_heights = []
            if hasattr(self.detector, 'detection_results') and i < len(self.detector.detection_results):
                if self.detector.detection_results[i] is not None:
                    for fly_data in self.detector.detection_results[i]:
                        # fly_data格式为 (x, y, height)
                        if len(fly_data) >= 3:
                            fly_heights.append(fly_data[2])
            
            all_fly_heights.append(fly_heights)
            max_fly_count = max(max_fly_count, len(fly_heights))
            tube_heights.append(self.detector.get_tube_height(i))
        
        # 转置表格：行是果蝇，列是管子
        # 设置表格行数和列数
        self.result_table.setRowCount(max_fly_count)
        # 第一行是表头，后面每行是一个果蝇在不同管子中的高度百分比
        self.result_table.setColumnCount(tube_count)
        
        # 设置表头为基因型名称
        headers = []
        for i in range(tube_count):
            genotype_name = self.detector.genotype_names[i] if i < len(self.detector.genotype_names) else f"管子{i+1}"
            headers.append(genotype_name)
        self.result_table.setVerticalHeaderLabels([f"果蝇{i+1}" for i in range(max_fly_count)])
        self.result_table.setHorizontalHeaderLabels(headers)
        
        # 填充表格数据
        for j in range(tube_count):  # 列（管子）
            tube_height = tube_heights[j]
            fly_heights = all_fly_heights[j]
            
            for i in range(max_fly_count):  # 行（果蝇）
                if i < len(fly_heights) and tube_height > 0:
                    height = fly_heights[i]
                    # 计算百分比
                    percentage = (height / tube_height) * 100
                    self.result_table.setItem(i, j, QTableWidgetItem(f"{percentage:.1f}%"))
                else:
                    self.result_table.setItem(i, j, QTableWidgetItem("-"))
        
        # 调整列宽
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
    def reset_detection_data(self):
        """重置检测数据"""
        self.detector.reset_data()  # 使用reset_data方法替代reset_detection_data
        self.update_result_table()
        self.status_label.setText("检测数据已重置")
        
    def export_detection_data(self):
        """导出检测数据，包括原始数据、优化数据和百分比数据"""
        if not self.detector.detection_history:
            QMessageBox.warning(self, "警告", "没有可导出的数据")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存检测数据", "", "CSV文件 (*.csv)"
        )
        
        if file_path:
            try:
                # 导出数据，获取所有导出的文件路径
                exported_files = self.detector.export_detection_data(file_path)
                
                # 显示成功消息，包含所有导出的文件
                file_names = [os.path.basename(f) for f in exported_files]
                file_list = "\n".join([f"• {name}" for name in file_names])
                
                QMessageBox.information(
                    self, "导出成功", 
                    f"数据已成功导出到以下文件:\n{file_list}"
                )
                
                self.status_label.setText(f"数据已导出到: {os.path.dirname(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出数据失败: {str(e)}")
                
    def import_videos(self):
        """导入多个视频文件"""
        # 使用上次打开的文件夹路径作为默认路径
        start_folder = self.last_opened_folder if self.last_opened_folder else ""
        
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "选择视频文件", start_folder, "视频文件 (*.avi *.mp4 *.mov *.mkv *.mts)"
        )
        
        if file_paths:
            # 记录这次打开的文件夹路径
            if file_paths:
                self.last_opened_folder = os.path.dirname(file_paths[0])
            
            # 添加到视频列表
            for file_path in file_paths:
                if file_path not in self.video_list:  # 避免重复添加
                    self.video_list.append(file_path)
            
            # 更新视频列表显示
            self.update_video_list()
            
            # 如果当前没有选中视频，选中第一个
            if self.current_video_index < 0 and self.video_list:
                self.current_video_index = 0
                self.video_list_widget.setCurrentRow(0)
                self.load_current_video()
                
            self.status_label.setText(f"已导入 {len(file_paths)} 个视频文件")
    
    def add_videos_to_list(self, video_paths):
        """添加视频文件到列表（用于拖放功能）"""
        if not video_paths:
            return
            
        # 记录这次打开的文件夹路径
        if video_paths:
            self.last_opened_folder = os.path.dirname(video_paths[0])
        
        # 添加到视频列表
        new_videos_count = 0
        for file_path in video_paths:
            if file_path not in self.video_list:  # 避免重复添加
                self.video_list.append(file_path)
                new_videos_count += 1
        
        # 更新视频列表显示
        self.update_video_list()
        
        # 如果当前没有选中视频，选中第一个新添加的视频
        if self.current_video_index < 0 and self.video_list:
            # 找到第一个新添加的视频的索引
            for i, path in enumerate(self.video_list):
                if path in video_paths:
                    self.current_video_index = i
                    self.video_list_widget.setCurrentRow(i)
                    self.load_current_video()
                    break
        
        if new_videos_count > 0:
            self.status_label.setText(f"已添加 {new_videos_count} 个视频文件")
        else:
            self.status_label.setText("所有视频都已存在于列表中")
    
    def update_video_list(self):
        """更新视频列表显示"""
        self.video_list_widget.clear()
        for video_path in self.video_list:
            # 只显示文件名，不显示完整路径
            file_name = os.path.basename(video_path)
            self.video_list_widget.addItem(file_name)
    
    def on_video_selected(self, item):
        """处理视频选择事件"""
        # 获取选中的行索引
        row = self.video_list_widget.row(item)
        if row >= 0 and row < len(self.video_list):
            self.current_video_index = row
            self.load_current_video()
    
    def load_current_video(self):
        """加载当前选中的视频"""
        if self.current_video_index >= 0 and self.current_video_index < len(self.video_list):
            video_path = self.video_list[self.current_video_index]
            if self.video_player.load_video(video_path):
                self.video_path = video_path
                file_name = os.path.basename(video_path)
                self.status_label.setText(f"已加载视频: {file_name}")
                
                # 重置检测数据
                self.reset_detection_data()
                
                # 重置背景帧
                self.background_frame = None
                self.detector.set_background(None)
                
                # 重置管子区域
                self.detector.tube_regions = [None] * self.detector.tube_count
                self.update_tube_table()
            else:
                QMessageBox.warning(self, "错误", f"无法加载视频文件: {os.path.basename(video_path)}")
    
    def remove_video(self):
        """移除选中的视频"""
        current_row = self.video_list_widget.currentRow()
        if current_row >= 0:
            # 从列表中移除
            self.video_list.pop(current_row)
            
            # 更新显示
            self.update_video_list()
            
            # 如果移除的是当前视频，需要重新选择
            if current_row == self.current_video_index:
                if self.video_list:
                    # 如果还有视频，选择相邻的视频
                    if current_row >= len(self.video_list):
                        self.current_video_index = len(self.video_list) - 1
                    else:
                        self.current_video_index = current_row
                    
                    self.video_list_widget.setCurrentRow(self.current_video_index)
                    self.load_current_video()
                else:
                    # 如果没有视频了，重置状态
                    self.current_video_index = -1
                    self.video_path = None
                    self.video_player.unload_video()
                    self.status_label.setText("请导入视频")
            elif current_row < self.current_video_index:
                # 如果移除的视频在当前视频之前，更新索引
                self.current_video_index -= 1
            
            self.status_label.setText("已移除视频")
    
    def clear_videos(self):
        """清空视频列表"""
        reply = QMessageBox.question(self, "确认", "确定要清空所有视频吗？", 
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 清空列表
            self.video_list.clear()
            self.update_video_list()
            
            # 重置状态
            self.current_video_index = -1
            self.video_path = None
            self.video_player.unload_video()
            
            # 重置检测数据
            self.reset_detection_data()
            
            # 重置背景帧
            self.background_frame = None
            self.detector.set_background(None)
            
            # 重置管子区域
            self.detector.tube_regions = [None] * self.detector.tube_count
            self.update_tube_table()
            
            self.status_label.setText("已清空视频列表")
    
    def copy_selected_cells(self):
        """复制选中的表格单元格到剪贴板"""
        selected_ranges = self.result_table.selectedRanges()
        if not selected_ranges:
            return
        
        # 获取第一个选中的范围
        selected_range = selected_ranges[0]
        top_row = selected_range.topRow()
        bottom_row = selected_range.bottomRow()
        left_col = selected_range.leftColumn()
        right_col = selected_range.rightColumn()
        
        # 构建要复制的文本
        copied_text = ""
        
        # 如果选中了多行多列，包含表头
        if bottom_row - top_row > 0 or right_col - left_col > 0:
            # 添加列标题
            for col in range(left_col, right_col + 1):
                header_item = self.result_table.horizontalHeaderItem(col)
                header_text = header_item.text() if header_item else ""
                copied_text += header_text
                if col < right_col:
                    copied_text += "\t"
            copied_text += "\n"
        
        # 添加选中的单元格内容
        for row in range(top_row, bottom_row + 1):
            # 添加行标题
            row_header_item = self.result_table.verticalHeaderItem(row)
            row_header_text = row_header_item.text() if row_header_item else ""
            copied_text += row_header_text + "\t"
            
            # 添加单元格内容
            for col in range(left_col, right_col + 1):
                item = self.result_table.item(row, col)
                cell_text = item.text() if item else ""
                copied_text += cell_text
                if col < right_col:
                    copied_text += "\t"
            
            if row < bottom_row:
                copied_text += "\n"
        
        # 复制到剪贴板
        clipboard = QApplication.clipboard()
        clipboard.setText(copied_text)
        
        # 显示状态消息
        self.status_label.setText(f"已复制 {bottom_row - top_row + 1} 行 {right_col - left_col + 1} 列数据到剪贴板")