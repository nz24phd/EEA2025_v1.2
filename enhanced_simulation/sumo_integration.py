"""
SUMO交通仿真集成模块
用于实现真实的交通-电力耦合仿真
"""

import os
import sys
import traci
import numpy as np
from typing import Dict, List, Tuple
import pandas as pd

class SUMOIntegration:
    """SUMO交通仿真集成类"""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.is_connected = False
        
        # 检查SUMO环境
        if 'SUMO_HOME' in os.environ:
            tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
            sys.path.append(tools)
        else:
            print("警告: SUMO_HOME环境变量未设置")
            
    def start_simulation(self, gui: bool = False):
        """启动SUMO仿真"""
        try:
            sumo_binary = "sumo-gui" if gui else "sumo"
            sumo_cmd = [sumo_binary, "-c", self.config_path, "--step-length", "1"]
            traci.start(sumo_cmd)
            self.is_connected = True
            print("✓ SUMO仿真已启动")
        except Exception as e:
            print(f"❌ SUMO启动失败: {e}")
            self.is_connected = False
            
    def step(self):
        """执行一个仿真步骤"""
        if self.is_connected:
            traci.simulationStep()
            
    def get_vehicles_on_road(self) -> List[Dict]:
        """获取道路上的所有车辆信息"""
        if not self.is_connected:
            return []
            
        vehicles = []
        for veh_id in traci.vehicle.getIDList():
            vehicles.append({
                'id': veh_id,
                'position': traci.vehicle.getPosition(veh_id),
                'speed': traci.vehicle.getSpeed(veh_id),
                'route': traci.vehicle.getRouteID(veh_id),
                'lane_position': traci.vehicle.getLanePosition(veh_id),
                'road_id': traci.vehicle.getRoadID(veh_id)
            })
        return vehicles
        
    def close(self):
        """关闭SUMO连接"""
        if self.is_connected:
            traci.close()
            self.is_connected = False
            print("✓ SUMO仿真已关闭")

# 创建增强的道路网络文件
def create_enhanced_sumo_network():
    """创建更真实的SUMO道路网络"""
    
    # 节点文件 - 模拟Wellington CBD的简化路网
    nodes_content = """<nodes>
    <!-- 主干道节点 -->
    <node id="n0" x="0" y="0" />
    <node id="n1" x="500" y="0" />
    <node id="n2" x="1000" y="0" />
    <node id="n3" x="1500" y="0" />
    
    <!-- 支路节点 -->
    <node id="n4" x="500" y="300" />
    <node id="n5" x="1000" y="300" />
    
    <!-- 环路节点 -->
    <node id="n6" x="250" y="-200" />
    <node id="n7" x="750" y="-200" />
    <node id="n8" x="1250" y="-200" />
</nodes>"""
    
    # 边文件 - 定义道路段
    edges_content = """<edges>
    <!-- 主干道 (Lambton Quay模拟) -->
    <edge id="main_1" from="n0" to="n1" priority="2" numLanes="2" speed="13.89" />
    <edge id="main_2" from="n1" to="n2" priority="2" numLanes="2" speed="13.89" />
    <edge id="main_3" from="n2" to="n3" priority="2" numLanes="2" speed="13.89" />
    
    <!-- 支路 (Willis Street模拟) -->
    <edge id="side_1" from="n1" to="n4" priority="1" numLanes="1" speed="11.11" />
    <edge id="side_2" from="n4" to="n5" priority="1" numLanes="1" speed="11.11" />
    <edge id="side_3" from="n5" to="n2" priority="1" numLanes="1" speed="11.11" />
    
    <!-- 环路 (Featherston Street模拟) -->
    <edge id="loop_1" from="n0" to="n6" priority="1" numLanes="1" speed="8.33" />
    <edge id="loop_2" from="n6" to="n7" priority="1" numLanes="1" speed="8.33" />
    <edge id="loop_3" from="n7" to="n8" priority="1" numLanes="1" speed="8.33" />
    <edge id="loop_4" from="n8" to="n3" priority="1" numLanes="1" speed="8.33" />
</edges>"""
    
    # 路线文件 - 定义车辆和路线
    routes_content = """<routes>
    <!-- 车辆类型定义 -->
    <vType id="ev_bdwpt" vClass="passenger" length="4.5" maxSpeed="16.67" accel="2.5" decel="4.5" sigma="0.5" color="0,1,0" />
    <vType id="ev_standard" vClass="passenger" length="4.5" maxSpeed="16.67" accel="2.5" decel="4.5" sigma="0.5" color="0,0,1" />
    <vType id="normal_car" vClass="passenger" length="4.5" maxSpeed="16.67" accel="2.5" decel="4.5" sigma="0.5" color="1,1,0" />
    
    <!-- 路线定义 -->
    <route id="route_main" edges="main_1 main_2 main_3" />
    <route id="route_side" edges="main_1 side_1 side_2 side_3 main_3" />
    <route id="route_loop" edges="loop_1 loop_2 loop_3 loop_4" />
    
    <!-- 交通流定义 - 使用flow而不是individual vehicles -->
    <flow id="flow_main_ev" type="ev_bdwpt" route="route_main" begin="0" end="3600" number="50" />
    <flow id="flow_side_ev" type="ev_standard" route="route_side" begin="0" end="3600" number="30" />
    <flow id="flow_normal" type="normal_car" route="route_main" begin="0" end="3600" number="100" />
</routes>"""
    
    # 配置文件
    config_content = """<configuration>
    <input>
        <net-file value="enhanced_road.net.xml"/>
        <route-files value="enhanced_road.rou.xml"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="3600"/>
        <step-length value="1"/>
    </time>
    <processing>
        <lateral-resolution value="0.8"/>
        <collision.check-junctions value="true"/>
    </processing>
</configuration>"""
    
    # 保存文件
    os.makedirs("sumo_files_v2", exist_ok=True)
    
    with open("sumo_files_v2/enhanced_road.nod.xml", "w") as f:
        f.write(nodes_content)
        
    with open("sumo_files_v2/enhanced_road.edg.xml", "w") as f:
        f.write(edges_content)
        
    with open("sumo_files_v2/enhanced_road.rou.xml", "w") as f:
        f.write(routes_content)
        
    with open("sumo_files_v2/enhanced_road.sumocfg", "w") as f:
        f.write(config_content)
        
    print("✓ 增强的SUMO网络文件已创建")
    
    # 生成网络文件
    try:
        import subprocess
        subprocess.run([
            "netconvert",
            "-n", "sumo_files_v2/enhanced_road.nod.xml",
            "-e", "sumo_files_v2/enhanced_road.edg.xml",
            "-o", "sumo_files_v2/enhanced_road.net.xml"
        ], check=True)
        print("✓ SUMO网络文件已生成")
    except Exception as e:
        print(f"⚠️ 网络生成失败（需要SUMO工具）: {e}")
        print("请手动运行: netconvert -n enhanced_road.nod.xml -e enhanced_road.edg.xml -o enhanced_road.net.xml")

if __name__ == "__main__":
    # 测试创建网络
    create_enhanced_sumo_network()