import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any
import multiprocessing as mp
import json
import os
import sys

# 确保在每个进程中都能找到我们的模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 在模块级别导入所需的类
try:
    from pypower.api import runpf, ppoption
except ImportError:
    print("警告：无法导入pypower，某些功能可能不可用")

class SimulationScenario:
    """定义蒙特卡洛分析的仿真场景"""
    def __init__(self, bdwpt_penetration, traffic_density, day_type, weather_condition, pv_penetration, scenario_name):
        self.bdwpt_penetration = bdwpt_penetration  # 0.0 到 1.0
        self.traffic_density = traffic_density      # 'low', 'medium', 'high'
        self.day_type = day_type                   # 'weekday', 'weekend'
        self.weather_condition = weather_condition # 'clear', 'rain', 'cold'
        self.pv_penetration = pv_penetration       # 太阳能光伏渗透率 (0.0 到 1.0)
        self.scenario_name = scenario_name
    
    def to_dict(self):
        return {
            'bdwpt_penetration': self.bdwpt_penetration,
            'traffic_density': self.traffic_density,
            'day_type': self.day_type,
            'weather_condition': self.weather_condition,
            'pv_penetration': self.pv_penetration,
            'scenario_name': self.scenario_name
        }

class SimulationResults:
    """存储单次仿真运行的结果"""
    def __init__(self, scenario, run_id, **kwargs):
        self.scenario = scenario
        self.run_id = run_id
        
        # 电压性能指标
        self.min_voltage_pu = kwargs.get('min_voltage_pu', 1.0)
        self.max_voltage_pu = kwargs.get('max_voltage_pu', 1.0)
        self.voltage_violations = kwargs.get('voltage_violations', 0)
        self.avg_voltage_deviation = kwargs.get('avg_voltage_deviation', 0.0)
        
        # 负荷和发电指标
        self.peak_demand_mw = kwargs.get('peak_demand_mw', 0.0)
        self.peak_shaving_achieved_mw = kwargs.get('peak_shaving_achieved_mw', 0.0)
        self.reverse_power_flow_hours = kwargs.get('reverse_power_flow_hours', 0)
        self.total_energy_traded_mwh = kwargs.get('total_energy_traded_mwh', 0.0)
        
        # EV指标
        self.avg_ev_soc_end = kwargs.get('avg_ev_soc_end', 0.5)
        self.charging_efficiency = kwargs.get('charging_efficiency', 0.95)
        self.v2g_utilization = kwargs.get('v2g_utilization', 0.0)
        
        # 电网性能
        self.total_losses_mwh = kwargs.get('total_losses_mwh', 0.0)
        self.transformer_loading_max = kwargs.get('transformer_loading_max', 0.0)
        self.line_loading_max = kwargs.get('line_loading_max', 0.0)
        
        # 经济指标
        self.grid_cost_savings = kwargs.get('grid_cost_savings', 0.0)
        self.ev_owner_revenue = kwargs.get('ev_owner_revenue', 0.0)
    
    def to_dict(self):
        result_dict = {}
        # 添加场景信息
        result_dict.update(self.scenario.to_dict())
        # 添加结果信息
        result_dict.update({
            'run_id': self.run_id,
            'min_voltage_pu': self.min_voltage_pu,
            'max_voltage_pu': self.max_voltage_pu,
            'voltage_violations': self.voltage_violations,
            'avg_voltage_deviation': self.avg_voltage_deviation,
            'peak_demand_mw': self.peak_demand_mw,
            'peak_shaving_achieved_mw': self.peak_shaving_achieved_mw,
            'reverse_power_flow_hours': self.reverse_power_flow_hours,
            'total_energy_traded_mwh': self.total_energy_traded_mwh,
            'avg_ev_soc_end': self.avg_ev_soc_end,
            'charging_efficiency': self.charging_efficiency,
            'v2g_utilization': self.v2g_utilization,
            'total_losses_mwh': self.total_losses_mwh,
            'transformer_loading_max': self.transformer_loading_max,
            'line_loading_max': self.line_loading_max,
            'grid_cost_savings': self.grid_cost_savings,
            'ev_owner_revenue': self.ev_owner_revenue
        })
        return result_dict

