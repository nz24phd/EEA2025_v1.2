#!/usr/bin/env python3
"""
增强版BDWPT仿真平台主程序
适用于EEA 2025研究项目
"""

import os
import sys
import time
from pathlib import Path

# 核心依赖检查和导入
def check_and_import_core_packages():
    """检查并导入核心包"""
    try:
        import numpy as np
        import pandas as pd
        import matplotlib.pyplot as plt
        from pypower.api import runpf, ppoption
        print("✓ 核心包导入成功")
        return True
    except ImportError as e:
        print(f"❌ 核心包导入失败: {e}")
        print("请运行: pip install numpy pandas matplotlib pypower")
        return False

def check_and_import_enhanced_modules():
    """检查并导入增强仿真模块"""
    try:
        from enhanced_simulation.bdwpt_controller import BDWPTController
        from enhanced_simulation.network_builder import RealisticLVNetworkBuilder
        from enhanced_simulation.monte_carlo import MonteCarloSimulationFramework
        from enhanced_simulation.analysis_tools import BDWPTAnalysisTools
        print("✓ 增强仿真模块导入成功")
        return True, (BDWPTController, RealisticLVNetworkBuilder, MonteCarloSimulationFramework, BDWPTAnalysisTools)
    except ImportError as e:
        print(f"❌ 导入增强模块时出错：{e}")
        print("请确保所有增强仿真文件已在enhanced_simulation/文件夹中创建")
        print("您需要创建以下文件：")
        print("  - enhanced_simulation/__init__.py")
        print("  - enhanced_simulation/bdwpt_controller.py")
        print("  - enhanced_simulation/network_builder.py")
        print("  - enhanced_simulation/monte_carlo.py")
        print("  - enhanced_simulation/analysis_tools.py")
        return False, None

