const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor(tag) { this.tag = tag; this.style = {}; this.children = []; }
  appendChild(child) { this.children.push(child); return child; }
  replaceChildren() { this.children = []; }
  dispatchEvent(event) { this.lastEvent = event; }
}
const elements = new Map();
const context = vm.createContext({
  HTMLElement: Element,
  document: { createElement: tag => new Element(tag) },
  customElements: { get: name => elements.get(name), define: (name, type) => elements.set(name, type) },
  window: {}, CustomEvent: class { constructor(type, args) { this.type = type; Object.assign(this, args); } },
});
const script = fs.readFileSync('custom_components/weasley_clock/www/weasley-card.js', 'utf8');
// A manual resource and automatic registration may load separate module URLs.
vm.runInContext(`(() => { ${script} })()`, context);
vm.runInContext(`(() => { ${script} })()`, context);
assert.equal(elements.size, 1);
assert.equal(context.window.customCards.length, 1);
const Card = elements.get('weasley-clock-card');
const card = new Card();
card.setConfig({image: 'clock face.png', hands: [{entity:'sensor.ron_clockhand', image:'ron.png'}]});
const hass = {language:'es', states: {'sensor.ron_clockhand': {state:'Home', attributes: {angle:8, friendly_name:'Ron', configuration_warning:'Entities do not exist: person.ron'}}}};
card.hass = hass;
const face = card.card.children[0];
assert.equal(face.children[0].src, '/weasley_clock/images/clock%20face.png');
assert.equal(face.children[1].style.transform, 'rotate(8deg)');
const row = card.card.children[1].children[0];
assert.match(row.children[0].textContent, /person.ron/);
row.onclick();
assert.equal(card.lastEvent.detail.entityId, 'sensor.ron_clockhand');
assert.equal(card.card.children.find(child => child.tag === 'a').href, '/config/integrations/integration/weasley_clock');
assert.equal(card.imageUrl('media-source://weasley_clock/ron.png'), '/weasley_clock/images/ron.png');
assert.equal(card.imageUrl('/local/weasley_clock/ron.png'), '/local/weasley_clock/ron.png');
hass.states['sensor.ron_clockhand'].state = 'unavailable';
card.hass = hass;
assert.equal(card.card.children[0].children.length, 1);
assert.throws(() => card.setConfig({image:'clock.png', hands:[{}]}), /entity and image/);
(async () => {
  const automatic = new Card();
  automatic.setConfig({});
  let request;
  const automaticHass = {language:'es', states: hass.states, callWS:async message => {
    request = message;
    if (message.type === 'weasley_clock/config') return {image:'/weasley_clock/images/clock.png', hands:[{entity:'sensor.ron_clockhand', image:'/weasley_clock/images/ron.png'}]};
    return {response:{url:'/weasley_clock/images/weasley_clock_snapshot.png?v=1', skipped_entities:[]}};
  }};
  automatic.hass = automaticHass;
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(request.type,'weasley_clock/config');
  assert.equal(automatic.card.children[0].children[0].src,'/weasley_clock/images/clock.png');
  await automatic.takeSnapshot();
  assert.equal(request.service,'snapshot');
  assert.equal(request.return_response,true);
  assert.equal(request.service_data.hands[0].entity,'sensor.ron_clockhand');
  assert.equal(automatic._snapshotUrl,'/weasley_clock/images/weasley_clock_snapshot.png?v=1');
  assert.equal(automatic._snapshotBusy,false);
  automaticHass.callWS=async () => {throw new Error('missing local image');};
  await automatic.takeSnapshot();
  assert.equal(automatic._snapshotError,'missing local image');
  const noFace=new Card();noFace.setConfig({});
  noFace.hass={...automaticHass,callWS:async()=>({image:null,hands:[]})};
  await new Promise(resolve=>setImmediate(resolve));
  assert.match(noFace.card.textContent,/reloj_weasley.png/);
  assert.equal(noFace.card.children[0].tag,'button');
  console.log('Card registration, rendering, discovery and snapshot action: passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
