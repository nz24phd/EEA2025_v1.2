"""
GIS道路网络映射模块
将SUMO道路段映射到配电网节点
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import json

class GISNetworkMapping:
    """GIS网络映射类"""
    
    def __init__(self):
        # Wellington CBD的简化映射
        self.road_to_bus_mapping = {
            # 主干道映射到主要馈线节点
            'main_1': [3, 4],      # 对应配电网节点3和4
            'main_2': [5, 6, 7],   # 对应配电网节点5,6,7
            'main_3': [8, 9],      # 对应配电网节点8,9
            
            # 支路映射到支线节点
            'side_1': [10, 11],
            'side_2': [12],
            'side_3': [13, 14],
            
            # 环路映射到其他节点
            'loop_1': [15],
            'loop_2': [16, 17],
            'loop_3': [18],
            'loop_4': [19, 20]
        }
        
        # BDWPT充电区域定义
        self.bdwpt_zones = [
            {
                'zone_id': 'CBD_Main',
                'road_segments': ['main_1', 'main_2'],
                'coverage_rate': 0.8,  # 80%的道路段覆盖BDWPT
                'max_power_kw': 50,
                'efficiency': 0.88
            },
            {
                'zone_id': 'CBD_Secondary',
                'road_segments': ['side_2', 'loop_2'],
                'coverage_rate': 0.6,
                'max_power_kw': 30,
                'efficiency': 0.85
            }
        ]
        
    def get_nearest_bus(self, road_id: str, position: float) -> int:
        """根据道路ID和位置获取最近的配电网节点"""
        if road_id not in self.road_to_bus_mapping:
            return 2  # 默认返回节点2
            
        buses = self.road_to_bus_mapping[road_id]
        if not buses:
            return 2
            
        # 简单的线性映射
        index = int(position * len(buses) / 1000)  # 假设道路长度1000m
        index = min(index, len(buses) - 1)
        
        return buses[index]
        
    def is_in_bdwpt_zone(self, road_id: str, position: float) -> Tuple[bool, Dict]:
        """检查车辆是否在BDWPT充电区域"""
        for zone in self.bdwpt_zones:
            if road_id in zone['road_segments']:
                # 检查是否在覆盖范围内
                if np.random.random() < zone['coverage_rate']:
                    return True, zone
        return False, None
        
    def calculate_zone_power_distribution(self, vehicles_in_zone: List[Dict], 
                                        zone_info: Dict) -> Dict[int, float]:
        """计算区域内的功率分配到各节点"""
        power_distribution = {}
        
        # 获取该区域涉及的所有节点
        zone_buses = []
        for road in zone_info['road_segments']:
            zone_buses.extend(self.road_to_bus_mapping.get(road, []))
            
        if not zone_buses:
            return {}
            
        # 计算总功率
        total_power = 0
        for vehicle in vehicles_in_zone:
            power = vehicle.get('charging_power_kw', 0)
            total_power += power
            
        # 平均分配到各节点
        power_per_bus = total_power / len(zone_buses)
        for bus in zone_buses:
            power_distribution[bus] = power_per_bus
            
        return power_distribution
        
    def create_mapping_visualization(self) -> str:
        """创建映射关系的可视化（文本格式）"""
        viz = "=== GIS道路到配电网映射 ===\n\n"
        
        viz += "道路段 -> 配电网节点:\n"
        for road, buses in self.road_to_bus_mapping.items():
            viz += f"  {road}: {buses}\n"
            
        viz += "\nBDWPT充电区域:\n"
        for zone in self.bdwpt_zones:
            viz += f"  {zone['zone_id']}:\n"
            viz += f"    道路: {zone['road_segments']}\n"
            viz += f"    覆盖率: {zone['coverage_rate']*100}%\n"
            viz += f"    最大功率: {zone['max_power_kw']} kW\n"
            
        return viz
        
    def export_mapping_config(self, filename: str = "gis_mapping_config.json"):
        """导出映射配置"""
        config = {
            'road_to_bus_mapping': self.road_to_bus_mapping,
            'bdwpt_zones': self.bdwpt_zones,
            'metadata': {
                'city': 'Wellington',
                'coordinate_system': 'NZTM2000',
                'created': pd.Timestamp.now().isoformat()
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(config, f, indent=2)
            
        print(f"✓ 映射配置已保存到: {filename}")

# 测试函数
def test_gis_mapping():
    """测试GIS映射功能"""
    mapper = GISNetworkMapping()
    
    print("测试GIS映射功能:\n")
    
    # 测试最近节点查找
    test_cases = [
        ('main_1', 250),
        ('main_2', 500),
        ('side_2', 100)
    ]
    
    for road_id, position in test_cases:
        bus = mapper.get_nearest_bus(road_id, position)
        print(f"道路 {road_id} 位置 {position}m -> 节点 {bus}")
        
    # 测试BDWPT区域
    print("\n测试BDWPT区域:")
    for road in ['main_1', 'side_2', 'loop_3']:
        in_zone, zone_info = mapper.is_in_bdwpt_zone(road, 500)
        if in_zone:
            print(f"道路 {road} 在BDWPT区域 {zone_info['zone_id']}")
        else:
            print(f"道路 {road} 不在BDWPT区域")
            
    # 显示映射可视化
    print("\n" + mapper.create_mapping_visualization())
    
    # 导出配置
    mapper.export_mapping_config()

if __name__ == "__main__":
    test_gis_mapping()