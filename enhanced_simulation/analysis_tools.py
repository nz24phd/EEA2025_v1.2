# 文件: enhanced_simulation/analysis_tools.py (完整替换)

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

class BDWPTAnalysisTools:
    """
    增强版BDWPT分析和可视化工具
    - 修正了削峰计算逻辑
    - 解决了中文乱码问题
    """

    def __init__(self, results_csv_path='results/monte_carlo_v2_results.csv'):
        # --- 字体设置：解决中文乱码的关键 ---
        try:
            plt.rcParams['font.sans-serif'] = ['SimHei']  # 'SimHei' 是一个常用的中文字体
            plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示为方块的问题
        except Exception as e:
            print(f"注意：设置中文字体失败，可能仍然存在乱码。请确保系统已安装'SimHei'字体。错误: {e}")
        
        self.results_df = pd.read_csv(results_csv_path)
        self.summary_df = self._calculate_summary()

    def _calculate_summary(self):
        """
        后处理仿真结果，计算正确的削峰和经济效益
        """
        # 按场景分组，计算基础指标的均值
        grouped = self.results_df.groupby('scenario_name')
        summary = grouped.mean(numeric_only=True)

        # --- 核心逻辑：正确计算削峰和经济效益 ---
        if 'Baseline' in summary.index:
            baseline_peak_demand = summary.loc['Baseline']['peak_demand_mw']
            
            # 计算每个场景相对于Baseline的削峰量
            summary['peak_shaving_achieved_mw'] = baseline_peak_demand - summary['peak_demand_mw']
            
            # 重新计算电网节省成本 (假设 $350/kW-peak)
            summary['grid_cost_savings'] = summary['peak_shaving_achieved_mw'] * 1000 * 0.35
        else:
            # 如果没有Baseline，无法计算削峰
            summary['peak_shaving_achieved_mw'] = 0
            summary['grid_cost_savings'] = 0

        summary = summary.reset_index()
        # 确保场景按预期顺序排列
        scenario_order = ['Baseline', 'Low_BDWPT', 'High_BDWPT', 'High_Traffic_Rain', 'Weekend_HighPV']
        summary['scenario_name'] = pd.Categorical(summary['scenario_name'], categories=scenario_order, ordered=True)
        summary = summary.sort_values('scenario_name')
        
        return summary

    def run_all_plots(self, show=False):
        """生成所有分析图表"""
        print("\n📊 开始生成分析图表...")
        os.makedirs('results/plots', exist_ok=True)
        
        self.plot_peak_shaving(save_path='results/plots/peak_shaving_analysis.png')
        self.plot_voltage_performance(save_path='results/plots/voltage_performance_analysis.png')
        self.plot_economic_benefits(save_path='results/plots/economic_benefits_analysis.png')
        self.plot_ev_performance(save_path='results/plots/ev_performance_analysis.png')
        
        print("✓ 所有图表已生成并保存到 results/plots/ 文件夹")

        if show:
            plt.show()

    def plot_peak_shaving(self, save_path):
        plt.figure(figsize=(12, 7))
        sns.barplot(data=self.summary_df, x='scenario_name', y='peak_shaving_achieved_mw', palette='viridis')
        plt.title('各场景平均削峰效果对比', fontsize=16)
        plt.ylabel('平均削峰量 (MW)', fontsize=12)
        plt.xlabel('仿真场景', fontsize=12)
        plt.xticks(rotation=15, ha='right')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.savefig(save_path, dpi=300)
        plt.close()

    def plot_voltage_performance(self, save_path):
        plt.figure(figsize=(12, 7))
        sns.boxplot(data=self.results_df, x='scenario_name', y='min_voltage_pu', palette='plasma')
        plt.axhline(0.95, color='red', linestyle='--', label='电压下限 (0.95 p.u.)')
        plt.title('各场景最低电压分布', fontsize=16)
        plt.ylabel('最低电压 (p.u.)', fontsize=12)
        plt.xlabel('仿真场景', fontsize=12)
        plt.xticks(rotation=15, ha='right')
        plt.legend()
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.savefig(save_path, dpi=300)
        plt.close()

    def plot_economic_benefits(self, save_path):
        plot_data = self.summary_df[['scenario_name', 'grid_cost_savings', 'ev_owner_revenue']].melt(
            id_vars='scenario_name', var_name='Benefit Type', value_name='Value ($)'
        )
        
        plt.figure(figsize=(12, 7))
        sns.barplot(data=plot_data, x='scenario_name', y='Value ($)', hue='Benefit Type', palette='coolwarm')
        plt.title('各场景经济效益分析', fontsize=16)
        plt.ylabel('平均经济效益 ($)', fontsize=12)
        plt.xlabel('仿真场景', fontsize=12)
        plt.xticks(rotation=15, ha='right')
        plt.legend(title='效益类型')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.savefig(save_path, dpi=300)
        plt.close()

    def plot_ev_performance(self, save_path):
        fig, axes = plt.subplots(1, 2, figsize=(18, 7))
        
        # 平均最终SoC
        sns.boxplot(ax=axes[0], data=self.results_df, x='scenario_name', y='avg_ev_soc_end', hue='scenario_name', palette='winter', legend=False)
        axes[0].set_title('各场景EV平均最终SoC', fontsize=14)
        axes[0].set_xlabel('仿真场景', fontsize=12)
        axes[0].set_ylabel('平均最终SoC', fontsize=12)
        axes[0].tick_params(axis='x', rotation=15)
        axes[0].grid(axis='y', linestyle='--', alpha=0.7)
        
        # V2G利用率
        sns.barplot(ax=axes[1], data=self.summary_df, x='scenario_name', y='v2g_utilization', hue='scenario_name', palette='autumn', legend=False)
        axes[1].set_title('各场景V2G利用率', fontsize=14)
        axes[1].set_xlabel('仿真场景', fontsize=12)
        axes[1].set_ylabel('V2G事件比例', fontsize=12)
        axes[1].tick_params(axis='x', rotation=15)
        axes[1].grid(axis='y', linestyle='--', alpha=0.7)

        plt.suptitle('电动汽车性能指标对比', fontsize=18)
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.savefig(save_path, dpi=300)
        plt.close()

    def generate_report(self):
        """生成一个文本格式的总结报告"""
        report = "====== BDWPT仿真分析报告 ======\n\n"
        for index, row in self.summary_df.iterrows():
            report += f"--- 场景: {row['scenario_name']} ---\n"
            report += f"  - 电压表现: 平均最低电压 {row['min_voltage_pu']:.4f} p.u.\n"
            report += f"  - 削峰效果: 平均削峰 {row['peak_shaving_achieved_mw']:.4f} MW\n"
            report += f"  - 电网节省: ${row['grid_cost_savings']:,.2f}\n"
            report += f"  - EV车主收入: ${row['ev_owner_revenue']:,.2f}\n"
            report += f"  - V2G利用率: {row['v2g_utilization']:.2%}\n\n"
        
        print(report)
        with open('results/analysis_summary_report.txt', 'w', encoding='utf-8') as f:
            f.write(report)
        print("✓ 文本分析报告已保存到 results/analysis_summary_report.txt")

if __name__ == '__main__':
    # 这个部分允许你独立运行此文件来重新生成图表，而无需重新跑仿真
    tools = BDWPTAnalysisTools()
    tools.run_all_plots()
    tools.generate_report()