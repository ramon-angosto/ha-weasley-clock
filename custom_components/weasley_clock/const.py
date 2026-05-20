"""Constants for the Weasley Clock integration."""

DOMAIN = "weasley_clock"

# The 13 default keys for the config flow
CONF_SLOTS = [f"slot_{i}_name" for i in range(1, 14)]

# Calculated angles for 13 positions (360 / 13)
# Starting from 0 and moving clockwise
CLOCK_ANGLES = [
    0,      # Slot 1
    27.69,  # Slot 2
    55.38,  # Slot 3
    83.08,  # Slot 4
    110.77, # Slot 5
    138.46, # Slot 6
    166.15, # Slot 7
    193.85, # Slot 8
    221.54, # Slot 9
    249.23, # Slot 10
    276.92, # Slot 11
    304.62, # Slot 12
    332.31  # Slot 13
]