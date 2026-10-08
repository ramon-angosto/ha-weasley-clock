"""Regression checks for validation and sensor updates without an HA install."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'custom_components' / 'weasley_clock'


def load_function(filename, name, namespace):
    tree = ast.parse((ROOT / filename).read_text(encoding='utf-8-sig'))
    nodes = list(tree.body)
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            nodes.extend(node.body)
    function = next(node for node in nodes if isinstance(node, ast.FunctionDef) and node.name == name)
    function.decorator_list = []
    exec(compile(ast.Module(body=[function], type_ignores=[]), filename, 'exec'), namespace)
    return namespace[name]


class RegressionTests(unittest.TestCase):
    def test_hub_location_states_and_stable_ids(self):
        from types import SimpleNamespace
        namespace = {'SensorEntity': object, 'DeviceInfo': dict, 'DOMAIN': 'weasley_clock',
                     'CLOCK_ANGLES': list(range(13))}
        tree = ast.parse((ROOT / 'sensor.py').read_text(encoding='utf-8-sig'))
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'WeasleyLocationSensor')
        exec(compile(ast.Module(body=[cls], type_ignores=[]), 'sensor.py', 'exec'), namespace)
        entry = SimpleNamespace(entry_id='hub', data={f'slot_{i}_name': f'Place {i}' for i in range(1, 14)}, options={})
        sensors = [namespace['WeasleyLocationSensor'](entry, i) for i in range(1, 14)]
        self.assertEqual([s._attr_native_value for s in sensors], [f'Place {i}' for i in range(1, 14)])
        self.assertEqual(len({s._attr_unique_id for s in sensors}), 13)
        entry.options = {'slot_1_name': 'Home'}
        renamed = namespace['WeasleyLocationSensor'](entry, 1)
        self.assertEqual(renamed._attr_native_value, 'Home')
        self.assertEqual(renamed._attr_unique_id, sensors[0]._attr_unique_id)
        self.assertEqual(renamed._attr_device_info['identifiers'], {('weasley_clock', 'hub')})

    def test_slot_names(self):
        validate = load_function('config_flow.py', 'validate_slots', {})
        data = {f'slot_{i}_name': f'Location {i}' for i in range(1, 14)}
        self.assertEqual(validate(data), {})
        data['slot_2_name'] = data['slot_1_name']
        self.assertIn('base', validate(data))
        data['slot_2_name'] = ' '
        self.assertIn('base', validate(data))

    def test_template_error_unknown_and_recovery(self):
        class TemplateError(Exception):
            pass
        callback = load_function('sensor.py', '_async_on_template_update', {'TemplateError': TemplateError})
        from types import SimpleNamespace
        writes = []
        sensor = SimpleNamespace(_mapping={'Home': 0, 'Work': 27.69}, _offset=8,
                                 _attr_extra_state_attributes={}, _update_diagnostics=lambda: None, async_write_ha_state=lambda: writes.append(True))
        for result, available, angle in [(' Work ', True, 35.69), ('Other', False, None),
                                          (TemplateError('bad template'), False, None), ('Home', True, 8)]:
            callback(sensor, None, [SimpleNamespace(result=result)])
            self.assertEqual(sensor._attr_available, available)
            self.assertEqual(sensor._attr_extra_state_attributes['angle'], angle)
        self.assertEqual(len(writes), 4)
        self.assertIsNone(sensor._attr_extra_state_attributes['configuration_error'])

    def test_missing_entity_warning_and_recovery(self):
        from types import SimpleNamespace
        update = load_function('sensor.py', '_update_diagnostics', {
            'async_track_state_change_event': lambda *args: lambda: None,
        })
        states = {}
        sensor = SimpleNamespace(
            _template=SimpleNamespace(async_render_to_info=lambda: SimpleNamespace(entities={'person.ron'})),
            hass=SimpleNamespace(states=states), _attr_extra_state_attributes={},
            _remove_diagnostic_listener=lambda: None, async_write_ha_state=lambda: None,
        )
        sensor._update_diagnostics = lambda event=None: update(sensor, event)
        update(sensor)
        self.assertEqual(sensor._attr_extra_state_attributes['missing_entities'], ['person.ron'])
        states['person.ron'] = SimpleNamespace(state='unavailable')
        update(sensor, object())
        self.assertEqual(sensor._attr_extra_state_attributes['missing_entities'], [])
        self.assertEqual(sensor._attr_extra_state_attributes['unavailable_entities'], ['person.ron'])
        states['person.ron'].state = 'home'
        update(sensor, object())
        self.assertIsNone(sensor._attr_extra_state_attributes['configuration_warning'])


if __name__ == '__main__':
    unittest.main()
