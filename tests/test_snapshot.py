"""Regression checks for real image composition and snapshot file boundaries."""
import ast
import asyncio
import math
from types import SimpleNamespace
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]/'custom_components'/'weasley_clock'
spec=importlib.util.spec_from_file_location('weasley_renderer',ROOT/'render.py')
render=importlib.util.module_from_spec(spec);spec.loader.exec_module(render)


class SnapshotTests(unittest.TestCase):
    def test_clockwise_rotation_and_transparency(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            Image.new('RGBA',(100,100),'white').save(root/'face.png')
            hand=Image.new('RGBA',(100,100),(0,0,0,0))
            for x in range(48,53):
                for y in range(10,51): hand.putpixel((x,y),(255,0,0,255))
            hand.save(root/'hand.png')
            size=render.render_snapshot(root/'face.png',[{'path':root/'hand.png','angle':90}],root/'snapshot.png')
            self.assertEqual(size,(100,100))
            with Image.open(root/'snapshot.png') as result:
                self.assertEqual(result.getpixel((80,50)),(255,0,0,255))
                self.assertEqual(result.getpixel((50,20)),(255,255,255,255))
                self.assertEqual(result.getpixel((10,10)),(255,255,255,255))

    def test_offsets_size_and_layer_order(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            Image.new('RGBA',(100,100),'white').save(root/'face.png')
            Image.new('RGBA',(100,100),'red').save(root/'red.png')
            Image.new('RGBA',(100,100),'blue').save(root/'blue.png')
            hands=[{'path':root/'red.png','angle':0,'width':'50%','left':'25%','top':'25%'},
                   {'path':root/'blue.png','angle':0,'width':'10%','left':'45%','top':'45%'}]
            render.render_snapshot(root/'face.png',hands,root/'snapshot.png',200)
            with Image.open(root/'snapshot.png') as result:
                self.assertEqual(result.size,(200,200))
                self.assertEqual(result.getpixel((60,60)),(255,0,0,255))
                self.assertEqual(result.getpixel((100,100)),(0,0,255,255))
                self.assertEqual(result.getpixel((10,10)),(255,255,255,255))

    def test_local_paths_and_traversal(self):
        with TemporaryDirectory() as directory:
            root=Path(directory); media=root/'media';media.mkdir();www=root/'www';www.mkdir()
            Image.new('RGB',(2,2)).save(media/'face.png')
            Image.new('RGB',(2,2)).save(www/'legacy.png')
            self.assertEqual(render.resolve_image('media-source://weasley_clock/face.png',media,www),(media/'face.png').resolve())
            self.assertEqual(render.resolve_image('/local/legacy.png',media,www),(www/'legacy.png').resolve())
            for value in ['../www/legacy.png','https://example.com/image.png','/etc/file.png','/local/../media/face.png']:
                with self.assertRaises(ValueError):render.resolve_image(value,media,www)

    def test_discovery_ignores_snapshots_and_ambiguous_faces(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            for name in ['a.png','b.png','manecilla_ron.png',render.SNAPSHOT_FILENAME]:
                Image.new('RGB',(2,2)).save(root/name)
            self.assertIsNone(render.discover_face(root))
            Image.new('RGB',(2,2)).save(root/'reloj_weasley.jpg')
            self.assertEqual(render.discover_face(root),'reloj_weasley.jpg')
            self.assertEqual(render.find_image(root,['manecilla_ron']),'manecilla_ron.png')


class SnapshotActionTests(unittest.IsolatedAsyncioTestCase):
    async def test_action_freezes_angles_and_reports_unavailable_hands(self):
        tree=ast.parse((ROOT/'graphics.py').read_text(encoding='utf-8-sig'))
        functions=[node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in ('create_snapshot','async_snapshot')]
        class HomeAssistantError(Exception):pass
        namespace={'math':math,'quote':__import__('urllib.parse',fromlist=['quote']).quote,
                   'DOMAIN':'weasley_clock','HomeAssistantError':HomeAssistantError,
                   'resolve_image':render.resolve_image,'render_snapshot':render.render_snapshot}
        exec(compile(ast.Module(body=functions,type_ignores=[]),'graphics.py','exec'),namespace)
        with TemporaryDirectory() as directory:
            root=Path(directory)
            Image.new('RGB',(100,100),'white').save(root/'face.png')
            image=Image.new('RGBA',(100,100),(0,0,0,0))
            for x in range(48,53):
                for y in range(10,51):image.putpixel((x,y),(255,0,0,255))
            image.save(root/'ron.png')
            layout={'image':'face.png','hands':[{'entity':'sensor.ron','image':'ron.png'}, {'entity':'sensor.ginny','image':'ron.png'}]}
            async def get_layout(hass):return layout
            namespace['async_layout']=get_layout
            state=SimpleNamespace(state='Home',attributes={'angle':90})
            states={'sensor.ron':state,'sensor.ginny':SimpleNamespace(state='unavailable',attributes={'angle':180})}
            async def executor(function,*args):
                # A new state arrives after angles have been captured.
                state.attributes['angle']=180
                return function(*args)
            hass=SimpleNamespace(data={'weasley_clock':{'image_path':str(root),'snapshot_lock':asyncio.Lock()}},
                                 states=states,async_add_executor_job=executor,
                                 config=SimpleNamespace(path=lambda *args:str(root)))
            call=SimpleNamespace(data={'filename':render.SNAPSHOT_FILENAME},return_response=True)
            result=await namespace['async_snapshot'](hass,call)
            self.assertEqual(result['skipped_entities'],['sensor.ginny'])
            self.assertEqual(result['media_content_id'],'media-source://weasley_clock/'+render.SNAPSHOT_FILENAME)
            self.assertTrue(Path(result['filename']).is_file())
            with Image.open(result['filename']) as capture:self.assertEqual(capture.getpixel((80,50)),(255,0,0,255))
            with self.assertRaises(ValueError):namespace['create_snapshot'](root,root,'face.png',[],'face.png',None)


if __name__=='__main__':unittest.main()
