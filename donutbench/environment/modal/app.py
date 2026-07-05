"""Deploy environment/Dockerfile to Modal and run it as a Harbor-style trial.

Harbor (https://harborframework.com) runs a task's environment/Dockerfile in a
container that exposes /solution, /tests, and /logs/verifier/reward.txt. This
script reproduces that contract on a Modal Sandbox so the task can be built and
exercised without a local Docker daemon: Image.from_dockerfile() builds the
image on Modal's remote builders instead of a local one.
"""

from dataclasses import dataclass
from pathlib import Path
import tarfile
import tempfile

import modal
from modal.exception import SandboxFilesystemNotFoundError

MODAL_IMAGE_DIR = Path(__file__).parent
ENVIRONMENT_DIR = MODAL_IMAGE_DIR.parent
TASK_DIR = ENVIRONMENT_DIR.parent
DOCKERFILE_PATH = ENVIRONMENT_DIR / "Dockerfile"

HARBOR_SOLUTION_DIR = "/solution"
HARBOR_TESTS_DIR = "/tests"
HARBOR_LOGS_DIR = "/logs"
HARBOR_OUTPUTS_DIR = "/outputs"
HARBOR_REWARD_PATH = f"{HARBOR_LOGS_DIR}/verifier/reward.txt"
HARBOR_WRITABLE_DIRS = (
    f"{HARBOR_LOGS_DIR}/agent",
    f"{HARBOR_LOGS_DIR}/verifier",
    f"{HARBOR_LOGS_DIR}/artifacts",
    HARBOR_OUTPUTS_DIR,
)

app = modal.App("rosettacommons-foundry")
image = modal.Image.from_dockerfile(
    DOCKERFILE_PATH, context_dir=ENVIRONMENT_DIR)


@dataclass(frozen=True)
class TrialConfig:
    gpu_type: str | None
    sandbox_timeout_seconds: int
    download_dir: Path


@dataclass(frozen=True)
class TrialResult:
    solve_exit_code: int
    test_exit_code: int
    reward: str | None


@app.local_entrypoint()
def main(
    gpu_type: str = "L40S",
    sandbox_timeout_minutes: int = 5,
    download_dir: str = "trial_output",
) -> None:
    config = TrialConfig(
        gpu_type=gpu_type or None,
        sandbox_timeout_seconds=sandbox_timeout_minutes * 60,
        download_dir=Path(download_dir),
    )
    sandbox = create_sandbox(config)
    try:
        prepare_harbor_directories(sandbox)
        stage_task_files(sandbox)
        result = run_trial(sandbox)
        download_trial_outputs(sandbox, config.download_dir)
        report_trial_result(result)
    finally:
        sandbox.terminate()


def create_sandbox(config: TrialConfig) -> modal.Sandbox:
    return modal.Sandbox.create(
        "sh", "-c", "sleep infinity",
        app=app,
        image=image,
        gpu=config.gpu_type,
        timeout=config.sandbox_timeout_seconds,
    )


def prepare_harbor_directories(sandbox: modal.Sandbox) -> None:
    directories = " ".join(HARBOR_WRITABLE_DIRS)
    execute_command(
        sandbox, f"mkdir -p {directories} && chmod -R 777 {HARBOR_LOGS_DIR} {HARBOR_OUTPUTS_DIR}"
    )


def stage_task_files(sandbox: modal.Sandbox) -> None:
    upload_directory(sandbox, TASK_DIR / "solution", HARBOR_SOLUTION_DIR)
    upload_directory(sandbox, TASK_DIR / "tests", HARBOR_TESTS_DIR)


def run_trial(sandbox: modal.Sandbox) -> TrialResult:
    solve_exit_code = execute_command(
        sandbox, f"bash {HARBOR_SOLUTION_DIR}/solve.sh")
    test_exit_code = execute_command(
        sandbox, f"bash {HARBOR_TESTS_DIR}/test.sh")
    reward = read_remote_file_if_present(sandbox, HARBOR_REWARD_PATH)
    return TrialResult(solve_exit_code, test_exit_code, reward)


def download_trial_outputs(sandbox: modal.Sandbox, download_dir: Path) -> None:
    download_directory(sandbox, HARBOR_LOGS_DIR, download_dir / "logs")
    download_directory(sandbox, HARBOR_OUTPUTS_DIR, download_dir / "outputs")


def report_trial_result(result: TrialResult) -> None:
    print(f"solve.sh exit code: {result.solve_exit_code}")
    print(f"test.sh exit code: {result.test_exit_code}")
    print(f"reward: {result.reward!r}")


def execute_command(sandbox: modal.Sandbox, command: str) -> int:
    process = sandbox.exec("bash", "-c", command)
    for line in process.stdout:
        print(line, end="")
    for line in process.stderr:
        print(line, end="")
    return process.wait()


def read_remote_file_if_present(sandbox: modal.Sandbox, remote_path: str) -> str | None:
    try:
        return sandbox.filesystem.read_text(remote_path).strip()
    except SandboxFilesystemNotFoundError:
        return None


def upload_directory(sandbox: modal.Sandbox, source_dir: Path, remote_dir: str) -> None:
    with tempfile.TemporaryDirectory() as scratch_dir:
        archive_path = Path(scratch_dir) / "upload.tar.gz"
        with tarfile.open(archive_path, "w:gz") as archive:
            archive.add(source_dir, arcname=".")
        remote_archive_path = f"/tmp/{archive_path.name}"
        sandbox.filesystem.copy_from_local(archive_path, remote_archive_path)
    execute_command(
        sandbox, f"mkdir -p {remote_dir} && tar xzf {remote_archive_path} -C {remote_dir}")


def download_directory(sandbox: modal.Sandbox, remote_dir: str, target_dir: Path) -> None:
    remote_archive_path = f"/tmp/{target_dir.name}.tar.gz"
    execute_command(
        sandbox, f"tar czf {remote_archive_path} -C {remote_dir} .")
    target_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as scratch_dir:
        archive_path = Path(scratch_dir) / "download.tar.gz"
        sandbox.filesystem.copy_to_local(remote_archive_path, archive_path)
        with tarfile.open(archive_path) as archive:
            archive.extractall(target_dir)
