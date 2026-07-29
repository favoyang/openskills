import importlib.util
import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "temp_workspace.py"
SPEC = importlib.util.spec_from_file_location("temp_workspace", SCRIPT)
temp_workspace = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(temp_workspace)


class TempWorkspaceTests(unittest.TestCase):
    def test_create_is_private_and_cleanup_removes_only_managed_workspace(self):
        workspace = temp_workspace.create_workspace()
        try:
            marker = workspace / temp_workspace.MARKER
            self.assertEqual(workspace.parent, temp_workspace.workspace_parent())
            self.assertEqual(
                marker.read_text(encoding="utf-8"),
                temp_workspace.MARKER_CONTENT,
            )
            if os.name != "nt":
                self.assertEqual(stat.S_IMODE(workspace.stat().st_mode), 0o700)
                self.assertEqual(stat.S_IMODE(marker.stat().st_mode), 0o600)

            draft = workspace / "article.html"
            draft.write_text("private draft", encoding="utf-8")
            temp_workspace.cleanup_workspace(workspace)
            self.assertFalse(workspace.exists())
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def test_windows_workspace_root_uses_local_app_data(self):
        with tempfile.TemporaryDirectory() as local_app_data:
            parent = temp_workspace.workspace_parent(
                platform_name="nt",
                environ={"LOCALAPPDATA": local_app_data},
            )

            self.assertEqual(parent, Path(local_app_data).resolve() / "Temp")
            self.assertTrue(parent.is_dir())

    def test_cleanup_rejects_unmanaged_temporary_directory(self):
        unmanaged = Path(tempfile.mkdtemp(prefix=temp_workspace.PREFIX))
        try:
            with self.assertRaises(temp_workspace.WorkspaceError):
                temp_workspace.cleanup_workspace(unmanaged)
            self.assertTrue(unmanaged.is_dir())
        finally:
            shutil.rmtree(unmanaged)

    def test_cleanup_rejects_symlink_to_managed_workspace(self):
        workspace = temp_workspace.create_workspace()
        link = Path(tempfile.gettempdir()) / f"{temp_workspace.PREFIX}symlink-test"
        try:
            link.symlink_to(workspace, target_is_directory=True)
            with self.assertRaises(temp_workspace.WorkspaceError):
                temp_workspace.cleanup_workspace(link)
            self.assertTrue(workspace.is_dir())
        finally:
            link.unlink(missing_ok=True)
            shutil.rmtree(workspace, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
