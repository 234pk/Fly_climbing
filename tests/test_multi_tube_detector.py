#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sys
import os
import cv2
import numpy as np
from unittest.mock import Mock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from video_player.multi_tube_detector import MultiTubeFlyDetector


class TestMultiTubeFlyDetector(unittest.TestCase):
    """多管子果蝇检测器测试类"""
    
    def setUp(self):
        """测试前的设置"""
        self.detector = MultiTubeFlyDetector()
        
        # 创建测试图像
        self.test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.test_frame[:] = (100, 100, 100)  # 灰色背景
        
        # 创建测试背景帧
        self.background_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.background_frame[:] = (100, 100, 100)  # 灰色背景
        
    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.detector.tube_count, 5)
        self.assertEqual(len(self.detector.tube_regions), 5)
        self.assertEqual(len(self.detector.genotype_names), 5)
        self.assertEqual(self.detector.threshold, 30)
        self.assertEqual(self.detector.min_area, 50)
        self.assertEqual(self.detector.max_area, 500)
        
    def test_set_tube_count(self):
        """测试设置管子数量"""
        self.detector.set_tube_count(3)
        self.assertEqual(self.detector.tube_count, 3)
        self.assertEqual(len(self.detector.tube_regions), 3)
        self.assertEqual(len(self.detector.genotype_names), 3)
        self.assertEqual(len(self.detector.fly_positions), 3)
        
        # 测试管子数量小于1的情况
        with self.assertRaises(ValueError):
            self.detector.set_tube_count(0)
            
    def test_set_tube_region(self):
        """测试设置管子区域"""
        region = (100, 100, 200, 200)  # x, y, width, height
        self.detector.set_tube_region(0, region)
        self.assertEqual(self.detector.tube_regions[0], region)
        
        # 测试管子索引超出范围
        with self.assertRaises(IndexError):
            self.detector.set_tube_region(10, region)
            
    def test_set_genotype_name(self):
        """测试设置基因型名称"""
        name = "测试基因型"
        self.detector.set_genotype_name(0, name)
        self.assertEqual(self.detector.genotype_names[0], name)
        
        # 测试管子索引超出范围
        with self.assertRaises(IndexError):
            self.detector.set_genotype_name(10, name)
            
    def test_set_background(self):
        """测试设置背景帧"""
        self.detector.set_background(self.background_frame)
        self.assertTrue(np.array_equal(self.detector.background_frame, self.background_frame))
        
    def test_set_threshold(self):
        """测试设置阈值"""
        threshold = 50
        self.detector.set_threshold(threshold)
        self.assertEqual(self.detector.threshold, threshold)
        
    def test_get_fly_position(self):
        """测试获取果蝇位置"""
        # 设置管子区域
        region = (100, 100, 200, 200)
        self.detector.set_tube_region(0, region)
        
        # 设置背景帧
        self.detector.set_background(self.background_frame)
        
        # 创建测试帧，包含一个白色斑点模拟果蝇
        test_frame = self.background_frame.copy()
        cv2.circle(test_frame, (200, 200), 20, (255, 255, 255), -1)
        
        # 检测果蝇
        self.detector.detect_all_tubes(test_frame)
        
        # 获取果蝇位置
        position = self.detector.get_fly_position(0)
        self.assertIsNotNone(position)
        self.assertEqual(len(position), 2)  # x, y坐标
        
        # 测试管子索引超出范围
        with self.assertRaises(IndexError):
            self.detector.get_fly_position(10)
            
    def test_get_climbing_height(self):
        """测试获取爬行高度"""
        # 设置管子区域
        region = (100, 100, 200, 400)  # 高管子
        self.detector.set_tube_region(0, region)
        
        # 设置背景帧
        self.detector.set_background(self.background_frame)
        
        # 创建测试帧，包含一个白色斑点模拟果蝇
        test_frame = self.background_frame.copy()
        cv2.circle(test_frame, (200, 200), 20, (255, 255, 255), -1)
        
        # 检测果蝇
        self.detector.detect_all_tubes(test_frame)
        
        # 获取爬行高度
        height = self.detector.get_climbing_height(0)
        self.assertIsNotNone(height)
        self.assertGreaterEqual(height, 0)
        
        # 测试管子索引超出范围
        with self.assertRaises(IndexError):
            self.detector.get_climbing_height(10)
            
    def test_auto_detect_tubes(self):
        """测试通过ROI区域自动划分管子区域"""
        # 创建测试图像
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        test_frame[:] = (100, 100, 100)  # 灰色背景
        
        # 测试1: 不指定ROI区域，使用整个图像
        regions = self.detector.auto_detect_tubes(test_frame, tube_count=5)
        
        self.assertEqual(len(regions), 5)
        
        # 检查每个区域是否有效
        for i, region in enumerate(regions):
            self.assertEqual(len(region), 4)  # x, y, width, height
            self.assertGreater(region[2], 0)  # width > 0
            self.assertGreater(region[3], 0)  # height > 0
            # 验证区域是水平划分的
            expected_x = i * (640 // 5)
            self.assertEqual(region[0], expected_x)
            self.assertEqual(region[1], 0)  # 从顶部开始
            self.assertEqual(region[2], 640 // 5)  # 宽度相等
            self.assertEqual(region[3], 480)  # 全高度
            
        # 测试2: 指定ROI区域
        roi_region = (100, 50, 400, 300)  # (x, y, w, h)
        regions = self.detector.auto_detect_tubes(test_frame, roi_region=roi_region, tube_count=4)
        
        self.assertEqual(len(regions), 4)
        
        # 检查ROI区域内的划分
        for i, region in enumerate(regions):
            self.assertEqual(len(region), 4)  # x, y, width, height
            self.assertGreater(region[2], 0)  # width > 0
            self.assertGreater(region[3], 0)  # height > 0
            # 验证区域是在ROI内水平划分的
            expected_x = 100 + i * (400 // 4)
            self.assertEqual(region[0], expected_x)
            self.assertEqual(region[1], 50)  # ROI的y坐标
            self.assertEqual(region[2], 400 // 4)  # ROI宽度等分
            self.assertEqual(region[3], 300)  # ROI高度
            
    def test_compare_genotypes(self):
        """测试比较基因型"""
        # 设置管子区域和基因型名称
        for i in range(3):
            region = (100 + i * 100, 100, 50, 300)
            self.detector.set_tube_region(i, region)
            self.detector.set_genotype_name(i, f"基因型{i+1}")
            
        # 设置背景帧
        self.detector.set_background(self.background_frame)
        
        # 创建测试帧，包含不同高度的果蝇
        test_frame = self.background_frame.copy()
        for i in range(3):
            x = 125 + i * 100
            y = 350 - i * 50  # 不同高度
            cv2.circle(test_frame, (x, y), 20, (255, 255, 255), -1)
            
        # 检测多次以积累数据
        for _ in range(10):
            self.detector.detect_all_tubes(test_frame)
            
        # 比较基因型
        results = self.detector.compare_genotypes()
        
        self.assertEqual(len(results), 3)
        
        # 检查结果结构
        for result in results:
            self.assertIn('name', result)
            self.assertIn('current_height', result)
            self.assertIn('max_height', result)
            self.assertIn('avg_height', result)
            
    def test_export_data(self):
        """测试导出数据"""
        # 设置管子区域和基因型名称
        for i in range(2):
            region = (100 + i * 100, 100, 50, 300)
            self.detector.set_tube_region(i, region)
            self.detector.set_genotype_name(i, f"基因型{i+1}")
            
        # 设置背景帧
        self.detector.set_background(self.background_frame)
        
        # 创建测试帧
        test_frame = self.background_frame.copy()
        for i in range(2):
            x = 125 + i * 100
            y = 350 - i * 50
            cv2.circle(test_frame, (x, y), 20, (255, 255, 255), -1)
            
        # 检测多次以积累数据
        for _ in range(5):
            self.detector.detect_all_tubes(test_frame)
            
        # 导出数据
        data = self.detector.export_data()
        
        # 检查导出数据结构
        self.assertIn('tube_count', data)
        self.assertIn('genotype_names', data)
        self.assertIn('detection_history', data)
        self.assertIn('tube_regions', data)
        
        self.assertEqual(data['tube_count'], 2)
        self.assertEqual(len(data['genotype_names']), 2)
        
    def test_reset_data(self):
        """测试重置数据"""
        # 设置管子区域
        region = (100, 100, 50, 300)
        self.detector.set_tube_region(0, region)
        
        # 设置背景帧
        self.detector.set_background(self.background_frame)
        
        # 创建测试帧并检测
        test_frame = self.background_frame.copy()
        cv2.circle(test_frame, (125, 200), 20, (255, 255, 255), -1)
        
        self.detector.detect_all_tubes(test_frame)
        
        # 确保有检测数据
        self.assertIsNotNone(self.detector.fly_positions[0])
        self.assertTrue(any(self.detector.detection_history[0]))
        
        # 重置数据
        self.detector.reset_data()
        
        # 检查数据是否已重置
        self.assertIsNone(self.detector.fly_positions[0])
        self.assertFalse(any(self.detector.detection_history[0]))
        
    def test_draw_detections(self):
        """测试绘制检测结果"""
        # 设置管子区域
        region = (100, 100, 50, 300)
        self.detector.set_tube_region(0, region)
        self.detector.set_genotype_name(0, "测试基因型")
        
        # 设置背景帧
        self.detector.set_background(self.background_frame)
        
        # 创建测试帧
        test_frame = self.background_frame.copy()
        cv2.circle(test_frame, (125, 200), 20, (255, 255, 255), -1)
        
        # 检测果蝇
        self.detector.detect_all_tubes(test_frame)
        
        # 绘制检测结果
        result_frame = self.detector.draw_detections(test_frame)
        
        # 检查返回的帧
        self.assertEqual(result_frame.shape, test_frame.shape)
        self.assertFalse(np.array_equal(result_frame, test_frame))  # 应该有绘制内容


if __name__ == '__main__':
    unittest.main()