"""
增强版Monte Carlo仿真框架
集成真实SUMO交通仿真
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import multiprocessing as mp
import os
import sys
import json
import copy

# 导入增强模块
from enhanced_simulation.monte_carlo import SimulationScenario, SimulationResults
from enhanced_simulation.bdwpt_controller import BDWPTController
from enhanced_simulation.network_builder import RealisticLVNetworkBuilder
from enhanced_simulation.sumo_integration import SUMOIntegration
from enhanced_simulation.gis_network_mapping import GISNetworkMapping
from enhanced_simulation.advanced_bdwpt import AdvancedBDWPTModeling
# from enhanced_simulation.analysis_tools import BDWPTAnalysisTools

class EnhancedMonteCarloFramework:
    """集成SUMO的增强版Monte Carlo框架"""
    
    def __init__(self, base_network: Dict, use_sumo: bool = True):
        self.base_network = base_network
        self.use_sumo = use_sumo
        self.runs_per_scenario = 10
        
        # 定义更详细的场景
        self.scenarios = [
            SimulationScenario(0.0, 'medium', 'weekday', 'clear', 0.3, 'Baseline'),
            SimulationScenario(0.15, 'medium', 'weekday', 'clear', 0.3, 'Low_BDWPT'),
            SimulationScenario(0.40, 'medium', 'weekday', 'clear', 0.3, 'High_BDWPT'),
            SimulationScenario(0.40, 'high', 'weekday', 'rain', 0.3, 'High_Traffic_Rain'),
            SimulationScenario(0.40, 'low', 'weekend', 'clear', 0.5, 'Weekend_HighPV')
        ]
        
    def run_single_simulation_with_sumo(self, scenario: SimulationScenario, 
                                      run_id: int) -> SimulationResults:
        """运行包含SUMO的单次仿真"""
        
        print(f"  运行 {scenario.scenario_name} - 第{run_id+1}次")

        # 初始化组件
        bdwpt_controller = BDWPTController()
        network_builder = RealisticLVNetworkBuilder()
        gis_mapper = GISNetworkMapping()
        bdwpt_model = AdvancedBDWPTModeling()
        
        # 复制基础网络
        current_network = copy.deepcopy(self.base_network)
        
        # 结果跟踪
        voltage_history = []
        power_history = []
        ev_stats = []
        
        if self.use_sumo:
            # 使用SUMO仿真
            sumo = SUMOIntegration("sumo_files_v2/enhanced_road.sumocfg")
            sumo.start_simulation(gui=False)
            
            try:
                # 仿真16小时(从早上7点到晚上11点)
                simulation_duration = 16 * 3600  # 16小时，单位为秒
                for step in range(simulation_duration):  # 16小时，1秒步长
                    sumo.step()
                    
                    # 每15分钟（900秒）更新一次电力网络
                    if step % 900 == 0:
                        current_time = 7 + step / 3600  # 从早上7点开始
                        
                        # 获取道路上的车辆
                        vehicles = sumo.get_vehicles_on_road()
                        
                        # 处理每辆车
                        total_power_by_bus = {}
                        active_evs = 0
                        
                        for vehicle in vehicles:
                            veh_id = vehicle['id']
                            road_id = vehicle['road_id']
                            position = vehicle['lane_position']
                            speed = vehicle['speed']
                            
                            # 检查是否是EV
                            if 'ev' in veh_id:
                                active_evs += 1
                                
                                # 检查是否在BDWPT区域
                                in_zone, zone_info = gis_mapper.is_in_bdwpt_zone(road_id, position)
                                
                                if in_zone and np.random.random() < scenario.bdwpt_penetration:
                                    # 初始化EV（如果需要）
                                    if veh_id not in bdwpt_controller.ev_states:
                                        bdwpt_controller.initialize_ev(veh_id, True, int(current_time))
                                    
                                    # 获取最近的配电网节点
                                    nearest_bus = gis_mapper.get_nearest_bus(road_id, position)
                                    
                                    # 获取该节点的电压
                                    bus_idx = nearest_bus - 1
                                    if 0 <= bus_idx < len(current_network['bus']):
                                        voltage = current_network['bus'][bus_idx][7]
                                    else:
                                        voltage = 1.0
                                    
                                    # 计算功率指令
                                    grid_demand = sum(current_network['bus'][:, 2])
                                    power_command = bdwpt_controller.calculate_power_command(
                                        veh_id, voltage, int(current_time), grid_demand
                                    )
                                    
                                    # 使用高级模型计算动态效率
                                    speed_kmh = speed * 3.6
                                    alignment_error = np.random.uniform(0, 15)
                                    air_gap = np.random.uniform(12, 20)
                                    
                                    dynamic_efficiency = bdwpt_model.calculate_dynamic_efficiency(
                                        speed_kmh, alignment_error, air_gap
                                    )
                                    
                                    adjusted_power = 0
                                    if power_command > 0: # 充电 G2V
                                        adjusted_power = power_command * dynamic_efficiency
                                    elif power_command < 0: # 放电 V2G
                                        adjusted_power = power_command / max(dynamic_efficiency, 0.1) # 避免除以零

                                    # 累加到对应节点
                                    if nearest_bus not in total_power_by_bus:
                                        total_power_by_bus[nearest_bus] = 0
                                    total_power_by_bus[nearest_bus] += adjusted_power / 1000  # 转换为MW
                                    
                                    # 更新EV SoC
                                    bdwpt_controller.update_ev_soc(veh_id, adjusted_power, 30/3600)
                        
                        # 更新网络负荷
                        network_with_time = network_builder.update_loads_for_time(
                            current_network, int(current_time), scenario.day_type
                        )
                        
                        # 应用EV功率到网络
                        for bus_id, power_mw in total_power_by_bus.items():
                            bus_idx = bus_id - 1
                            if 0 <= bus_idx < len(network_with_time['bus']):
                                network_with_time['bus'][bus_idx][2] += power_mw
                                network_with_time['bus'][bus_idx][3] += power_mw * 0.2
                        
                        # 运行潮流计算
                        from pypower.api import runpf, ppoption
                        ppopt = ppoption(VERBOSE=0, OUT_ALL=0)
                        results, success = runpf(network_with_time, ppopt)
                        
                        if success:
                            min_voltage = min(results['bus'][:, 7])
                            total_demand = sum(results['bus'][:, 2])
                            
                            voltage_history.append(min_voltage)
                            power_history.append(total_demand)
                            ev_stats.append({
                                'active_evs': active_evs,
                                'charging_evs': len(total_power_by_bus),
                                'total_ev_power': sum(total_power_by_bus.values())
                            })
                            
            finally:
                sumo.close()
                
        else:
            # === 为“快速演示”模式（不使用SUMO）实现的简化仿真逻辑 ===
            print("  运行简化模型（无SUMO）...")
            num_evs = 30  # 假设有30辆EV
            
            # 初始化EV
            for i in range(num_evs):
                veh_id = f"demo_ev_{i}"
                is_bdwpt = np.random.random() < scenario.bdwpt_penetration
                if is_bdwpt:
                    bdwpt_controller.initialize_ev(veh_id, True, 0)

            # 按小时步长仿真24小时
            for hour in range(24):
                # 更新住宅和光伏负荷
                network_with_time = network_builder.update_loads_for_time(
                    current_network, hour, scenario.day_type
                )
                network_with_time = network_builder.add_pv_generation(
                    network_with_time, hour, scenario.pv_penetration
                )
                
                # 计算所有EV的总功率
                total_ev_power_mw = 0
                for veh_id, ev_state in bdwpt_controller.ev_states.items():
                    if ev_state.bdwpt_enabled:
                        # 简化模型：假设电压恒定，电网需求为总负荷
                        voltage = 1.0 
                        grid_demand = sum(network_with_time['bus'][:, 2]) # 有功功率PD之和
                        
                        power_command_kw = bdwpt_controller.calculate_power_command(
                            veh_id, voltage, hour, grid_demand
                        )
                        
                        # 在简化模型中，我们假设效率为1
                        total_ev_power_mw += power_command_kw / 1000.0
                        
                        # 更新EV SoC
                        bdwpt_controller.update_ev_soc(veh_id, power_command_kw, 1.0) # 1小时步长
                
                # 将EV总功率应用到网络的低压母线上 (Bus 2)
                network_with_time['bus'][1][2] += total_ev_power_mw # Bus索引为1
                
                # 运行潮流计算
                from pypower.api import runpf, ppoption
                ppopt = ppoption(VERBOSE=0, OUT_ALL=0)
                results, success = runpf(network_with_time, ppopt)
                
                if success:
                    min_voltage = min(results['bus'][:, 7])
                    total_demand = sum(results['bus'][:, 2])
                    voltage_history.append(min_voltage)
                    power_history.append(total_demand)
                    # 简化统计
                    ev_stats.append({
                        'active_evs': len(bdwpt_controller.ev_states),
                        'charging_evs': len(bdwpt_controller.ev_states),
                        'total_ev_power': total_ev_power_mw
                    })
            # === 简化仿真逻辑结束 ===
            
        # 计算最终指标
        return self._calculate_results(scenario, run_id, voltage_history, 
                                     power_history, ev_stats, bdwpt_controller)
        
    def _calculate_results(self, scenario, run_id, voltage_history, 
                          power_history, ev_stats, bdwpt_controller):
        """计算仿真结果指标"""
        
        # 基础指标
        min_voltage = min(voltage_history) if voltage_history else 1.0
        max_voltage = max(voltage_history) if voltage_history else 1.0
        voltage_violations = sum(1 for v in voltage_history if v < 0.95 or v > 1.05)
        
        # 削峰指标
        baseline_peak = max(power_history[:len(power_history)//3]) if power_history else 0
        actual_peak = max(power_history) if power_history else 0
        peak_shaving = max(0, baseline_peak - actual_peak)
        
        # EV指标
        controller_metrics = bdwpt_controller.get_performance_metrics()
        
        # 经济指标
        # peak_reduction_value = peak_shaving * 1000 * 0.35  # $0.35/kW
        energy_traded = controller_metrics['total_energy_traded_kwh']
        energy_value = energy_traded * 0.15  # $0.15/kWh
        
        # return SimulationResults(
        #     scenario=scenario,
        #     run_id=run_id,
        #     min_voltage_pu=min_voltage,
        #     max_voltage_pu=max_voltage,
        #     voltage_violations=voltage_violations,
        #     avg_voltage_deviation=np.mean([abs(v - 1.0) for v in voltage_history]) if voltage_history else 0,
        #     peak_demand_mw=actual_peak,
        #     peak_shaving_achieved_mw=peak_shaving,
        #     total_energy_traded_mwh=energy_traded / 1000,
        #     avg_ev_soc_end=controller_metrics['avg_final_soc'],
        #     v2g_utilization=controller_metrics.get('v2g_participation_rate', 0),
        #     grid_cost_savings=peak_reduction_value,
        #     ev_owner_revenue=energy_value * 0.5
        # )
        
        return SimulationResults(
            scenario=scenario,
            run_id=run_id,
            min_voltage_pu=min_voltage,
            max_voltage_pu=max_voltage,
            voltage_violations=voltage_violations,
            avg_voltage_deviation=np.mean([abs(v - 1.0) for v in voltage_history]) if voltage_history else 0,
            peak_demand_mw=actual_peak,
            # 将peak_shaving和grid_cost_savings暂时设为0，它们将在后处理中计算
            peak_shaving_achieved_mw=0, 
            grid_cost_savings=0,
            total_energy_traded_mwh=energy_traded / 1000,
            avg_ev_soc_end=controller_metrics['avg_final_soc'],
            v2g_utilization=controller_metrics.get('v2g_participation_rate', 0),
            # ev_owner_revenue的计算可以保留，因为它不依赖于peak_shaving
            ev_owner_revenue=energy_traded * 0.15 * 0.5 
        )
    
    def run_analysis(self):
        """运行完整分析"""
        print("开始增强版Monte Carlo分析（包含SUMO）")
        
        all_results = []
        
        for scenario in self.scenarios:
            print(f"\n场景: {scenario.scenario_name}")
            
            # 使用简单的循环代替多进程，以简化调试
            for run_id in range(self.runs_per_scenario):
                result = self.run_single_simulation_with_sumo(scenario, run_id)
                all_results.append(result)
                
        # 转换为DataFrame
        results_data = [r.to_dict() for r in all_results]
        results_df = pd.DataFrame(results_data)
        
        # 保存结果
        os.makedirs("results", exist_ok=True)
        results_df.to_csv('results/monte_carlo_v2_results.csv', index=False)
        
        # 生成统计摘要
        summary = self._generate_summary(results_df)
        with open('results/summary_v2.json', 'w') as f:
            json.dump(summary, f, indent=2)
            
        print("\n✓ 分析完成！结果已保存到results文件夹")
        
        return results_df, summary
        
    def _generate_summary(self, results_df):
        """生成统计摘要"""
        summary = {}
        
        for scenario_name in results_df['scenario_name'].unique():
            scenario_data = results_df[results_df['scenario_name'] == scenario_name]
            
            summary[scenario_name] = {
                'voltage_performance': {
                    'min_voltage_mean': float(scenario_data['min_voltage_pu'].mean()),
                    'min_voltage_std': float(scenario_data['min_voltage_pu'].std()),
                    'violations_mean': float(scenario_data['voltage_violations'].mean())
                },
                'peak_shaving': {
                    'mean_mw': float(scenario_data['peak_shaving_achieved_mw'].mean()),
                    'std_mw': float(scenario_data['peak_shaving_achieved_mw'].std())
                },
                'economics': {
                    'grid_savings_mean': float(scenario_data['grid_cost_savings'].mean()),
                    'ev_revenue_mean': float(scenario_data['ev_owner_revenue'].mean())
                }
            }
            
        return summary