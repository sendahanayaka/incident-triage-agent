import os
import unittest
from pathlib import Path
from unittest.mock import patch

from mcp import Client
from mcp.types import ListRootsResult, Root

from filesystem_mcp import (
    REPO_ROOT,
    WORKSPACE_DIR,
    configured_workspace,
    connect_filesystem,
    filesystem_server_parameters,
)

RELEASE_FILES = ("RELEASE_NOTES.md", "service-config.yaml", "service-manifest.json")


class WorkspaceConfigurationTests(unittest.TestCase):
    def test_rejects_the_parent_directory_as_a_workspace_override(self) -> None:
        with patch.dict(os.environ, {"FILESYSTEM_WORKSPACE": "mock_data"}):
            with self.assertRaisesRegex(ValueError, "must point to"):
                filesystem_server_parameters()

    def test_accepts_the_same_workspace_as_an_absolute_path(self) -> None:
        with patch.dict(os.environ, {"FILESYSTEM_WORKSPACE": str(WORKSPACE_DIR)}):
            self.assertEqual(configured_workspace(), WORKSPACE_DIR)


class FilesystemMcpTests(unittest.IsolatedAsyncioTestCase):
    async def test_discovers_read_only_tools_and_lists_release_files(self) -> None:
        async with connect_filesystem() as filesystem:
            self.assertEqual(
                {tool.name for tool in filesystem.tools},
                {"list_allowed_directories", "list_directory", "read_text_file"},
            )
            for tool in filesystem.tools:
                self.assertTrue(tool.annotations and tool.annotations.read_only_hint)
                self.assertEqual(tool.input_schema["type"], "object")

            result = await filesystem.call_tool("list_directory", {"path": "."})
            self.assertFalse(result.is_error)
            for filename in RELEASE_FILES:
                self.assertIn(filename, result.content[0].text)

    async def test_reads_all_release_files_through_mcp(self) -> None:
        async with connect_filesystem() as filesystem:
            for filename in RELEASE_FILES:
                with self.subTest(filename=filename):
                    result = await filesystem.call_tool("read_text_file", {"path": filename})
                    self.assertFalse(result.is_error, result.content)
                    self.assertEqual(
                        result.content[0].text,
                        (WORKSPACE_DIR / filename).read_bytes().decode("utf-8"),
                    )

    async def test_client_refuses_outside_paths_and_tools_it_does_not_expose(self) -> None:
        async with connect_filesystem() as filesystem:
            with self.assertRaisesRegex(PermissionError, "outside mock_data/workspace"):
                await filesystem.call_tool("read_text_file", {"path": str(REPO_ROOT / "README.md")})
            with self.assertRaisesRegex(PermissionError, "unavailable"):
                await filesystem.call_tool("write_file")

    async def test_official_server_enforces_the_scope_independently_of_the_client(self) -> None:
        # Connect to the same launch configuration without the application wrapper.
        async with Client(filesystem_server_parameters(), read_timeout_seconds=10) as client:
            tools = (await client.list_tools()).tools
            self.assertTrue(tools)
            self.assertTrue(all(tool.annotations and tool.annotations.read_only_hint for tool in tools))
            self.assertNotIn("write_file", {tool.name for tool in tools})
            scope = await client.call_tool("list_allowed_directories")
            self.assertFalse(scope.is_error)
            paths = scope.structured_content["content"].splitlines()[1:]
            self.assertEqual([Path(path) for path in paths], [WORKSPACE_DIR])

            for tool, path in [
                ("read_text_file", REPO_ROOT / "README.md"),
                ("list_directory", WORKSPACE_DIR.parent),
            ]:
                with self.subTest(tool=tool):
                    result = await client.call_tool(tool, {"path": str(path)})
                    self.assertTrue(result.is_error)
                    self.assertIn("Access denied", result.content[0].text)

            allowed = await client.call_tool(
                "read_text_file", {"path": str(WORKSPACE_DIR / "service-manifest.json")}
            )
            self.assertFalse(allowed.is_error)

    async def test_legacy_client_roots_are_confined_to_the_workspace(self) -> None:
        roots_requested = False

        async def list_roots(_context) -> ListRootsResult:
            nonlocal roots_requested
            roots_requested = True
            return ListRootsResult(roots=[Root(uri=REPO_ROOT.as_uri())])

        async with Client(
            filesystem_server_parameters(),
            mode="legacy",
            list_roots_callback=list_roots,
            read_timeout_seconds=10,
        ) as client:
            scope = await client.call_tool("list_allowed_directories")
            self.assertTrue(roots_requested)
            self.assertFalse(scope.is_error)
            paths = scope.structured_content["content"].splitlines()[1:]
            self.assertEqual([Path(path) for path in paths], [WORKSPACE_DIR])


if __name__ == "__main__":
    unittest.main()
