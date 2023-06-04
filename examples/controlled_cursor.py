from machine import Pin, SoftI2C
from i2c_lcd import LiquidCrystalI2C

LCD_COLS = 20
LCD_ROWS = 4

i2c = SoftI2C(sda=Pin(21), scl=Pin(22))

lcd = LiquidCrystalI2C(i2c, 0x27, LCD_COLS, LCD_ROWS)

# this settings allows for better line wrapping
lcd.set_controlled_cursor(True)
lcd.home()
lcd.display()
lcd.backlight()

lcd.print("lorem ipsum dolor sit amet")
