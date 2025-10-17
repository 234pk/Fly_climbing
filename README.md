# Fly Climbing 多管子实验视频分析器

这是一个用于分析Fly Climbing实验视频的软件，可以同时检测多个管子中不同基因型果蝇的爬行高度，从而比较果蝇的爬行能力。

## 功能特点
- 支持多管子（多基因型）同时检测
- 实时统计和比较不同基因型果蝇的爬行高度
- 基于背景减法的果蝇检测算法
- 可视化检测结果和管子区域
- 历史数据记录和查看
- 数据导出功能（JSON格式）
- 可调节的检测阈值

## 项目结构
```
Fly_climbing/
├── README.md
├── 使用说明.md
├── requirements.txt
├── main.py
├── video_player/
│   ├── __init__.py
│   ├── player.py          # 视频播放器
│   ├── ui.py              # 原始UI（单管子）
│   ├── fly_detector.py    # 果蝇检测器
│   ├── multi_tube_detector.py  # 多管子检测器
│   └── multi_tube_ui.py   # 多管子UI
└── tests/
    └── test_player.py
```

## 安装依赖
```bash
pip install -r requirements.txt
```

## 使用方法
1. 启动软件：
```bash
python main.py
```

2. 详细使用步骤请参考 [使用说明.md](使用说明.md)

## 核心功能

### 多管子检测
- 支持同时检测多个管子中的果蝇
- 可为每个管子设置对应的基因型名称
- 自动计算每个管子中果蝇的爬行高度

### 数据比较
- 实时比较不同基因型果蝇的爬行能力
- 显示最大高度、平均高度等统计数据
- 自动排名，找出爬行能力最强和最弱的基因型

### 数据导出
- 支持将检测数据导出为JSON格式
- 包含时间戳、帧索引、高度等详细信息
- 便于后续数据分析和处理
# Fly_climbing