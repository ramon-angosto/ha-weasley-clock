# Weasley Clock for Home Assistant

A Harry Potter-inspired family location clock for Home Assistant, with a custom
integration and Lovelace dashboard card. Use Jinja templates to point each
person's clock hand at home, work, travelling, or any of your configured locations.

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.9%2B-18BCF2)](https://www.home-assistant.io/)
[![HACS custom repository](https://img.shields.io/badge/HACS-Custom%20repository-41BDF5)](https://www.hacs.xyz/docs/faq/custom_repositories/)
[![Latest release](https://img.shields.io/github/v/release/ramon-angosto/ha-weasley-clock)](https://github.com/ramon-angosto/ha-weasley-clock/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

![Weasley Clock showing two family members on a custom clock face](docs/weasley_clock.PNG)

## Features

- One Weasley Clock integration entry with configurable person subentries.
- 13 named clock positions, each exposed as a text sensor.
- A Jinja template per person using your existing Home Assistant entities.
- Individual hand offsets to help separate people at the same location.
- A Lovelace card with custom face and hand images, person states, and diagnostics.
- Clock graphics accessible in Multimedia, with automatic dashboard resource registration.
- Automatic migration from older separate person entries while preserving sensor IDs.

## Installation

Requires **Home Assistant 2026.9 or newer**. For HACS installation, HACS must already
be installed. This project is available as a **custom repository**.

### HACS

1. Open **HACS**, then its menu and **Custom repositories**.
2. Add `https://github.com/ramon-angosto/ha-weasley-clock` with type **Integration**.
3. Find **Weasley Clock** in HACS and download the latest release.
4. Restart Home Assistant.
5. Open **Settings > Devices & services > Add integration > Weasley Clock**.
6. Configure the 13 locations, then add people inside the clock entry.
7. Upload your clock graphics to **Media > My media > weasley_clock** and add the
   **Weasley Clock** dashboard card using the YAML example below.

See the [HACS custom repository guide](https://www.hacs.xyz/docs/faq/custom_repositories/)
for the repository menu, and [release notes](https://github.com/ramon-angosto/ha-weasley-clock/releases)
for changes between versions.

### Manual installation

1. Download the source ZIP from the [latest release](https://github.com/ramon-angosto/ha-weasley-clock/releases/latest).
2. Copy `custom_components/weasley_clock` into `/config/custom_components/`.
3. Restart Home Assistant and follow steps 5–7 above.

## Configuration and graphics

[Prepare graphics](#asset-preparation-graphics) ·
[Configure the clock and people](#setup-guide) ·
[Template example](#example-logic-template) ·
[Dashboard card](#dashboard-card-frontend) ·
[Upgrade guide](#updating-to-120)

## Asset Preparation (Graphics)
Before configuring the integration, you need to create your custom Clock Face and Hands.

**Clock Face Example:**  
![Clock Face Example](docs/weasley_clockface_example.png)

**Clock Hand Example:**  
![Clock Hand Example](docs/weasley_clockhand_example.png)

1.  **Edit the Design Files:**
    * This project includes design templates for the Clock Face and the Hands in the `TemplateFiles` folder.
    * You can edit these using **Affinity Photo**.
    * **Important Font Note:** If you want your text to match the original templates, please install the [Big Caslon Medium font](https://fontsgeek.com/fonts/big-caslon-medium?ref=readme) before editing.
    * **Customizing texts:** Open the image you want to modify, select the text component, and type the desired name (for the Clock Face locations or the family members).
    * **Saving components:** When saving from the main template file that contains all components, ensure you export *only* the specific component you need (e.g., a single hand), while strictly keeping the original canvas size. **For the clock hands, it is crucial to save them as `.png` with a transparent background.**
    * Customize the length or color of the Hands for each family member as needed.

2.  **Export Images:**
    * **Clock Face:** Export as `.jpg` or `.png`.
    * **Hands:** MUST be exported as `.png` with a **Transparent Background**.

3.  **Upload to Home Assistant:**
    * Use the File Editor addon or Samba to access your Home Assistant folders.
    * After installing the integration, open **Media > My media > weasley_clock** and upload the images.
    * On Home Assistant OS this folder is `/media/weasley_clock/`. A custom media directory is also supported.
    * The images also appear in **Media > Weasley Clock**.
    * Use `/weasley_clock/images/reloj_weasley.jpeg` in the dashboard card. Existing `/local/weasley_clock/` URLs continue to work.

---

## Setup Guide

### 1. Initial Configuration (The Clock Face)
1.  Go to **Settings > Devices & Services > Add Integration**.
2.  Search for **Weasley Clock**.
3.  **Step 1:** You will be prompted to name your 13 clock positions.
    * *Important:* These names must match the text you wrote on your Affinity Clock Face template.
    * *Order:* The order corresponds to the clock hands moving clockwise from the top (12:00 position is usually "Home").

### 2. Adding a Person (The Hand)
Open **Settings > Devices & services > Weasley Clock** and use **Add person** on the existing clock entry (the subentry add control). People belong to that clock; they do not create separate integration entries.
1.  **Name:** Enter the person's name (e.g., `Ron`). 
    * *Note:* This will create an entity named `sensor.ron_clockhand`.
2.  **Offset:** (Optional) Enter a number (e.g., `8`). This rotates the hand slightly so it doesn't cover other hands when in the same location.
3.  **Template:** Paste your Jinja2 logic here (see example below).

---

## Example Logic (Template)

**The Goal:**
We want to track "Ron Weasley". We want to use native Home Assistant Groups for family zones so we don't have to hardcode them.

**1. Create Helpers (Optional but Recommended):**
* Go to **Settings > Devices > Helpers > Create Helper > Group > Zone Group**.
* Name: `Family Houses`.
* Members: Select `zone.grandma`, `zone.parents`, etc.

**2. The Template Logic:**
Paste this into the "Template" field during setup.

```jinja
{# --- DEFINE VARIABLES --- #}
{# Change these entities to match your device #}
{% set tracker = 'device_tracker.iphone_ron' %}
{% set battery = states('sensor.iphone_ron_battery_level') | int(100) %}
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

## Dashboard Card (Frontend)
Add a **"Manual"** card to your dashboard and paste this YAML. The weasley-clock-card is automatically installed by the integration.

**Note on Styling:** If your hands are different sizes, use the top, left, and width properties to align them perfectly with the center pivot point.

```YAML
type: custom:weasley-clock-card
image: /weasley_clock/images/reloj_weasley.jpeg
hands:
  # Hand 1: Ron
  - entity: sensor.ron_clockhand
    image: /weasley_clock/images/manecilla_ron.png
    width: 100%
    
  # Hand 2: Ginny (Example of custom sizing in CSS)
  - entity: sensor.ginny_clockhand
    image: /weasley_clock/images/manecilla_ginny.png
    width: 117%
    top: -8.5%
    left: -8.5%
```

## Updating to 1.2.0

Requires Home Assistant **2026.9 or newer**. Replace the complete
`/config/custom_components/weasley_clock/` folder (including `translations`,
`media_source.py`, and `www`), restart Home Assistant, and refresh browser/app pages.
The integration page should show **version 1.2.0**.

There is one entry named **Weasley Clock**. Its configuration edits the 13
positions; each position is a text sensor showing its name, such as `Home`.
Add people inside this entry using the person subentry add control, then use
**Reconfigure** on a person's subentry to edit their name, offset, and template.
Changing a location name also requires changing templates that return its old name.

Existing separate person entries migrate automatically into the clock as person
subentries. Their sensor entity IDs, unique IDs, device IDs and areas are retained.
The old `Weasley Clock Hub` title becomes `Weasley Clock`. The old numeric count
sensor is replaced by 13 location sensors. Do not delete and recreate Ron.

### Images in Multimedia

The integration creates `weasley_clock` in your configured local media directory
(`/media/weasley_clock` on Home Assistant OS). Upload the face and hand images
through **Media > My media > weasley_clock**. They are also browsable under
**Media > Weasley Clock**. PNG, JPG, JPEG, GIF and WebP files are supported.
Images from `/config/www/weasley_clock` are copied there on startup without
replacing existing media files. The old files and `/local/` URLs remain available.

Card images can use a filename (`ron.png`), an image URL
(`/weasley_clock/images/ron.png`), or
`media-source://weasley_clock/ron.png`. Clock graphics are served as public static
assets, just like the previous `/local/` images; use this folder for graphics.

### Card loading

The integration serves **weasley-card.js** and registers it automatically as a
Lovelace **JavaScript module** in storage mode. It also loads it through the
frontend module manager. The card appears as **Weasley Clock** in the card picker.

If your dashboard resources use YAML, include:

```yaml
resources:
  - url: /weasley_clock/weasley-card.js?v=1.2.0
    type: module
```

If the editor says `Custom element doesn't exist: weasley-clock-card`:

1. Check the installed integration version is **1.2.0**, then restart Home Assistant.
2. Open `/weasley_clock/weasley-card.js?v=1.2.0` on your Home Assistant address.
   It should return JavaScript. A 404 means the integration or its `www` folder
   was not installed or set up successfully.
3. In **Settings > Dashboards > Resources** (advanced mode), verify that URL exists
   with type **JavaScript module**. Add it manually if needed, then refresh the page.
4. Remove outdated manual resources for this card if they still load an old copy.

The card displays each person's state and a **Configure Weasley Clock** link.
Use `show_states: false` or `show_configure: false` to hide these. Click a person's
state for entity details. A template execution error or an unrecognised location
makes the sensor unavailable and displays `configuration_error` in the card.
Missing or unavailable entity references show `configuration_warning`,
`missing_entities`, and `unavailable_entities`. Valid fallback locations remain
usable. Diagnostics check entity references accessed in the evaluated Jinja branch;
unexecuted branches and arbitrary strings are not exhaustively validated.

### Development checks

```text
python -m unittest discover -s tests -v
node tests/test_card.cjs
```

The Python checks use lightweight HA API doubles; verify the installed integration
and browser resource in Home Assistant as well.

## License

Licensed under the [MIT License](LICENSE).
