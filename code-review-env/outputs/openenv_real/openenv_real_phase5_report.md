# GraphReview Report

## Executive Summary
- Source root: /home/lightdesk/Downloads/Projects/NodeAudit/OpenEnv/src
- Episode id: all
- Modules in scope: 202
- Confidence score: 0.100
- Precision: 0.000 | Recall: 0.000 | F1: 0.000
- Security coverage: 0.000 | Dependency attribution validity: 0.000

## Security Analysis
### openenv.auto.auto_env
- [LOW] B404 line 37: Consider possible security implications associated with the subprocess module.
- [LOW] B603 line 322: subprocess call - check for execution of untrusted input.
- [LOW] B110 line 442: Try, Except, Pass detected.

### openenv.cli.commands.build
- [LOW] B404 line 12: Consider possible security implications associated with the subprocess module.
- [LOW] B603 line 213: subprocess call - check for execution of untrusted input.

### openenv.cli.commands.init
- [LOW] B404 line 7: Consider possible security implications associated with the subprocess module.
- [LOW] B311 line 207: Standard pseudo-random generators are not suitable for security/cryptographic purposes.
- [LOW] B311 line 208: Standard pseudo-random generators are not suitable for security/cryptographic purposes.
- [LOW] B311 line 209: Standard pseudo-random generators are not suitable for security/cryptographic purposes.
- [LOW] B603 line 377: subprocess call - check for execution of untrusted input.
- [LOW] B110 line 496: Try, Except, Pass detected.

### openenv.cli.commands.serve
- [MEDIUM] B104 line 36: Possible binding to all interfaces.

### openenv.cli.templates.openenv_env.server.app
- [MEDIUM] B104 line 56: Possible binding to all interfaces.

### openenv.core.containers.runtime.providers
- [LOW] B404 line 112: Consider possible security implications associated with the subprocess module.
- [LOW] B603 line 115: subprocess call - check for execution of untrusted input.
- [LOW] B607 line 115: Starting a process with a partial executable path
- [LOW] B404 line 149: Consider possible security implications associated with the subprocess module.
- [LOW] B603 line 180: subprocess call - check for execution of untrusted input.
- [LOW] B404 line 199: Consider possible security implications associated with the subprocess module.
- [LOW] B603 line 203: subprocess call - check for execution of untrusted input.
- [LOW] B607 line 203: Starting a process with a partial executable path
- [LOW] B603 line 211: subprocess call - check for execution of untrusted input.
- [LOW] B607 line 211: Starting a process with a partial executable path
- [LOW] B404 line 346: Consider possible security implications associated with the subprocess module.
- [LOW] B603 line 417: subprocess call - check for execution of untrusted input.
- [LOW] B404 line 446: Consider possible security implications associated with the subprocess module.
- [LOW] B603 line 449: subprocess call - check for execution of untrusted input.
- [LOW] B607 line 449: Starting a process with a partial executable path
- [LOW] B404 line 496: Consider possible security implications associated with the subprocess module.
- [LOW] B603 line 499: subprocess call - check for execution of untrusted input.
- [LOW] B607 line 499: Starting a process with a partial executable path
- [LOW] B404 line 515: Consider possible security implications associated with the subprocess module.
- [LOW] B603 line 518: subprocess call - check for execution of untrusted input.
- [LOW] B607 line 518: Starting a process with a partial executable path
- [LOW] B603 line 537: subprocess call - check for execution of untrusted input.
- [LOW] B607 line 537: Starting a process with a partial executable path
- [LOW] B404 line 547: Consider possible security implications associated with the subprocess module.
- [LOW] B603 line 549: subprocess call - check for execution of untrusted input.
- [LOW] B607 line 549: Starting a process with a partial executable path
- [LOW] B603 line 559: subprocess call - check for execution of untrusted input.
- [LOW] B607 line 559: Starting a process with a partial executable path

### openenv.core.containers.runtime.uv_provider
- [LOW] B404 line 7: Consider possible security implications associated with the subprocess module.
- [LOW] B603 line 18: subprocess call - check for execution of untrusted input.
- [LOW] B607 line 18: Starting a process with a partial executable path
- [MEDIUM] B104 line 106: Possible binding to all interfaces.
- [LOW] B603 line 165: subprocess call - check for execution of untrusted input.
- [MEDIUM] B104 line 169: Possible binding to all interfaces.

### openenv.core.containers.test_local_docker_provider
- [MEDIUM] B113 line 54: Call to requests without timeout
- [LOW] B101 line 57: Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.
- [LOW] B101 line 58: Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.
- [MEDIUM] B113 line 63: Call to requests without timeout
- [LOW] B101 line 73: Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.
- [LOW] B101 line 74: Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.
- [MEDIUM] B113 line 79: Call to requests without timeout
- [LOW] B101 line 89: Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.
- [LOW] B101 line 90: Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.
- [LOW] B101 line 93: Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.
- [MEDIUM] B113 line 98: Call to requests without timeout
- [LOW] B101 line 103: Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.
- [LOW] B101 line 104: Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.
- [MEDIUM] B113 line 110: Call to requests without timeout
- [LOW] B101 line 115: Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.
- [MEDIUM] B113 line 119: Call to requests without timeout
- [LOW] B101 line 121: Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.
- [LOW] B101 line 165: Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.
- [MEDIUM] B113 line 172: Call to requests without timeout
- [LOW] B101 line 173: Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.
- [MEDIUM] B113 line 212: Call to requests without timeout
- [LOW] B101 line 213: Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.

### openenv.core.env_client
- [LOW] B110 line 199: Try, Except, Pass detected.
- [LOW] B110 line 203: Try, Except, Pass detected.
- [LOW] B101 line 215: Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.
- [LOW] B101 line 220: Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.

### openenv.core.env_server.http_server
- [LOW] B110 line 402: Try, Except, Pass detected.
- [LOW] B110 line 416: Try, Except, Pass detected.
- [LOW] B110 line 421: Try, Except, Pass detected.

### openenv.core.env_server.mcp_environment
- [MEDIUM] B102 line 279: Use of exec detected.

### openenv.core.env_server.web_interface
- [LOW] B110 line 183: Try, Except, Pass detected.
- [LOW] B110 line 191: Try, Except, Pass detected.
- [LOW] B110 line 200: Try, Except, Pass detected.

### openenv.core.mcp_client
- [LOW] B110 line 227: Try, Except, Pass detected.
- [LOW] B110 line 325: Try, Except, Pass detected.
- [LOW] B110 line 334: Try, Except, Pass detected.

### openenv.core.sync_client
- [LOW] B101 line 123: Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.
- [LOW] B110 line 227: Try, Except, Pass detected.

### openenv.core.tools.git_server_client
- [LOW] B404 line 13: Consider possible security implications associated with the subprocess module.
- [LOW] B603 line 123: subprocess call - check for execution of untrusted input.
- [LOW] B607 line 123: Starting a process with a partial executable path
- [LOW] B110 line 133: Try, Except, Pass detected.
- [LOW] B603 line 150: subprocess call - check for execution of untrusted input.
- [LOW] B607 line 150: Starting a process with a partial executable path
- [LOW] B603 line 211: subprocess call - check for execution of untrusted input.
- [LOW] B607 line 211: Starting a process with a partial executable path
- [LOW] B603 line 222: subprocess call - check for execution of untrusted input.
- [LOW] B607 line 222: Starting a process with a partial executable path
- [LOW] B603 line 259: subprocess call - check for execution of untrusted input.
- [LOW] B607 line 259: Starting a process with a partial executable path
- [LOW] B603 line 266: subprocess call - check for execution of untrusted input.
- [LOW] B607 line 266: Starting a process with a partial executable path
- [LOW] B603 line 276: subprocess call - check for execution of untrusted input.
- [LOW] B607 line 276: Starting a process with a partial executable path
- [LOW] B603 line 290: subprocess call - check for execution of untrusted input.
- [LOW] B607 line 290: Starting a process with a partial executable path
- [LOW] B603 line 300: subprocess call - check for execution of untrusted input.
- [LOW] B607 line 300: Starting a process with a partial executable path
- [LOW] B603 line 331: subprocess call - check for execution of untrusted input.
- [LOW] B603 line 355: subprocess call - check for execution of untrusted input.
- [LOW] B607 line 355: Starting a process with a partial executable path

## Cascade Attribution Summary
## Module Reviews
### __init__
- Status: pending
- Summary: exports: [] | issues: 0 | depends_on: []
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 0
- Reviews: 0

### openenv.__init__
- Status: pending
- Summary: exports: [_load_package_version()->str, __getattr__(name: str)->None, __dir__()->list[str]] | issues: 5 | depends_on: [__future__, __future__.annotations, importlib, importlib.import_module, importlib.metadata]
- Shape: functions=_load_package_version, __getattr__, __dir__
- Findings: 5
- Reviews: 0