def _run_single_simulation_worker(scenario_and_run_data):
    """工作进程函数，需要在模块级别定义"""
    scenario_dict, run_id, base_network_data = scenario_and_run_data
    
    # 重构场景对象
    scenario = SimulationScenario(
        scenario_dict['bdwpt_penetration'],
        scenario_dict['traffic_density'],
        scenario_dict['day_type'],
        scenario_dict['weather_condition'],
        scenario_dict['pv_penetration'],
        scenario_dict['scenario_name']
    )
    
    # 在工作进程中导入所需模块
    try:
        from enhanced_simulation.bdwpt_controller import BDWPTController
        from enhanced_simulation.network_builder import RealisticLVNetworkBuilder
        from pypower.api import runpf, ppoption
    except ImportError as e:
        print(f"工作进程导入失败: {e}")
        return _create_failed_result(scenario, run_id)
    
    try:
        # 重建网络（从传递的数据）
        base_network = {
            'version': base_network_data['version'],
            'baseMVA': base_network_data['baseMVA'],
            'bus': np.array(base_network_data['bus']),
            'gen': np.array(base_network_data['gen']),
            'branch': np.array(base_network_data['branch']),
            'bus_names': base_network_data.get('bus_names', []),
            'load_profiles': base_network_data.get('load_profiles', {})
        }
        
        # 应用随机变化
        varied_network = _apply_stochastic_variations(base_network, scenario, run_id)
        
        # 初始化仿真组件
        bdwpt_controller = BDWPTController()
        network_builder = RealisticLVNetworkBuilder()
        
        # 仿真指标跟踪
        voltage_history = []
        power_flow_history = []
        ev_soc_history = []
        baseline_peak_mw = 0.0
        actual_peak_mw = 0.0
        
        # 基于时间的仿真（24小时完整循环）
        simulation_hours = 24
        time_steps_per_hour = 2  # 30分钟分辨率，平衡精度和速度
        total_steps = simulation_hours * time_steps_per_hour
        
        # 首先运行基准情况以确定baseline peak
        baseline_network = network_builder.update_loads_for_time(varied_network, 18, scenario.day_type)  # 晚高峰
        if scenario.pv_penetration > 0:
            baseline_network = network_builder.add_pv_generation(baseline_network, 18, scenario.pv_penetration)
        
        ppopt = ppoption(VERBOSE=0, OUT_ALL=0)
        baseline_results, baseline_success = runpf(baseline_network, ppopt)
        if baseline_success:
            baseline_peak_mw = sum(baseline_results['bus'][:, 2])
        
        # 主仿真循环
        for step in range(total_steps):
            current_hour = step // time_steps_per_hour
            time_fraction = (step % time_steps_per_hour) / time_steps_per_hour
            
            # 为当前时间更新网络负荷
            current_network = network_builder.update_loads_for_time(varied_network, current_hour, scenario.day_type)
            
            # 添加PV发电（如果适用）
            if scenario.pv_penetration > 0:
                current_network = network_builder.add_pv_generation(current_network, current_hour, scenario.pv_penetration)
            
            # 模拟交通模式和EV数量
            num_evs = _simulate_traffic_pattern(current_hour, scenario.traffic_density)
            
            # 记录当前无EV状态作为基准
            ppopt = ppoption(VERBOSE=0, OUT_ALL=0)
            no_ev_results, no_ev_success = runpf(current_network, ppopt)
            
            if no_ev_success:
                baseline_demand = sum(no_ev_results['bus'][:, 2])
                baseline_min_voltage = min(no_ev_results['bus'][:, 7])
            else:
                baseline_demand = 0.1
                baseline_min_voltage = 1.0
            
            # 处理BDWPT启用的车辆
            total_ev_power_mw = 0.0
            
            for ev_id in range(min(num_evs, 15)):  # 限制EV数量以加快速度
                veh_id = f"ev_{step}_{ev_id}"
                
                # 随机选择连接节点（住宅节点）
                residential_buses = list(range(3, len(current_network['bus']) + 1))
                if residential_buses:
                    node_id = np.random.choice(residential_buses)
                else:
                    continue
                
                # 初始化或更新EV
                if veh_id not in bdwpt_controller.ev_states:
                    is_bdwpt = np.random.random() < scenario.bdwpt_penetration
                    bdwpt_controller.initialize_ev(veh_id, is_bdwpt, current_hour)
                
                # 获取当前电压（使用上一步结果或初始值）
                if len(voltage_history) > 0:
                    local_voltage = voltage_history[-1]
                else:
                    local_voltage = 1.0
                
                # 计算功率指令
                power_command_kw = bdwpt_controller.calculate_power_command(
                    veh_id, local_voltage, current_hour, baseline_demand
                )
                
                # 应用功率到网络
                if power_command_kw != 0:
                    bus_index = node_id - 1
                    power_mw = power_command_kw / 1000.0
                    current_network['bus'][bus_index][2] += power_mw  # 有功功率
                    current_network['bus'][bus_index][3] += power_mw * 0.2  # 无功功率
                    total_ev_power_mw += power_mw
                
                # 更新EV SoC
                time_step_hours = 1.0 / time_steps_per_hour
                bdwpt_controller.update_ev_soc(veh_id, power_command_kw, time_step_hours)
            
            # 运行潮流计算
            ppopt = ppoption(VERBOSE=0, OUT_ALL=0)
            results, success = runpf(current_network, ppopt)
            
            if success:
                # 记录电压指标
                voltages = results['bus'][:, 7]
                min_voltage = min(voltages)
                max_voltage = max(voltages)
                voltage_history.append(min_voltage)
                
                # 记录功率指标
                total_demand_mw = sum(results['bus'][:, 2])
                power_flow_history.append(total_demand_mw)
                actual_peak_mw = max(actual_peak_mw, total_demand_mw)
                
                # 记录EV SoCs
                current_socs = [ev.soc for ev in bdwpt_controller.ev_states.values() 
                               if ev.bdwpt_enabled and ev.is_connected]
                if current_socs:
                    ev_soc_history.append(np.mean(current_socs))
            else:
                # 潮流计算失败，记录默认值
                voltage_history.append(0.9)
                power_flow_history.append(baseline_demand)
        
        # 计算最终指标
        result = _calculate_simulation_metrics(
            scenario, run_id, voltage_history, power_flow_history, 
            ev_soc_history, baseline_peak_mw, actual_peak_mw, bdwpt_controller
        )
        
        return result
        
    except Exception as e:
        print(f"场景 {scenario.scenario_name}, 运行 {run_id} 仿真失败: {str(e)}")
        return _create_failed_result(scenario, run_id)