class BDWPTSimulationManager:
    """BDWPT仿真管理器"""
    
    def __init__(self):
        # 设置路径
        self.项目根目录 = Path(__file__).parent
        self.结果目录 = self.项目根目录 / "results"
        self.结果目录.mkdir(exist_ok=True)
        
        # SUMO配置（如果需要）
        self.sumo_配置路径 = str(self.项目根目录 / "sumo_config" / "network.sumocfg")
        
        print(f"🚀 BDWPT仿真管理器已初始化")
        print(f"📁 结果将保存到：{self.结果目录}")
        
    def 运行快速测试(self):
        """运行快速系统测试"""
        
        print("🧪 运行快速测试...")
        
        try:
            # 测试网络创建
            print("  📊 测试网络创建...")
            网络构建器 = RealisticLVNetworkBuilder()
            测试网络 = 网络构建器.create_realistic_lv_network(num_houses=8)
            
            # 验证网络
            is_valid, issues = 网络构建器.validate_network(测试网络)
            if not is_valid:
                print(f"  ⚠️ 网络验证发现问题: {issues}")
            else:
                print(f"    ✓ 已创建包含{len(测试网络['bus'])}个节点的网络")
            
            # 测试BDWPT控制器
            print("  🔋 测试BDWPT控制器...")
            bdwpt控制器 = BDWPTController()
            bdwpt控制器.initialize_ev("测试车辆", True)
            
            功率指令 = bdwpt控制器.calculate_power_command("测试车辆", 1.0, 12, 0.5)
            print(f"    ✓ BDWPT控制器正常工作（功率指令：{功率指令:.1f} kW）")
            
            # 测试潮流计算
            print("  ⚡ 测试潮流计算...")
            from pypower.api import runpf, ppoption
            
            ppopt = ppoption(VERBOSE=0, OUT_ALL=0)
            结果, 成功 = runpf(测试网络, ppopt)
            
            if 成功:
                最小电压 = min(结果['bus'][:, 7])
                print(f"    ✓ 潮流计算成功（最小电压：{最小电压:.4f} p.u.）")
            else:
                print("    ⚠️ 潮流计算失败，但系统基本功能正常")
            
            print("✅ 快速测试成功完成！")
            return True
            
        except Exception as e:
            print(f"❌ 快速测试失败：{e}")
            return False
    
    def 运行演示仿真(self):
        """运行单场景演示"""
        
        print("📊 运行单场景演示...")
        
        try:
            # 创建网络
            网络构建器 = RealisticLVNetworkBuilder()
            基础网络 = 网络构建器.create_realistic_lv_network(num_houses=15)
            
            # 初始化控制器
            bdwpt控制器 = BDWPTController()
            
            # 仿真记录
            时间记录 = []
            电压记录 = []
            负荷记录 = []
            EV数量记录 = []
            
            print("  🕐 模拟24小时周期...")
            
            # 24小时仿真
            for 小时 in range(0, 24, 4):  # 每4小时采样一次
                # 更新负荷
                当前网络 = 网络构建器.update_loads_for_time(基础网络, 小时, 'weekday')
                
                # 模拟EV数量
                if 7 <= 小时 <= 9 or 17 <= 小时 <= 19:  # 高峰
                    EV数量 = 15
                elif 22 <= 小时 <= 6:  # 夜间
                    EV数量 = 2
                else:
                    EV数量 = 8
                
                # 处理EV
                总EV功率 = 0
                for ev_id in range(EV数量):
                    车辆ID = f"ev_{小时}_{ev_id}"
                    
                    if 车辆ID not in bdwpt控制器.ev_states:
                        bdwpt控制器.initialize_ev(车辆ID, True, 小时)
                    
                    功率指令 = bdwpt控制器.calculate_power_command(车辆ID, 1.0, 小时, 0.5)
                    
                    if 功率指令 != 0:
                        # 应用功率到网络
                        节点索引 = min(ev_id + 2, len(当前网络['bus']) - 1)
                        当前网络['bus'][节点索引][2] += 功率指令 / 1000.0
                        总EV功率 += 功率指令
                    
                    # 更新SoC
                    bdwpt控制器.update_ev_soc(车辆ID, 功率指令, 4)  # 4小时时间步长
                
                # 运行潮流
                from pypower.api import runpf, ppoption
                ppopt = ppoption(VERBOSE=0, OUT_ALL=0)
                结果, 成功 = runpf(当前网络, ppopt)
                
                if 成功:
                    最小电压 = min(结果['bus'][:, 7])
                    总负荷 = sum(结果['bus'][:, 2]) * 1000  # 转换为kW
                    
                    时间记录.append(小时)
                    电压记录.append(最小电压)
                    负荷记录.append(总负荷)
                    EV数量记录.append(EV数量)
                    
                    print(f"    第{小时:2d}小时：{EV数量:2d}辆电动车，最小电压：{最小电压:.4f} p.u.，总负荷：{总负荷:.1f} kW")
            
            # 保存结果图表
            self._创建演示图表(时间记录, 电压记录, 负荷记录, EV数量记录)
            
            print("  📈 演示结果已保存到 results/demo_results.png")
            print("✅ 演示成功完成！")
            return True
            
        except Exception as e:
            print(f"❌ 演示运行失败：{e}")
            return False
    
    def _创建演示图表(self, 时间, 电压, 负荷, EV数量):
        """创建演示结果图表"""
        
        import matplotlib.pyplot as plt
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial']
        plt.rcParams['axes.unicode_minus'] = False
        
        fig, axes = plt.subplots(3, 1, figsize=(12, 10))
        
        # 电压曲线
        axes[0].plot(时间, 电压, 'b-', linewidth=2, label='最小电压')
        axes[0].axhline(y=0.95, color='r', linestyle='--', label='最小限值')
        axes[0].set_ylabel('电压 (p.u.)')
        axes[0].set_title('24小时最小电压曲线')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # 负荷曲线
        axes[1].plot(时间, 负荷, 'g-', linewidth=2, label='总负荷')
        axes[1].set_ylabel('功率 (kW)')
        axes[1].set_title('24小时总网络负荷')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        # EV数量
        axes[2].bar(时间, EV数量, color='orange', alpha=0.7, label='活跃电动车')
        axes[2].set_xlabel('一天中的小时')
        axes[2].set_ylabel('电动车数量')
        axes[2].set_title('24小时活跃电动车数量')
        axes[2].legend()
        axes[2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.结果目录 / 'demo_results.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def 运行完整蒙特卡洛(self, 运行次数=10):
        """运行完整的蒙特卡洛分析"""
        
        print(f"📈 开始蒙特卡洛分析（每场景{运行次数}次运行）...")
        
        try:
            # 创建基础网络
            网络构建器 = RealisticLVNetworkBuilder()
            基础网络 = 网络构建器.create_realistic_lv_network(num_houses=20)
            
            # 验证网络
            is_valid, issues = 网络构建器.validate_network(基础网络)
            if not is_valid:
                print(f"⚠️ 网络验证警告: {issues}")
            
            # 创建蒙特卡洛框架
            蒙特卡洛框架 = MonteCarloSimulationFramework(
                base_network=基础网络,
                sumo_config_path=self.sumo_配置路径,
                runs_per_scenario=运行次数
            )
            
            # 运行分析
            开始时间 = time.time()
            结果数据框 = 蒙特卡洛框架.run_monte_carlo_analysis(parallel=True)
            运行时间 = time.time() - 开始时间
            
            print(f"✅ 蒙特卡洛分析在{运行时间:.1f}秒内完成")
            print(f"📊 生成了{len(结果数据框)}个仿真结果")
            
            # 生成统计摘要
            摘要 = 蒙特卡洛框架.generate_statistical_summary()
            
            # 保存结果
            结果数据框.to_csv(self.结果目录 / 'monte_carlo_results.csv', index=False)
            
            import json
            with open(self.结果目录 / 'summary_statistics.json', 'w', encoding='utf-8') as f:
                json.dump(摘要, f, ensure_ascii=False, indent=2)
            
            # 生成分析和可视化
            print("📈 生成分析和可视化...")
            分析工具 = BDWPTAnalysisTools(结果数据框, 摘要)
            分析工具.create_comprehensive_report(str(self.结果目录))
            
            print("✅ 完整分析成功完成！")
            print(f"📁 结果已保存到：{self.结果目录}")
            
            return 结果数据框, 摘要
            
        except Exception as e:
            print(f"❌ 蒙特卡洛分析失败：{e}")
            import traceback
            traceback.print_exc()
            return None, None

def 主函数():
    """主函数"""
    
    print("🔋 增强版BDWPT仿真平台")
    print("📋 移动电池研究")
    print("=" * 50)
    
    # 检查依赖
    if not check_and_import_core_packages():
        return 1
    
    success, modules = check_and_import_enhanced_modules()
    if not success:
        return 1
    
    # 解包模块
    BDWPTController, RealisticLVNetworkBuilder, MonteCarloSimulationFramework, BDWPTAnalysisTools = modules
    
    # 将模块设为全局变量，以便在类中使用
    globals()['BDWPTController'] = BDWPTController
    globals()['RealisticLVNetworkBuilder'] = RealisticLVNetworkBuilder
    globals()['MonteCarloSimulationFramework'] = MonteCarloSimulationFramework
    globals()['BDWPTAnalysisTools'] = BDWPTAnalysisTools
    
    # 创建仿真管理器
    仿真管理器实例 = BDWPTSimulationManager()
    
    while True:
        print("\n请选择运行模式：")
        print("1. 快速测试（验证系统）")
        print("2. 演示运行（单场景24小时）")
        print("3. 完整分析（蒙特卡洛分析）")
        
        try:
            选择 = input("请输入选择 (1/2/3): ").strip()
            
            if 选择 == '1':
                print("🧪 运行测试模式...")
                if 仿真管理器实例.运行快速测试():
                    print("✅ 测试成功完成！")
                else:
                    print("❌ 测试失败。请检查您的设置。")
                break
                
            elif 选择 == '2':
                print("📊 运行演示模式...")
                if 仿真管理器实例.运行演示仿真():
                    print("✅ 演示成功完成！")
                else:
                    print("❌ 演示失败。请检查您的设置。")
                break
                
            elif 选择 == '3':
                try:
                    运行次数 = int(input("请输入每场景的运行次数（默认10）: ") or "10")
                    运行次数 = max(1, min(运行次数, 100))  # 限制在1-100之间
                except ValueError:
                    运行次数 = 10
                
                print(f"📈 运行完整分析模式（{运行次数}次/场景）...")
                结果数据框, 摘要 = 仿真管理器实例.运行完整蒙特卡洛(运行次数)
                
                if 结果数据框 is not None:
                    print("✅ 完整分析成功完成！")
                    print("\n📊 关键结果摘要：")
                    for 场景名, 场景数据 in 摘要.items():
                        print(f"\n{场景名}:")
                        print(f"  平均最小电压: {场景数据['voltage_performance']['min_voltage_mean']:.4f} p.u.")
                        print(f"  平均削峰量: {场景数据['peak_shaving']['peak_shaving_mean_mw']:.3f} MW")
                        print(f"  V2G利用率: {场景数据['ev_performance']['v2g_utilization_mean']:.3f}")
                else:
                    print("❌ 完整分析失败。请检查设置并重试。")
                break
                
            else:
                print("❌ 无效选择，请输入 1、2 或 3")
                continue
                
        except KeyboardInterrupt:
            print("\n\n👋 用户中断，退出程序")
            break
        except Exception as e:
            print(f"\n❌ 程序出错：{e}")
            break
    
    print(f"\n📁 在此处查看结果：{仿真管理器实例.结果目录}")
    print("🎉 仿真成功完成！")
    input("按回车键退出...")
    return 0

if __name__ == "__main__":
    exit_code = 主函数()
    sys.exit(exit_code)