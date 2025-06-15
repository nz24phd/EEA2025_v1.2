import numpy as np
from typing import Dict, List, Tuple, Optional
import pandas as pd

class RealisticLVNetworkBuilder:
    """现实低压配电网络构建器"""
    
    # def __init__(self):
    #     # 标准低压参数
    #     self.base_voltage_kv = 0.4  # 400V低压系统
    #     self.base_mva = 1.0  # 1MVA基准
    def __init__(self):
        # 使用NZ数据
        nz_specs = NZDistributionNetworkData().nz_network_standards
        
        self.base_voltage_kv = nz_specs['voltage_levels']['lv_secondary'] # 0.4kV
        self.base_mva = 1.0
        self.cable_params = nz_specs['cable_standards']['underground_cu_95'] # 使用95mm²铜缆
        
        # 典型负荷配置文件 (p.u.)
        self.load_profiles = {
            'residential': {
                'weekday': [0.4, 0.35, 0.3, 0.3, 0.35, 0.5, 0.7, 0.9, 0.8, 0.7, 0.65, 0.6,
                           0.55, 0.5, 0.5, 0.55, 0.7, 0.9, 1.0, 0.95, 0.85, 0.7, 0.55, 0.45],
                'weekend': [0.45, 0.4, 0.35, 0.35, 0.4, 0.45, 0.55, 0.65, 0.7, 0.75, 0.8, 0.85,
                           0.9, 0.85, 0.8, 0.75, 0.8, 0.85, 0.9, 0.85, 0.8, 0.7, 0.6, 0.5]
            }
        }
        
    def create_realistic_lv_network(self, num_houses: int = 20) -> Dict:
        """创建现实的低压配电网络"""
        
        # 确保合理的房屋数量
        num_houses = min(max(num_houses, 8), 50)
        total_buses = num_houses + 2  # 房屋 + 变压器 + 馈线点
        
        # 1. 创建节点矩阵 [bus_num, bus_type, Pd, Qd, Gs, Bs, area, Vm, Va, baseKV, zone, Vmax, Vmin]
        bus = np.zeros((total_buses, 13))
        
        # 主变压器节点 (slack bus)
        bus[0, :] = [1, 3, 0, 0, 0, 0, 1, 1.0, 0, self.base_voltage_kv, 1, 1.1, 0.9]
        
        # 低压母线节点 (PV bus - 连接到变压器)
        bus[1, :] = [2, 2, 0, 0, 0, 0, 1, 1.0, 0, self.base_voltage_kv, 1, 1.05, 0.95]
        
        # 住宅负荷节点 (PQ buses)
        for i in range(2, total_buses):
            house_load_kw = np.random.uniform(3, 8)  # 3-8kW典型住宅负荷
            house_load_mw = house_load_kw / 1000.0
            house_load_mvar = house_load_mw * 0.3  # 功率因数约0.95
            
            bus[i, :] = [i+1, 1, house_load_mw, house_load_mvar, 0, 0, 1, 1.0, 0, 
                        self.base_voltage_kv, 1, 1.05, 0.95]
        
        # 2. 创建发电机矩阵 [bus, Pg, Qg, Qmax, Qmin, Vg, mBase, status, Pmax, Pmin]
        gen = np.array([
            [1, 0, 0, 999, -999, 1.0, self.base_mva * 100, 1, 999, -999],  # 主网连接
            [2, 0, 0, 50, -50, 1.0, self.base_mva * 100, 1, 50, 0]       # 变压器
        ])
        
        # 3. 创建线路矩阵 [fbus, tbus, r, x, b, rateA, rateB, rateC, ratio, angle, status, angmin, angmax]
        branches = []
        
        # 主变压器连接 (高压到低压)
        # 典型400kVA变压器: 11kV/0.4kV
        transformer_r = 0.02  # 2%电阻
        transformer_x = 0.05  # 5%电抗
        branches.append([1, 2, transformer_r, transformer_x, 0, 0.4, 0.5, 0.6, 0, 0, 1, -360, 360])
        
        # 低压配电线路 (从母线到各住宅)
        for i in range(3, total_buses + 1):
            # 计算到母线的距离 (模拟街道布局)
            distance_m = np.random.uniform(50, 200)  # 50-200米
            
            # 低压电缆参数 (XLPE 电缆)
            # r_per_km = 0.32  # ohm/km (95mm²电缆)
            # x_per_km = 0.08  # ohm/km
            r_per_km = self.cable_params['r_ohm_km']
            x_per_km = self.cable_params['x_ohm_km']
            # 转换为标准化值
            distance_km = distance_m / 1000.0
            r_pu = (r_per_km * distance_km) / ((self.base_voltage_kv**2) / self.base_mva)
            x_pu = (x_per_km * distance_km) / ((self.base_voltage_kv**2) / self.base_mva)
            
            # 限制最小阻抗避免数值问题
            r_pu = max(r_pu, 0.001)
            x_pu = max(x_pu, 0.0005)
            
            branches.append([2, i, r_pu, x_pu, 0, 0.1, 0.12, 0.15, 0, 0, 1, -360, 360])
        
        branch = np.array(branches)
        
        # 4. 创建网络字典
        network = {
            'version': '2',
            'baseMVA': self.base_mva,
            'bus': bus,
            'gen': gen,
            'branch': branch,
            'bus_names': [f'Bus_{i+1}' for i in range(total_buses)],
            'load_profiles': self.load_profiles.copy()
        }
        
        return network
    
    def update_loads_for_time(self, network: Dict, hour: int, day_type: str = 'weekday') -> Dict:
        """根据时间更新负荷"""
        
        updated_network = {
            'version': network['version'],
            'baseMVA': network['baseMVA'],
            'bus': network['bus'].copy(),
            'gen': network['gen'].copy(),
            'branch': network['branch'].copy(),
            'bus_names': network['bus_names'].copy(),
            'load_profiles': network['load_profiles'].copy()
        }
        
        # 获取负荷配置文件
        hour = hour % 24  # 确保在0-23范围内
        load_multiplier = self.load_profiles['residential'][day_type][hour]
        
        # 更新所有负荷节点 (跳过前两个系统节点)
        for i in range(2, len(updated_network['bus'])):
            if updated_network['bus'][i][1] == 1:  # PQ节点
                # 添加随机变化 (±15%)
                random_factor = np.random.uniform(0.85, 1.15)
                final_multiplier = load_multiplier * random_factor
                
                # 应用负荷乘数
                base_pd = network['bus'][i][2]  # 基础有功负荷
                base_qd = network['bus'][i][3]  # 基础无功负荷
                
                updated_network['bus'][i][2] = base_pd * final_multiplier
                updated_network['bus'][i][3] = base_qd * final_multiplier
        
        return updated_network
    
    def add_pv_generation(self, network: Dict, hour: int, pv_penetration: float = 0.3) -> Dict:
        """添加太阳能光伏发电"""
        
        updated_network = {
            'version': network['version'],
            'baseMVA': network['baseMVA'],
            'bus': network['bus'].copy(),
            'gen': network['gen'].copy(),
            'branch': network['branch'].copy(),
            'bus_names': network['bus_names'].copy(),
            'load_profiles': network['load_profiles'].copy()
        }
        
        # 太阳辐照模型 (简化)
        if 6 <= hour <= 18:  # 日照时间
            sun_angle = np.pi * (hour - 6) / 12  # 太阳角度
            irradiance = np.sin(sun_angle) * np.random.uniform(0.7, 1.0)  # 考虑云层
        else:
            irradiance = 0.0
        
        # 应用PV到部分住宅
        num_houses = len(updated_network['bus']) - 2
        num_pv_houses = int(num_houses * pv_penetration)
        
        for i in range(2, 2 + num_pv_houses):
            if updated_network['bus'][i][1] == 1:  # 负荷节点
                # 典型住宅PV系统 (3-5kW)
                pv_capacity_kw = np.random.uniform(3, 5)
                pv_output_kw = pv_capacity_kw * irradiance
                pv_output_mw = pv_output_kw / 1000.0
                
                # 减少负荷 (净计量)
                updated_network['bus'][i][2] -= pv_output_mw  # 减少有功负荷
                updated_network['bus'][i][3] -= pv_output_mw * 0.1  # 轻微减少无功负荷
        
        return updated_network
    
    def validate_network(self, network: Dict) -> Tuple[bool, List[str]]:
        """验证网络参数合理性"""
        
        issues = []
        
        # 检查节点数据
        bus = network['bus']
        branch = network['branch']
        
        # 1. 电压基准检查
        voltages = bus[:, 7]  # Vm列
        if np.any(voltages < 0.5) or np.any(voltages > 1.5):
            issues.append("初始电压设置不合理")
        
        # 2. 负荷合理性检查
        loads_mw = bus[:, 2]  # Pd列
        total_load = np.sum(loads_mw)
        if total_load <= 0 or total_load > 1.0:  # 总负荷应在合理范围
            issues.append(f"总负荷不合理: {total_load:.3f} MW")
        
        # 3. 线路阻抗检查
        resistances = branch[:, 2]  # r列
        reactances = branch[:, 3]   # x列
        
        if np.any(resistances <= 0) or np.any(reactances < 0):
            issues.append("线路阻抗参数不合理")
        
        if np.any(resistances > 1.0) or np.any(reactances > 1.0):
            issues.append("线路阻抗过大，可能导致电压问题")
        
        # 4. 节点连通性检查
        bus_numbers = set(bus[:, 0].astype(int))
        branch_buses = set(branch[:, 0].astype(int)) | set(branch[:, 1].astype(int))
        
        if not branch_buses.issubset(bus_numbers):
            issues.append("存在未定义的线路连接节点")
        
        return len(issues) == 0, issues
    
    def get_network_summary(self, network: Dict) -> Dict:
        """获取网络摘要信息"""
        
        bus = network['bus']
        branch = network['branch']
        
        num_buses = len(bus)
        num_branches = len(branch)
        
        # 负荷统计
        total_load_mw = np.sum(bus[:, 2])
        total_load_mvar = np.sum(bus[:, 3])
        
        # 节点类型统计
        slack_buses = np.sum(bus[:, 1] == 3)
        pv_buses = np.sum(bus[:, 1] == 2)
        pq_buses = np.sum(bus[:, 1] == 1)
        
        summary = {
            'total_buses': num_buses,
            'total_branches': num_branches,
            'slack_buses': slack_buses,
            'pv_buses': pv_buses,
            'pq_buses': pq_buses,
            'total_load_mw': total_load_mw,
            'total_load_mvar': total_load_mvar,
            'total_load_kw': total_load_mw * 1000,
            'base_voltage_kv': self.base_voltage_kv,
            'base_mva': network['baseMVA']
        }
        
        return summary
    
    def create_network_validation_report(self, network: Dict) -> str:
        """创建网络验证报告"""
        is_valid, issues = self.validate_network(network)
        summary = self.get_network_summary(network)
        
        report = "=== 网络验证报告 ===\n"
        report += f"网络状态: {'✓ 有效' if is_valid else '❌ 有问题'}\n"
        report += f"节点总数: {summary['total_buses']}\n"
        report += f"线路总数: {summary['total_branches']}\n"
        report += f"总负荷: {summary['total_load_kw']:.1f} kW\n"
        report += f"基准电压: {summary['base_voltage_kv']} kV\n"
        
        if issues:
            report += "\n发现的问题:\n"
            for issue in issues:
                report += f"  - {issue}\n"
        
        return report