def _simulate_traffic_pattern(hour: int, traffic_density: str) -> int:
    """改进的交通模式模拟"""
    base_traffic = {
        'low': 2,
        'medium': 5,
        'high': 10
    }
    
    # 基于小时的交通模式（更现实）
    if 7 <= hour <= 9 or 17 <= hour <= 19:  # 高峰时间
        multiplier = 2.0
    elif 22 <= hour <= 6:  # 夜间
        multiplier = 0.2
    elif 10 <= hour <= 16:  # 白天
        multiplier = 1.2
    else:
        multiplier = 0.8
    
    base_count = base_traffic.get(traffic_density, 5)
    actual_count = int(base_count * multiplier + np.random.poisson(1))
    return max(0, actual_count)

def _apply_stochastic_variations(base_network: Dict, scenario: SimulationScenario, run_id: int) -> Dict:
    """应用随机变化以创建现实的不确定性"""
    varied_network = {
        'version': base_network['version'],
        'baseMVA': base_network['baseMVA'],
        'bus': base_network['bus'].copy(),
        'gen': base_network['gen'].copy(),
        'branch': base_network['branch'].copy(),
        'bus_names': base_network.get('bus_names', []).copy(),
        'load_profiles': base_network.get('load_profiles', {}).copy()
    }
    
    # 设置随机种子以获得可重现的结果
    np.random.seed(run_id * 1000 + hash(scenario.scenario_name) % 1000)
    
    # 变化基础负荷（15%变化范围）
    for i, bus_data in enumerate(varied_network['bus']):
        if bus_data[1] == 1:  # PQ负荷节点
            load_multiplier = np.random.normal(1.0, 0.15)
            load_multiplier = np.clip(load_multiplier, 0.7, 1.3)
            
            varied_network['bus'][i][2] *= load_multiplier
            varied_network['bus'][i][3] *= load_multiplier
    
    # 天气条件影响
    weather_factor = 1.0
    if scenario.weather_condition == 'cold':
        weather_factor = 1.15  # 增加供暖负荷
    elif scenario.weather_condition == 'rain':
        weather_factor = 1.05  # 轻微增加负荷
    
    # 应用天气影响
    for i, bus_data in enumerate(varied_network['bus']):
        if bus_data[1] == 1:  # PQ节点
            varied_network['bus'][i][2] *= weather_factor
            varied_network['bus'][i][3] *= weather_factor
    
    return varied_network

