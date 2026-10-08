class WeasleyClockCard extends HTMLElement {
  setConfig(config) {
    if (config.hands !== undefined && !Array.isArray(config.hands)) throw new Error('Define hands as a list');
    if (config.hands?.some(hand => !hand.entity || !hand.image)) {
      throw new Error('Each hand needs entity and image');
    }
    this.config = config;
    this._automatic = null;
    this._loadError = null;
    this._loadGeneration = (this._loadGeneration || 0) + 1;
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
    if ((!this.config.image || this.config.hands === undefined) && !this._automatic) {
      this.card.textContent = this._loadError || (hass.language?.startsWith('es') ? 'Buscando el reloj en Multimedia\u2026' : 'Looking for the clock in Multimedia\u2026');
      if (!this._loading && !this._loadError) this.loadAutomaticConfig();
      return;
    }
    const config = { ...this.config, image: this.config.image || this._automatic?.image,
      hands: this.config.hands ?? this._automatic?.hands ?? [] };
    this._resolved = config;
    if (!config.image) {
      this.card.textContent = hass.language?.startsWith('es')
        ? 'No se encontr\u00f3 la base. Sube reloj_weasley.png a Multimedia o configura su imagen en Weasley Clock.'
        : 'No clock face found. Upload reloj_weasley.png in Multimedia or configure its image in Weasley Clock.';
      const retry = document.createElement('button');
      retry.textContent = hass.language?.startsWith('es') ? 'Buscar de nuevo' : 'Search again';
      retry.onclick = () => { this._automatic = null; this._loadError = null; this.hass = this._hass; };
      this.card.appendChild(retry);
      return;
    }
    const face = document.createElement('div');
    Object.assign(face.style, { position: 'relative', width: '100%', overflow: 'hidden' });
    const background = document.createElement('img');
    background.src = this.imageUrl(config.image);
    background.alt = 'Weasley Clock';
    background.style.width = '100%';
    background.style.display = 'block';
    face.appendChild(background);
    this.card.appendChild(face);
    const states = document.createElement('div');
    states.style.padding = '16px';
    config.hands.forEach(hand => {
      const state = hass.states[hand.entity];
      const angle = state?.attributes.angle;
      if (hand.image && state && !['unknown', 'unavailable'].includes(state.state) && Number.isFinite(angle)) {
        const image = document.createElement('img');
        image.src = this.imageUrl(hand.image);
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
    if (this.config.show_snapshot !== false) {
      const button = document.createElement('button');
      button.textContent = hass.language?.startsWith('es') ? 'Obtener captura' : 'Snapshot';
      button.disabled = Boolean(this._snapshotBusy);
      button.onclick = () => this.takeSnapshot();
      this.card.appendChild(button);
      if (this._snapshotError) {
        const error = document.createElement('div');
        error.textContent = this._snapshotError;
        this.card.appendChild(error);
      }
      if (this._snapshotUrl) {
        const imageLink = document.createElement('a');
        imageLink.href = this._snapshotUrl;
        imageLink.target = '_blank';
        imageLink.rel = 'noopener';
        imageLink.textContent = hass.language?.startsWith('es') ? 'Abrir captura PNG' : 'Open PNG snapshot';
        this.card.appendChild(imageLink);
      }
    }
    if (this.config.show_configure !== false) {
      const link = document.createElement('a');
      link.textContent = hass.language?.startsWith('es') ? 'Configurar Weasley Clock' : 'Configure Weasley Clock';
      link.href = '/config/integrations/integration/weasley_clock';
      Object.assign(link.style, { display: 'block', padding: '16px', color: 'var(--primary-color)' });
      this.card.appendChild(link);
    }
  }

  async loadAutomaticConfig() {
    const generation = this._loadGeneration;
    this._loading = true;
    try {
      const config = await this._hass.callWS({ type: 'weasley_clock/config' });
      if (generation !== this._loadGeneration) return;
      this._automatic = config;
    } catch (error) {
      if (generation !== this._loadGeneration) return;
      this._loadError = error.message || String(error);
    } finally {
      this._loading = false;
      if (this._hass) this.hass = this._hass;
    }
  }

  async takeSnapshot() {
    if (this._snapshotBusy || !this._resolved?.image) return;
    const config = this._resolved;
    this._snapshotBusy = true;
    this._snapshotError = null;
    this._snapshotUrl = null;
    this.hass = this._hass;
    try {
      const result = await this._hass.callWS({
        type: 'call_service', domain: 'weasley_clock', service: 'snapshot',
        return_response: true,
        service_data: {
          image: config.image,
          hands: config.hands.map(hand => ({ entity: hand.entity, image: hand.image || '',
            width: hand.width || '100%', top: hand.top || '0%', left: hand.left || '0%' })),
        },
      });
      this._snapshotUrl = result.response.url;
      if (result.response.skipped_entities?.length) {
        this._snapshotError = (this._hass.language?.startsWith('es') ? 'Manecillas omitidas: ' : 'Skipped hands: ')
          + result.response.skipped_entities.join(', ');
      }
    } catch (error) {
      this._snapshotError = error.message || String(error);
    } finally {
      this._snapshotBusy = false;
      this.hass = this._hass;
    }
  }

  imageUrl(value) {
    const mediaPrefix = 'media-source://weasley_clock/';
    if (value.startsWith(mediaPrefix)) {
      return '/weasley_clock/images/' + value.slice(mediaPrefix.length).split('/').map(encodeURIComponent).join('/');
    }
    // Filenames refer to the clock folder shown in Multimedia.
    if (!value.startsWith('/') && !value.includes('://')) {
      return '/weasley_clock/images/' + value.split('/').map(encodeURIComponent).join('/');
    }
    return value;
  }

  static getStubConfig() {
    return {};
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
