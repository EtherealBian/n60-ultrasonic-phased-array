# 50MHz 外部晶振输入
create_clock -period 20.000 -name clk_50m -waveform {0.000 10.000} [get_ports clk_50m]

# 50MHz 时钟
set_property PACKAGE_PIN H16 [get_ports clk_50m]
set_property IOSTANDARD LVCMOS33 [get_ports clk_50m]

# 复位信号
set_property IOSTANDARD LVCMOS33 [get_ports async_rst_n]
set_property PACKAGE_PIN R19 [get_ports async_rst_n]

set_property IOSTANDARD LVCMOS33 [get_ports uart_rx]
set_property PACKAGE_PIN W15 [get_ports uart_rx]

set_property IOSTANDARD LVCMOS33 [get_ports led]
set_property PACKAGE_PIN G14 [get_ports led]

set_property IOSTANDARD LVCMOS33 [get_ports config_led]
set_property PACKAGE_PIN C20 [get_ports config_led]

set_property IOSTANDARD LVCMOS33 [get_ports key_in]
set_property PACKAGE_PIN T19 [get_ports key_in]


set_property IOSTANDARD LVCMOS33 [get_ports i2c_scl]
set_property PACKAGE_PIN U18 [get_ports i2c_scl]

set_property IOSTANDARD LVCMOS33 [get_ports i2c_sda]
set_property PACKAGE_PIN U19  [get_ports i2c_sda]

set_property IOSTANDARD LVCMOS33 [get_ports clk_mclk]
set_property PACKAGE_PIN Y18 [get_ports clk_mclk]

set_property IOSTANDARD LVCMOS33 [get_ports wm8978_bclk]
set_property PACKAGE_PIN W18 [get_ports wm8978_bclk]

set_property IOSTANDARD LVCMOS33 [get_ports wm8978_lrck]
set_property PACKAGE_PIN W19 [get_ports wm8978_lrck]

set_property IOSTANDARD LVCMOS33 [get_ports wm8978_adcdat]
set_property PACKAGE_PIN Y16 [get_ports wm8978_adcdat]

set_property PULLTYPE PULLUP [get_ports i2c_scl]
set_property PULLTYPE PULLUP [get_ports i2c_sda]
set_clock_groups -name ckock_asy -asynchronous -group [get_clocks -of_objects [get_pins u_mmcm/inst/mmcm_adv_inst/CLKOUT0]] -group [get_clocks [list [get_clocks -of_objects [get_pins u_mmcm/inst/mmcm_adv_inst/CLKOUT1]] [get_clocks -of_objects [get_pins u_mmcm/inst/mmcm_adv_inst/CLKFBOUT]]]]

# ====================================================================
# A 组: transducer_io[0] ~ transducer_io[11] (对应 A0 ~ A11)
# ====================================================================
set_property PACKAGE_PIN H20 [get_ports {transducer_io[0]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[0]}]

set_property PACKAGE_PIN J20 [get_ports {transducer_io[1]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[1]}]

set_property PACKAGE_PIN G17 [get_ports {transducer_io[2]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[2]}]

set_property PACKAGE_PIN G18 [get_ports {transducer_io[3]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[3]}]

set_property PACKAGE_PIN L15 [get_ports {transducer_io[4]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[4]}]

set_property PACKAGE_PIN L14 [get_ports {transducer_io[5]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[5]}]

set_property PACKAGE_PIN K14 [get_ports {transducer_io[6]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[6]}]

set_property PACKAGE_PIN J14 [get_ports {transducer_io[7]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[7]}]

set_property PACKAGE_PIN J18 [get_ports {transducer_io[8]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[8]}]

set_property PACKAGE_PIN H18 [get_ports {transducer_io[9]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[9]}]

set_property PACKAGE_PIN G15 [get_ports {transducer_io[10]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[10]}]

set_property PACKAGE_PIN H15 [get_ports {transducer_io[11]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[11]}]


# ====================================================================
# B 组: transducer_io[12] ~ transducer_io[23] (对应 B0 ~ B11)
# ====================================================================
set_property PACKAGE_PIN M15 [get_ports {transducer_io[12]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[12]}]

set_property PACKAGE_PIN M14 [get_ports {transducer_io[13]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[13]}]

set_property PACKAGE_PIN K16 [get_ports {transducer_io[14]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[14]}]

set_property PACKAGE_PIN J16 [get_ports {transducer_io[15]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[15]}]

set_property PACKAGE_PIN N16 [get_ports {transducer_io[16]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[16]}]

set_property PACKAGE_PIN N15 [get_ports {transducer_io[17]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[17]}]

set_property PACKAGE_PIN L19 [get_ports {transducer_io[18]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[18]}]

set_property PACKAGE_PIN L20 [get_ports {transducer_io[19]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[19]}]

set_property PACKAGE_PIN K19 [get_ports {transducer_io[20]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[20]}]

set_property PACKAGE_PIN J19 [get_ports {transducer_io[21]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[21]}]

set_property PACKAGE_PIN L17 [get_ports {transducer_io[22]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[22]}]

