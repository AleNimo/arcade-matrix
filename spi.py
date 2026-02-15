from amaranth import *

DEFAULT_FIFO_SIZE = 128 # bytes
DEFAULT_WORD_SIZE = 16  # bytes
INIT_CONFIG_REG = 0x04  # clk_div = 2, CPHA = 0, CPOL = 0
# (7-2: clk_div-1, 1: CPHA, 0: CPOL)

def rising_edge(m, signal_in):
    prev = Signal()
    
    m.d.sync += prev.eq(signal_in)

    return signal_in & ~prev

class SPI(Elaboratable):
    def __init__(self, *, fifo_size: int = DEFAULT_FIFO_SIZE, word_size: int = DEFAULT_WORD_SIZE):
        
        assert word_size in [8, 16], "word_size can only be 8 or 16"
        assert fifo_size % word_size == 0, f"fifo_size must be a multiple of word_size {word_size}"

        self.word_size = word_size
        self.fifo_size = fifo_size
        
        self.data_in = Signal(word_size)    # In (Data to load in the internal fifo)
        self.load_data = Signal()           # In (Loads data_in to fifo on rising edge)
        self.xfer_fifo = Signal()           # In (Starts xfer on rising edge)
        
        self.config_reg = Signal(8)         # In (7-2: clk_div-1, 1: CPHA, 0: CPOL)
        
        self.mosi = Signal()                # Out
        self.sclk = Signal()                # Out
        self.cs = Signal()                  # Out

        # Initial values
        self.config_reg.init = INIT_CONFIG_REG
        
    def elaborate(self, platform):

        m = Module()

        sync = m.d.sync
        comb = m.d.comb

        xfer_active = Signal()
        comb += self.cs.eq(~xfer_active)

        delay_counter = Signal(5)

        # Expresions derived from the config register:
        clock_cycle = self.config_reg >> 2
        clock_margin = clock_cycle // 4

        cpha = self.config_reg[1]
        cpol = self.config_reg[0]

        # Signals for the fifo
        fifo = Signal(self.fifo_size*8)
        
        fifo_word_size = self.fifo_size // self.word_size

        fifo_storage_index = Signal(range(fifo_word_size))
        fifo_xfer_index = Signal(range(fifo_word_size))
        
        # TODO Test if the rising_edge function can go inside the IF
        load_data_re = rising_edge(m, self.load_data)
        xfer_fifo_re = rising_edge(m, self.xfer_fifo)

        # IDLE STATE
        with m.If(~xfer_active):
        
            # The clock follows the value of CPOL in the config reg
            sync += self.sclk.eq(cpol)

            # Load data_in to the fifo on rising edge of load_data, update the storage index
            with m.If(load_data_re & (fifo_storage_index < (fifo_word_size - 1))):
                sync += fifo.word_select(fifo_storage_index, self.word_size).eq(self.data_in)
                sync += fifo_storage_index.eq(fifo_storage_index + 1)

            # If rising edge of xfer_fifo and there is data in fifo, start xfer 
            with m.If(xfer_fifo_re & fifo_storage_index > 0):
                sync += xfer_active.eq(1)
                
                # Start the clock period plus a minor margin to avoid violating the setup time of the SPI slave
                sync += delay_counter.eq(clock_cycle + clock_margin) 
                
        # XFER STATE
        with m.Else():
            
            # Serial output always points to the fifo xfer index value
            sync += self.mosi.eq(fifo.bit_select(fifo_xfer_index, 1))

            # Serial clock generation using the delay counter value as reference
            with m.If(cpha):
                sync += self.sclk.eq(delay_counter > clock_cycle // 2)
            with m.Else():
                sync += self.sclk.eq(delay_counter < clock_cycle // 2)

            # If the delay counter has a margin above the clock period, it means the clock can't change from cpol yet 
            with m.If(delay_counter > clock_cycle):
                sync += self.sclk.eq(cpol)

            # Wait until the next serial clock period
            with m.If(delay_counter > 0):
                sync += delay_counter.eq(delay_counter - 1)
 
            # At every clock period finish, update the fifo xfer index until the fifo is empty 
            # TODO: Check if changing the index and the mosi value (dependant on the index) at the same time adds a cycle delay or not. (If it does then change the index combinationally)
            with m.Elif(fifo_xfer_index < fifo_storage_index):
                sync += fifo_xfer_index.eq(fifo_xfer_index + 1) 
                sync += delay_counter.eq(clock_cycle)

            # Once the fifo is empty, reset indexes and exit xfer state
            with m.Else():
                sync += xfer_active.eq(0)
                sync += fifo_xfer_index.eq(0)
                sync += fifo_storage_index.eq(0)
                
        return m
