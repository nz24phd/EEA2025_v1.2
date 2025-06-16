import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import random

class ChargingMode(Enum):
    """充电模式枚举"""
    G2V = "G2V"  # 网络到车辆
    V2G = "V2G"  # 车辆到网络
    IDLE = "IDLE"  # 空闲

@dataclass
class EVState:
    """电动车状态信息"""
    vehicle_id: str
    bdwpt_enabled: bool = False
    soc: float = 0.5  # 电量状态 (0-1)
    battery_capacity_kwh: float = 60.0  # 电池容量 (kWh)
    max_power_kw: float = 50.0  # 最大功率 (kW)
    charging_efficiency: float = 0.95  # 充电效率
    is_connected: bool = True  # 是否连接到道路
    charging_power_kw: float = 0.0  # 当前充电功率
    arrival_time: int = 0  # 到达时间 (小时)
    departure_time: int = 24  # 离开时间 (小时)
    target_soc: float = 0.8  # 目标SoC
    min_soc: float = 0.2  # 最低SoC
    participation_willingness: float = 0.8  # V2G参与意愿 (0-1)

class BDWPTController:
    """增强版双向无线充电控制器"""
    
    def __init__(self):
        self.ev_states: Dict[str, EVState] = {}
        
        # 控制参数
        self.voltage_threshold_low = 0.95  # 低电压阈值
        self.voltage_threshold_high = 1.05  # 高电压阈值
        self.peak_demand_threshold_mw = 0.1  # 0.8 # 峰值需求阈值
        
        # 价格信号 ($/kWh)
        self.electricity_prices = {
            0: 0.08, 1: 0.08, 2: 0.08, 3: 0.08, 4: 0.08, 5: 0.08,  # 夜间
            6: 0.12, 7: 0.25, 8: 0.35, 9: 0.30, 10: 0.28, 11: 0.30,  # 上午
            12: 0.32, 13: 0.30, 14: 0.28, 15: 0.30, 16: 0.32, 17: 0.35,  # 下午
            18: 0.40, 19: 0.38, 20: 0.30, 21: 0.25, 22: 0.15, 23: 0.10   # 晚间
        }
        
        # 统计信息
        self.total_energy_traded_kwh = 0.0
        self.peak_shaving_achieved_kw = 0.0
        self.v2g_events = 0
        self.g2v_events = 0
        
    def initialize_ev(self, vehicle_id: str, bdwpt_enabled: bool = True, 
                     current_hour: int = 0) -> None:
        """初始化电动车"""
        
        # 随机生成现实的参数
        soc = np.random.uniform(0.2, 0.9)  # 初始SoC
        battery_capacity = np.random.uniform(50, 80)  # 电池容量
        max_power = np.random.uniform(30, 50)  # 最大功率
        
        # 随机行程时间
        arrival = current_hour
        departure = min(24, arrival + np.random.randint(1, 8))  # 停留1-8小时
        
        self.ev_states[vehicle_id] = EVState(
            vehicle_id=vehicle_id,
            bdwpt_enabled=bdwpt_enabled,
            soc=soc,
            battery_capacity_kwh=battery_capacity,
            max_power_kw=max_power,
            charging_efficiency=np.random.uniform(0.90, 0.98),
            arrival_time=arrival,
            departure_time=departure,
            target_soc=np.random.uniform(0.75, 0.95),
            participation_willingness=np.random.uniform(0.6, 1.0) if bdwpt_enabled else 0.0
        )
        
    def calculate_power_command(self, vehicle_id: str, local_voltage: float, 
                              current_hour: int, grid_demand_mw: float) -> float:
        """计算功率指令 (正值=充电G2V, 负值=放电V2G)"""
        
        if vehicle_id not in self.ev_states:
            return 0.0
            
        ev = self.ev_states[vehicle_id]
        
        if not ev.bdwpt_enabled or not ev.is_connected:
            return 0.0
            
        # 检查时间窗口
        if current_hour < ev.arrival_time or current_hour >= ev.departure_time:
            ev.is_connected = False
            return 0.0
            
        # 获取当前电价
        current_price = self.electricity_prices.get(current_hour, 0.20)
        
        # 1. 安全约束检查
        if ev.soc <= ev.min_soc:
            # 电量过低，必须充电
            power_kw = min(ev.max_power_kw * 0.8, 30.0)
            ev.charging_power_kw = power_kw
            self.g2v_events += 1
            print(f"EV {vehicle_id}: G2V emergency charging ({power_kw:.1f} kW)")
            return power_kw
            
        if ev.soc >= 0.95:
            # 电量满了，停止充电
            ev.charging_power_kw = 0.0
            return 0.0
            
        # 2. 电网支撑决策
        voltage_violation = False
        demand_violation = False
        
        if local_voltage < self.voltage_threshold_low:
            voltage_violation = True
            
        if grid_demand_mw > self.peak_demand_threshold_mw:
            demand_violation = True
            
        # 3. 智能充放电策略
        if voltage_violation or demand_violation:
            # 电网需要支撑 - 考虑V2G放电
            # if (ev.soc > 0.6 and 
            #     ev.participation_willingness > 0.5 and
            #     np.random.random() < 0.7):  # 70%概率参与V2G
            # 改进逻辑: 参与意愿越高，越有可能参与
            if (ev.soc > 0.6 and 
            np.random.random() < ev.participation_willingness):
                
                # V2G放电功率计算
                max_discharge = min(
                    ev.max_power_kw * 0.6,  # 限制在最大功率的60%
                    (ev.soc - ev.min_soc) * ev.battery_capacity_kwh * 2  # 基于可用电量
                )
                
                power_kw = -min(max_discharge, 25.0)  # 负值表示放电
                ev.charging_power_kw = power_kw
                self.v2g_events += 1
                self.peak_shaving_achieved_kw += abs(power_kw)
                
                print(f"EV {vehicle_id}: V2G grid support ({abs(power_kw):.1f} kW)")
                return power_kw
                
        # 4. 经济优化充电
        if current_price < 0.20:  # 低电价时段
            if ev.soc < ev.target_soc:
                # 机会充电
                power_kw = min(
                    ev.max_power_kw * 0.8,
                    (ev.target_soc - ev.soc) * ev.battery_capacity_kwh * 2,
                    40.0  # 限制最大功率
                )
                ev.charging_power_kw = power_kw
                self.g2v_events += 1
                print(f"EV {vehicle_id}: G2V opportunistic charging ({power_kw:.1f} kW)")
                return power_kw
                
        elif current_price > 0.30:  # 高电价时段
            if (ev.soc > 0.7 and 
                ev.participation_willingness > 0.6 and
                np.random.random() < 0.4):  # 40%概率在高价时段放电
                
                power_kw = -min(ev.max_power_kw * 0.5, 20.0)
                ev.charging_power_kw = power_kw
                self.v2g_events += 1
                print(f"EV {vehicle_id}: V2G price arbitrage ({abs(power_kw):.1f} kW)")
                return power_kw
                
        # 5. 默认慢充
        if ev.soc < ev.target_soc:
            power_kw = min(15.0, ev.max_power_kw * 0.3)  # 慢充
            ev.charging_power_kw = power_kw
            return power_kw
            
        # 6. 空闲状态
        ev.charging_power_kw = 0.0
        return 0.0
        
    def update_ev_soc(self, vehicle_id: str, power_kw: float, time_step_hours: float) -> None:
        """更新电动车SoC"""
        
        if vehicle_id not in self.ev_states:
            return
            
        ev = self.ev_states[vehicle_id]
        
        if power_kw == 0:
            return
            
        # 计算能量变化
        if power_kw > 0:  # 充电
            energy_kwh = power_kw * time_step_hours * ev.charging_efficiency
            soc_change = energy_kwh / ev.battery_capacity_kwh
            ev.soc = min(1.0, ev.soc + soc_change)
            self.total_energy_traded_kwh += energy_kwh
            
        else:  # 放电
            energy_kwh = abs(power_kw) * time_step_hours / ev.charging_efficiency
            soc_change = energy_kwh / ev.battery_capacity_kwh
            ev.soc = max(0.0, ev.soc - soc_change)
            self.total_energy_traded_kwh += energy_kwh
            
    def get_aggregated_power(self, current_hour: int) -> Dict[str, float]:
        """获取聚合功率统计"""
        
        total_g2v = 0.0
        total_v2g = 0.0
        active_vehicles = 0
        
        for ev in self.ev_states.values():
            if ev.is_connected and ev.bdwpt_enabled:
                if current_hour >= ev.arrival_time and current_hour < ev.departure_time:
                    active_vehicles += 1
                    if ev.charging_power_kw > 0:
                        total_g2v += ev.charging_power_kw
                    elif ev.charging_power_kw < 0:
                        total_v2g += abs(ev.charging_power_kw)
                        
        return {
            "total_g2v_kw": total_g2v,
            "total_v2g_kw": total_v2g,
            "net_power_kw": total_g2v - total_v2g,
            "active_vehicles": active_vehicles,
            "v2g_utilization": total_v2g / max(total_g2v + total_v2g, 1.0)
        }
        
    def get_performance_metrics(self) -> Dict[str, float]:
        """获取性能指标"""
        
        total_vehicles = len(self.ev_states)
        bdwpt_vehicles = sum(1 for ev in self.ev_states.values() if ev.bdwpt_enabled)
        
        avg_soc = np.mean([ev.soc for ev in self.ev_states.values()]) if total_vehicles > 0 else 0.5
        
        v2g_participation = self.v2g_events / max(bdwpt_vehicles, 1)
        
        return {
            "total_vehicles": total_vehicles,
            "bdwpt_vehicles": bdwpt_vehicles,
            "avg_final_soc": avg_soc,
            "total_energy_traded_kwh": self.total_energy_traded_kwh,
            "peak_shaving_achieved_kw": self.peak_shaving_achieved_kw,
            "v2g_events": self.v2g_events,
            "g2v_events": self.g2v_events,
            "v2g_participation_rate": v2g_participation
        }
        
    def reset_statistics(self):
        """重置统计信息"""
        self.total_energy_traded_kwh = 0.0
        self.peak_shaving_achieved_kw = 0.0
        self.v2g_events = 0
        self.g2v_events = 0