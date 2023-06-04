from machine import SoftI2C
from time import sleep_ms, sleep_us

# commands
LCD_FUNCTIONRESET = 0x30
LCD_FUNCTION = 0x20
LCD_CLEARDISPLAY = 0x01
LCD_RETURNHOME = 0x02
LCD_ENTRYMODESET = 0x04
LCD_DISPLAYCONTROL = 0x08
LCD_CURSORSHIFT = 0x10
LCD_FUNCTIONSET = 0x20
LCD_CGRAM = 0x40
LCD_DDRAM = 0x80

# flags for display entry mode
LCD_ENTRYRIGHT = 0x00
LCD_ENTRYLEFT = 0x02
LCD_ENTRYSHIFTINCREMENT = 0x01
LCD_ENTRYSHIFTDECREMENT = 0x00

# flags for display on/off control
LCD_DISPLAYON = 0x04
LCD_DISPLAYOFF = 0x00
LCD_CURSORON = 0x02
LCD_CURSOROFF = 0x00
LCD_BLINKON = 0x01
LCD_BLINKOFF = 0x00

# flags for display/cursor shift
LCD_DISPLAYMOVE = 0x08
LCD_CURSORMOVE = 0x00
LCD_MOVERIGHT = 0x04
LCD_MOVELEFT = 0x00

# flags for function set
LCD_8BITMODE = 0x10
LCD_4BITMODE = 0x00
LCD_2LINE = 0x08
LCD_1LINE = 0x00
LCD_5x10DOTS = 0x04
LCD_5x8DOTS = 0x00

# flags for backlight control
LCD_BACKLIGHT = 0x08
LCD_NOBACKLIGHT = 0x00
EN = 0b100

