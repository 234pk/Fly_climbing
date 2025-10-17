#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cv2
import numpy as np


class MultiTubeFlyDetector:
    """多管子果蝇检测器类，用于同时检测多个管子中的果蝇并比较爬行能力"""
    
    def __init__(self, tube_count=5):
        """
        初始化多管子果蝇检测器
        
        参数:
            tube_count: 管子数量
        """
        self.tube_count = tube_count
        self.tube_regions = [None] * tube_count
        self.genotype_names = [f"管子{i+1}" for i in range(tube_count)]
        self.background_frame = None
        
        # 检测参数
        self.threshold = 15  # 背景减法的阈值
        self.min_area = 40   # 最小果蝇区域面积
        self.max_area = 500  # 最大果蝇区域面积
        
        # 检测结果
        self.fly_positions = [None] * tube_count
        self.climbing_heights = [0] * tube_count
        self.max_heights = [0] * tube_count
        self.avg_heights = [0] * tube_count
        self.detection_history = [[] for _ in range(tube_count)]
        
    def set_tube_count(self, tube_count):
        """设置管子数量"""
        self.tube_count = tube_count
        self.tube_regions = [None] * tube_count
        self.genotype_names = [f"管子{i+1}" for i in range(tube_count)]
        self.fly_positions = [None] * tube_count
        self.climbing_heights = [0] * tube_count
        self.max_heights = [0] * tube_count
        self.avg_heights = [0] * tube_count
        self.detection_history = [[] for _ in range(tube_count)]
        
    def set_tube_region(self, tube_index, region):
        """
        设置指定管子的区域
        
        参数:
            tube_index: 管子索引
            region: 管子区域 (x, y, width, height)
        """
        if 0 <= tube_index < self.tube_count:
            self.tube_regions[tube_index] = region
            
    def set_tube_regions(self, regions):
        """
        设置所有管子的区域
        
        参数:
            regions: 管子区域列表，每个元素为 (x, y, width, height)
        """
        if len(regions) == self.tube_count:
            self.tube_regions = regions[:]
        elif len(regions) < self.tube_count:
            # 如果提供的区域数少于管子数，只设置前几个
            self.tube_regions[:len(regions)] = regions
        else:
            # 如果提供的区域数多于管子数，只使用前几个
            self.tube_regions = regions[:self.tube_count]
                
    def set_genotype_name(self, tube_index, name):
        """
        设置指定管子的基因型名称
        
        参数:
            tube_index: 管子索引
            name: 基因型名称
        """
        if 0 <= tube_index < self.tube_count:
            self.genotype_names[tube_index] = name
            
    def set_background(self, background_frame):
        """设置背景帧"""
        self.background_frame = background_frame
            
    def set_threshold(self, threshold):
        """设置检测阈值"""
        self.threshold = threshold
            
    def detect_all_tubes(self, frame):
        """
        检测所有管子中的果蝇
        
        参数:
            frame: 当前帧图像
            
        返回:
            每个管子中检测到的果蝇信息列表，每个元素是一个元组(x, y, height)
        """
        results = []
        
        # 清空当前检测的历史数据，避免叠加
        for i in range(self.tube_count):
            self.detection_history[i] = []
        
        for i in range(self.tube_count):
            if self.tube_regions[i] is not None:
                # 获取管子区域
                x, y, w, h = self.tube_regions[i]
                tube_region = frame[y:y+h, x:x+w]
                bg_region = self.background_frame[y:y+h, x:x+w]
                
                # 背景减法
                diff = cv2.absdiff(tube_region, bg_region)
                gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                
                # 二值化
                _, thresh = cv2.threshold(gray_diff, self.threshold, 255, cv2.THRESH_BINARY)
                
                # 形态学操作，去除噪声
                kernel = np.ones((3, 3), np.uint8)
                thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
                thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
                
                # 查找轮廓
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # 筛选合适的轮廓
                valid_contours = []
                for contour in contours:
                    area = cv2.contourArea(contour)
                    if self.min_area <= area <= self.max_area:
                        valid_contours.append(contour)
                
                # 检测所有符合条件的果蝇
                tube_fly_results = []
                for contour in valid_contours:
                    # 计算轮廓的质心
                    M = cv2.moments(contour)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        
                        # 转换为全局坐标
                        global_x = x + cx
                        global_y = y + cy
                        
                        # 计算爬行高度（从管子底部到果蝇位置的距离）
                        height = h - cy
                        
                        # 记录果蝇位置和高度
                        tube_fly_results.append((global_x, global_y, height))
                        
                        # 添加到检测历史
                        self.detection_history[i].append(height)
                
                # 更新检测结果
                if tube_fly_results:
                    # 使用第一个果蝇作为主要位置（用于兼容性）
                    self.fly_positions[i] = (tube_fly_results[0][0], tube_fly_results[0][1])
                    
                    # 使用最高果蝇的高度作为当前高度
                    heights = [fly[2] for fly in tube_fly_results]
                    self.climbing_heights[i] = max(heights)
                    
                    # 更新最大高度
                    max_height = max(heights)
                    if max_height > self.max_heights[i]:
                        self.max_heights[i] = max_height
                        
                    # 计算平均高度
                    if self.detection_history[i]:
                        self.avg_heights[i] = sum(self.detection_history[i]) / len(self.detection_history[i])
                else:
                    self.fly_positions[i] = None
                    self.climbing_heights[i] = 0
                
                results.append(tube_fly_results)
            else:
                results.append([])
                
        return results
        
    def _detect_fly_in_tube(self, frame, tube_index):
        """
        检测指定管子中的果蝇
        
        参数:
            frame: 当前帧图像
            tube_index: 管子索引
            
        返回:
            是否检测到果蝇
        """
        if self.tube_regions[tube_index] is None or self.background_frame is None:
            return False
            
        # 提取管子区域
        x, y, w, h = self.tube_regions[tube_index]
        tube_region = frame[y:y+h, x:x+w]
        bg_region = self.background_frame[y:y+h, x:x+w]
        
        # 背景减法
        diff = cv2.absdiff(tube_region, bg_region)
        gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        
        # 二值化
        _, thresh = cv2.threshold(gray_diff, self.threshold, 255, cv2.THRESH_BINARY)
        
        # 形态学操作，去除噪声
        kernel = np.ones((3, 3), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        # 查找轮廓
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 筛选合适的轮廓
        valid_contours = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if self.min_area <= area <= self.max_area:
                valid_contours.append(contour)
                
        # 如果没有找到合适的轮廓，返回False
        if not valid_contours:
            self.fly_positions[tube_index] = None
            self.climbing_heights[tube_index] = 0
            return False
            
        # 检测所有符合条件的果蝇
        fly_positions = []
        fly_heights = []
        
        for contour in valid_contours:
            # 计算轮廓的质心
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                
                # 转换为全局坐标
                global_x = x + cx
                global_y = y + cy
                
                # 计算爬行高度（从管子底部到果蝇位置的距离）
                height = h - cy
                
                # 记录果蝇位置和高度
                fly_positions.append((global_x, global_y))
                fly_heights.append(height)
                
                # 添加到检测历史
                self.detection_history[tube_index].append(height)
        
        # 更新检测结果
        if fly_positions:
            # 使用第一个果蝇作为主要位置（用于兼容性）
            self.fly_positions[tube_index] = fly_positions[0]
            
            # 使用最高果蝇的高度作为当前高度
            self.climbing_heights[tube_index] = max(fly_heights)
            
            # 更新最大高度
            max_height = max(fly_heights)
            if max_height > self.max_heights[tube_index]:
                self.max_heights[tube_index] = max_height
                
            # 计算平均高度
            if self.detection_history[tube_index]:
                self.avg_heights[tube_index] = sum(self.detection_history[tube_index]) / len(self.detection_history[tube_index])
                
            return True
        else:
            self.fly_positions[tube_index] = None
            self.climbing_heights[tube_index] = 0
            return False
        
    def get_max_height(self, tube_index):
        """获取指定管子的最大爬行高度"""
        if 0 <= tube_index < self.tube_count:
            return self.max_heights[tube_index]
        return 0
        
    def get_avg_height(self, tube_index):
        """获取指定管子的平均爬行高度"""
        if 0 <= tube_index < self.tube_count:
            return self.avg_heights[tube_index]
        return 0
        
    def get_current_height(self, tube_index):
        """获取指定管子的当前爬行高度"""
        if 0 <= tube_index < self.tube_count:
            return self.climbing_heights[tube_index]
        return 0
        
    def get_tube_height(self, tube_index):
        """
        获取指定管子的高度
        
        参数:
            tube_index: 管子索引
            
        返回:
            管子的高度（像素）
        """
        if 0 <= tube_index < self.tube_count and self.tube_regions[tube_index] is not None:
            _, _, _, h = self.tube_regions[tube_index]
            return h
        return 0
        
    def get_all_fly_heights(self, tube_index):
        """
        获取指定管子中所有检测到的果蝇高度
        
        参数:
            tube_index: 管子索引
            
        返回:
            该管子中所有果蝇的高度列表
        """
        heights = []
        
        # 只从detection_results中获取高度数据（手动选择的果蝇）
        if hasattr(self, 'detection_results') and tube_index < len(self.detection_results):
            if self.detection_results[tube_index] is not None:
                for fly_data in self.detection_results[tube_index]:
                    # fly_data格式为 (x, y, height)
                    if len(fly_data) >= 3:
                        heights.append(fly_data[2])
        
        return heights
        
    def get_fly_areas(self, frame):
        """
        获取当前帧中检测到的所有果蝇面积
        
        参数:
            frame: 当前帧图像
            
        返回:
            所有果蝇的面积列表
        """
        areas = []
        
        if self.background_frame is None:
            return areas
            
        for i in range(self.tube_count):
            if self.tube_regions[i] is not None:
                # 获取管子区域
                x, y, w, h = self.tube_regions[i]
                tube_region = frame[y:y+h, x:x+w]
                bg_region = self.background_frame[y:y+h, x:x+w]
                
                # 背景减法
                diff = cv2.absdiff(tube_region, bg_region)
                gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                
                # 二值化
                _, thresh = cv2.threshold(gray_diff, self.threshold, 255, cv2.THRESH_BINARY)
                
                # 形态学操作，去除噪声
                kernel = np.ones((3, 3), np.uint8)
                thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
                thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
                
                # 查找轮廓
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # 筛选合适的轮廓并记录面积
                for contour in contours:
                    area = cv2.contourArea(contour)
                    if area > 0:  # 只记录有效面积
                        areas.append(area)
        
        return areas
        
    def compare_genotypes(self):
        """
        比较不同基因型果蝇的爬行能力
        
        返回:
            排序后的基因型列表，按平均爬行高度降序排列
        """
        genotype_data = []
        for i in range(self.tube_count):
            if self.tube_regions[i] is not None and self.detection_history[i]:
                genotype_data.append({
                    'name': self.genotype_names[i],
                    'index': i,
                    'max_height': self.max_heights[i],
                    'avg_height': self.avg_heights[i],
                    'current_height': self.climbing_heights[i]
                })
                
        # 按平均高度降序排序
        genotype_data.sort(key=lambda x: x['avg_height'], reverse=True)
        
        return genotype_data
        
    def draw_detections(self, frame):
        """
        在帧上绘制所有管子的检测结果
        
        参数:
            frame: 要绘制的帧
            
        返回:
            绘制后的帧
        """
        for i in range(self.tube_count):
            if self.tube_regions[i] is not None:
                # 绘制管子区域
                x, y, w, h = self.tube_regions[i]
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # 绘制果蝇位置
                if self.fly_positions[i] is not None:
                    cv2.circle(frame, self.fly_positions[i], 5, (0, 0, 255), -1)
                    
                    # 绘制爬行高度线
                    cv2.line(frame, (x, y + h - self.climbing_heights[i]), 
                            (x + w, y + h - self.climbing_heights[i]), (255, 0, 0), 2)
                
                # 在管子区域上方显示基因型名称和当前高度
                text = f"{self.genotype_names[i]}: {int(self.climbing_heights[i])}px"
                cv2.putText(frame, text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                
        return frame
        
    def export_data(self):
        """
        导出检测数据
        
        返回:
            包含所有检测数据的字典
        """
        data = {
            'tube_count': self.tube_count,
            'genotype_names': self.genotype_names,
            'detection_history': self.detection_history,
            'tube_regions': self.tube_regions
        }
        
        return data
        
    def reset_data(self):
        """重置所有检测数据"""
        self.fly_positions = [None] * self.tube_count
        self.climbing_heights = [0] * self.tube_count
        self.max_heights = [0] * self.tube_count
        self.avg_heights = [0] * self.tube_count
        self.detection_history = [[] for _ in range(self.tube_count)]
        
        # 重置检测结果
        if hasattr(self, 'detection_results'):
            self.detection_results = [None] * self.tube_count
        
    def export_detection_data(self, file_path):
        """
        导出检测数据到CSV文件，包含优化后的数据
        
        参数:
            file_path: 导出文件路径
        """
        import csv
        import json
        import os
        
        # 获取文件名和目录
        file_dir = os.path.dirname(file_path)
        file_name = os.path.basename(file_path)
        name_without_ext = os.path.splitext(file_name)[0]
        
        # 1. 导出原始检测数据到CSV
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # 写入表头
            headers = ['管子编号', '基因型名称', '最大爬行高度', '平均爬行高度']
            
            # 添加每个检测时间点的数据列
            max_history_length = max(len(history) for history in self.detection_history) if self.detection_history else 0
            for i in range(max_history_length):
                headers.append(f'检测点{i+1}')
            
            writer.writerow(headers)
            
            # 写入每个管子的数据
            for i in range(self.tube_count):
                row = [
                    i + 1,  # 管子编号
                    self.genotype_names[i],  # 基因型名称
                    self.max_heights[i],  # 最大爬行高度
                    self.avg_heights[i]  # 平均爬行高度
                ]
                
                # 添加检测历史数据
                if i < len(self.detection_history):
                    row.extend(self.detection_history[i])
                
                # 如果该管子的检测历史数据少于最大长度，用空值填充
                while len(row) < len(headers):
                    row.append('')
                
                writer.writerow(row)
        
        # 2. 导出优化后的数据到JSON文件
        optimized_data = {
            'tube_count': self.tube_count,
            'genotype_names': self.genotype_names,
            'detection_history': self.detection_history,
            'max_heights': self.max_heights,
            'avg_heights': self.avg_heights,
            'climbing_heights': self.climbing_heights,
            'tube_regions': self.tube_regions,
            'genotype_comparison': self.compare_genotypes(),
            'detection_parameters': {
                'threshold': self.threshold,
                'min_area': self.min_area,
                'max_area': self.max_area
            }
        }
        
        # 保存优化数据到JSON文件
        json_path = os.path.join(file_dir, f"{name_without_ext}_optimized.json")
        with open(json_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(optimized_data, jsonfile, ensure_ascii=False, indent=2)
        
        # 3. 导出百分比数据到CSV文件（与表格显示一致）
        percent_path = os.path.join(file_dir, f"{name_without_ext}_percentage.csv")
        with open(percent_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # 获取每个管子的所有果蝇高度
            all_fly_heights = []
            max_fly_count = 0
            tube_heights = []
            
            for i in range(self.tube_count):
                fly_heights = self.get_all_fly_heights(i)
                all_fly_heights.append(fly_heights)
                max_fly_count = max(max_fly_count, len(fly_heights))
                tube_heights.append(self.get_tube_height(i))
            
            # 写入表头
            headers = ['果蝇编号'] + self.genotype_names
            writer.writerow(headers)
            
            # 写入数据
            for i in range(max_fly_count):
                row = [f"果蝇{i+1}"]
                for j in range(self.tube_count):
                    tube_height = tube_heights[j]
                    fly_heights = all_fly_heights[j]
                    
                    if i < len(fly_heights) and tube_height > 0:
                        height = fly_heights[i]
                        # 计算百分比
                        percentage = (height / tube_height) * 100
                        row.append(f"{percentage:.1f}%")
                    else:
                        row.append("-")
                
                writer.writerow(row)
        
        return [file_path, json_path, percent_path]
        
    def auto_detect_tubes(self, frame, roi_region=None, tube_count=None):
        """
        通过ROI区域自动划分管子区域
        
        参数:
            frame: 输入帧
            roi_region: 手动划定的ROI区域 (x, y, w, h)，如果为None则使用整个图像
            tube_count: 管子数量，如果为None则使用当前设置的管子数量
            
        返回:
            划分后的管子区域列表
        """
        if tube_count is not None:
            self.set_tube_count(tube_count)
            
        # 如果没有指定ROI区域，使用整个图像
        if roi_region is None:
            height, width = frame.shape[:2]
            roi_x, roi_y, roi_w, roi_h = 0, 0, width, height
        else:
            roi_x, roi_y, roi_w, roi_h = roi_region
            
        # 根据管子数量均匀划分ROI区域
        tube_width = roi_w // self.tube_count
        tube_regions = []
        
        for i in range(self.tube_count):
            x = roi_x + i * tube_width
            y = roi_y
            w = tube_width
            h = roi_h
            tube_regions.append((x, y, w, h))
            
        # 设置管子区域
        self.tube_regions = tube_regions
        return tube_regions