class AdvancedBDWPTModeling:
    """Advanced BDWPT system modeling with realistic constraints"""
    
    def __init__(self):
        # Based on recent BDWPT research and commercial systems
        self.bdwpt_characteristics = {
            'power_levels': {
                'light_duty': {'max_kw': 20, 'efficiency': 0.85},
                'medium_duty': {'max_kw': 50, 'efficiency': 0.88},
                'heavy_duty': {'max_kw': 100, 'efficiency': 0.90}
            },
            'operational_constraints': {
                'min_speed_kmh': 5,      # Minimum speed for BDWPT operation
                'max_speed_kmh': 80,     # Maximum speed for effective coupling
                'alignment_tolerance_cm': 20,  # Lateral alignment tolerance
                'air_gap_range_cm': (10, 25)   # Vertical air gap range
            },
            'infrastructure_costs': {
                'primary_coil_per_m': 2500,    # $/m of road
                'power_electronics_per_mw': 150000,  # $/MW
                'installation_factor': 1.5     # Multiplier for total installation
            }
        }
    
    def calculate_dynamic_efficiency(self, speed_kmh, alignment_error_cm, air_gap_cm):
        """Calculate BDWPT efficiency based on dynamic conditions"""
        base_efficiency = 0.88
        
        # Speed-dependent efficiency
        if speed_kmh < 20:
            speed_factor = 0.95  # Lower efficiency at very low speeds
        elif speed_kmh > 60:
            speed_factor = 0.92  # Reduced efficiency at high speeds
        else:
            speed_factor = 1.0
        
        # Alignment penalty
        alignment_factor = max(0.7, 1.0 - (alignment_error_cm / 30))
        
        # Air gap penalty
        optimal_gap = 15  # cm
        gap_factor = max(0.8, 1.0 - abs(air_gap_cm - optimal_gap) / 20)
        
        return base_efficiency * speed_factor * alignment_factor * gap_factor