def _calculate_simulation_metrics(scenario: SimulationScenario, run_id: int,
                                voltage_history: List, power_flow_history: List,
                                ev_soc_history: List, baseline_peak_mw: float,
                                actual_peak_mw: float, bdwpt_controller) -> SimulationResults:
    """从仿真结果计算综合指标"""
    
    # 电压指标
    if voltage_history:
        voltages = np.array(voltage_history)
        min_voltage = np.min(voltages)
        max_voltage = np.max(voltages)
        voltage_violations = np.sum((voltages < 0.95) | (voltages > 1.05))
        avg_voltage_dev = np.mean(np.abs(voltages - 1.0))
    else:
        min_voltage = 1.0
        max_voltage = 1.0
        voltage_violations = 0
        avg_voltage_dev = 0.0
    
    # 削峰计算
    peak_shaving_achieved_mw = max(0, baseline_peak_mw - actual_peak_mw)
    
    # 反向功率流
    reverse_flow_hours = sum(1 for p in power_flow_history if p < 0)
    
    # 获取BDWPT控制器性能指标
    controller_metrics = bdwpt_controller.get_performance_metrics()
    
    # EV指标
    avg_final_soc = controller_metrics.get('avg_final_soc', 0.5)
    v2g_participation = controller_metrics.get('v2g_participation_rate', 0.0)
    total_energy_traded_kwh = controller_metrics.get('total_energy_traded_kwh', 0.0)
    
    # 经济估算
    peak_tariff_per_kw = 0.35  # $/kW 削峰收益
    energy_price = 0.15  # $/kWh 能量价格
    
    grid_savings = peak_shaving_achieved_mw * 1000 * peak_tariff_per_kw
    ev_revenue = total_energy_traded_kwh * energy_price * 0.5  # EV车主获得50%收益
    
    return SimulationResults(
        scenario=scenario,
        run_id=run_id,
        min_voltage_pu=min_voltage,
        max_voltage_pu=max_voltage,
        voltage_violations=int(voltage_violations),
        avg_voltage_deviation=avg_voltage_dev,
        peak_demand_mw=actual_peak_mw,
        peak_shaving_achieved_mw=peak_shaving_achieved_mw,
        reverse_power_flow_hours=int(reverse_flow_hours),
        total_energy_traded_mwh=total_energy_traded_kwh / 1000,
        avg_ev_soc_end=avg_final_soc,
        charging_efficiency=0.95,
        v2g_utilization=v2g_participation,
        total_losses_mwh=0.0,
        transformer_loading_max=actual_peak_mw / 0.4,  # 基于400kVA变压器
        line_loading_max=0.0,
        grid_cost_savings=grid_savings,
        ev_owner_revenue=ev_revenue
    )

def _create_failed_result(scenario: SimulationScenario, run_id: int) -> SimulationResults:
    """为失败的仿真创建结果对象"""
    return SimulationResults(
        scenario=scenario, 
        run_id=run_id,
        min_voltage_pu=1.0,
        max_voltage_pu=1.0,
        voltage_violations=0,
        avg_ev_soc_end=0.5,
        peak_demand_mw=0.1,
        peak_shaving_achieved_mw=0.0
    )

