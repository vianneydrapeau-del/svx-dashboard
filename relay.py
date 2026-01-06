import RPi.GPIO as GPIO

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

class Relay:
    def __init__(self, gpio=12, active_low=True):
        self.pin = gpio
        self.active_low = active_low
        GPIO.setup(self.pin, GPIO.OUT)
        self.off()

    def on(self):
        GPIO.output(self.pin, GPIO.LOW if self.active_low else GPIO.HIGH)

    def off(self):
        GPIO.output(self.pin, GPIO.HIGH if self.active_low else GPIO.LOW)

    def state(self):
        val = GPIO.input(self.pin)
        if self.active_low:
            return val == GPIO.LOW
        return val == GPIO.HIGH

