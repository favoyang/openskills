import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('roles', Path(__file__).parents[1] / 'scripts' / 'resolve_roles.py')
roles = importlib.util.module_from_spec(spec)
spec.loader.exec_module(roles)


class RolesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / 'home'
        self.project = Path(self.temp.name) / 'project'

    def result(self, **kwargs):
        return roles.resolve(self.project, self.home, **kwargs)['roles'][2]

    def profile(self, directory, model='test-review', effort='low', filename='reviewer.toml'):
        directory.mkdir(parents=True, exist_ok=True)
        file = directory / filename
        file.write_text(f'name = "reviewer"\ndescription = "Review"\ndeveloper_instructions = "Review only"\nmodel = "{model}"\nmodel_reasoning_effort = "{effort}"\n')
        return file

    def test_missing_roles_are_optional(self):
        result = self.result()
        self.assertEqual(result['status'], 'missing')
        self.assertEqual(result['subagentOverrides'], {})
        self.assertEqual(result['fallback'], 'inherit parent settings')

    def test_project_replaces_personal_and_explicit_model_does_not_mix_effort(self):
        self.profile(self.home / 'agents')
        project = self.profile(self.project / '.codex/agents', 'project-model', 'medium')
        self.assertEqual(self.result()['taskOverrides'], {'model': 'project-model', 'thinking': 'medium'})
        self.assertEqual(self.result()['source'], str(project.resolve()))
        self.assertEqual(self.result(explicit_model='user-model')['taskOverrides'], {'model': 'user-model'})
        self.assertEqual(self.result(explicit_effort='high')['subagentOverrides'], {'model': 'project-model', 'reasoning_effort': 'high'})

    def test_invalid_project_does_not_silently_use_personal(self):
        self.profile(self.home / 'agents')
        file = self.profile(self.project / '.codex/agents')
        file.write_text('model = [broken')
        result = self.result()
        self.assertEqual(result['status'], 'invalid')
        self.assertEqual(result['taskOverrides'], {})
        self.assertEqual(self.result(explicit_model='user-model')['status'], 'configured')

    def test_explicit_effort_replaces_invalid_configured_effort(self):
        self.profile(self.home / 'agents', effort='bad')
        self.assertEqual(self.result()['status'], 'invalid')
        result = self.result(explicit_effort='high')
        self.assertEqual(result['status'], 'configured')
        self.assertEqual(result['subagentOverrides'], {'model': 'test-review', 'reasoning_effort': 'high'})

    def test_malformed_catalog_is_advisory_and_never_crashes(self):
        self.profile(self.home / 'agents')
        for levels in (None, {}, 'bad', [None]):
            with self.subTest(levels=levels):
                (self.home / 'models_cache.json').write_text(json.dumps({'models': [{'slug': 'test-review', 'supported_reasoning_levels': levels}]}))
                result = roles.resolve(self.project, self.home)
                self.assertEqual(result['roles'][2]['status'], 'configured')
                self.assertIsNone(result['catalogSource'])
                self.assertTrue(result['problems'])

    def test_unreadable_or_non_directory_layer_is_not_missing(self):
        directory = self.home / 'agents'
        self.home.mkdir(parents=True)
        directory.write_text('not a directory')
        result = self.result()
        self.assertEqual(result['status'], 'invalid')
        self.assertTrue(result['problems'])
        with patch.object(roles.os, 'scandir', side_effect=PermissionError()):
            found, problems = roles.read_layer(directory)
            self.assertTrue(problems)
            self.assertTrue(found['reviewer']['problems'])

    def test_model_only_omits_effort_for_native_interface(self):
        result = self.result(explicit_model='user-model')
        self.assertEqual(result['subagentOverrides'], {'model': 'user-model'})
        self.assertEqual(result['taskOverrides'], {'model': 'user-model'})
        self.assertIsNone(result['effort'])

    def test_native_name_and_duplicates(self):
        self.profile(self.home / 'agents', filename='custom-name.toml')
        self.assertEqual(self.result()['model'], 'test-review')
        self.profile(self.home / 'agents')
        self.assertEqual(self.result()['status'], 'invalid')

    def test_bad_types_return_diagnostics(self):
        file = self.profile(self.home / 'agents')
        file.write_text('name="reviewer"\nmodel = ["bad"]\n')
        self.assertEqual(self.result()['status'], 'invalid')

    def test_catalog_model_and_effort_fail_visibly(self):
        self.profile(self.home / 'agents')
        catalog = self.home / 'models_cache.json'
        catalog.write_text(json.dumps({'models': [{'slug': 'test-review', 'supported_reasoning_levels': [{'effort': 'medium'}]}]}))
        self.assertEqual(self.result()['status'], 'unavailable')
        self.assertEqual(self.result()['taskOverrides'], {})
        self.assertEqual(self.result(explicit_effort='medium')['status'], 'configured')
        self.assertEqual(self.result(explicit_model='missing-model')['status'], 'unavailable')

    def test_setup_preserves_existing_custom_named_definition(self):
        file = self.profile(self.home / 'agents', filename='custom.toml')
        before = file.read_bytes()
        self.assertFalse(roles.setup('reviewer', 'new-model', 'medium', self.home)['created'])
        self.assertEqual(file.read_bytes(), before)
        self.assertFalse((self.home / 'agents/reviewer.toml').exists())

    def test_setup_roundtrip_and_idempotence(self):
        self.assertTrue(roles.setup('reviewer', 'test-review', 'low', self.home)['created'])
        self.assertEqual(self.result()['model'], 'test-review')
        self.assertFalse(roles.setup('reviewer', 'replacement', 'medium', self.home)['created'])


if __name__ == '__main__':
    unittest.main()
