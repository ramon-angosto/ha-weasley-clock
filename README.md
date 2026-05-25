# Weasley Clock Custom Component
![Weasley Clock Banner](docs/Weasley_clock.PNG)

A complete solution for a Harry Potter style Location Clock in Home Assistant. It manages the logic, the mathematics, and the frontend display.


## 🎨 Asset Preparation (Graphics)
Before configuring the integration, you need to create your custom Clock Face and Hands.

1.  **Edit the Design Files:**
    * This project includes design templates for the Clock Face and the Hands in the `TemplateFiles` folder.
    * You can edit these using **Affinity Photo**.
    * **Customizing texts:** Open the image you want to modify, select the text component, and type the desired name (for the Clock Face locations or the family members).
    * **Saving components:** When saving from the main template file that contains all components, ensure you export *only* the specific component you need (e.g., a single hand), while strictly keeping the original canvas size. **For the clock hands, it is crucial to save them as `.png` with a transparent background.**
    * Customize the length or color of the Hands for each family member as needed.

2.  **Export Images:**
    * **Clock Face:** Export as `.jpg` or `.png`.
    * **Hands:** MUST be exported as `.png` with a **Transparent Background**.

3.  **Upload to Home Assistant:**
    * Use the File Editor addon or Samba to access your Home Assistant folders.
    * Navigate to the `/config/www/` folder.
    * Create a new folder, I would recommend it naming it: `weasley_clock`.
    * Upload your exported images here.
    * *Result:* Your files should be accessible at `/local/weasley_clock/reloj_weasley.jpeg`.

---

## ⚙️ Setup Guide

### 1. Initial Configuration (The Clock Face)
1.  Go to **Settings > Devices & Services > Add Integration**.
2.  Search for **Weasley Clock**.
3.  **Step 1:** You will be prompted to name your 13 clock positions.
    * *Important:* These names must match the text you wrote on your Affinity Clock Face template.
    * *Order:* The order corresponds to the clock hands moving clockwise from the top (12:00 position is usually "Home").

### 2. Adding a Person (The Hand)
To add a person, go to **Settings > Devices > Add Integration > Weasley Clock** again.
1.  **Name:** Enter the person's name (e.g., `Ramon`). 
    * *Note:* This will create an entity named `sensor.ramon_clockhand`.
2.  **Offset:** (Optional) Enter a number (e.g., `8`). This rotates the hand slightly so it doesn't cover other hands when in the same location.
3.  **Template:** Paste your Jinja2 logic here (see example below).

---

## 📝 Example Logic (Template)

**The Goal:**
We want to track "Ramon". We want to use native Home Assistant Groups for family zones so we don't have to hardcode them.

**1. Create Helpers (Optional but Recommended):**
* Go to **Settings > Devices > Helpers > Create Helper > Group > Zone Group**.
* Name: `Family Houses`.
* Members: Select `zone.grandma`, `zone.parents`, etc.

**2. The Template Logic:**
Paste this into the "Template" field during setup.

```jinja
{# --- DEFINE VARIABLES --- #}
{# Change these entities to match your device #}
{% set tracker = 'device_tracker.iphone_ramon' %}
{% set battery = states('sensor.iphone_ramon_battery_level') | int(100) %}
{% set current_zone = states(tracker) %}
{% set is_night = is_state('sun.sun', 'below_horizon') %}

{# --- DEFINE GROUPS --- #}
{# We check if the current zone is inside our helper groups #}
{% set family_zones = state_attr('group.family_houses', 'entity_id') %}

{# --- LOGIC PRIORITY --- #}
{# The result MUST match one of the names you defined in Step 1 #}

{% if battery < 10 %}
  Mortal Peril
{% elif current_zone == 'home' and is_night %}
  In Bed
{% elif current_zone == 'home' %}
  Home
{% elif current_zone == 'work' %}
  Work
{% elif family_zones and current_zone in family_zones %}
  Family
{% elif current_zone == 'gym' %}
  Gym
{% elif current_zone == 'not_home' %}
  Traveling
{% else %}
  Lost
{% endif %}
```

## 🖥️ Dashboard Card (Frontend)
Add a **"Manual"** card to your dashboard and paste this YAML. The weasley-clock-card is automatically installed by the integration.

**Note on Styling:** If your hands are different sizes, use the top, left, and width properties to align them perfectly with the center pivot point.

```YAML
type: custom:weasley-clock-card
image: /local/weasley_clock/reloj_weasley.jpeg
hands:
  # Hand 1: Ramon
  - entity: sensor.ramon_clockhand
    image: /local/weasley_clock/manecilla_ramon.png
    width: 100%
    
  # Hand 2: Vero (Example of custom sizing in CSS)
  - entity: sensor.vero_clockhand
    image: /local/weasley_clock/manecilla_vero.png
    width: 117%
    top: -8.5%
    left: -8.5%
```