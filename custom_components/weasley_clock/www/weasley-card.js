class WeasleyClockCard extends HTMLElement {
  setConfig(config) {
    if (!config.image) throw new Error('Define image for the clock face');
    if (!Array.isArray(config.hands)) throw new Error('Define hands as a list');
    if (config.hands.some(hand => !hand.entity || !hand.image)) {
      throw new Error('Each hand needs entity and image');
    }
    this.config = config;
    if (this._hass) this.hass = this._hass;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.config) return;
    if (!this.card) {
      this.card = document.createElement('ha-card');
      this.appendChild(this.card);
    }
    this.card.replaceChildren();
    const face = document.createElement('div');
    Object.assign(face.style, { position: 'relative', width: '100%', overflow: 'hidden' });
    const background = document.createElement('img');
    background.src = this.config.image;
    background.alt = 'Weasley Clock';
    background.style.width = '100%';
    background.style.display = 'block';
    face.appendChild(background);
    this.card.appendChild(face);
    const states = document.createElement('div');
    states.style.padding = '16px';
    this.config.hands.forEach(hand => {
      const state = hass.states[hand.entity];
      const angle = state?.attributes.angle;
      if (state && !['unknown', 'unavailable'].includes(state.state) && Number.isFinite(angle)) {
        const image = document.createElement('img');
        image.src = hand.image;
        image.alt = state.attributes.friendly_name || hand.entity;
        Object.assign(image.style, {
          position: 'absolute', top: hand.top || '0%', left: hand.left || '0%',
          width: hand.width || '100%', transformOrigin: 'center center',
          transform: `rotate(${angle}deg)`, pointerEvents: 'none',
        });
        face.appendChild(image);
      }
      if (this.config.show_states !== false) {
        const row = document.createElement('div');
        row.textContent = `${hand.name || state?.attributes.friendly_name || hand.entity}: ${state?.state || 'Entidad no encontrada'}`;
        const error = state?.attributes.configuration_error;
        const warning = state?.attributes.configuration_warning;
        if (error || warning) {
          const message = document.createElement('div');
          message.textContent = `\u26a0 ${[error, warning].filter(Boolean).join(' / ')}`;
          message.style.color = 'var(--warning-color, #b26a00)';
          row.appendChild(message);
        }
        row.style.cursor = 'pointer';
        row.onclick = () => this.dispatchEvent(new CustomEvent('hass-more-info', {
          detail: { entityId: hand.entity }, bubbles: true, composed: true,
        }));
        states.appendChild(row);
      }
    });
    if (this.config.show_states !== false) this.card.appendChild(states);
    if (this.config.show_configure !== false) {
      const link = document.createElement('a');
      link.textContent = hass.language?.startsWith('es') ? 'Configurar Weasley Clock' : 'Configure Weasley Clock';
      link.href = '/config/integrations/integration/weasley_clock';
      Object.assign(link.style, { display: 'block', padding: '16px', color: 'var(--primary-color)' });
      this.card.appendChild(link);
    }
  }

  static getStubConfig() {
    return { image: '/local/weasley_clock/reloj_weasley.jpeg', hands: [] };
  }

  getCardSize() { return 3; }
}

if (!customElements.get('weasley-clock-card')) {
  customElements.define('weasley-clock-card', WeasleyClockCard);
}
window.customCards = window.customCards || [];
if (!window.customCards.some(card => card.type === 'weasley-clock-card')) {
  window.customCards.push({
    type: 'weasley-clock-card', name: 'Weasley Clock',
    description: 'Location clock with hand states and configuration access',
  });
}
