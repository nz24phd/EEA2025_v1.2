class NZDistributionNetworkData:
    """New Zealand specific distribution network parameters and validation"""
    
    def __init__(self):
        # Real NZ LV network data based on Aurora Energy, Vector, etc.
        self.nz_network_standards = {
            'voltage_levels': {
                'lv_primary': 11.0,      # kV
                'lv_secondary': 0.4,     # kV (400V)
                'voltage_tolerance': 0.06 # ±6% as per NZ standards
            },
            'typical_loads': {
                'residential_avg_kw': 2.5,
                'residential_peak_kw': 8.0,
                'commercial_avg_kw': 15.0,
                'industrial_avg_kw': 50.0
            },
            'cable_standards': {
                # Based on NZ Electrical Code (NZECP)
                'underground_cu_95': {'r_ohm_km': 0.32, 'x_ohm_km': 0.08},
                'underground_cu_185': {'r_ohm_km': 0.164, 'x_ohm_km': 0.075},
                'overhead_acsr_wolf': {'r_ohm_km': 0.31, 'x_ohm_km': 0.35}
            }
        }
        
        # Auckland/Wellington specific traffic patterns
        self.nz_traffic_patterns = {
            'weekday_peaks': [(7, 9), (17, 19)],  # Morning and evening peaks
            'weekend_pattern': 'distributed',
            'holiday_factor': 0.7,
            'school_holiday_factor': 0.8
        }