set_property PACKAGE_PIN L16 [get_ports {transducer_io[23]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[23]}]


# ====================================================================
# C 组: transducer_io[24] ~ transducer_io[35] (对应 C0 ~ C11)
# ====================================================================
set_property PACKAGE_PIN T15 [get_ports {transducer_io[24]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[24]}]

set_property PACKAGE_PIN T14 [get_ports {transducer_io[25]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[25]}]

set_property PACKAGE_PIN R16 [get_ports {transducer_io[26]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[26]}]

set_property PACKAGE_PIN R17 [get_ports {transducer_io[27]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[27]}]

set_property PACKAGE_PIN R14 [get_ports {transducer_io[28]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[28]}]

set_property PACKAGE_PIN P14 [get_ports {transducer_io[29]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[29]}]

set_property PACKAGE_PIN V17 [get_ports {transducer_io[30]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[30]}]

set_property PACKAGE_PIN V18 [get_ports {transducer_io[31]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[31]}]

set_property PACKAGE_PIN P15 [get_ports {transducer_io[32]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[32]}]

set_property PACKAGE_PIN P16 [get_ports {transducer_io[33]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[33]}]

set_property PACKAGE_PIN U17 [get_ports {transducer_io[34]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[34]}]

set_property PACKAGE_PIN T16 [get_ports {transducer_io[35]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[35]}]


# ====================================================================
# D 组: transducer_io[36] ~ transducer_io[47] (对应丝印 D0 ~ D11)
# ====================================================================
# D0 -> JP1_10 -> U20
set_property PACKAGE_PIN U20 [get_ports {transducer_io[36]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[36]}]

# D1 -> JP1_9 -> T20
set_property PACKAGE_PIN T20 [get_ports {transducer_io[37]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[37]}]

# D2 -> JP1_3 -> N17
set_property PACKAGE_PIN N17 [get_ports {transducer_io[38]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[38]}]

# D3 -> JP1_4 -> P18
set_property PACKAGE_PIN P18 [get_ports {transducer_io[39]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[39]}]

# D4 -> JP1_14 -> W20
set_property PACKAGE_PIN W20 [get_ports {transducer_io[40]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[40]}]

# D5 -> JP1_13 -> V20
set_property PACKAGE_PIN V20 [get_ports {transducer_io[41]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[41]}]

# D6 -> JP1_5 -> N20
set_property PACKAGE_PIN N20 [get_ports {transducer_io[42]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[42]}]

# D7 -> JP1_6 -> P20
set_property PACKAGE_PIN P20 [get_ports {transducer_io[43]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[43]}]

# D8 -> JP1_1 -> N18
set_property PACKAGE_PIN N18 [get_ports {transducer_io[44]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[44]}]

# D9 -> JP1_2 -> P19
set_property PACKAGE_PIN P19 [get_ports {transducer_io[45]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[45]}]

# D10 -> JP1_8 -> R18
set_property PACKAGE_PIN R18 [get_ports {transducer_io[46]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[46]}]

# D11 -> JP1_7 -> T17
set_property PACKAGE_PIN T17 [get_ports {transducer_io[47]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[47]}]


# ====================================================================
# E 组: transducer_io[48] ~ transducer_io[59] (对应丝印 E0 ~ E11)
# ====================================================================
# E0 -> JP1_38 -> U12
set_property PACKAGE_PIN U12 [get_ports {transducer_io[48]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[48]}]

# E1 -> JP1_37 -> T12
set_property PACKAGE_PIN T12 [get_ports {transducer_io[49]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[49]}]

# E2 -> JP1_31 -> U14
set_property PACKAGE_PIN U14 [get_ports {transducer_io[50]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[50]}]

# E3 -> JP1_32 -> U15
set_property PACKAGE_PIN U15 [get_ports {transducer_io[51]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[51]}]

# E4 -> JP1_40 -> T10
set_property PACKAGE_PIN T10 [get_ports {transducer_io[52]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[52]}]

# E5 -> JP1_39 -> T11
set_property PACKAGE_PIN T11 [get_ports {transducer_io[53]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[53]}]

# E6 -> JP1_33 -> U13
set_property PACKAGE_PIN U13 [get_ports {transducer_io[54]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[54]}]

# E7 -> JP1_34 -> V13
set_property PACKAGE_PIN V13 [get_ports {transducer_io[55]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[55]}]

# E8 -> JP1_27 -> W14
set_property PACKAGE_PIN W14 [get_ports {transducer_io[56]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[56]}]

# E9 -> JP1_28 -> Y14
set_property PACKAGE_PIN Y14 [get_ports {transducer_io[57]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[57]}]

# E10 -> JP1_36 -> W13
set_property PACKAGE_PIN W13 [get_ports {transducer_io[58]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[58]}]

# E11 -> JP1_35 -> V12
set_property PACKAGE_PIN V12 [get_ports {transducer_io[59]}]
set_property IOSTANDARD LVCMOS33 [get_ports {transducer_io[59]}]

