
function mpc = case5_feeder
% CASE5_FEEDER A simple 5-bus radial feeder for MATPOWER

mpc.version = '2';
mpc.baseMVA = 100; % 系统基准容量

% bus data
% bus_i, type, Pd, Qd, Gs, Bs, area, Vm, Va, baseKV, zone, Vmax, Vmin
% type: 1=PQ, 2=PV, 3=slack
mpc.bus = [
    1, 3, 0,    0,    0, 0, 1, 1.0,  0, 0.4, 1, 1.1, 0.9;
    2, 1, 0.01, 0.005, 0, 0, 1, 1.0,  0, 0.4, 1, 1.1, 0.9; % 10kW 基础负荷
    3, 1, 0.01, 0.005, 0, 0, 1, 1.0,  0, 0.4, 1, 1.1, 0.9;
    4, 1, 0.01, 0.005, 0, 0, 1, 1.0,  0, 0.4, 1, 1.1, 0.9;
    5, 1, 0.01, 0.005, 0, 0, 1, 1.0,  0, 0.4, 1, 1.1, 0.9;
];

% generator data
% bus, Pg, Qg, Qmax, Qmin, Vg, mBase, status, Pmax, Pmin, ...
mpc.gen = [
    1, 0, 0, 999, -999, 1.0, 100, 1, 999, -999;
];

% branch data
% fbus, tbus, r, x, b, rateA, rateB, rateC, ratio, angle, status, angmin, angmax
% 假设每段线路阻抗相同
line_r = 0.5; % 线路电阻 (p.u.) - 这是一个示意值
line_x = 0.25; % 线路电抗 (p.u.) - 这是一个示意值
mpc.branch = [
    1, 2, line_r, line_x, 0, 999, 999, 999, 0, 0, 1, -360, 360;
    2, 3, line_r, line_x, 0, 999, 999, 999, 0, 0, 1, -360, 360;
    3, 4, line_r, line_x, 0, 999, 999, 999, 0, 0, 1, -360, 360;
    4, 5, line_r, line_x, 0, 999, 999, 999, 0, 0, 1, -360, 360;
];