class LiquidCrystalI2C:
    """
    This class is to interface with LCD displays (conforming to spec) over I2C. 
    """
    __control_cursor = False
    __cursor = (0, 0)
    __inter: SoftI2C
    __displayfunction: int = 0
    __displaycontrol: int = 0
    __displaymode: int = 0
    __ltr = True
    __offsets = []
    __addr: int = 0x27
    __cols: int = 20
    __rows: int = 4
    __backlight: int = LCD_NOBACKLIGHT

    def __init__(self, ic2_inter: SoftI2C, i2c_addr: int, cols: int, rows: int, charsize = LCD_5x8DOTS) -> None:
        """
        Initializes the display instance. Since this constructor doesn't home the display 
        the homing must be done after the initial setup is completed.
        """
        self.__inter = ic2_inter
        self.__addr = i2c_addr
        self.__cols = cols
        self.__cursor = (0, 0)
        self.__rows = rows
        self.__displayfunction = LCD_4BITMODE | LCD_1LINE | charsize

        self.__offsets = [0x00, 0x40, 0x00+cols, 0x40+cols]

        if rows > 1:
            self.__displayfunction |= LCD_2LINE

        self.expander_write(self.__backlight)
        sleep_ms(20)

        # three timed resets, needed delay values are rounded up to whole ms
        for _ in range(0, 2):
            self.write4(LCD_FUNCTIONRESET)
            sleep_ms(5)

        self.write4(LCD_FUNCTIONRESET)
        sleep_ms(1)

        self.write4(LCD_FUNCTION)
        sleep_ms(1)

        self.command(LCD_FUNCTIONSET | self.__displayfunction)
    
        self.__displaycontrol = LCD_DISPLAYON | LCD_CURSOROFF | LCD_BLINKOFF
        self.display()
        
        self.clear()

        self.__displaymode = LCD_ENTRYLEFT | LCD_ENTRYSHIFTDECREMENT

        self.command(LCD_ENTRYMODESET | self.__displaymode)

    def print(self, content: str):
        """
        Prints a string character by character.
        """
        if not isinstance(content, str):
            content = str(content)
        for char in content:
            self.write(ord(char))

    def clear(self):
        """
        Removes any entries from the display and sets the cursor to (0,0) position.
        """
        self.command(LCD_CLEARDISPLAY)
        self.__cursor = (0, 0)
        sleep_ms(2)
    
    def home(self):
        """
        Sets the cursor to the (0,0) position.
        """
        self.command(LCD_RETURNHOME)
        self.__cursor = (0, 0)
        sleep_ms(2)

    def set_cursor(self, x: int = 0, y: int = 0):
        """
        Moves the cursor to the specified (x,y) or (col,row) position.
        """

        if y >= self.__rows:
            y = self.__rows - 1
        self.command(LCD_DDRAM | (x + self.__offsets[y]))

    def set_controlled_cursor(self, enable: bool):
        """
        Set if cursor movement is controlled by the MicroPython script.
        
        :param bool enable: Enabled or disabled
        """
        self.__control_cursor = enable
        if not enable:
            # restore native functionality
            if self.__ltr:
                self.ltr()
            else:
                self.rtl()

    def move_cursor(self, right: bool):
        """
        Moves the cursor by one field left or right.
        
        :param bool right: True: right, False: left
        """
        x, y = self.__cursor[0], self.__cursor[1]
        if right:
            x += 1
        else:
            x -= 1

        if x == -1:
            x = self.__cols - 1
            y -= 1
            if y == -1:
                y = self.__rows - 1
        elif x == self.__cols:
            y += 1
            if y == self.__rows:
                y = 0
            x = 0

        if self.__control_cursor:
            self.set_cursor(x, y)

        self.__cursor = (x,y)

    def scroll_left(self):
        """
        Shifts the current cursor position by one to the left.
        """
        if self.__control_cursor:
            self.move_cursor(False)
        else:
            self.command(LCD_CURSORSHIFT | LCD_DISPLAYMOVE | LCD_MOVELEFT)

    def scroll_right(self):
        """
        Shifts the current cursor position by one to the right.
        """
        if self.__control_cursor:
            self.move_cursor(True)
        else:
            self.command(LCD_CURSORSHIFT | LCD_DISPLAYMOVE | LCD_MOVERIGHT)

    def autoscroll(self):
        """
        Enables native autoscroll feature. Disables controlled cursor.
        """
        self.set_controlled_cursor(False)
        self.__displaymode |= LCD_ENTRYSHIFTINCREMENT
        self.command(LCD_ENTRYMODESET | self.__displaymode)
    
    def no_autoscroll(self):
        """
        Disabled native autoscroll feature.
        """
        self.__displaymode &= ~LCD_ENTRYSHIFTINCREMENT
        self.command(LCD_ENTRYMODESET | self.__displaymode)

    def display(self):
        """
        Turns the display on quickly.
        """
        self.__displaycontrol |= LCD_DISPLAYON
        self.command(LCD_DISPLAYCONTROL | self.__displaycontrol)

    def no_display(self):
        """
        Turns the display off quickly.
        """
        self.__displaycontrol &= ~LCD_DISPLAYON
        self.command(LCD_DISPLAYCONTROL | self.__displaycontrol)
    
    def blink(self):
        """
        Enables cursor blinking.
        """
        self.__displaycontrol |= LCD_BLINKON
        self.command(LCD_DISPLAYCONTROL | self.__displaycontrol)

    def no_blink(self):
        """
        Disables cursor blinking.
        """
        self.__displaycontrol &= ~LCD_BLINKON
        self.command(LCD_DISPLAYCONTROL | self.__displaycontrol)

    def backlight(self):
        """
        Turns the backlight on.  
        """
        self.__backlight = LCD_BACKLIGHT
        self.expander_write(0)

    def no_backlight(self):
        """
        Turns the backlight off.  
        """
        self.__backlight = LCD_NOBACKLIGHT
        self.expander_write(0)

    def ltr(self):
        """
        Sets the text direction to left-to-right.
        """
        self.__ltr = True
        if not self.__control_cursor:
            self.__displaymode |= LCD_ENTRYLEFT
            self.command(LCD_ENTRYMODESET | self.__displaymode)

    def rtl(self):
        """
        Sets the text direction to right-to-left.
        """
        self.__ltr = False
        if not self.__control_cursor:
            self.__displaymode &= ~LCD_ENTRYLEFT
            self.command(LCD_ENTRYMODESET | self.__displaymode)

    def create_char(self, location: int, charmap):
        """
        Creates a custom char on the specified location.

        :param int location: Location of the created char (0 to 7)
        :param bytearray charmap: Bytearray representation of desired char 
        """
        location &= 0x7
        self.command(LCD_CGRAM | (location << 3))
        for i in range(0,8):
            self.send(charmap[i], 1)

    def command(self, value: int):
        """
        Sends a command message to the display. 
        For the right call codes refer to the docs of your display (standardised).
        """
        self.send(value, 0)

    def write(self, value: int):
        """
        Sends a message to the display. Should be used only to input visible chars.
        If you want to register a custom char or do something else: use a send method in HIGH state. 
        """
        self.send(value, 1)
        self.move_cursor(self.__ltr)

    def send(self, value: int, mode: int):
        hi = value & 0xf0
        lo = (value << 4) & 0xf0

        self.write4(hi | mode)
        self.write4(lo | mode)

    def write4(self, value: int): 
        self.expander_write(value)
        self.pulse_enable(value)

    def pulse_enable(self, data: int):
        self.expander_write(data | EN)
        sleep_us(1)

        self.expander_write(data & ~EN)
        sleep_us(50)

    def expander_write(self, data: int):
        """
        A direct call to the display via I2C interface.
        """
        self.__inter.writeto(self.__addr, bytes([data | self.__backlight]))