### openenv.auto.__init__
- Status: pending
- Summary: exports: [] | issues: 0 | depends_on: [openenv.auto.auto_action, openenv.auto.auto_action.AutoAction, openenv.auto.auto_env, openenv.auto.auto_env.AutoEnv]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 0
- Reviews: 0

### openenv.auto._discovery
- Status: pending
- Summary: exports: [get_client_class(self)->Type, get_action_class(self)->Type, get_observation_class(self)->Type, _normalize_env_name(name: str)->str, _is_hub_url(name: str)->bool] | issues: 22 | depends_on: [dataclasses, dataclasses.asdict, dataclasses.dataclass, importlib, importlib.metadata]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 22
- Reviews: 0

### openenv.auto._discovery::EnvironmentDiscovery
- Status: pending
- Summary: Chunk EnvironmentDiscovery lines 341-553
- Shape: classes=EnvironmentDiscovery
- Findings: 0
- Reviews: 0

### openenv.auto._discovery::EnvironmentInfo
- Status: pending
- Summary: Chunk EnvironmentInfo lines 37-139
- Shape: classes=EnvironmentInfo
- Findings: 0
- Reviews: 0

### openenv.auto._discovery::_create_env_info_from_package
- Status: pending
- Summary: Chunk _create_env_info_from_package lines 260-338
- Shape: functions=_create_env_info_from_package
- Findings: 0
- Reviews: 0

### openenv.auto._discovery::_infer_class_name
- Status: pending
- Summary: Chunk _infer_class_name lines 192-223
- Shape: functions=_infer_class_name
- Findings: 0
- Reviews: 0

### openenv.auto._discovery::_is_hub_url
- Status: pending
- Summary: Chunk _is_hub_url lines 170-189
- Shape: functions=_is_hub_url
- Findings: 0
- Reviews: 0

### openenv.auto._discovery::_load_manifest_from_package
- Status: pending
- Summary: Chunk _load_manifest_from_package lines 226-257
- Shape: functions=_load_manifest_from_package
- Findings: 0
- Reviews: 0

### openenv.auto._discovery::_normalize_env_name
- Status: pending
- Summary: Chunk _normalize_env_name lines 142-167
- Shape: functions=_normalize_env_name
- Findings: 0
- Reviews: 0

### openenv.auto._discovery::get_discovery
- Status: pending
- Summary: Chunk get_discovery lines 560-576
- Shape: functions=get_discovery
- Findings: 0
- Reviews: 0

### openenv.auto._discovery::reset_discovery
- Status: pending
- Summary: Chunk reset_discovery lines 579-584
- Shape: functions=reset_discovery
- Findings: 0
- Reviews: 0

### openenv.auto.auto_action
- Status: pending
- Summary: exports: [__init__(self)->None, from_env(cls, name: str, skip_install: bool)->Type, from_hub(cls, env_name: str, skip_install: bool)->Type, get_action_info(cls, name: str)->Dict[str, Any], list_actions(cls)->None] | issues: 8 | depends_on: [__future__, __future__.annotations, difflib, difflib.get_close_matches, logging]
- Shape: classes=AutoAction
- Findings: 8
- Reviews: 0

### openenv.auto.auto_env
- Status: pending
- Summary: exports: [_has_uv()->bool, _get_pip_command()->list[str], _confirm_remote_install(repo_id: str)->bool, __init__(self)->None, _resolve_space_url(cls, repo_id: str)->str] | issues: 56 | depends_on: [__future__, __future__.annotations, difflib, difflib.get_close_matches, importlib]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 56
- Reviews: 0

### openenv.auto.auto_env::AutoEnv
- Status: pending
- Summary: Chunk AutoEnv lines 120-897
- Shape: classes=AutoEnv
- Findings: 0
- Reviews: 0

### openenv.auto.auto_env::_confirm_remote_install
- Status: pending
- Summary: Chunk _confirm_remote_install lines 77-117
- Shape: functions=_confirm_remote_install
- Findings: 0
- Reviews: 0

### openenv.auto.auto_env::_get_pip_command
- Status: pending
- Summary: Chunk _get_pip_command lines 65-74
- Shape: functions=_get_pip_command
- Findings: 0
- Reviews: 0

### openenv.auto.auto_env::_has_uv
- Status: pending
- Summary: Chunk _has_uv lines 60-62
- Shape: functions=_has_uv
- Findings: 0
- Reviews: 0

### openenv.cli.__init__
- Status: pending
- Summary: exports: [] | issues: 0 | depends_on: []
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 0
- Reviews: 0

### openenv.cli.__main__
- Status: pending
- Summary: exports: [main()->None] | issues: 4 | depends_on: [openenv.cli.commands, openenv.cli.commands.build, openenv.cli.commands.fork, openenv.cli.commands.init, openenv.cli.commands.push]
- Shape: functions=main
- Findings: 4
- Reviews: 0

### openenv.cli._cli_utils
- Status: pending
- Summary: exports: [validate_env_structure(env_dir: Path, strict: bool)->List[str]] | issues: 1 | depends_on: [pathlib, pathlib.Path, rich.console, rich.console.Console, typing]
- Shape: functions=validate_env_structure
- Findings: 1
- Reviews: 0

### openenv.cli._validation
- Status: pending
- Summary: exports: [_make_criterion(criterion_id: str, description: str, passed: bool)->dict[str, Any], _normalize_runtime_url(base_url: str)->str, _runtime_standard_profile(api_version: str)->str, _build_summary(criteria: list[dict[str, Any]])->dict[str, Any], validate_running_environment(base_url: str, timeout_s: float)->dict[str, Any]] | issues: 5 | depends_on: [pathlib, pathlib.Path, requests, tomli, tomllib]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 5
- Reviews: 0

### openenv.cli._validation::_build_summary
- Status: pending
- Summary: Chunk _build_summary lines 75-98
- Shape: functions=_build_summary
- Findings: 0
- Reviews: 0

### openenv.cli._validation::_make_criterion
- Status: pending
- Summary: Chunk _make_criterion lines 26-49
- Shape: functions=_make_criterion
- Findings: 0
- Reviews: 0

### openenv.cli._validation::_normalize_runtime_url
- Status: pending
- Summary: Chunk _normalize_runtime_url lines 52-65
- Shape: functions=_normalize_runtime_url
- Findings: 0
- Reviews: 0

### openenv.cli._validation::_runtime_standard_profile
- Status: pending
- Summary: Chunk _runtime_standard_profile lines 68-72
- Shape: functions=_runtime_standard_profile
- Findings: 0
- Reviews: 0

### openenv.cli._validation::build_local_validation_json_report
- Status: pending
- Summary: Chunk build_local_validation_json_report lines 554-594
- Shape: functions=build_local_validation_json_report
- Findings: 0
- Reviews: 0

### openenv.cli._validation::format_validation_report
- Status: pending
- Summary: Chunk format_validation_report lines 536-551
- Shape: functions=format_validation_report
- Findings: 0
- Reviews: 0

### openenv.cli._validation::get_deployment_modes
- Status: pending
- Summary: Chunk get_deployment_modes lines 507-533
- Shape: functions=get_deployment_modes
- Findings: 0
- Reviews: 0

### openenv.cli._validation::validate_multi_mode_deployment
- Status: pending
- Summary: Chunk validate_multi_mode_deployment lines 429-504
- Shape: functions=validate_multi_mode_deployment
- Findings: 0
- Reviews: 0

### openenv.cli._validation::validate_running_environment
- Status: pending
- Summary: Chunk validate_running_environment lines 101-426
- Shape: functions=validate_running_environment
- Findings: 0
- Reviews: 0

### openenv.cli.commands.__init__
- Status: pending
- Summary: exports: [] | issues: 0 | depends_on: [openenv.cli.commands, openenv.cli.commands.build, openenv.cli.commands.fork, openenv.cli.commands.init, openenv.cli.commands.push]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 0
- Reviews: 0

### openenv.cli.commands.build
- Status: pending
- Summary: exports: [_detect_build_context(env_path: Path)->tuple[str, Path, Path | None], _prepare_standalone_build(env_path: Path, temp_dir: Path)->Path, _prepare_inrepo_build(env_path: Path, repo_root: Path, temp_dir: Path)->Path, _run_command(cmd: list[str], cwd: Path | None, check: bool)->subprocess.CompletedProcess, _build_docker_image(env_path: Path, tag: str | None, context_path: Path | None, dockerfile: Path | None, build_args: dict[str, str] | None, no_cache: bool)->bool] | issues: 13 | depends_on: [__future__, __future__.annotations, openenv.cli._cli_utils, openenv.cli._cli_utils.console, pathlib]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 13
- Reviews: 0

