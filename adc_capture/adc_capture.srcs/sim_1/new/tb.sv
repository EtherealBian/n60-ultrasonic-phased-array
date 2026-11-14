`timescale 1ns / 1ps
// 功能: I2S 主机接收器 Testbench (修复版：完美处理 16-bit 紧凑边界)

module tb_i2s_rx_master();

    // ==========================================
    // 1. 仿真信号声明
    // ==========================================
    logic        rst_n;
    logic        mclk;
    
    wire         bclk;
    wire         lrck;
    logic        adcdat;
    
    wire signed [15:0] left_data;
    wire signed [15:0] right_data;
    wire               data_valid;

    // ==========================================
    // 2. 例化被测设计 (DUT)
    // ==========================================
    i2s_rx_master u_dut (
        .rst_n      (rst_n),
        .mclk       (mclk),
        .bclk       (bclk),
        .lrck       (lrck),
        .adcdat     (adcdat),
        .left_data  (left_data),
        .right_data (right_data),
        .data_valid (data_valid)
    );

    // ==========================================
    // 3. 时钟生成 (MCLK = 12.288MHz)
    // ==========================================
    initial begin
        mclk = 0;
        forever #40.69 mclk = ~mclk;
    end

    // ==========================================
    // 4. 虚拟 WM8978 I2S 从机发送模型 (修正版)
    // ==========================================
    localparam logic [15:0] TEST_LEFT_VAL  = 16'hA5A5;
    localparam logic [15:0] TEST_RIGHT_VAL = 16'h5A5A;

    logic        lrck_d;
    logic        is_right;
    integer      bit_idx;

    initial begin
        adcdat   = 1'b0;
        lrck_d   = 1'b0;
        is_right = 1'b0;
        bit_idx  = 0;
    end

    // I2S 规范：从机在 BCLK 的【下降沿】改变数据，主机在【上升沿】采样
    always_ff @(negedge bclk or negedge rst_n) begin
        if (!rst_n) begin
            adcdat   <= 1'b0;
            lrck_d   <= 1'b0;
            bit_idx  <= 0;
            is_right <= 1'b0;
        end else begin
            lrck_d <= lrck;
            
            // 边沿检测：LRCK 发生翻转
            if (lrck != lrck_d) begin
                // 【精髓修复】在 LRCK 翻转的这一个 BCLK 周期，输出上一个声道的最后一位 (LSB)！
                // 如果 lrck 刚变成 1(右声道)，说明左声道刚结束，补发左声道的 bit 0
                // 如果 lrck 刚变成 0(左声道)，说明右声道刚结束，补发右声道的 bit 0
                adcdat   <= lrck ? TEST_LEFT_VAL[0] : TEST_RIGHT_VAL[0];
                
                bit_idx  <= 15;      // 准备在下一个 BCLK 周期发送 MSB
                is_right <= lrck;    
            end 
            // 正常的帧内数据移位过程
            else begin
                if (bit_idx > 0) begin
                    adcdat <= is_right ? TEST_RIGHT_VAL[bit_idx] : TEST_LEFT_VAL[bit_idx];
                    bit_idx <= bit_idx - 1;
                end
            end
        end
    end

    // ==========================================
    // 5. 激励与监控逻辑
    // ==========================================
    initial begin
        rst_n = 0;
        #200;
        rst_n = 1;

        $display("=========================================================");
        $display("   I2S Receiver Testbench Started");
        $display("   Expected Left:  0xA5A5");
        $display("   Expected Right: 0x5A5A");
        $display("=========================================================");

        // 丢弃第一帧（复位同步时的残缺帧）
        @(posedge data_valid);
        $display("[%0t] Skipping partial first frame...", $time);

        // 严格校验后续 3 帧
        repeat(3) begin
            @(posedge data_valid);
            $display("[%0t] FRAME RECEIVED -> Left: 0x%h | Right: 0x%h", 
                     $time, left_data, right_data);
                     
            if (left_data !== TEST_LEFT_VAL || right_data !== TEST_RIGHT_VAL) begin
                $display(">>> ERROR: Data Mismatch! <<<");
                $stop;
            end else begin
                $display(">>> PASS: Frame data is perfect! <<<");
            end
        end

        #2000;
        $display("=========================================================");
        $display("   Simulation Finished Successfully");
        $display("=========================================================");
        $finish;
    end

endmodule