#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入测试模块
from tests.test_multi_tube_detector import TestMultiTubeFlyDetector
from tests.test_player import TestVideoPlayer


def create_test_suite():
    """创建测试套件"""
    suite = unittest.TestSuite()
    
    # 添加测试用例
    suite.addTest(unittest.makeSuite(TestMultiTubeFlyDetector))
    suite.addTest(unittest.makeSuite(TestVideoPlayer))
    
    return suite


if __name__ == '__main__':
    # 创建测试套件
    suite = create_test_suite()
    
    # 创建测试运行器
    runner = unittest.TextTestRunner(verbosity=2)
    
    # 运行测试
    result = runner.run(suite)
    
    # 如果测试失败，返回非零退出码
    sys.exit(not result.wasSuccessful())