### openenv.cli.commands.build::_build_docker_image
- Status: pending
- Summary: Chunk _build_docker_image lines 232-306
- Shape: functions=_build_docker_image
- Findings: 0
- Reviews: 0

### openenv.cli.commands.build::_detect_build_context
- Status: pending
- Summary: Chunk _detect_build_context lines 25-67
- Shape: functions=_detect_build_context
- Findings: 0
- Reviews: 0

### openenv.cli.commands.build::_prepare_inrepo_build
- Status: pending
- Summary: Chunk _prepare_inrepo_build lines 117-202
- Shape: functions=_prepare_inrepo_build
- Findings: 0
- Reviews: 0

### openenv.cli.commands.build::_prepare_standalone_build
- Status: pending
- Summary: Chunk _prepare_standalone_build lines 70-114
- Shape: functions=_prepare_standalone_build
- Findings: 0
- Reviews: 0

### openenv.cli.commands.build::_push_docker_image
- Status: pending
- Summary: Chunk _push_docker_image lines 309-319
- Shape: functions=_push_docker_image
- Findings: 0
- Reviews: 0

### openenv.cli.commands.build::_run_command
- Status: pending
- Summary: Chunk _run_command lines 205-229
- Shape: functions=_run_command
- Findings: 0
- Reviews: 0

### openenv.cli.commands.build::build
- Status: pending
- Summary: Chunk build lines 323-461
- Shape: functions=build
- Findings: 0
- Reviews: 0

### openenv.cli.commands.fork
- Status: pending
- Summary: exports: [_parse_key_value(s: str)->tuple[str, str], _ensure_hf_authenticated()->str, fork(source_space: Annotated[str, typer.Argument(help="Source Space ID in format 'owner/space-name' (e.g. org/my-openenv-space)")], repo_id: Annotated[str | None, typer.Option('--repo-id', '-r', help='Target repo ID for the fork (default: created under your account with same name)')], private: Annotated[bool, typer.Option('--private', help='Create the forked Space as private')], set_env: Annotated[list[str], typer.Option('--set-env', '-e', help='Set Space variable (public). Can be repeated. Format: KEY=VALUE')], set_secret: Annotated[list[str], typer.Option('--set-secret', '--secret', '-s', help='Set Space secret. Can be repeated. Format: KEY=VALUE')], hardware: Annotated[str | None, typer.Option('--hardware', '-H', help='Request hardware (e.g. t4-medium, cpu-basic). See Hub docs for options.')])->None] | issues: 6 | depends_on: [__future__, __future__.annotations, huggingface_hub, huggingface_hub.HfApi, huggingface_hub.login]
- Shape: functions=_parse_key_value, _ensure_hf_authenticated, fork
- Findings: 6
- Reviews: 0

### openenv.cli.commands.init
- Status: pending
- Summary: exports: [_snake_to_pascal(snake_str: str)->str, _get_env_prefix(env_name: str)->str, _snake_to_camel(snake_str: str)->str, _snake_to_title(snake_str: str)->str, _validate_env_name(name: str)->str] | issues: 13 | depends_on: [__future__, __future__.annotations, importlib, importlib.resources, openenv.cli._cli_utils]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 13
- Reviews: 0

### openenv.cli.commands.init::_copy_and_template_file
- Status: pending
- Summary: Chunk _copy_and_template_file lines 273-298
- Shape: functions=_copy_and_template_file
- Findings: 0
- Reviews: 0

### openenv.cli.commands.init::_copy_template_directory
- Status: pending
- Summary: Chunk _copy_template_directory lines 301-359
- Shape: functions=_copy_template_directory
- Findings: 0
- Reviews: 0

### openenv.cli.commands.init::_create_template_replacements
- Status: pending
- Summary: Chunk _create_template_replacements lines 213-246
- Shape: functions=_create_template_replacements
- Findings: 0
- Reviews: 0

### openenv.cli.commands.init::_generate_uv_lock
- Status: pending
- Summary: Chunk _generate_uv_lock lines 362-393
- Shape: functions=_generate_uv_lock
- Findings: 0
- Reviews: 0

### openenv.cli.commands.init::_get_env_prefix
- Status: pending
- Summary: Chunk _get_env_prefix lines 24-38
- Shape: functions=_get_env_prefix
- Findings: 0
- Reviews: 0

### openenv.cli.commands.init::_get_random_hf_space_config
- Status: pending
- Summary: Chunk _get_random_hf_space_config lines 72-210
- Shape: functions=_get_random_hf_space_config
- Findings: 0
- Reviews: 0

### openenv.cli.commands.init::_replace_in_content
- Status: pending
- Summary: Chunk _replace_in_content lines 249-255
- Shape: functions=_replace_in_content
- Findings: 0
- Reviews: 0

### openenv.cli.commands.init::_should_rename_file
- Status: pending
- Summary: Chunk _should_rename_file lines 258-270
- Shape: functions=_should_rename_file
- Findings: 0
- Reviews: 0

### openenv.cli.commands.init::_snake_to_camel
- Status: pending
- Summary: Chunk _snake_to_camel lines 41-44
- Shape: functions=_snake_to_camel
- Findings: 0
- Reviews: 0

### openenv.cli.commands.init::_snake_to_pascal
- Status: pending
- Summary: Chunk _snake_to_pascal lines 19-21
- Shape: functions=_snake_to_pascal
- Findings: 0
- Reviews: 0

### openenv.cli.commands.init::_snake_to_title
- Status: pending
- Summary: Chunk _snake_to_title lines 47-49
- Shape: functions=_snake_to_title
- Findings: 0
- Reviews: 0

### openenv.cli.commands.init::_validate_env_name
- Status: pending
- Summary: Chunk _validate_env_name lines 52-69
- Shape: functions=_validate_env_name
- Findings: 0
- Reviews: 0

### openenv.cli.commands.init::init
- Status: pending
- Summary: Chunk init lines 397-500
- Shape: functions=init
- Findings: 0
- Reviews: 0

### openenv.cli.commands.push
- Status: pending
- Summary: exports: [_path_matches_pattern(relative_path: Path, pattern: str)->bool, _should_exclude_path(relative_path: Path, ignore_patterns: list[str])->bool, _read_ignore_file(ignore_path: Path)->tuple[list[str], int], _load_ignore_patterns(env_dir: Path, exclude_file: str | None)->list[str], _merge_ignore_file(ignore_path: Path)->None] | issues: 28 | depends_on: [__future__, __future__.annotations, fnmatch, fnmatch.fnmatch, huggingface_hub]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 28
- Reviews: 0

### openenv.cli.commands.push::_copytree_ignore_factory
- Status: pending
- Summary: Chunk _copytree_ignore_factory lines 133-153
- Shape: functions=_copytree_ignore_factory
- Findings: 0
- Reviews: 0

### openenv.cli.commands.push::_create_hf_space
- Status: pending
- Summary: Chunk _create_hf_space lines 406-426
- Shape: functions=_create_hf_space
- Findings: 0
- Reviews: 0

### openenv.cli.commands.push::_ensure_hf_authenticated
- Status: pending
- Summary: Chunk _ensure_hf_authenticated lines 189-251
- Shape: functions=_ensure_hf_authenticated
- Findings: 0
- Reviews: 0

### openenv.cli.commands.push::_load_ignore_patterns
- Status: pending
- Summary: Chunk _load_ignore_patterns lines 94-130
- Shape: functions=_load_ignore_patterns
- Findings: 0
- Reviews: 0

### openenv.cli.commands.push::_path_matches_pattern
- Status: pending
- Summary: Chunk _path_matches_pattern lines 30-67
- Shape: functions=_path_matches_pattern
- Findings: 0
- Reviews: 0

### openenv.cli.commands.push::_prepare_staging_directory
- Status: pending
- Summary: Chunk _prepare_staging_directory lines 254-403
- Shape: functions=_prepare_staging_directory
- Findings: 0
- Reviews: 0

### openenv.cli.commands.push::_read_ignore_file
- Status: pending
- Summary: Chunk _read_ignore_file lines 77-91
- Shape: functions=_read_ignore_file
- Findings: 0
- Reviews: 0

### openenv.cli.commands.push::_should_exclude_path
- Status: pending
- Summary: Chunk _should_exclude_path lines 70-74
- Shape: functions=_should_exclude_path
- Findings: 0
- Reviews: 0

### openenv.cli.commands.push::_upload_to_hf_space
- Status: pending
- Summary: Chunk _upload_to_hf_space lines 429-466
- Shape: functions=_upload_to_hf_space
- Findings: 0
- Reviews: 0

### openenv.cli.commands.push::_validate_openenv_directory
- Status: pending
- Summary: Chunk _validate_openenv_directory lines 156-186
- Shape: functions=_validate_openenv_directory
- Findings: 0
- Reviews: 0

