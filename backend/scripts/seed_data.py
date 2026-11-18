"""演示数据：8 间实验室 + 每间 4 台设备。

用法（在 backend 目录下）：
    .venv\\Scripts\\python.exe -m scripts.seed_data

脚本是幂等的：已经有实验室数据时直接跳过，不会重复插入。
"""

from datetime import datetime

from app.database import SessionLocal
from app.models.equipment import Equipment
from app.models.lab import Lab

LABS = [
    (1, "计算机实验室", "综合实验楼201", 30, "08:00", "18:00"),
    (2, "电子实验室", "综合实验楼202", 24, "08:00", "18:00"),
    (3, "物理实验室", "综合实验楼203", 20, "08:00", "17:00"),
    (4, "化学实验室", "综合实验楼301", 20, "08:00", "18:00"),
    (5, "生物实验室", "综合实验楼302", 20, "08:00", "18:00"),
    (6, "人工智能实验室", "综合实验楼401", 30, "08:00", "18:00"),
    (7, "机器人实验室", "综合实验楼402", 20, "09:00", "17:00"),
    (8, "软件工程实验室", "综合实验楼501", 40, "08:00", "20:00"),
]

EQUIPMENTS = [
    (1, 1, "RTX4090", "深度学习训练显卡", "24G 显存", 2, 1),
    (2, 1, "开发主机", "学生上机编程", "i7 / 32G / 1T SSD", 20, 1),
    (3, 1, "投影仪", "讲课演示", "1080P", 1, 1),
    (4, 1, "千兆交换机", "机房组网", "24 口", 1, 1),
    (5, 2, "示波器", "电路波形观测", "100MHz 双通道", 8, 1),
    (6, 2, "信号发生器", "信号源实验", "DDS 60MHz", 6, 1),
    (7, 2, "数字万用表", "电子测量", "4 位半", 10, 0),
    (8, 2, "直流稳压电源", "电路供电", "30V 5A", 8, 1),
    (9, 3, "光学实验台", "几何光学实验", "1.2m 隔振台", 4, 1),
    (10, 3, "氦氖激光器", "干涉衍射实验", "632.8nm", 2, 1),
    (11, 3, "力学轨道", "牛顿定律实验", "气垫导轨 1.5m", 3, 1),
    (12, 3, "分光计", "光谱测量", "0.1° 精度", 4, 1),
    (13, 4, "电子天平", "试剂称量", "0.1mg", 6, 1),
    (14, 4, "离心机", "样品分离", "4000rpm", 2, 1),
    (15, 4, "通风橱", "有机实验", "1.5m", 3, 1),
    (16, 4, "pH 计", "溶液酸碱度", "0.01pH", 4, 1),
    (17, 5, "显微镜", "细胞观察", "1000x 光学", 10, 1),
    (18, 5, "恒温培养箱", "菌种培养", "室温 ~ 60℃", 2, 1),
    (19, 5, "移液器", "微量取样", "0.5-10μL", 20, 1),
    (20, 5, "PCR 仪", "基因扩增", "96 孔", 1, 0),
    (21, 6, "GPU 训练服务器", "大模型微调", "2 * RTX4090 / 128G", 1, 1),
    (22, 6, "RTX4090", "深度学习训练显卡", "24G 显存", 4, 1),
    (23, 6, "深度相机", "视觉数据采集", "RealSense D435i", 3, 1),
    (24, 6, "标注工作站", "数据集标注", "i9 / 64G", 6, 1),
    (25, 7, "UR5 机械臂", "工业机械臂教学", "负载 5kg", 2, 1),
    (26, 7, "Livox 激光雷达", "SLAM 建图", "Mid-360", 3, 1),
    (27, 7, "RealSense 深度相机", "视觉抓取", "D435i", 4, 1),
    (28, 7, "Jetson Orin", "边缘计算", "32G", 4, 1),
    (29, 8, "开发主机", "项目实训", "i7 / 32G / 1T SSD", 40, 1),
    (30, 8, "显示器", "双屏开发", "27 寸 2K", 40, 1),
    (31, 8, "投影仪", "答辩演示", "1080P", 2, 1),
    (32, 8, "代码服务器", "Git 与 CI", "8 核 / 32G", 1, 1),
]


def main() -> None:
    db = SessionLocal()
    try:
        if db.query(Lab).count() > 0:
            print("已存在实验室数据，跳过种子数据")
            return

        now = datetime.now()
        for lab_id, name, location, capacity, open_time, close_time in LABS:
            db.add(
                Lab(
                    id=lab_id,
                    name=name,
                    description=name,
                    img=None,
                    location=location,
                    capacity=capacity,
                    open_time=open_time,
                    close_time=close_time,
                    status=1,
                    create_time=now,
                    update_time=now,
                )
            )
        db.flush()

        for eq_id, lab_id, name, description, spec, quantity, status in EQUIPMENTS:
            db.add(
                Equipment(
                    id=eq_id,
                    lab_id=lab_id,
                    name=name,
                    description=description,
                    img=None,
                    spec=spec,
                    quantity=quantity,
                    status=status,
                    create_time=now,
                    update_time=now,
                )
            )

        db.commit()
        print(f"已写入 {len(LABS)} 间实验室、{len(EQUIPMENTS)} 台设备")
    finally:
        db.close()


if __name__ == "__main__":
    main()