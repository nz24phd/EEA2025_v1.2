# 文件: main_v2.py (完整替换)

import time
import os
import sys

# 动态添加路径以便导入增强模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from enhanced_simulation.network_builder import RealisticLVNetworkBuilder
from enhanced_simulation.sumo_integration import create_enhanced_sumo_network
from enhanced_simulation.gis_network_mapping import GISNetworkMapping
from enhanced_simulation.monte_carlo_v2 import EnhancedMonteCarloFramework
from enhanced_simulation.analysis_tools import BDWPTAnalysisTools

def setup_simulation_environment():
    """准备仿真所需的文件和环境"""
    print("1️⃣ 创建SUMO道路网络...")
    if not os.path.exists('sumo_files_v2/enhanced_road.net.xml'):
        create_enhanced_sumo_network()
    else:
        print("✓ SUMO网络已存在")

    print("\n2️⃣ 创建配电网络...")
    builder = RealisticLVNetworkBuilder()
    network = builder.create_realistic_lv_network()
    is_valid, issues = builder.validate_network(network)
    if is_valid:
        print("✓ 配电网络创建成功")
    else:
        print("⚠️ 配电网络创建警告:", issues)
    
    print("\n3️⃣ 创建GIS道路映射...")
    mapper = GISNetworkMapping()
    # 定义好要保存的路径
    config_path = 'results/gis_mapping.json'
    # 将路径字符串作为参数传递给方法
    mapper.export_mapping_config(filename=config_path)
    # 在打印时也使用我们定义的路径变量
    print(f"✓ 映射配置已保存到: {config_path}")
    
    return network

def run_quick_demo(base_network):
    """运行一个不依赖SUMO的快速演示"""
    print("\n运行快速演示...")
    start_time = time.time()
    
    mc_framework = EnhancedMonteCarloFramework(base_network, use_sumo=False)
    results_df, summary = mc_framework.run_analysis()
    
    end_time = time.time()
    print(f"\n分析用时: {end_time - start_time:.1f} 秒")
    
    analysis_tools = BDWPTAnalysisTools()
    analysis_tools.run_all_plots()
    analysis_tools.generate_report()

def run_full_simulation(base_network):
    """运行一个使用SUMO的单次完整仿真"""
    print("\n运行完整仿真（使用SUMO）...")
    start_time = time.time()

    mc_framework = EnhancedMonteCarloFramework(base_network, use_sumo=True)
    mc_framework.runs_per_scenario = 1
    mc_framework.scenarios = [mc_framework.scenarios[2]]
    
    results_df, summary = mc_framework.run_analysis()

    end_time = time.time()
    print(f"\n分析用时: {end_time - start_time:.1f} 秒")
    
    if not results_df.empty:
        analysis_tools = BDWPTAnalysisTools()
        analysis_tools.run_all_plots()
        analysis_tools.generate_report()

def run_monte_carlo(base_network):
    """运行用户自定义的批量Monte Carlo分析"""
    print("\n运行Monte Carlo分析...")
    try:
        runs = int(input("每个场景运行次数 (建议10-50): "))
        use_sumo_input = input("使用SUMO? (y/n): ").lower()
        use_sumo = use_sumo_input == 'y'
    except (ValueError, IndexError):
        print("输入无效，使用默认值 (10次, 使用SUMO)")
        runs = 10
        use_sumo = True

    start_time = time.time()

    mc_framework = EnhancedMonteCarloFramework(base_network, use_sumo=use_sumo)
    mc_framework.runs_per_scenario = runs
    results_df, summary = mc_framework.run_analysis()

    end_time = time.time()
    print(f"\n分析用时: {end_time - start_time:.1f} 秒")

    analysis_tools = BDWPTAnalysisTools()
    analysis_tools.run_all_plots()
    analysis_tools.generate_report()

def main():
    """主函数入口"""
    print("="*50)
    print("🔋 BDWPT仿真平台 v1.4 - 最终稳定版")
    print("📋 集成SUMO交通仿真与高级分析")
    print("="*50)
    
    base_network = setup_simulation_environment()
    
    while True:
        print("\n请选择运行模式:")
        print("1. 快速演示（不使用SUMO）")
        print("2. 完整仿真（使用SUMO，单次运行）")
        print("3. 批量分析（Monte Carlo）")
        print("4. 仅生成图表（如果已有results.csv）")
        print("5. 退出")
        
        choice = input("请输入选择 (1/2/3/4/5): ")
        
        if choice == '1':
            run_quick_demo(base_network)
            break
        elif choice == '2':
            run_full_simulation(base_network)
            break
        elif choice == '3':
            run_monte_carlo(base_network)
            break
        elif choice == '4':
            print("\n重新生成分析图表...")
            results_path = 'results/monte_carlo_v2_results.csv'
            if os.path.exists(results_path):
                analysis_tools = BDWPTAnalysisTools(results_csv_path=results_path)
                analysis_tools.run_all_plots()
                analysis_tools.generate_report()
            else:
                print(f"错误: '{results_path}' 未找到。请先运行一次仿真。")
            break
        elif choice == '5':
            print("程序退出。")
            break
        else:
            print("无效输入，请输入1, 2, 3, 4或5。")

if __name__ == "__main__":
    main()