### openenv.cli.commands.push::push
- Status: pending
- Summary: Chunk push lines 470-718
- Shape: functions=push
- Findings: 0
- Reviews: 0

### openenv.cli.commands.serve
- Status: pending
- Summary: exports: [serve(env_path: Annotated[str | None, typer.Argument(help='Path to the environment directory (default: current directory)')], port: Annotated[int, typer.Option('--port', '-p', help='Port to serve on')], host: Annotated[str, typer.Option('--host', help='Host to bind to')], reload: Annotated[bool, typer.Option('--reload', help='Enable auto-reload on code changes')])->None] | issues: 3 | depends_on: [__future__, __future__.annotations, openenv.cli._cli_utils, openenv.cli._cli_utils.console, pathlib]
- Shape: functions=serve
- Findings: 3
- Reviews: 0

### openenv.cli.commands.skills
- Status: pending
- Summary: exports: [_build_skill_md()->str, _remove_existing(path: Path, force: bool)->None, _install_to(skills_dir: Path, force: bool)->Path, _create_symlink(agent_skills_dir: Path, central_skill_path: Path, force: bool)->Path, skills_preview()->None] | issues: 6 | depends_on: [__future__, __future__.annotations, openenv, openenv.__version__, os]
- Shape: functions=_build_skill_md, _remove_existing, _install_to, _create_symlink, skills_preview, skills_add
- Findings: 6
- Reviews: 0

### openenv.cli.commands.validate
- Status: pending
- Summary: exports: [_looks_like_url(value: str)->bool, validate(target: Annotated[str | None, typer.Argument(help='Path to the environment directory (default: current directory) or a running OpenEnv URL (http://... or https://...)')], url: Annotated[str | None, typer.Option('--url', help='Validate a running OpenEnv server by base URL (e.g. http://localhost:8000)')], json_output: Annotated[bool, typer.Option('--json', help='Output local validation report as JSON (runtime validation is JSON by default)')], timeout: Annotated[float, typer.Option('--timeout', help='HTTP timeout in seconds for runtime validation', min=0.1)], verbose: Annotated[bool, typer.Option('--verbose', '-v', help='Show detailed information')])->None] | issues: 5 | depends_on: [json, openenv.cli._validation, openenv.cli._validation.build_local_validation_json_report, openenv.cli._validation.format_validation_report, openenv.cli._validation.get_deployment_modes]
- Shape: functions=_looks_like_url, validate
- Findings: 5
- Reviews: 0

### openenv.cli.templates.__init__
- Status: pending
- Summary: exports: [] | issues: 0 | depends_on: []
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 0
- Reviews: 0

### openenv.cli.templates.openenv_env.__init__
- Status: pending
- Summary: exports: [] | issues: 0 | depends_on: [openenv.cli.templates.openenv_env.client, openenv.cli.templates.openenv_env.client.__ENV_CLASS_NAME__Env, openenv.cli.templates.openenv_env.models, openenv.cli.templates.openenv_env.models.__ENV_CLASS_NAME__Action, openenv.cli.templates.openenv_env.models.__ENV_CLASS_NAME__Observation]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 0
- Reviews: 0

### openenv.cli.templates.openenv_env.client
- Status: pending
- Summary: exports: [_step_payload(self, action: __ENV_CLASS_NAME__Action)->Dict, _parse_result(self, payload: Dict)->StepResult[__ENV_CLASS_NAME__Observation], _parse_state(self, payload: Dict)->State] | issues: 8 | depends_on: [openenv.cli.templates.openenv_env.models, openenv.cli.templates.openenv_env.models.__ENV_CLASS_NAME__Action, openenv.cli.templates.openenv_env.models.__ENV_CLASS_NAME__Observation, openenv.core, openenv.core.EnvClient]
- Shape: classes=__ENV_CLASS_NAME__Env
- Findings: 8
- Reviews: 0

### openenv.cli.templates.openenv_env.models
- Status: pending
- Summary: exports: [] | issues: 6 | depends_on: [openenv.core.env_server.types, openenv.core.env_server.types.Action, openenv.core.env_server.types.Observation, pydantic, pydantic.Field]
- Shape: classes=__ENV_CLASS_NAME__Action, __ENV_CLASS_NAME__Observation
- Findings: 6
- Reviews: 0

### openenv.cli.templates.openenv_env.server.__ENV_NAME___environment
- Status: pending
- Summary: exports: [__init__(self)->None, reset(self)->__ENV_CLASS_NAME__Observation, step(self, action: __ENV_CLASS_NAME__Action)->__ENV_CLASS_NAME__Observation, state(self)->State] | issues: 7 | depends_on: [models, models.__ENV_CLASS_NAME__Action, models.__ENV_CLASS_NAME__Observation, openenv.cli.templates.openenv_env.models, openenv.cli.templates.openenv_env.models.__ENV_CLASS_NAME__Action]
- Shape: classes=__ENV_CLASS_NAME__Environment
- Findings: 7
- Reviews: 0

### openenv.cli.templates.openenv_env.server.__init__
- Status: pending
- Summary: exports: [] | issues: 0 | depends_on: [openenv.cli.templates.openenv_env.server.__ENV_NAME___environment, openenv.cli.templates.openenv_env.server.__ENV_NAME___environment.__ENV_CLASS_NAME__Environment]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 0
- Reviews: 0

### openenv.cli.templates.openenv_env.server.app
- Status: pending
- Summary: exports: [main(host: str, port: int)->None] | issues: 4 | depends_on: [argparse, models, models.__ENV_CLASS_NAME__Action, models.__ENV_CLASS_NAME__Observation, openenv.cli.templates.openenv_env.models]
- Shape: functions=main
- Findings: 4
- Reviews: 0

### openenv.core.__init__
- Status: pending
- Summary: exports: [__getattr__(name: str)->None, __dir__()->list[str]] | issues: 14 | depends_on: [__future__, __future__.annotations, importlib, importlib.import_module, openenv.core]
- Shape: functions=__getattr__, __dir__
- Findings: 14
- Reviews: 0

### openenv.core.client_types
- Status: pending
- Summary: exports: [] | issues: 1 | depends_on: [dataclasses, dataclasses.dataclass, typing, typing.Generic, typing.Optional]
- Shape: classes=StepResult
- Findings: 1
- Reviews: 0

### openenv.core.containers.__init__
- Status: pending
- Summary: exports: [] | issues: 0 | depends_on: []
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 0
- Reviews: 0

### openenv.core.containers.runtime.__init__
- Status: pending
- Summary: exports: [] | issues: 0 | depends_on: [openenv.core.containers.runtime.providers, openenv.core.containers.runtime.providers.ContainerProvider, openenv.core.containers.runtime.providers.DockerSwarmProvider, openenv.core.containers.runtime.providers.KubernetesProvider, openenv.core.containers.runtime.providers.LocalDockerProvider]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 0
- Reviews: 0

### openenv.core.containers.runtime.daytona_provider
- Status: pending
- Summary: exports: [__init__(self)->None, _discover_server_cmd(self, sandbox: Any, port: int)->str, _find_openenv_yaml(self, sandbox: Any)->Optional[str], _parse_app_field(yaml_content: str)->Optional[str], _parse_dockerfile_cmd(dockerfile_content: str)->Optional[str]] | issues: 23 | depends_on: [__future__, __future__.annotations, daytona, daytona.CreateSandboxFromImageParams, daytona.CreateSandboxFromSnapshotParams]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 23
- Reviews: 0

### openenv.core.containers.runtime.daytona_provider::DaytonaProvider
- Status: pending
- Summary: Chunk DaytonaProvider lines 26-572
- Shape: classes=DaytonaProvider
- Findings: 0
- Reviews: 0

### openenv.core.containers.runtime.providers
- Status: pending
- Summary: exports: [start_container(self, image: str, port: Optional[int], env_vars: Optional[Dict[str, str]])->str, stop_container(self)->None, wait_for_ready(self, base_url: str, timeout_s: float)->None, __init__(self)->None, start_container(self, image: str, port: Optional[int], env_vars: Optional[Dict[str, str]])->str] | issues: 58 | depends_on: [__future__, __future__.annotations, abc, abc.ABC, abc.abstractmethod]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 58
- Reviews: 0

### openenv.core.containers.runtime.providers::ContainerProvider
- Status: pending
- Summary: Chunk ContainerProvider lines 20-89
- Shape: classes=ContainerProvider
- Findings: 0
- Reviews: 0

### openenv.core.containers.runtime.providers::DockerSwarmProvider
- Status: pending
- Summary: Chunk DockerSwarmProvider lines 291-590
- Shape: classes=DockerSwarmProvider
- Findings: 0
- Reviews: 0

