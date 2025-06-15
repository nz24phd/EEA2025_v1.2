import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import os

class BDWPTAnalysisTools:
    """BDWPT研究的简化分析和可视化工具"""
    
    def __init__(self, results_df: pd.DataFrame, summary_stats: Dict):
        self.results_df = results_df
        self.summary_stats = summary_stats
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'Arial']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 设置绘图风格
        try:
            plt.style.use('seaborn-v0_8')
        except:
            plt.style.use('default')
        
        # 场景颜色
        self.colors = {
            'Baseline': '#FF6B6B',
            'Low_BDWPT': '#4ECDC4', 
            'High_BDWPT': '#45B7D1',
            'High_Traffic_PV': '#96CEB4',
            'Weekend': '#FFEAA7'
        }
    
    def create_comprehensive_report(self, output_dir: str):
        """生成综合分析报告"""
        
        print("生成BDWPT分析报告...")
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. 电压性能分析
        try:
            self.plot_voltage_performance_comparison(output_dir)
            print("✓ 电压性能分析完成")
        except Exception as e:
            print(f"⚠️ 电压性能分析失败: {e}")
        
        # 2. 削峰效果分析
        try:
            self.plot_peak_shaving_effectiveness(output_dir)
            print("✓ 削峰效果分析完成")
        except Exception as e:
            print(f"⚠️ 削峰效果分析失败: {e}")
        
        # 3. 经济效益分析
        try:
            self.plot_economic_benefits(output_dir)
            print("✓ 经济效益分析完成")
        except Exception as e:
            print(f"⚠️ 经济效益分析失败: {e}")
        
        # 4. EV性能分析
        try:
            self.plot_ev_performance_metrics(output_dir)
            print("✓ EV性能分析完成")
        except Exception as e:
            print(f"⚠️ EV性能分析失败: {e}")
        
        # 5. 综合对比分析
        try:
            self.create_summary_comparison(output_dir)
            print("✓ 综合对比分析完成")
        except Exception as e:
            print(f"⚠️ 综合对比分析失败: {e}")
        
        # 6. 生成数据表格
        try:
            self.create_summary_tables(output_dir)
            print("✓ 数据表格生成完成")
        except Exception as e:
            print(f"⚠️ 数据表格生成失败: {e}")
        
        print(f"📊 完整分析报告已保存至: {output_dir}")
    
    def plot_voltage_performance_comparison(self, output_dir: str):
        """电压性能对比分析"""
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('电压性能对比分析', fontsize=16, fontweight='bold')
        
        # 1. 最小电压分布
        ax1 = axes[0, 0]
        for scenario in self.results_df['scenario_name'].unique():
            data = self.results_df[self.results_df['scenario_name'] == scenario]['min_voltage_pu']
            if len(data) > 0:
                ax1.hist(data, alpha=0.7, label=scenario, bins=10, 
                        color=self.colors.get(scenario, 'gray'))
        
        ax1.axvline(x=0.95, color='red', linestyle='--', label='最低限值 (0.95 p.u.)')
        ax1.set_xlabel('最小电压 (p.u.)')
        ax1.set_ylabel('频次')
        ax1.set_title('最小电压分布')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 电压违规次数
        ax2 = axes[0, 1]
        violation_means = self.results_df.groupby('scenario_name')['voltage_violations'].mean()
        violation_stds = self.results_df.groupby('scenario_name')['voltage_violations'].std()
        
        bars = ax2.bar(violation_means.index, violation_means.values, 
                      yerr=violation_stds.values, capsize=5,
                      color=[self.colors.get(s, 'gray') for s in violation_means.index])
        
        ax2.set_ylabel('平均电压违规次数')
        ax2.set_title('各场景电压违规情况')
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(True, alpha=0.3)
        
        # 添加数值标签
        for bar, mean_val in zip(bars, violation_means.values):
            if not np.isnan(mean_val):
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                        f'{mean_val:.1f}', ha='center', va='bottom')
        
        # 3. 电压改善对比
        ax3 = axes[1, 0]
        try:
            baseline_violations = self.results_df[self.results_df['scenario_name'] == 'Baseline']['voltage_violations'].mean()
            
            improvements = []
            scenario_names = []
            for scenario in self.results_df['scenario_name'].unique():
                if scenario != 'Baseline':
                    scenario_violations = self.results_df[self.results_df['scenario_name'] == scenario]['voltage_violations'].mean()
                    if not np.isnan(baseline_violations) and not np.isnan(scenario_violations):
                        improvement = ((baseline_violations - scenario_violations) / max(baseline_violations, 0.1)) * 100
                        improvements.append(improvement)
                        scenario_names.append(scenario)
            
            if improvements:
                bars = ax3.bar(scenario_names, improvements, 
                              color=[self.colors.get(s, 'gray') for s in scenario_names])
                ax3.set_ylabel('电压违规减少 (%)')
                ax3.set_title('相对基准场景的电压改善')
                ax3.tick_params(axis='x', rotation=45)
                ax3.grid(True, alpha=0.3)
                
                # 添加数值标签
                for bar, improvement in zip(bars, improvements):
                    ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                            f'{improvement:.1f}%', ha='center', va='bottom')
        except Exception as e:
            ax3.text(0.5, 0.5, f'电压改善分析失败:\n{str(e)}', ha='center', va='center', transform=ax3.transAxes)
        
        # 4. 电压偏差箱线图
        ax4 = axes[1, 1]
        voltage_dev_data = []
        labels = []
        
        for scenario in self.results_df['scenario_name'].unique():
            data = self.results_df[self.results_df['scenario_name'] == scenario]['avg_voltage_deviation']
            data_clean = data.dropna()
            if len(data_clean) > 0:
                voltage_dev_data.append(data_clean)
                labels.append(scenario)
        
        if voltage_dev_data:
            box_plot = ax4.boxplot(voltage_dev_data, labels=labels, patch_artist=True)
            
            # 为箱子着色
            for patch, scenario in zip(box_plot['boxes'], labels):
                patch.set_facecolor(self.colors.get(scenario, 'gray'))
                patch.set_alpha(0.7)
            
            ax4.set_ylabel('平均电压偏差 (p.u.)')
            ax4.set_title('电压偏差分布')
            ax4.tick_params(axis='x', rotation=45)
            ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/voltage_performance_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_peak_shaving_effectiveness(self, output_dir: str):
        """削峰效果分析"""
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('削峰效果分析', fontsize=16, fontweight='bold')
        
        # 1. 平均削峰量
        ax1 = axes[0, 0]
        peak_reduction_means = self.results_df.groupby('scenario_name')['peak_shaving_achieved_mw'].mean()
        peak_reduction_stds = self.results_df.groupby('scenario_name')['peak_shaving_achieved_mw'].std()
        
        bars = ax1.bar(peak_reduction_means.index, peak_reduction_means.values * 1000,  # 转换为kW
                      yerr=peak_reduction_stds.values * 1000, capsize=5,
                      color=[self.colors.get(s, 'gray') for s in peak_reduction_means.index])
        
        ax1.set_ylabel('削峰量 (kW)')
        ax1.set_title('各场景平均削峰效果')
        ax1.tick_params(axis='x', rotation=45)
        ax1.grid(True, alpha=0.3)
        
        # 添加数值标签
        for bar, mean_val in zip(bars, peak_reduction_means.values):
            if not np.isnan(mean_val):
                ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                        f'{mean_val*1000:.1f}', ha='center', va='bottom')
        
        # 2. 削峰百分比分布
        ax2 = axes[0, 1]
        
        # 计算削峰百分比
        self.results_df['peak_reduction_percent'] = np.where(
            self.results_df['peak_demand_mw'] > 0,
            (self.results_df['peak_shaving_achieved_mw'] / self.results_df['peak_demand_mw']) * 100,
            0
        )
        
        for scenario in self.results_df['scenario_name'].unique():
            data = self.results_df[self.results_df['scenario_name'] == scenario]['peak_reduction_percent']
            data_clean = data.dropna()
            if len(data_clean) > 0:
                ax2.hist(data_clean, alpha=0.7, label=scenario, bins=10,
                        color=self.colors.get(scenario, 'gray'))
        
        ax2.set_xlabel('削峰百分比 (%)')
        ax2.set_ylabel('频次')
        ax2.set_title('削峰百分比分布')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. 峰值需求对比
        ax3 = axes[1, 0]
        peak_demand_means = self.results_df.groupby('scenario_name')['peak_demand_mw'].mean()
        
        bars = ax3.bar(peak_demand_means.index, peak_demand_means.values * 1000,
                      color=[self.colors.get(s, 'gray') for s in peak_demand_means.index])
        
        ax3.set_ylabel('峰值需求 (kW)')
        ax3.set_title('各场景峰值需求对比')
        ax3.tick_params(axis='x', rotation=45)
        ax3.grid(True, alpha=0.3)
        
        # 4. BDWPT渗透率 vs 削峰效果
        ax4 = axes[1, 1]
        
        # 过滤有BDWPT的场景
        bdwpt_scenarios = self.results_df[self.results_df['bdwpt_penetration'] > 0]
        
        if len(bdwpt_scenarios) > 0:
            scatter = ax4.scatter(bdwpt_scenarios['bdwpt_penetration'] * 100,
                                 bdwpt_scenarios['peak_shaving_achieved_mw'] * 1000,
                                 c=[self.colors.get(s, 'gray') for s in bdwpt_scenarios['scenario_name']],
                                 alpha=0.6, s=50)
            
            ax4.set_xlabel('BDWPT渗透率 (%)')
            ax4.set_ylabel('削峰量 (kW)')
            ax4.set_title('BDWPT渗透率与削峰效果关系')
            ax4.grid(True, alpha=0.3)
        else:
            ax4.text(0.5, 0.5, '没有BDWPT场景数据', ha='center', va='center', transform=ax4.transAxes)
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/peak_shaving_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_economic_benefits(self, output_dir: str):
        """经济效益分析"""
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('经济效益分析', fontsize=16, fontweight='bold')
        
        # 1. 电网成本节约
        ax1 = axes[0, 0]
        grid_savings_means = self.results_df.groupby('scenario_name')['grid_cost_savings'].mean()
        
        bars = ax1.bar(grid_savings_means.index, grid_savings_means.values,
                      color=[self.colors.get(s, 'gray') for s in grid_savings_means.index])
        
        ax1.set_ylabel('电网成本节约 ($)')
        ax1.set_title('各场景电网成本节约')
        ax1.tick_params(axis='x', rotation=45)
        ax1.grid(True, alpha=0.3)
        
        # 2. EV车主收益
        ax2 = axes[0, 1]
        ev_revenue_means = self.results_df.groupby('scenario_name')['ev_owner_revenue'].mean()
        
        bars = ax2.bar(ev_revenue_means.index, ev_revenue_means.values,
                      color=[self.colors.get(s, 'gray') for s in ev_revenue_means.index])
        
        ax2.set_ylabel('EV车主收益 ($)')
        ax2.set_title('各场景EV车主收益')
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(True, alpha=0.3)
        
        # 3. 总经济效益
        ax3 = axes[1, 0]
        self.results_df['total_benefits'] = (self.results_df['grid_cost_savings'] + 
                                           self.results_df['ev_owner_revenue'])
        
        benefit_means = self.results_df.groupby('scenario_name')['total_benefits'].mean()
        
        bars = ax3.bar(benefit_means.index, benefit_means.values,
                      color=[self.colors.get(s, 'gray') for s in benefit_means.index])
        
        ax3.set_ylabel('总经济效益 ($)')
        ax3.set_title('各场景总经济效益')
        ax3.tick_params(axis='x', rotation=45)
        ax3.grid(True, alpha=0.3)
        
        # 4. 效益组成饼图（选择一个高BDWPT场景）
        ax4 = axes[1, 1]
        
        try:
            high_bdwpt_data = self.results_df[self.results_df['scenario_name'] == 'High_BDWPT']
            if len(high_bdwpt_data) > 0:
                grid_savings = high_bdwpt_data['grid_cost_savings'].mean()
                ev_revenue = high_bdwpt_data['ev_owner_revenue'].mean()
                
                if not np.isnan(grid_savings) and not np.isnan(ev_revenue):
                    labels = ['电网成本节约', 'EV车主收益']
                    sizes = [grid_savings, ev_revenue]
                    colors = ['#FF9999', '#66B2FF']
                    
                    ax4.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
                    ax4.set_title('高BDWPT场景效益组成')
                else:
                    ax4.text(0.5, 0.5, '数据不足', ha='center', va='center', transform=ax4.transAxes)
            else:
                ax4.text(0.5, 0.5, '无高BDWPT场景数据', ha='center', va='center', transform=ax4.transAxes)
        except Exception as e:
            ax4.text(0.5, 0.5, f'效益分析失败:\n{str(e)}', ha='center', va='center', transform=ax4.transAxes)
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/economic_benefits_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_ev_performance_metrics(self, output_dir: str):
        """EV性能指标分析"""
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('电动车性能分析', fontsize=16, fontweight='bold')
        
        # 1. 最终SoC分布
        ax1 = axes[0, 0]
        for scenario in self.results_df['scenario_name'].unique():
            if scenario != 'Baseline':  # 基准场景没有EV
                data = self.results_df[self.results_df['scenario_name'] == scenario]['avg_ev_soc_end']
                data_clean = data.dropna()
                if len(data_clean) > 0:
                    ax1.hist(data_clean, alpha=0.7, label=scenario, bins=10,
                            color=self.colors.get(scenario, 'gray'))
        
        ax1.axvline(x=0.8, color='green', linestyle='--', alpha=0.8, label='目标SoC (80%)')
        ax1.axvline(x=0.2, color='red', linestyle='--', alpha=0.8, label='最低SoC (20%)')
        ax1.set_xlabel('最终电量状态')
        ax1.set_ylabel('频次')
        ax1.set_title('EV最终电量状态分布')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. V2G利用率
        ax2 = axes[0, 1]
        v2g_means = self.results_df[self.results_df['scenario_name'] != 'Baseline'].groupby('scenario_name')['v2g_utilization'].mean()
        
        if len(v2g_means) > 0:
            bars = ax2.bar(v2g_means.index, v2g_means.values * 100,  # 转换为百分比
                          color=[self.colors.get(s, 'gray') for s in v2g_means.index])
            
            ax2.set_ylabel('V2G利用率 (%)')
            ax2.set_title('各场景V2G利用率')
            ax2.tick_params(axis='x', rotation=45)
            ax2.grid(True, alpha=0.3)
            
            # 添加数值标签
            for bar, mean_val in zip(bars, v2g_means.values):
                if not np.isnan(mean_val):
                    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                            f'{mean_val*100:.1f}%', ha='center', va='bottom')
        
        # 3. 能量交易量
        ax3 = axes[1, 0]
        energy_means = self.results_df[self.results_df['scenario_name'] != 'Baseline'].groupby('scenario_name')['total_energy_traded_mwh'].mean()
        
        if len(energy_means) > 0:
            bars = ax3.bar(energy_means.index, energy_means.values * 1000,  # 转换为kWh
                          color=[self.colors.get(s, 'gray') for s in energy_means.index])
            
            ax3.set_ylabel('平均能量交易 (kWh)')
            ax3.set_title('各场景能量交易量')
            ax3.tick_params(axis='x', rotation=45)
            ax3.grid(True, alpha=0.3)
        
        # 4. BDWPT渗透率 vs 效益相关性
        ax4 = axes[1, 1]
        bdwpt_data = self.results_df[self.results_df['bdwpt_penetration'] > 0]
        
        if len(bdwpt_data) > 0:
            scatter = ax4.scatter(bdwpt_data['bdwpt_penetration'] * 100,
                                 bdwpt_data['total_benefits'],
                                 c=[self.colors.get(s, 'gray') for s in bdwpt_data['scenario_name']],
                                 alpha=0.6, s=50)
            
            ax4.set_xlabel('BDWPT渗透率 (%)')
            ax4.set_ylabel('总经济效益 ($)')
            ax4.set_title('BDWPT渗透率与效益关系')
            ax4.grid(True, alpha=0.3)
        else:
            ax4.text(0.5, 0.5, '没有BDWPT数据', ha='center', va='center', transform=ax4.transAxes)
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/ev_performance_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def create_summary_comparison(self, output_dir: str):
        """创建综合对比图"""
        
        fig, axes = plt.subplots(2, 3, figsize=(16, 10))
        fig.suptitle('BDWPT技术综合效果对比', fontsize=16, fontweight='bold')
        
        # 关键指标对比
        metrics = [
            ('min_voltage_pu', '最小电压 (p.u.)', axes[0, 0]),
            ('voltage_violations', '电压违规次数', axes[0, 1]),
            ('peak_shaving_achieved_mw', '削峰量 (MW)', axes[0, 2]),
            ('v2g_utilization', 'V2G利用率', axes[1, 0]),
            ('total_benefits', '总经济效益 ($)', axes[1, 1]),
            ('avg_ev_soc_end', '平均最终SoC', axes[1, 2])
        ]
        
        for metric, title, ax in metrics:
            try:
                scenario_means = self.results_df.groupby('scenario_name')[metric].mean()
                scenario_stds = self.results_df.groupby('scenario_name')[metric].std()
                
                bars = ax.bar(scenario_means.index, scenario_means.values,
                             yerr=scenario_stds.values, capsize=3,
                             color=[self.colors.get(s, 'gray') for s in scenario_means.index])
                
                ax.set_ylabel(title)
                ax.tick_params(axis='x', rotation=45)
                ax.grid(True, alpha=0.3)
                
                # 添加数值标签
                for bar, mean_val in zip(bars, scenario_means.values):
                    if not np.isnan(mean_val):
                        if metric == 'peak_shaving_achieved_mw':
                            label = f'{mean_val*1000:.1f}'
                        elif metric in ['v2g_utilization', 'avg_ev_soc_end']:
                            label = f'{mean_val:.2f}'
                        else:
                            label = f'{mean_val:.1f}'
                        
                        ax.text(bar.get_x() + bar.get_width()/2, 
                               bar.get_height() + (scenario_stds.iloc[bars.index(bar)] if not np.isnan(scenario_stds.iloc[bars.index(bar)]) else 0) + 0.01,
                               label, ha='center', va='bottom', fontsize=8)
            except Exception as e:
                ax.text(0.5, 0.5, f'数据不足:\n{str(e)}', ha='center', va='center', transform=ax.transAxes)
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/comprehensive_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def create_summary_tables(self, output_dir: str):
        """创建汇总表格"""
        
        # 创建场景对比表
        summary_data = []
        for scenario in self.results_df['scenario_name'].unique():
            scenario_data = self.results_df[self.results_df['scenario_name'] == scenario]
            
            summary_data.append({
                '场景': scenario,
                'BDWPT渗透率 (%)': f"{scenario_data['bdwpt_penetration'].iloc[0]*100:.0f}",
                '最小电压 (p.u.)': f"{scenario_data['min_voltage_pu'].mean():.4f} ± {scenario_data['min_voltage_pu'].std():.4f}",
                '电压违规次数': f"{scenario_data['voltage_violations'].mean():.1f} ± {scenario_data['voltage_violations'].std():.1f}",
                '削峰量 (kW)': f"{scenario_data['peak_shaving_achieved_mw'].mean()*1000:.1f} ± {scenario_data['peak_shaving_achieved_mw'].std()*1000:.1f}",
                '总经济效益 ($)': f"{scenario_data['total_benefits'].mean():.2f} ± {scenario_data['total_benefits'].std():.2f}",
                'V2G利用率': f"{scenario_data['v2g_utilization'].mean():.3f} ± {scenario_data['v2g_utilization'].std():.3f}",
                '平均最终SoC': f"{scenario_data['avg_ev_soc_end'].mean():.3f} ± {scenario_data['avg_ev_soc_end'].std():.3f}"
            })
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_csv(f"{output_dir}/scenario_comparison_table.csv", index=False, encoding='utf-8-sig')
        
        # 保存原始数据
        self.results_df.to_csv(f"{output_dir}/raw_simulation_results.csv", index=False, encoding='utf-8-sig')
        
        print(f"✓ 数据表格已保存至 {output_dir}")
        
        return summary_df