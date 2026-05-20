class WeasleyClockCard extends HTMLElement {
  set hass(hass) {
    if (!this.content) {
      const card = document.createElement('ha-card');
      this.content = document.createElement('div');
      this.content.style.position = 'relative';
      this.content.style.width = '100%';
      this.content.style.overflow = 'visible';
      card.appendChild(this.content);
      this.appendChild(card);
    }

    const config = this.config;

    // Background Image
    let html = `<img src="${config.image}" style="width: 100%; display: block;">`;

    // Render Hands
    config.hands.forEach(hand => {
      const entityId = hand.entity;
      const stateObj = hass.states[entityId];

      // Get Angle from Backend
      const angle = (stateObj && stateObj.attributes.angle !== undefined)
                    ? stateObj.attributes.angle
                    : 0;

      // Styling applied per hand
      const top = hand.top || "0%";
      const left = hand.left || "0%";
      const width = hand.width || "100%";

      html += `
        <div style="
          position: absolute;
          top: ${top};
          left: ${left};
          width: ${width};
          transform-origin: center center;
          transform: rotate(${angle}deg);
          transition: transform 1.5s cubic-bezier(0.4, 0, 0.2, 1);
          pointer-events: none;
          z-index: 1;
        ">
          <img src="${hand.image}" style="width: 100%;">
        </div>
      `;
    });

    this.content.innerHTML = html;
  }

  setConfig(config) {
    if (!config.hands) {
      throw new Error('You need to define hands');
    }
    this.config = config;
  }

  getCardSize() {
    return 3;
  }
}

customElements.define('weasley-clock-card', WeasleyClockCard);