### openenv.core.containers.runtime.providers::KubernetesProvider
- Status: pending
- Summary: Chunk KubernetesProvider lines 593-607
- Shape: classes=KubernetesProvider
- Findings: 0
- Reviews: 0

### openenv.core.containers.runtime.providers::LocalDockerProvider
- Status: pending
- Summary: Chunk LocalDockerProvider lines 92-288
- Shape: classes=LocalDockerProvider
- Findings: 0
- Reviews: 0

### openenv.core.containers.runtime.providers::RuntimeProvider
- Status: pending
- Summary: Chunk RuntimeProvider lines 610-669
- Shape: classes=RuntimeProvider
- Findings: 0
- Reviews: 0

### openenv.core.containers.runtime.uv_provider
- Status: pending
- Summary: exports: [_check_uv_installed()->None, _find_free_port()->int, _create_uv_command()->list[str], _poll_health(health_url: str, timeout_s: float)->None, __init__(self)->None] | issues: 11 | depends_on: [__future__, __future__.annotations, openenv.core.containers.runtime.providers, openenv.core.containers.runtime.providers.RuntimeProvider, os]
- Shape: functions=_check_uv_installed, _find_free_port, _create_uv_command, _poll_health | classes=UVProvider
- Findings: 11
- Reviews: 0

### openenv.core.containers.test_local_docker_provider
- Status: pending
- Summary: exports: [test_local_docker_provider()->None, test_provider_with_custom_port()->None, test_provider_with_env_vars()->None] | issues: 48 | depends_on: [openenv.core.containers.runtime, openenv.core.containers.runtime.LocalDockerProvider, pathlib, pathlib.Path, requests]
- Shape: functions=test_local_docker_provider, test_provider_with_custom_port, test_provider_with_env_vars
- Findings: 48
- Reviews: 0

### openenv.core.env_client
- Status: pending
- Summary: exports: [__init__(self, base_url: str, connect_timeout_s: float, message_timeout_s: float, max_message_size_mb: float, provider: Optional['ContainerProvider | RuntimeProvider'], mode: Optional[str])->None, __setattr__(self, name: str, value: Any)->None, connect(self)->'EnvClient', disconnect(self)->None, _ensure_connected(self)->None] | issues: 14 | depends_on: [__future__, __future__.annotations, abc, abc.ABC, abc.abstractmethod]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 14
- Reviews: 0

### openenv.core.env_client::EnvClient
- Status: pending
- Summary: Chunk EnvClient lines 54-484
- Shape: classes=EnvClient
- Findings: 0
- Reviews: 0

### openenv.core.env_server.__init__
- Status: pending
- Summary: exports: [] | issues: 3 | depends_on: [openenv.core.env_server.base_transforms, openenv.core.env_server.base_transforms.CompositeTransform, openenv.core.env_server.base_transforms.NullTransform, openenv.core.env_server.exceptions, openenv.core.env_server.exceptions.ConcurrencyConfigurationError]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 3
- Reviews: 0

### openenv.core.env_server.base_transforms
- Status: pending
- Summary: exports: [__init__(self, transforms: list[Transform])->None, __call__(self, observation: Observation)->Observation, __call__(self, observation: Observation)->Observation] | issues: 2 | depends_on: [openenv.core.env_server.interfaces, openenv.core.env_server.interfaces.Transform, openenv.core.env_server.types, openenv.core.env_server.types.Observation]
- Shape: classes=CompositeTransform, NullTransform
- Findings: 2
- Reviews: 0

### openenv.core.env_server.exceptions
- Status: pending
- Summary: exports: [__init__(self, environment_name: str, max_concurrent_envs: int, message: Optional[str])->None, __init__(self, active_sessions: int, max_sessions: int, message: Optional[str])->None, __init__(self, session_id: str, message: Optional[str])->None, __init__(self, reason: str, message: Optional[str])->None, __init__(self, factory_name: str, message: Optional[str])->None] | issues: 1 | depends_on: [typing, typing.Optional]
- Shape: classes=OpenEnvError, ConcurrencyConfigurationError, SessionCapacityError, SessionNotFoundError, SessionCreationError, EnvironmentFactoryError
- Findings: 1
- Reviews: 0

### openenv.core.env_server.gradio_theme
- Status: pending
- Summary: exports: [] | issues: 0 | depends_on: [__future__, __future__.annotations, gradio]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 0
- Reviews: 0

### openenv.core.env_server.gradio_ui
- Status: pending
- Summary: exports: [_escape_md(text: str)->str, _format_observation(data: Dict[str, Any])->str, _readme_section(metadata: Optional[EnvironmentMetadata])->str, get_gradio_display_title(metadata: Optional[EnvironmentMetadata], fallback: str)->str, build_gradio_app(web_manager: Any, action_fields: List[Dict[str, Any]], metadata: Optional[EnvironmentMetadata], is_chat_env: bool, title: str, quick_start_md: Optional[str])->gr.Blocks] | issues: 11 | depends_on: [__future__, __future__.annotations, gradio, json, openenv.core.env_server.types]
- Shape: functions=_escape_md, _format_observation, _readme_section, get_gradio_display_title, build_gradio_app
- Findings: 11
- Reviews: 0

### openenv.core.env_server.http_server
- Status: pending
- Summary: exports: [_make_json_serializable(obj: Any)->Any, __init__(self, env: Callable[[], Environment], action_cls: Type[Action], observation_cls: Type[Observation], max_concurrent_envs: Optional[int], concurrency_config: Optional[ConcurrencyConfig])->None, _validate_concurrency_safety(self)->None, get_capacity_status(self)->ServerCapacityStatus, _run_sync_in_thread_pool(self, func: Callable[..., Observation])->Observation] | issues: 61 | depends_on: [__future__, __future__.annotations, asyncio, concurrent.futures, concurrent.futures.ThreadPoolExecutor]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 61
- Reviews: 0

### openenv.core.env_server.http_server::HTTPEnvServer
- Status: pending
- Summary: Chunk HTTPEnvServer lines 116-1486
- Shape: classes=HTTPEnvServer
- Findings: 0
- Reviews: 0

### openenv.core.env_server.http_server::_make_json_serializable
- Status: pending
- Summary: Chunk _make_json_serializable lines 79-106
- Shape: functions=_make_json_serializable
- Findings: 0
- Reviews: 0

### openenv.core.env_server.http_server::create_app
- Status: pending
- Summary: Chunk create_app lines 1489-1546
- Shape: functions=create_app
- Findings: 0
- Reviews: 0

### openenv.core.env_server.http_server::create_fastapi_app
- Status: pending
- Summary: Chunk create_fastapi_app lines 1549-1646
- Shape: functions=create_fastapi_app
- Findings: 0
- Reviews: 0

### openenv.core.env_server.interfaces
- Status: pending
- Summary: exports: [apply_chat_template(self, conversation: list[Message], tokenize: bool, return_tensors: str | None)->Any, decode(self, token_ids: Any, skip_special_tokens: bool)->str, __call__(self, observation: ObsT)->ObsT, __init__(self, transform: Optional[Transform[ObsT]], rubric: Optional['Rubric'])->None, reset(self, seed: Optional[int], episode_id: Optional[str])->ObsT] | issues: 9 | depends_on: [abc, abc.ABC, abc.abstractmethod, inspect, openenv.core.env_server.types]
- Shape: classes=Message, ModelTokenizer, Transform, Environment
- Findings: 9
- Reviews: 0

### openenv.core.env_server.mcp_environment
- Status: pending
- Summary: exports: [get_server_tools(mcp_server: Any)->Dict[str, Any], __init__(self, mcp_server: Any, transform: Optional[Any])->None, _require_mcp_client(self)->Any, _require_mcp_server(self)->Any, mcp_session(self)->None] | issues: 10 | depends_on: [abc, abc.abstractmethod, asyncio, collections, collections.defaultdict]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 10
- Reviews: 0

### openenv.core.env_server.mcp_environment::MCPEnvironment
- Status: pending
- Summary: Chunk MCPEnvironment lines 107-645
- Shape: classes=MCPEnvironment
- Findings: 0
- Reviews: 0

### openenv.core.env_server.mcp_environment::get_server_tools
- Status: pending
- Summary: Chunk get_server_tools lines 88-104
- Shape: functions=get_server_tools
- Findings: 0
- Reviews: 0

### openenv.core.env_server.mcp_types
- Status: pending
- Summary: exports: [from_code(cls, code: JsonRpcErrorCode, message: Optional[str], data: Any)->'JsonRpcError', model_dump(self)->Dict[str, Any], model_dump_json(self)->str, success(cls, result: Any, request_id: Optional[Union[str, int]])->'JsonRpcResponse', error_response(cls, code: JsonRpcErrorCode, message: Optional[str], data: Any, request_id: Optional[Union[str, int]])->'JsonRpcResponse'] | issues: 3 | depends_on: [enum, enum.Enum, json, openenv.core.env_server.types, openenv.core.env_server.types.Action]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 3
- Reviews: 0

