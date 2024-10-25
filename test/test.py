import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ClockCycles
from frequency_counter.test.test_seven_segment import read_segments
import random

async def reset(dut):
    dut.rst_n.value = 0
    dut.signal.value = 0
    dut.load_period.value = 0
    dut.debug_mode.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1;
    await ClockCycles(dut.clk, 5)

async def update_period(dut, period):
    # period is a 12 bit counter, top 4 via ui_in[7:5] and bottom 8 via uio_in (when debug_mode is 0)
    dut._log.info(f"set period to be {period} cycles")
    dut.debug_mode.value = 0
    dut.period.value = period 
    dut.load_period.value = 1
    await ClockCycles(dut.clk, 1)
    dut.load_period.value = 0
    await ClockCycles(dut.clk, 1)

@cocotb.test()
async def test_frequency_count(dut):
    clock_mhz = 12
    clk_period_ns = round(1/clock_mhz * 1000, 2)
    dut._log.info(f"input clock = {clock_mhz} MHz = period {clk_period_ns} ns")

    clock = Clock(dut.clk, clk_period_ns, units="ns")
    clock_sig = cocotb.start_soon(clock.start())
    await reset(dut)
   
    # adjust the update period to match clock freq
    period = clock_mhz * 100 - 1
    await update_period(dut, period)
    
    for input_freq in [10, 15, 31, 69, 75, 90]:
        # create an input signal
        period_us = round((1/input_freq) * 100, 3)
        input_signal = cocotb.start_soon(Clock(dut.signal, period_us,  units="us").start())

        # give it 4 update periods to allow counters to adjust
        await ClockCycles(dut.clk, period * 4)
        output_freq = await read_segments(dut)
        dut._log.info(f"input freq = {input_freq} kHz, period = {period_us} us, display = {output_freq}")

        # output of the display should match the input frequency
        assert output_freq == input_freq

        # kill signal
        input_signal.kill()

    clock_sig.kill()

@cocotb.test()
async def test_debug(dut):
    clock = Clock(dut.clk, 100, units="ns")
    clock_sig = cocotb.start_soon(clock.start())
    dut.signal.value = 0
    await reset(dut)
    dut._log.info(f"checking oe is correct for non debug mode")
    # debug mode is set to 0 when we reset, so expect all uio_oe to be low
    assert dut.uio_oe == 0

    # enable debug mode
    dut._log.info(f"checking oe is correct for debug mode")
    dut.debug_mode.value = 1
    await ClockCycles(dut.clk, 1)
    assert dut.uio_oe == 0xff
    assert dut.dbg_state == 0
    assert dut.dbg_edge_count == 0
    assert dut.dbg_clk_count == 0

    dut._log.info(f"checking dbg clock count")
    await update_period(dut, 0b011000000000)

    # sync to the dbg signal
    while dut.dbg_clk_count != 1:
        await ClockCycles(dut.clk, 1)
       
    # dbg_clk_count is top 3 bits of 12 bit counter
    # in exactly 1 << 9 clock cycles, should increase by one
    count = 0
    while dut.dbg_clk_count != 2:
        await ClockCycles(dut.clk, 1)
        count += 1
    dut._log.info(f"clock took {count} cycles")
    assert count == 1 << 9

    # create an external signal
    # dbg_edge_count is top 3 bits of 7 bit counter
    count = 0
    input_signal = cocotb.start_soon(Clock(dut.signal, 1,  units="us").start())
    while dut.dbg_edge_count != 2:
        await ClockCycles(dut.signal, 1)
        count += 1
    dut._log.info(f"edge count took {count} signal cycles")
    # 1 more than you think because the signal is registered for metastability
    assert count == (1 << 5) + 1

    dut._log.info(f"checking debug state machine is counting for less than period cycles")
    # now check state cycles 0 -> 1 -> 2 -> 0
    count = 0
    while dut.dbg_state == 0:
        await ClockCycles(dut.clk, 1)
        assert count < 0b011000000000
        count += 1

    assert dut.dbg_state == 1

    dut._log.info(f"checking debug state machine is counting 10s for less than 10 cycles")
    count = 0
    while dut.dbg_state == 1:
        await ClockCycles(dut.clk, 1)
        assert count < 10
        count += 1

    assert dut.dbg_state == 2

    dut._log.info(f"checking debug state machine is in state units for 1 cycle")
    await ClockCycles(dut.clk, 1)
    assert dut.dbg_state == 0

