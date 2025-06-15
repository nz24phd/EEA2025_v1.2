import os
import sys
import traci
import numpy as np
# 核心修正：额外导入ppoption函数
from pypower.api import runpf, ppoption 
from matpower_files.case5_feeder_py import case5_feeder_data

# --- 仿真参数 ---
SUMO_CONFIG_PATH = "sumo_files/road.sumocfg"
SIMULATION_STEPS = 200
EV_CHARGING_POWER_KW = 30

# --- 检查SUMO环境变量 ---
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

def map_pos_to_node(position):
    if 0 <= position < 250: return 2
    elif 250 <= position < 500: return 3
    elif 500 <= position < 750: return 4
    elif 750 <= position <= 1000: return 5
    else: return None

def run_simulation():
    sumo_cmd = ["sumo", "-c", SUMO_CONFIG_PATH]
    traci.start(sumo_cmd)
    print("SUMO仿真已启动。")

    voltage_history = []
    print("\n--- 开始纯Python联合仿真 ---")
    
    # 核心修正：在这里创建一次包含所有默认值的选项字典
    # 我们告诉它我们不希望看到冗长的输出
    ppopt = ppoption(VERBOSE=0, OUT_ALL=0)

    for step in range(SIMULATION_STEPS):
        ppc = case5_feeder_data()
        
        traci.simulationStep()

        vehicle_ids = traci.vehicle.getIDList()
        active_evs = len(vehicle_ids)
        
        for veh_id in vehicle_ids:
            position = traci.vehicle.getLanePosition(veh_id)
            node_id = map_pos_to_node(position)
            
            if node_id is not None:
                bus_index = node_id - 1
                ev_load_mw = EV_CHARGING_POWER_KW / 1000.0
                
                ppc['bus'][bus_index][2] += ev_load_mw 
                ppc['bus'][bus_index][3] += ev_load_mw * np.tan(np.arccos(0.95))

        # 核心修正：将我们创建好的、完整的ppopt字典传入
        results, success = runpf(ppc, ppopt)
        
        if success:
            voltage_node5 = results['bus'][4][7]
            voltage_history.append(voltage_node5)
            print(f"时间步 {step}: {active_evs} 辆车在路上。节点5电压: {voltage_node5:.4f} p.u.")
        else:
            print(f"时间步 {step}: 潮流计算失败！")

    traci.close()
    print("\n--- 仿真结束 ---")

    # 绘制电压变化曲线图
    try:
        import matplotlib.pyplot as plt
        plt.figure()
        plt.plot(voltage_history)
        plt.title("Voltage at Node 5 over Time (PyPower)")
        plt.xlabel("Simulation Step")
        plt.ylabel("Voltage (p.u.)")
        plt.grid(True)
        plt.ylim(0.98, 1.01)
        plt.show()
    except ImportError:
        print("\n未安装matplotlib，无法绘制电压曲线图。请运行 'pip install matplotlib'。")

if __name__ == "__main__":
    run_simulation()