### openenv.core.env_server.mcp_types::CallToolAction
- Status: pending
- Summary: Chunk CallToolAction lines 244-258
- Shape: classes=CallToolAction
- Findings: 0
- Reviews: 0

### openenv.core.env_server.mcp_types::CallToolObservation
- Status: pending
- Summary: Chunk CallToolObservation lines 274-289
- Shape: classes=CallToolObservation
- Findings: 0
- Reviews: 0

### openenv.core.env_server.mcp_types::JsonRpcError
- Status: pending
- Summary: Chunk JsonRpcError lines 58-90
- Shape: classes=JsonRpcError
- Findings: 0
- Reviews: 0

### openenv.core.env_server.mcp_types::JsonRpcErrorCode
- Status: pending
- Summary: Chunk JsonRpcErrorCode lines 33-48
- Shape: classes=JsonRpcErrorCode
- Findings: 0
- Reviews: 0

### openenv.core.env_server.mcp_types::JsonRpcRequest
- Status: pending
- Summary: Chunk JsonRpcRequest lines 93-109
- Shape: classes=JsonRpcRequest
- Findings: 0
- Reviews: 0

### openenv.core.env_server.mcp_types::JsonRpcResponse
- Status: pending
- Summary: Chunk JsonRpcResponse lines 112-175
- Shape: classes=JsonRpcResponse
- Findings: 0
- Reviews: 0

### openenv.core.env_server.mcp_types::ListToolsAction
- Status: pending
- Summary: Chunk ListToolsAction lines 229-241
- Shape: classes=ListToolsAction
- Findings: 0
- Reviews: 0

### openenv.core.env_server.mcp_types::ListToolsObservation
- Status: pending
- Summary: Chunk ListToolsObservation lines 264-271
- Shape: classes=ListToolsObservation
- Findings: 0
- Reviews: 0

### openenv.core.env_server.mcp_types::McpMethod
- Status: pending
- Summary: Chunk McpMethod lines 51-55
- Shape: classes=McpMethod
- Findings: 0
- Reviews: 0

### openenv.core.env_server.mcp_types::Tool
- Status: pending
- Summary: Chunk Tool lines 183-199
- Shape: classes=Tool
- Findings: 0
- Reviews: 0

### openenv.core.env_server.mcp_types::ToolError
- Status: pending
- Summary: Chunk ToolError lines 212-223
- Shape: classes=ToolError
- Findings: 0
- Reviews: 0

### openenv.core.env_server.mcp_types::ToolErrorType
- Status: pending
- Summary: Chunk ToolErrorType lines 202-209
- Shape: classes=ToolErrorType
- Findings: 0
- Reviews: 0

### openenv.core.env_server.mcp_types::WSMCPMessage
- Status: pending
- Summary: Chunk WSMCPMessage lines 295-304
- Shape: classes=WSMCPMessage
- Findings: 0
- Reviews: 0

### openenv.core.env_server.mcp_types::WSMCPResponse
- Status: pending
- Summary: Chunk WSMCPResponse lines 307-317
- Shape: classes=WSMCPResponse
- Findings: 0
- Reviews: 0

### openenv.core.env_server.route_config
- Status: pending
- Summary: exports: [register_get_endpoints(app: FastAPI, configs: List[GetEndpointConfig])->None, make_endpoint(handler: Callable[[], BaseModel | dict])->Callable[[], BaseModel | dict], endpoint()->BaseModel | dict] | issues: 0 | depends_on: [dataclasses, dataclasses.dataclass, fastapi, fastapi.FastAPI, pydantic]
- Shape: functions=register_get_endpoints | classes=GetEndpointConfig
- Findings: 0
- Reviews: 0

### openenv.core.env_server.serialization
- Status: pending
- Summary: exports: [deserialize_action(action_data: Dict[str, Any], action_cls: Type[Action])->Action, deserialize_action_with_preprocessing(action_data: Dict[str, Any], action_cls: Type[Action])->Action, serialize_observation(observation: Observation)->Dict[str, Any]] | issues: 3 | depends_on: [json, openenv.core.env_server.mcp_types, openenv.core.env_server.mcp_types.CallToolAction, openenv.core.env_server.mcp_types.ListToolsAction, openenv.core.env_server.types]
- Shape: functions=deserialize_action, deserialize_action_with_preprocessing, serialize_observation
- Findings: 3
- Reviews: 0

### openenv.core.env_server.types
- Status: pending
- Summary: exports: [check_capacity_bounds(self)->'ServerCapacityStatus', available_slots(self)->int, is_at_capacity(self)->bool, from_counts(cls, active: int, max_sessions: int)->'ServerCapacityStatus'] | issues: 2 | depends_on: [enum, enum.Enum, pydantic, pydantic.BaseModel, pydantic.ConfigDict]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 2
- Reviews: 0

### openenv.core.env_server.types::Action
- Status: pending
- Summary: Chunk Action lines 54-69
- Shape: classes=Action
- Findings: 0
- Reviews: 0

### openenv.core.env_server.types::BaseMessage
- Status: pending
- Summary: Chunk BaseMessage lines 169-175
- Shape: classes=BaseMessage
- Findings: 0
- Reviews: 0

### openenv.core.env_server.types::CodeExecResult
- Status: pending
- Summary: Chunk CodeExecResult lines 200-205
- Shape: classes=CodeExecResult
- Findings: 0
- Reviews: 0

### openenv.core.env_server.types::ConcurrencyConfig
- Status: pending
- Summary: Chunk ConcurrencyConfig lines 317-329
- Shape: classes=ConcurrencyConfig
- Findings: 0
- Reviews: 0

### openenv.core.env_server.types::EnvironmentMetadata
- Status: pending
- Summary: Chunk EnvironmentMetadata lines 208-222
- Shape: classes=EnvironmentMetadata
- Findings: 0
- Reviews: 0

### openenv.core.env_server.types::HealthResponse
- Status: pending
- Summary: Chunk HealthResponse lines 239-245
- Shape: classes=HealthResponse
- Findings: 0
- Reviews: 0

### openenv.core.env_server.types::HealthStatus
- Status: pending
- Summary: Chunk HealthStatus lines 29-34
- Shape: classes=HealthStatus
- Findings: 0
- Reviews: 0

### openenv.core.env_server.types::Observation
- Status: pending
- Summary: Chunk Observation lines 72-91
- Shape: classes=Observation
- Findings: 0
- Reviews: 0

### openenv.core.env_server.types::ResetRequest
- Status: pending
- Summary: Chunk ResetRequest lines 94-107
- Shape: classes=ResetRequest
- Findings: 0
- Reviews: 0

### openenv.core.env_server.types::ResetResponse
- Status: pending
- Summary: Chunk ResetResponse lines 110-123
- Shape: classes=ResetResponse
- Findings: 0
- Reviews: 0

### openenv.core.env_server.types::SchemaResponse
- Status: pending
- Summary: Chunk SchemaResponse lines 225-236
- Shape: classes=SchemaResponse
- Findings: 0
- Reviews: 0

### openenv.core.env_server.types::ServerCapacityStatus
- Status: pending
- Summary: Chunk ServerCapacityStatus lines 332-369
- Shape: classes=ServerCapacityStatus
- Findings: 0
- Reviews: 0

### openenv.core.env_server.types::ServerMode
- Status: pending
- Summary: Chunk ServerMode lines 22-26
- Shape: classes=ServerMode
- Findings: 0
- Reviews: 0

### openenv.core.env_server.types::SessionInfo
- Status: pending
- Summary: Chunk SessionInfo lines 372-387
- Shape: classes=SessionInfo
- Findings: 0
- Reviews: 0

### openenv.core.env_server.types::State
- Status: pending
- Summary: Chunk State lines 178-197
- Shape: classes=State
- Findings: 0
- Reviews: 0

### openenv.core.env_server.types::StepRequest
- Status: pending
- Summary: Chunk StepRequest lines 126-152
- Shape: classes=StepRequest
- Findings: 0
- Reviews: 0

### openenv.core.env_server.types::StepResponse
- Status: pending
- Summary: Chunk StepResponse lines 155-166
- Shape: classes=StepResponse
- Findings: 0
- Reviews: 0

### openenv.core.env_server.types::WSCloseMessage
- Status: pending
- Summary: Chunk WSCloseMessage lines 273-276
- Shape: classes=WSCloseMessage
- Findings: 0
- Reviews: 0

### openenv.core.env_server.types::WSErrorCode
- Status: pending
- Summary: Chunk WSErrorCode lines 37-46
- Shape: classes=WSErrorCode
- Findings: 0
- Reviews: 0

