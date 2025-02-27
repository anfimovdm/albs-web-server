import pytest

from alws.constants import BuildTaskStatus
from alws.models import Build
from alws.utils.modularity import IndexWrapper
from tests.constants import CUSTOM_USER_ID
from tests.mock_classes import BaseAsyncTestCase


class TestBuildsEndpoints(BaseAsyncTestCase):
    @pytest.mark.parametrize("task_ids", [[1, 2, 3], []])
    async def test_ping(self, task_ids):
        response = await self.make_request(
            "post",
            "/api/v1/build_node/ping",
            json={"active_tasks": task_ids},
        )
        message = f"Cannot ping tasks:\n{response.text}"
        assert response.status_code == self.status_codes.HTTP_200_OK, message

    async def test_mark_build_as_cancelled(
        self,
        regular_build: Build,
        start_build,
    ):
        response = await self.make_request(
            "patch",
            f"/api/v1/builds/{regular_build.id}/cancel",
        )
        message = f"Cannot cancel build:\n{response.text}"
        assert response.status_code == self.status_codes.HTTP_200_OK, message
        response = await self.make_request(
            "get",
            f"/api/v1/builds/{regular_build.id}/",
        )
        build = response.json()
        cancelled_tasks = [
            task
            for task in build["tasks"]
            if task["status"] == BuildTaskStatus.CANCELLED
            and task["error"] == "Build task cancelled by user"
        ]
        message = "Build doesn't contain cancelled tasks"
        assert cancelled_tasks, message

    async def test_create_modular_build(
        self,
        modular_build_payload,
    ):
        response = await self.make_request(
            "post",
            "/api/v1/builds/",
            json=modular_build_payload,
        )
        message = f"Cannot create modular build:\n{response.text}"
        assert response.status_code == self.status_codes.HTTP_200_OK, message

    async def test_create_modular_build_with_wrong_payload(
        self,
        nonvalid_modular_build_payload,
    ):
        response = await self.make_request(
            "post",
            "/api/v1/builds/",
            json=nonvalid_modular_build_payload,
        )
        assert response.status_code == self.status_codes.HTTP_400_BAD_REQUEST

    async def test_build_create_without_permissions(
        self,
        modular_build_payload,
    ):
        old_token = self.headers.pop("Authorization", None)
        token = BaseAsyncTestCase.generate_jwt_token(str(CUSTOM_USER_ID))
        response = await self.make_request(
            "post",
            "/api/v1/builds/",
            json=modular_build_payload,
            headers={
                "Authorization": f"Bearer {token}",
            },
        )
        assert response.status_code == self.status_codes.HTTP_403_FORBIDDEN
        self.headers["Authorization"] = old_token

    async def test_build_delete(
        self,
        create_errata,
        build_done,
        build_for_release,
        delete_by_href,
    ):
        response = await self.make_request(
            "delete",
            f"/api/v1/builds/{build_for_release.id}/remove",
        )
        assert response.status_code == self.status_codes.HTTP_204_NO_CONTENT


@pytest.mark.usefixtures(
    "get_multilib_packages_from_pulp",
    "enable_beholder",
    "mock_beholder_call",
)
class TestModularBuilds(BaseAsyncTestCase):
    async def test_multilib_virt(
        self,
        multilib_virt_with_artifacts: str,
        modules_artifacts: dict,
        virt_modular_build: Build,
        virt_build_done,
        tmp_path,
    ):
        index_with_artifacts = IndexWrapper.from_template(
            multilib_virt_with_artifacts,
        )

        module_file = tmp_path / "modules.x86_64.yaml"
        build_index = IndexWrapper.from_template(module_file.read_text())
        for build_module in build_index.iter_modules():
            module = index_with_artifacts.get_module(
                build_module.name,
                build_module.stream,
            )
            assert (
                build_module.get_rpm_artifacts() == module.get_rpm_artifacts()
            )

        for arch in ["i686", "ppc64le"]:
            module_file = tmp_path / f"modules.{arch}.yaml"
            build_index = IndexWrapper.from_template(module_file.read_text())
            for build_module in build_index.iter_modules():
                artifacts = modules_artifacts[f"{build_module.name}:{arch}"]
                assert build_module.get_rpm_artifacts() == artifacts

    async def test_multilib_ruby(
        self,
        multilib_ruby_with_artifacts: str,
        modules_artifacts: dict,
        ruby_modular_build: Build,
        ruby_build_done,
        tmp_path,
    ):
        index_with_artifacts = IndexWrapper.from_template(
            multilib_ruby_with_artifacts,
        )
        module_file = tmp_path / "modules.x86_64.yaml"
        build_index = IndexWrapper.from_template(module_file.read_text())
        for build_module in build_index.iter_modules():
            module = index_with_artifacts.get_module(
                build_module.name,
                build_module.stream,
            )
            assert (
                build_module.get_rpm_artifacts() == module.get_rpm_artifacts()
            )
        for arch in ["i686", "aarch64"]:
            module_file = tmp_path / f"modules.{arch}.yaml"
            build_index = IndexWrapper.from_template(module_file.read_text())
            for build_module in build_index.iter_modules():
                artifacts = modules_artifacts[f"{build_module.name}:{arch}"]
                assert build_module.get_rpm_artifacts() == artifacts

    async def test_multilib_subversion(
        self,
        multilib_subversion_with_artifacts: str,
        modules_artifacts: dict,
        subversion_modular_build: Build,
        subversion_build_done,
        tmp_path,
    ):
        index_with_artifacts = IndexWrapper.from_template(
            multilib_subversion_with_artifacts,
        )
        module_file = tmp_path / "modules.x86_64.yaml"
        build_index = IndexWrapper.from_template(module_file.read_text())
        for build_module in build_index.iter_modules():
            module = index_with_artifacts.get_module(
                build_module.name,
                build_module.stream,
            )
            assert (
                build_module.get_rpm_artifacts() == module.get_rpm_artifacts()
            )
        for arch in ["i686", "aarch64"]:
            module_file = tmp_path / f"modules.{arch}.yaml"
            build_index = IndexWrapper.from_template(module_file.read_text())
            for build_module in build_index.iter_modules():
                artifacts = modules_artifacts[f"{build_module.name}:{arch}"]
                assert build_module.get_rpm_artifacts() == artifacts

    async def test_multilib_llvm(
        self,
        multilib_llvm_with_artifacts: str,
        modules_artifacts: dict,
        llvm_modular_build: Build,
        llvm_build_done,
        tmp_path,
    ):
        index_with_artifacts = IndexWrapper.from_template(
            multilib_llvm_with_artifacts,
        )
        module_file = tmp_path / "modules.x86_64.yaml"
        build_index = IndexWrapper.from_template(module_file.read_text())
        for build_module in build_index.iter_modules():
            module = index_with_artifacts.get_module(
                build_module.name,
                build_module.stream,
            )
            assert (
                build_module.get_rpm_artifacts() == module.get_rpm_artifacts()
            )
        module_file = tmp_path / "modules.i686.yaml"
        build_index = IndexWrapper.from_template(module_file.read_text())
        for build_module in build_index.iter_modules():
            artifacts = modules_artifacts[f"{build_module.name}:i686"]
            assert build_module.get_rpm_artifacts() == artifacts
