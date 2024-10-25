`default_nettype none

module tt_um_frequency_counter #( parameter MAX_COUNT = 24'd10_000_000 ) (
    input  wire [7:0] ui_in,    // Dedicated inputs - connected to the input switches
    output wire [7:0] uo_out,   // Dedicated outputs - connected to the 7 segment display
    input  wire [7:0] uio_in,   // IOs: Bidirectional Input path
    output wire [7:0] uio_out,  // IOs: Bidirectional Output path
    output wire [7:0] uio_oe,   // IOs: Bidirectional Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // will go high when the design is enabled
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

    wire reset = !rst_n;
    wire signal = ui_in[0];
    wire debug_mode = ui_in[1];
    wire load_period = ui_in[2];

    // use bidirectionals for 2 purposes, either debug state out, or period as input
    // depend on mode switch ui_in[1]
    // if mode input is high then debug enabled
    assign uio_oe = {8{debug_mode}};

    // 12 bit period given by top 4 bits of ui_in and all of uio_in
    wire [11:0] period = {ui_in[7:4], uio_in[7:0]};

    frequency_counter frequency_counter(
        .clk(clk),
        .reset(reset),
        .signal(signal),
        .period(period),              // 12 bits
        .period_load(load_period),

        .segments(uo_out[6:0]),       // 7 bits
        .digit(uo_out[7]),            // 1 bit

        .dbg_state(uio_out[1:0]),      // 2 bit state machine
        .dbg_clk_count(uio_out[4:2]),  // top 3 bits of 12 clk counter
        .dbg_edge_count(uio_out[7:5])  // top 3 bits of 7 bit edge counter
    );

endmodule