### openenv.core.env_server.types::WSErrorResponse
- Status: pending
- Summary: Chunk WSErrorResponse lines 308-314
- Shape: classes=WSErrorResponse
- Findings: 0
- Reviews: 0

### openenv.core.env_server.types::WSObservationResponse
- Status: pending
- Summary: Chunk WSObservationResponse lines 288-296
- Shape: classes=WSObservationResponse
- Findings: 0
- Reviews: 0

### openenv.core.env_server.types::WSResetMessage
- Status: pending
- Summary: Chunk WSResetMessage lines 248-255
- Shape: classes=WSResetMessage
- Findings: 0
- Reviews: 0

### openenv.core.env_server.types::WSStateMessage
- Status: pending
- Summary: Chunk WSStateMessage lines 267-270
- Shape: classes=WSStateMessage
- Findings: 0
- Reviews: 0

### openenv.core.env_server.types::WSStateResponse
- Status: pending
- Summary: Chunk WSStateResponse lines 299-305
- Shape: classes=WSStateResponse
- Findings: 0
- Reviews: 0

### openenv.core.env_server.types::WSStepMessage
- Status: pending
- Summary: Chunk WSStepMessage lines 258-264
- Shape: classes=WSStepMessage
- Findings: 0
- Reviews: 0

### openenv.core.env_server.web_interface
- Status: pending
- Summary: exports: [get_quick_start_markdown(metadata: Optional[EnvironmentMetadata], action_cls: Type[Action], observation_cls: Type[Observation])->str, load_environment_metadata(env: Environment, env_name: Optional[str])->EnvironmentMetadata, _load_readme_from_filesystem(env_name: Optional[str])->Optional[str], __init__(self, env: Environment, action_cls: Type[Action], observation_cls: Type[Observation], metadata: Optional[EnvironmentMetadata])->None, _get_valid_kwargs(sig: inspect.Signature, kwargs: Dict[str, Any], skip_params: Optional[set[str]])->Dict[str, Any]] | issues: 27 | depends_on: [__future__, __future__.annotations, asyncio, concurrent.futures, concurrent.futures.ThreadPoolExecutor]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 27
- Reviews: 0

### openenv.core.env_server.web_interface::ActionLog
- Status: pending
- Summary: Chunk ActionLog lines 206-218
- Shape: classes=ActionLog
- Findings: 0
- Reviews: 0

### openenv.core.env_server.web_interface::EpisodeState
- Status: pending
- Summary: Chunk EpisodeState lines 221-236
- Shape: classes=EpisodeState
- Findings: 0
- Reviews: 0

### openenv.core.env_server.web_interface::WebInterfaceManager
- Status: pending
- Summary: Chunk WebInterfaceManager lines 239-425
- Shape: classes=WebInterfaceManager
- Findings: 0
- Reviews: 0

### openenv.core.env_server.web_interface::_determine_input_type_from_schema
- Status: pending
- Summary: Chunk _determine_input_type_from_schema lines 635-665
- Shape: functions=_determine_input_type_from_schema
- Findings: 0
- Reviews: 0

### openenv.core.env_server.web_interface::_extract_action_fields
- Status: pending
- Summary: Chunk _extract_action_fields lines 590-632
- Shape: functions=_extract_action_fields
- Findings: 0
- Reviews: 0

### openenv.core.env_server.web_interface::_generate_help_text
- Status: pending
- Summary: Chunk _generate_help_text lines 680-697
- Shape: functions=_generate_help_text
- Findings: 0
- Reviews: 0

### openenv.core.env_server.web_interface::_generate_placeholder
- Status: pending
- Summary: Chunk _generate_placeholder lines 668-677
- Shape: functions=_generate_placeholder
- Findings: 0
- Reviews: 0

### openenv.core.env_server.web_interface::_is_chat_env
- Status: pending
- Summary: Chunk _is_chat_env lines 577-587
- Shape: functions=_is_chat_env
- Findings: 0
- Reviews: 0

### openenv.core.env_server.web_interface::_load_readme_from_filesystem
- Status: pending
- Summary: Chunk _load_readme_from_filesystem lines 166-203
- Shape: functions=_load_readme_from_filesystem
- Findings: 0
- Reviews: 0

### openenv.core.env_server.web_interface::create_web_interface_app
- Status: pending
- Summary: Chunk create_web_interface_app lines 428-574
- Shape: functions=create_web_interface_app
- Findings: 0
- Reviews: 0

### openenv.core.env_server.web_interface::get_quick_start_markdown
- Status: pending
- Summary: Chunk get_quick_start_markdown lines 73-107
- Shape: functions=get_quick_start_markdown
- Findings: 0
- Reviews: 0

### openenv.core.env_server.web_interface::load_environment_metadata
- Status: pending
- Summary: Chunk load_environment_metadata lines 110-163
- Shape: functions=load_environment_metadata
- Findings: 0
- Reviews: 0

### openenv.core.evals.__init__
- Status: pending
- Summary: exports: [] | issues: 6 | depends_on: [openenv.core.evals.base, openenv.core.evals.base.EvalHarness, openenv.core.evals.inspect_harness, openenv.core.evals.inspect_harness.InspectAIHarness, openenv.core.evals.types]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 6
- Reviews: 0

### openenv.core.evals.base
- Status: pending
- Summary: exports: [run(self, harness_version: str, library_versions: Dict[str, str], dataset: str, eval_parameters: Dict[str, Any])->Dict[str, Any], run_from_config(self, config: EvalConfig)->EvalResult, name(self)->str] | issues: 2 | depends_on: [abc, abc.ABC, abc.abstractmethod, openenv.core.evals.types, openenv.core.evals.types.EvalConfig]
- Shape: classes=EvalHarness
- Findings: 2
- Reviews: 0

### openenv.core.evals.inspect_harness
- Status: pending
- Summary: exports: [__init__(self)->None, run(self, harness_version: str, library_versions: Dict[str, str], dataset: str, eval_parameters: Dict[str, Any])->Dict[str, Any], _extract_scores(self, log: Any)->Dict[str, Any]] | issues: 7 | depends_on: [__future__, __future__.annotations, inspect_ai, inspect_ai.eval, openenv.core.evals.base]
- Shape: classes=InspectAIHarness
- Findings: 7
- Reviews: 0

### openenv.core.evals.types
- Status: pending
- Summary: exports: [] | issues: 0 | depends_on: [pydantic, pydantic.BaseModel, pydantic.ConfigDict, pydantic.Field, typing]
- Shape: classes=EvalConfig, EvalResult
- Findings: 0
- Reviews: 0

### openenv.core.generic_client
- Status: pending
- Summary: exports: [_step_payload(self, action: Dict[str, Any])->Dict[str, Any], _parse_result(self, payload: Dict[str, Any])->StepResult[Dict[str, Any]], _parse_state(self, payload: Dict[str, Any])->Dict[str, Any], __init__(self)->None, __repr__(self)->str] | issues: 0 | depends_on: [openenv.core.client_types, openenv.core.client_types.StepResult, openenv.core.env_client, openenv.core.env_client.EnvClient, typing]
- Shape: classes=GenericEnvClient, GenericAction
- Findings: 0
- Reviews: 0

### openenv.core.llm_client
- Status: pending
- Summary: exports: [to_message_dict(self)->dict[str, Any], __init__(self, endpoint: str, port: int)->None, complete(self, prompt: str)->str, complete_with_tools(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]])->LLMResponse, base_url(self)->str] | issues: 8 | depends_on: [__future__, __future__.annotations, abc, abc.ABC, abc.abstractmethod]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 8
- Reviews: 0

### openenv.core.llm_client::AnthropicClient
- Status: pending
- Summary: Chunk AnthropicClient lines 216-306
- Shape: classes=AnthropicClient
- Findings: 0
- Reviews: 0

### openenv.core.llm_client::LLMClient
- Status: pending
- Summary: Chunk LLMClient lines 67-120
- Shape: classes=LLMClient
- Findings: 0
- Reviews: 0

### openenv.core.llm_client::LLMResponse
- Status: pending
- Summary: Chunk LLMResponse lines 43-64
- Shape: classes=LLMResponse
- Findings: 0
- Reviews: 0

### openenv.core.llm_client::OpenAIClient
- Status: pending
- Summary: Chunk OpenAIClient lines 123-213
- Shape: classes=OpenAIClient
- Findings: 0
- Reviews: 0

### openenv.core.llm_client::ToolCall
- Status: pending
- Summary: Chunk ToolCall lines 34-39
- Shape: classes=ToolCall
- Findings: 0
- Reviews: 0

### openenv.core.llm_client::_clean_mcp_schema
- Status: pending
- Summary: Chunk _clean_mcp_schema lines 364-401
- Shape: functions=_clean_mcp_schema
- Findings: 0
- Reviews: 0

