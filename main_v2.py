#!/usr/bin/env python3
"""
EEA2025 v1.2 主程序
集成SUMO交通仿真的BDWPT分析
"""

import os
import sys
import time
from pathlib import Path

# 导入增强模块
from enhanced_simulation.bdwpt_controller import BDWPTController
from enhanced_simulation.network_builder import RealisticLVNetworkBuilder
from enhanced_simulation.monte_carlo_v2 import EnhancedMonteCarloFramework
from enhanced_simulation.analysis_tools import BDWPTAnalysisTools
from enhanced_simulation.sumo_integration import create_enhanced_sumo_network
from enhanced_simulation.gis_network_mapping import GISNetworkMapping

def main():
    print("🔋 BDWPT仿真平台 v1.2")
    print("📋 集成SUMO交通仿真")
    print("=" * 50)
    
    # 创建结果目录
    os.makedirs("results", exist_ok=True)
    os.makedirs("sumo_files_v2", exist_ok=True)
    
    # 步骤1: 创建SUMO网络（如果不存在）
    if not os.path.exists("sumo_files_v2/enhanced_road.net.xml"):
        print("\n1️⃣ 创建SUMO道路网络...")
        create_enhanced_sumo_network()
    else:
        print("\n1️⃣ SUMO网络已存在")
    
    # 步骤2: 创建配电网
    print("\n2️⃣ 创建配电网络...")
    network_builder = RealisticLVNetworkBuilder()
    base_network = network_builder.create_realistic_lv_network(num_houses=25)
    
    # 验证网络
    is_valid, issues = network_builder.validate_network(base_network)
    if not is_valid:
        print(f"⚠️ 网络验证警告: {issues}")
    else:
        print("✓ 配电网络创建成功")
    
    # 步骤3: 创建GIS映射
    print("\n3️⃣ 创建GIS道路映射...")
    gis_mapper = GISNetworkMapping()
    gis_mapper.export_mapping_config("results/gis_mapping.json")
    
    # 步骤4: 选择运行模式
    print("\n请选择运行模式:")
    print("1. 快速演示（不使用SUMO）")
    print("2. 完整仿真（使用SUMO，较慢）")
    print("3. 批量分析（Monte Carlo）")
    
    choice = input("\n请输入选择 (1/2/3): ").strip()
    
    if choice == '1':
        run_quick_demo(base_network)
    elif choice == '2':
        run_full_simulation(base_network)
    elif choice == '3':
        run_monte_carlo(base_network)
    else:
        print("无效选择")
        
def run_quick_demo(base_network):
    """快速演示模式"""
    print("\n运行快速演示...")
    
    # 使用简化的Monte Carlo（不用SUMO）
    mc_framework = EnhancedMonteCarloFramework(base_network, use_sumo=False)
    mc_framework.runs_per_scenario = 3  # 减少运行次数
    
    results_df, summary = mc_framework.run_analysis()
    
    # 生成分析报告
    analysis_tools = BDWPTAnalysisTools(results_df, summary)
    analysis_tools.create_comprehensive_report("results")
    
    print("\n✅ 演示完成！查看results文件夹")
    
def run_full_simulation(base_network):
    """完整仿真模式（使用SUMO）"""
    print("\n运行完整仿真（使用SUMO）...")
    
    # 检查SUMO
    if 'SUMO_HOME' not in os.environ:
        print("❌ 错误：SUMO_HOME环境变量未设置")
        print("请安装SUMO并设置环境变量")
        return
        
    # 运行包含SUMO的仿真
    mc_framework = EnhancedMonteCarloFramework(base_network, use_sumo=True)
    mc_framework.runs_per_scenario = 5
    
    results_df, summary = mc_framework.run_analysis()
    
    # 生成分析报告
    analysis_tools = BDWPTAnalysisTools(results_df, summary)
    analysis_tools.create_comprehensive_report("results")
    
    print("\n✅ 完整仿真完成！查看results文件夹")
    
def run_monte_carlo(base_network):
    """批量Monte Carlo分析"""
    print("\n运行Monte Carlo分析...")
    
    runs = int(input("每个场景运行次数 (建议10-50): ") or "10")
    use_sumo = input("使用SUMO? (y/n): ").lower() == 'y'
    
    mc_framework = EnhancedMonteCarloFramework(base_network, use_sumo=use_sumo)
    mc_framework.runs_per_scenario = runs
    
    start_time = time.time()
    results_df, summary = mc_framework.run_analysis()
    elapsed = time.time() - start_time
    
    print(f"\n分析用时: {elapsed:.1f} 秒")
    
    # 生成分析报告
    analysis_tools = BDWPTAnalysisTools(results_df, summary)
    analysis_tools.create_comprehensive_report("results")
    
    # 显示关键结果
    print("\n📊 关键结果:")
    for scenario, data in summary.items():
        print(f"\n{scenario}:")
        print(f"  平均最小电压: {data['voltage_performance']['min_voltage_mean']:.4f} p.u.")
        print(f"  削峰量: {data['peak_shaving']['mean_mw']:.3f} MW")
        print(f"  经济效益: ${data['economics']['grid_savings_mean']:.2f}")
    
if __name__ == "__main__":
    main()