class MonteCarloSimulationFramework:
    """BDWPT研究的完整蒙特卡洛仿真框架"""
    
    def __init__(self, 
                 base_network: Dict,
                 sumo_config_path: str,
                 num_scenarios: int = 3,
                 runs_per_scenario: int = 10):
        
        self.base_network = base_network
        self.sumo_config_path = sumo_config_path
        self.num_scenarios = num_scenarios
        self.runs_per_scenario = runs_per_scenario
        
        # 定义要测试的场景（现实化）
        self.scenarios = [
            SimulationScenario(0.0, 'medium', 'weekday', 'clear', 0.3, 'Baseline'),
            SimulationScenario(0.15, 'medium', 'weekday', 'clear', 0.3, 'Low_BDWPT'),
            SimulationScenario(0.40, 'medium', 'weekday', 'clear', 0.3, 'High_BDWPT'),
        ]
        
        # 结果存储
        self.all_results: List[SimulationResults] = []
        self.results_df: pd.DataFrame = None
    
    def run_monte_carlo_analysis(self, parallel: bool = True) -> pd.DataFrame:
        """运行完整的蒙特卡洛分析"""
        print(f"开始蒙特卡洛分析:")
        print(f"- {len(self.scenarios)} 个场景")
        print(f"- 每场景 {self.runs_per_scenario} 次运行")
        print(f"- 总计: {len(self.scenarios) * self.runs_per_scenario} 次仿真")
        
        if parallel and mp.cpu_count() > 1:
            return self._run_parallel_simulations()
        else:
            return self._run_sequential_simulations()
    
    def _run_parallel_simulations(self) -> pd.DataFrame:
        """使用多进程并行运行仿真"""
        simulation_tasks = []
        
        # 准备可序列化的网络数据
        serializable_network = {
            'version': self.base_network['version'],
            'baseMVA': self.base_network['baseMVA'],
            'bus': self.base_network['bus'].tolist(),
            'gen': self.base_network['gen'].tolist(),
            'branch': self.base_network['branch'].tolist(),
            'bus_names': self.base_network.get('bus_names', []),
            'load_profiles': self.base_network.get('load_profiles', {})
        }
        
        for scenario in self.scenarios:
            for run_id in range(self.runs_per_scenario):
                simulation_tasks.append((scenario.to_dict(), run_id, serializable_network))
        
        # 使用多进程池（限制核心数）
        num_cores = min(mp.cpu_count() - 1, 4)
        
        print(f"使用 {num_cores} 个CPU核心进行并行仿真...")
        
        with mp.Pool(num_cores) as pool:
            results = pool.map(_run_single_simulation_worker, simulation_tasks)
        
        self.all_results = results
        self._create_results_dataframe()
        return self.results_df
    
    def _run_sequential_simulations(self) -> pd.DataFrame:
        """顺序运行仿真（用于调试）"""
        for scenario in self.scenarios:
            print(f"\n运行场景: {scenario.scenario_name}")
            
            serializable_network = {
                'version': self.base_network['version'],
                'baseMVA': self.base_network['baseMVA'],
                'bus': self.base_network['bus'].tolist(),
                'gen': self.base_network['gen'].tolist(),
                'branch': self.base_network['branch'].tolist(),
                'bus_names': self.base_network.get('bus_names', []),
                'load_profiles': self.base_network.get('load_profiles', {})
            }
            
            for run_id in range(self.runs_per_scenario):
                if run_id % 5 == 0:
                    print(f"  运行 {run_id + 1}/{self.runs_per_scenario}")
                
                result = _run_single_simulation_worker((scenario.to_dict(), run_id, serializable_network))
                self.all_results.append(result)
        
        self._create_results_dataframe()
        return self.results_df
    
    def _create_results_dataframe(self):
        """将结果转换为pandas DataFrame用于分析"""
        results_data = []
        
        for result in self.all_results:
            results_data.append(result.to_dict())
        
        self.results_df = pd.DataFrame(results_data)
    
    def generate_statistical_summary(self) -> Dict:
        """生成蒙特卡洛结果的统计摘要"""
        if self.results_df is None:
            raise ValueError("没有可用结果。请先运行仿真。")
        
        summary = {}
        
        for scenario_name in self.results_df['scenario_name'].unique():
            scenario_data = self.results_df[self.results_df['scenario_name'] == scenario_name]
            
            summary[scenario_name] = {
                'voltage_performance': {
                    'min_voltage_mean': float(scenario_data['min_voltage_pu'].mean()),
                    'min_voltage_std': float(scenario_data['min_voltage_pu'].std()),
                    'voltage_violations_mean': float(scenario_data['voltage_violations'].mean()),
                },
                'peak_shaving': {
                    'peak_shaving_mean_mw': float(scenario_data['peak_shaving_achieved_mw'].mean()),
                    'peak_shaving_std_mw': float(scenario_data['peak_shaving_achieved_mw'].std()),
                },
                'economic_benefits': {
                    'grid_savings_mean': float(scenario_data['grid_cost_savings'].mean()),
                    'ev_revenue_mean': float(scenario_data['ev_owner_revenue'].mean()),
                },
                'ev_performance': {
                    'final_soc_mean': float(scenario_data['avg_ev_soc_end'].mean()),
                    'v2g_utilization_mean': float(scenario_data['v2g_utilization'].mean()),
                }
            }
        
        return summary