### openenv.core.llm_client::_mcp_tools_to_anthropic
- Status: pending
- Summary: Chunk _mcp_tools_to_anthropic lines 426-442
- Shape: functions=_mcp_tools_to_anthropic
- Findings: 0
- Reviews: 0

### openenv.core.llm_client::_mcp_tools_to_openai
- Status: pending
- Summary: Chunk _mcp_tools_to_openai lines 404-423
- Shape: functions=_mcp_tools_to_openai
- Findings: 0
- Reviews: 0

### openenv.core.llm_client::_openai_msgs_to_anthropic
- Status: pending
- Summary: Chunk _openai_msgs_to_anthropic lines 445-506
- Shape: functions=_openai_msgs_to_anthropic
- Findings: 0
- Reviews: 0

### openenv.core.llm_client::create_llm_client
- Status: pending
- Summary: Chunk create_llm_client lines 319-356
- Shape: functions=create_llm_client
- Findings: 0
- Reviews: 0

### openenv.core.mcp_client
- Status: pending
- Summary: exports: [__init__(self, base_url: str, connect_timeout_s: float, message_timeout_s: float, provider: Optional[Any], mode: Optional[str])->None, _next_request_id(self)->int, _production_mcp_url(self)->str, _get_http_client(self)->Any, _production_mcp_request(self, method: str, params: Optional[Dict[str, Any]])->Dict[str, Any]] | issues: 11 | depends_on: [asyncio, httpx, openenv.core.client_types, openenv.core.client_types.StepResult, openenv.core.env_client]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 11
- Reviews: 0

### openenv.core.mcp_client::MCPClientBase
- Status: pending
- Summary: Chunk MCPClientBase lines 71-339
- Shape: classes=MCPClientBase
- Findings: 0
- Reviews: 0

### openenv.core.mcp_client::MCPToolClient
- Status: pending
- Summary: Chunk MCPToolClient lines 342-484
- Shape: classes=MCPToolClient
- Findings: 0
- Reviews: 0

### openenv.core.rubrics.__init__
- Status: pending
- Summary: exports: [] | issues: 8 | depends_on: [openenv.core.rubrics.base, openenv.core.rubrics.base.Rubric, openenv.core.rubrics.containers, openenv.core.rubrics.containers.Gate, openenv.core.rubrics.containers.RubricDict]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 8
- Reviews: 0

### openenv.core.rubrics.base
- Status: pending
- Summary: exports: [__init__(self)->None, __setattr__(self, name: str, value: Any)->None, __call__(self, action: Any, observation: Any)->None, _call_sync(self, action: Any, observation: Any, result: float)->float, _call_async(self, action: Any, observation: Any, result_coro)->float] | issues: 5 | depends_on: [abc, abc.ABC, abc.abstractmethod, inspect, typing]
- Shape: classes=Rubric
- Findings: 5
- Reviews: 0

### openenv.core.rubrics.containers
- Status: pending
- Summary: exports: [_in_async_context()->bool, __init__(self)->None, forward(self, action: Any, observation: Any)->float, __call__(self, action: Any, observation: Any)->None, _empty_async(self, action, observation)->None] | issues: 32 | depends_on: [asyncio, inspect, openenv.core.rubrics.base, openenv.core.rubrics.base.Rubric, typing]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 32
- Reviews: 0

### openenv.core.rubrics.containers::Gate
- Status: pending
- Summary: Chunk Gate lines 261-326
- Shape: classes=Gate
- Findings: 0
- Reviews: 0

### openenv.core.rubrics.containers::RubricDict
- Status: pending
- Summary: Chunk RubricDict lines 499-574
- Shape: classes=RubricDict
- Findings: 0
- Reviews: 0

### openenv.core.rubrics.containers::RubricList
- Status: pending
- Summary: Chunk RubricList lines 443-496
- Shape: classes=RubricList
- Findings: 0
- Reviews: 0

### openenv.core.rubrics.containers::Sequential
- Status: pending
- Summary: Chunk Sequential lines 31-258
- Shape: classes=Sequential
- Findings: 0
- Reviews: 0

### openenv.core.rubrics.containers::WeightedSum
- Status: pending
- Summary: Chunk WeightedSum lines 329-440
- Shape: classes=WeightedSum
- Findings: 0
- Reviews: 0

### openenv.core.rubrics.containers::_in_async_context
- Status: pending
- Summary: Chunk _in_async_context lines 22-28
- Shape: functions=_in_async_context
- Findings: 0
- Reviews: 0

### openenv.core.rubrics.llm_judge
- Status: pending
- Summary: exports: [__init__(self, prompt_template: str, client: LLMClient)->None, forward(self, action: Any, observation: Any)->float, _render_prompt(self, action: Any, observation: Any)->str, _parse_score(self, response: str)->float, state_dict(self)->Dict[str, Any]] | issues: 5 | depends_on: [openenv.core.llm_client, openenv.core.llm_client.LLMClient, openenv.core.rubrics.base, openenv.core.rubrics.base.Rubric, re]
- Shape: classes=LLMJudge
- Findings: 5
- Reviews: 0

### openenv.core.rubrics.trajectory
- Status: pending
- Summary: exports: [__init__(self, intermediate_reward: float)->None, forward(self, action: Any, observation: Any)->float, score_trajectory(self, trajectory: List[Tuple[Any, Any]])->float, compute_step_rewards(self)->List[float], reset(self)->None] | issues: 5 | depends_on: [abc, abc.abstractmethod, openenv.core.rubrics.base, openenv.core.rubrics.base.Rubric, typing]
- Shape: classes=TrajectoryRubric, ExponentialDiscountingTrajectoryRubric
- Findings: 5
- Reviews: 0

### openenv.core.sync_client
- Status: pending
- Summary: exports: [__init__(self, async_client: 'EnvClient[ActT, ObsT, StateT]')->None, _run_loop_forever(self)->None, _ensure_loop(self)->asyncio.AbstractEventLoop, _run(self, coro: Any)->Any, _stop_loop(self)->None] | issues: 6 | depends_on: [__future__, __future__.annotations, asyncio, concurrent.futures, inspect]
- Shape: classes=SyncEnvClient
- Findings: 6
- Reviews: 0

### openenv.core.tools.__init__
- Status: pending
- Summary: exports: [] | issues: 1 | depends_on: [openenv.core.tools.git_server_client, openenv.core.tools.git_server_client.GitServerClient, openenv.core.tools.git_server_client.RepoInfo, openenv.core.tools.local_python_executor, openenv.core.tools.local_python_executor.PyExecutor]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 1
- Reviews: 0

### openenv.core.tools.git_server_client
- Status: pending
- Summary: exports: [__init__(self, gitea_url: str, username: str, password: str, workspace_dir: str)->None, _configure_git(self)->None, wait_for_ready(self, timeout: int)->bool, list_repositories(self)->list[dict[str, str]], clone_to_workspace(self, repo_name: str, target_dir: str | None, commit: str)->str] | issues: 35 | depends_on: [dataclasses, dataclasses.dataclass, json, os, pathlib]
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 35
- Reviews: 0

### openenv.core.tools.git_server_client::GitServerClient
- Status: pending
- Summary: Chunk GitServerClient lines 30-369
- Shape: classes=GitServerClient
- Findings: 0
- Reviews: 0

### openenv.core.tools.git_server_client::RepoInfo
- Status: pending
- Summary: Chunk RepoInfo lines 21-27
- Shape: classes=RepoInfo
- Findings: 0
- Reviews: 0

### openenv.core.tools.local_python_executor
- Status: pending
- Summary: exports: [__init__(self, additional_imports: list[str] | None)->None, run(self, code: str)->CodeExecResult] | issues: 14 | depends_on: [__future__, __future__.annotations, json, logging, openenv.core.env_server.types]
- Shape: classes=PyExecutor
- Findings: 14
- Reviews: 0

### openenv.core.utils
- Status: pending
- Summary: exports: [run_async_safely(coro)->None, convert_to_ws_url(url: str)->str] | issues: 0 | depends_on: [asyncio, concurrent.futures]
- Shape: functions=run_async_safely, convert_to_ws_url
- Findings: 0
- Reviews: 0

### openenv_core.__init__
- Status: pending
- Summary: exports: [__getattr__(name: str)->None, __dir__()->None, _alias(name: str)->None] | issues: 2 | depends_on: [__future__, __future__.annotations, importlib, sys, types]
- Shape: functions=__getattr__, __dir__, _alias
- Findings: 2
- Reviews: 0

## RL Integrity
- Trajectory reconstructable from DB annotations and episode records.
- Reward causality linked to each persisted action payload.
- Easy/Medium deterministic replay expected; Hard constrained by temperature=0 judge policy.
