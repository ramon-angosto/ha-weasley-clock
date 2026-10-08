"""Exercise migration, media files and dashboard registration without HA installed."""
import ast
import asyncio
from pathlib import Path
from shutil import copy2
from tempfile import TemporaryDirectory
from types import MappingProxyType, SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'custom_components' / 'weasley_clock'


def load(filename, names, namespace):
    tree = ast.parse((ROOT / filename).read_text(encoding='utf-8-sig'))
    nodes = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name in names]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), filename, 'exec'), namespace)
    return namespace


class UpgradeTests(unittest.IsolatedAsyncioTestCase):
    async def test_people_are_added_under_clock_subentries(self):
        from unittest.mock import Mock
        person = SimpleNamespace(subentry_id='person-ron', subentry_type='person', data={'name':'Ron'})
        entry = SimpleNamespace(entry_id='clock', data={f'slot_{i}_name':f'Place {i}' for i in range(1,14)}, options={'slot_1_name':'Home'}, subentries={'person-ron':person})
        registry = SimpleNamespace(async_get_entity_id=lambda *args:None)
        hand_factory = Mock(return_value='ron-sensor')
        add = Mock()
        ns=load('sensor.py', ['async_setup_entry'], {
            'HomeAssistant':object, 'ConfigEntry':object, 'AddEntitiesCallback':object,
            'DOMAIN':'weasley_clock', 'CLOCK_ANGLES':list(range(13)),
            'er':SimpleNamespace(async_get=lambda hass:registry),
            'WeasleyLocationSensor':lambda entry,slot:f'location-{slot}',
            'WeasleyHandSensor':hand_factory,
        })
        await ns['async_setup_entry']('hass',entry,add)
        self.assertEqual(len(add.call_args_list[0].args[0]),13)
        self.assertEqual(add.call_args_list[1].kwargs,{'config_subentry_id':'person-ron'})
        self.assertEqual(hand_factory.call_args.args[1],person)
        self.assertEqual(hand_factory.call_args.args[2]['Home'],0)
        self.assertIs(hand_factory.call_args.args[3],entry)

    async def test_person_reconfiguration_keeps_legacy_identifier(self):
        from unittest.mock import Mock
        ns=load('config_flow.py',['WeasleyPersonFlow'], {
            'config_entries':SimpleNamespace(ConfigSubentryFlow=object),
            'validate_hand':lambda hass,data:{},
        })
        flow=ns['WeasleyPersonFlow']()
        person=SimpleNamespace(data={'legacy_entry_id':'ron','name':'Ron','template':'Home'})
        clock=object()
        flow.hass=object()
        flow._get_reconfigure_subentry=lambda:person
        flow._get_entry=lambda:clock
        flow.async_update_and_abort=Mock(return_value='updated')
        result=await flow.async_step_reconfigure({'name':'Ronald','template':'Work','offset':8})
        self.assertEqual(result,'updated')
        data=flow.async_update_and_abort.call_args.kwargs['data']
        self.assertEqual(data['legacy_entry_id'],'ron')
        self.assertEqual(data['template'],'Work')

    async def test_migrate_legacy_person_and_retry_preserves_ids(self):
        clock = SimpleNamespace(entry_id='clock', title='Weasley Clock Hub', data={'slot_1_name':'Home'}, options={}, subentries={})
        legacy = SimpleNamespace(entry_id='ron', data={'name':'Ron', 'template':'Home'}, options={'template':'Work', 'offset':8})
        entity = SimpleNamespace(entity_id='sensor.ron_clockhand', unique_id='ron_clockhand', config_entry_id='ron', config_subentry_id=None)
        device = SimpleNamespace(id='device-ron', config_entry_id='ron', config_subentry_id=None, area_id='living-room')
        entries = [legacy, clock]
        actions = []
        def update(obj, changes):
            for key, value in changes.items(): setattr(obj, key.removeprefix('new_'), value)
        class Manager:
            fail_remove = True
            def async_entries(self, domain): return list(entries)
            def async_update_entry(self, entry, **changes): update(entry, changes)
            def async_add_subentry(self, parent, sub): parent.subentries[sub.subentry_id] = sub
            async def async_remove(self, entry_id):
                # Registry ownership must change before the old entry is removed.
                assert entity.config_entry_id == 'clock'
                assert device.config_entry_id == 'clock'
                if self.fail_remove:
                    raise RuntimeError('simulated interrupted upgrade')
                entries.remove(legacy)
                actions.append('remove')
        manager = Manager()
        devices = SimpleNamespace(
            async_get_or_create=lambda **kw: SimpleNamespace(id='clock-device'),
            async_update_device=lambda device_id, **kw: update(device, kw) if device_id=='device-ron' else None,
        )
        entities = SimpleNamespace(async_update_entity=lambda entity_id, **kw: update(entity, kw))
        hass = SimpleNamespace(config_entries=manager)
        subentry_factory = lambda **kw: SimpleNamespace(subentry_id='person-ron', **kw)
        ns = load('__init__.py', ['async_setup'], {
            'HomeAssistant': object, 'DOMAIN':'weasley_clock', 'MappingProxyType':MappingProxyType,
            'async_setup_graphics':lambda hass:None,
            'ConfigSubentry':subentry_factory,
            'dr':SimpleNamespace(async_get=lambda h:devices, async_entries_for_config_entry=lambda r, i: [device] if device.config_entry_id==i else []),
            'er':SimpleNamespace(async_get=lambda h:entities, async_entries_for_config_entry=lambda r, i: [entity] if entity.config_entry_id==i else []),
        })
        with self.assertRaises(RuntimeError): await ns['async_setup'](hass, {})
        manager.fail_remove = False
        await ns['async_setup'](hass, {})
        self.assertEqual(entries, [clock])
        self.assertEqual(clock.title, 'Weasley Clock')
        self.assertEqual(len(clock.subentries), 1)
        self.assertEqual(clock.subentries['person-ron'].data['template'], 'Work')
        self.assertEqual(entity.entity_id, 'sensor.ron_clockhand')
        self.assertEqual(entity.unique_id, 'ron_clockhand')
        self.assertEqual(entity.config_subentry_id, 'person-ron')
        self.assertEqual(device.via_device_id, 'clock-device')
        self.assertEqual(device.area_id, 'living-room')

    async def test_dashboard_resource_added_and_updated_once(self):
        class Resources:
            def __init__(self): self.items=[]
            async def async_get_info(self): pass
            def async_items(self): return self.items
            async def async_create_item(self, item): self.items.append({'id':'card', 'url':item['url'], 'type':item['res_type']})
            async def async_update_item(self, item_id, data): self.items[0].update(url=data['url'], type=data['res_type'])
        resources = Resources()
        hass = SimpleNamespace(data={'weasley_clock':{'static_path_registered':True}, 'lovelace':SimpleNamespace(resources=resources)})
        ns=load('__init__.py',['async_register_frontend'], {
            'DOMAIN':'weasley_clock', 'LOVELACE_DATA':'lovelace', 'ResourceStorageCollection':Resources,
            'CARD_URL':'/weasley_clock/weasley-card.js', 'CARD_RESOURCE':'/weasley_clock/weasley-card.js?v=1.2.0',
        })
        await ns['async_register_frontend'](hass)
        await ns['async_register_frontend'](hass)
        self.assertEqual(len(resources.items), 1)
        resources.items[0]['url']='/weasley_clock/weasley-card.js?v=1.1.0'
        await ns['async_register_frontend'](hass)
        self.assertEqual(resources.items[0]['url'], ns['CARD_RESOURCE'])
        self.assertEqual(resources.items[0]['type'],'module')

    def test_copy_old_graphics_without_overwriting_media(self):
        ns=load('__init__.py',['prepare_images'], {'Path':Path, 'copy2':copy2, 'DOMAIN':'weasley_clock', 'IMAGE_EXTENSIONS':{'.png','.jpg'}})
        with TemporaryDirectory() as directory:
            root=Path(directory); legacy=root/'www'; legacy.mkdir(); media=root/'media'
            (legacy/'ron.png').write_bytes(b'old')
            (legacy/'private.txt').write_text('skip')
            target=Path(ns['prepare_images'](str(media),str(legacy)))
            self.assertEqual((target/'ron.png').read_bytes(), b'old')
            self.assertFalse((target/'private.txt').exists())
            (target/'ron.png').write_bytes(b'uploaded')
            ns['prepare_images'](str(media),str(legacy))
            self.assertEqual((target/'ron.png').read_bytes(),b'uploaded')

    def test_media_path_traversal_is_rejected(self):
        class Unresolvable(Exception): pass
        ns=load('media_source.py',['WeasleyMediaSource'], {'MediaSource':object,'MediaSourceItem':object,'Unresolvable':Unresolvable,'Path':Path,'DOMAIN':'weasley_clock','IMAGE_EXTENSIONS':{'.png'}})
        source=object.__new__(ns['WeasleyMediaSource'])
        with TemporaryDirectory() as directory:
            root=Path(directory); images=root/'images'; images.mkdir()
            (root/'outside.png').write_bytes(b'outside'); (images/'ron.png').write_bytes(b'ron')
            source.hass=SimpleNamespace(data={'weasley_clock':{'image_path':str(images)}})
            self.assertEqual(source._image('ron.png'), (images/'ron.png').resolve())
            with self.assertRaises(Unresolvable): source._image('../outside.png')
            with self.assertRaises(Unresolvable): source._image(str(root/'outside.png'))


if __name__ == '__main__': unittest.main()
