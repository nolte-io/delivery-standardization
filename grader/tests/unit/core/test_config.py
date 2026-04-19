"""Tests for core/config.py — loading, validation, hashing."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from nolte_grader.core.config import GraderConfig, config_hash, load_config
from nolte_grader.core.errors import ConfigError


class TestLoadConfig:
    def test_loads_minimal_yaml(self, minimal_config_yaml: Path) -> None:
        cfg = load_config(minimal_config_yaml)
        assert cfg.jira.instance_url == "https://example.atlassian.net"
        assert cfg.projects.include == ["TEST"]

    def test_accepts_path_or_string(
        self, minimal_config_yaml: Path, minimal_config_dict: dict[str, Any]
    ) -> None:
        cfg_path = load_config(minimal_config_yaml)
        cfg_str = load_config(str(minimal_config_yaml))
        assert cfg_path == cfg_str

    def test_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "missing.yaml")

    def test_raises_config_error_for_non_mapping(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.yaml"
        path.write_text("- just\n- a\n- list\n")
        with pytest.raises(ConfigError, match="YAML mapping"):
            load_config(path)

    def test_raises_validation_error_for_extra_key(
        self, tmp_path: Path, minimal_config_dict: dict[str, Any]
    ) -> None:
        minimal_config_dict["rogue_key"] = "oops"
        path = tmp_path / "extra.yaml"
        path.write_text(yaml.safe_dump(minimal_config_dict))
        with pytest.raises(ValidationError):
            load_config(path)

    def test_raises_validation_error_for_missing_required(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.yaml"
        path.write_text("{}\n")
        with pytest.raises(ValidationError):
            load_config(path)


class TestAuthorizedApprovers:
    def test_for_project_merges_default_and_override(
        self, minimal_config_dict: dict[str, Any]
    ) -> None:
        minimal_config_dict["authorized_approvers"]["per_project"] = {
            "TEST": [{"accountId": "client-poc", "role": "client_poc"}]
        }
        cfg = GraderConfig.model_validate(minimal_config_dict)
        approvers = cfg.authorized_approvers.for_project("TEST")
        account_ids = {a.accountId for a in approvers}
        assert "u1" in account_ids
        assert "client-poc" in account_ids

    def test_for_project_returns_only_default_when_no_override(
        self, minimal_config_dict: dict[str, Any]
    ) -> None:
        cfg = GraderConfig.model_validate(minimal_config_dict)
        approvers = cfg.authorized_approvers.for_project("NOPROJ")
        assert len(approvers) == 1
        assert approvers[0].accountId == "u1"


class TestJudgeConfig:
    def test_model_for_uses_default(self, minimal_config_dict: dict[str, Any]) -> None:
        cfg = GraderConfig.model_validate(minimal_config_dict)
        assert cfg.judge.model_for("Y1") == "claude-sonnet-4-6"

    def test_model_for_uses_override(self, minimal_config_dict: dict[str, Any]) -> None:
        minimal_config_dict["judge"]["model_by_dimension"] = {"D3": "claude-opus-4-7"}
        cfg = GraderConfig.model_validate(minimal_config_dict)
        assert cfg.judge.model_for("D3") == "claude-opus-4-7"
        assert cfg.judge.model_for("Y1") == "claude-sonnet-4-6"


class TestTeamsConfig:
    def test_size_for_returns_default(self, minimal_config_dict: dict[str, Any]) -> None:
        cfg = GraderConfig.model_validate(minimal_config_dict)
        assert cfg.teams.size_for("ANYPROJECT") == 5

    def test_size_for_returns_override(self, minimal_config_dict: dict[str, Any]) -> None:
        minimal_config_dict["teams"]["per_project"] = {"TINY": {"size": 1}}
        cfg = GraderConfig.model_validate(minimal_config_dict)
        assert cfg.teams.size_for("TINY") == 1
        assert cfg.teams.size_for("OTHER") == 5

    def test_team_size_exception_fires_when_size_is_one(
        self, minimal_config_dict: dict[str, Any]
    ) -> None:
        minimal_config_dict["teams"]["per_project"] = {"SOLO": {"size": 1}}
        cfg = GraderConfig.model_validate(minimal_config_dict)
        assert cfg.teams.size_for("SOLO") == 1


class TestConfigHash:
    def test_returns_sha256_prefix(self, minimal_config_dict: dict[str, Any]) -> None:
        cfg = GraderConfig.model_validate(minimal_config_dict)
        h = config_hash(cfg)
        assert h.startswith("sha256:")
        assert len(h) == len("sha256:") + 64

    def test_identical_configs_produce_same_hash(
        self, minimal_config_dict: dict[str, Any]
    ) -> None:
        cfg_a = GraderConfig.model_validate(minimal_config_dict)
        cfg_b = GraderConfig.model_validate(copy.deepcopy(minimal_config_dict))
        assert config_hash(cfg_a) == config_hash(cfg_b)

    def test_different_configs_produce_different_hash(
        self, minimal_config_dict: dict[str, Any]
    ) -> None:
        cfg_a = GraderConfig.model_validate(minimal_config_dict)
        modified = copy.deepcopy(minimal_config_dict)
        modified["thresholds"]["cycle_time_days"] = 14
        cfg_b = GraderConfig.model_validate(modified)
        assert config_hash(cfg_a) != config_hash(cfg_b)

    def test_hash_stable_across_dict_insertion_order(
        self, minimal_config_dict: dict[str, Any]
    ) -> None:
        cfg_a = GraderConfig.model_validate(minimal_config_dict)
        reversed_dict = dict(reversed(list(minimal_config_dict.items())))
        cfg_b = GraderConfig.model_validate(reversed_dict)
        assert config_hash(cfg_a) == config_hash(cfg_b)

    def test_teams_size_change_changes_hash(
        self, minimal_config_dict: dict[str, Any]
    ) -> None:
        cfg_a = GraderConfig.model_validate(minimal_config_dict)
        modified = copy.deepcopy(minimal_config_dict)
        modified["teams"]["default"]["size"] = 2
        cfg_b = GraderConfig.model_validate(modified)
        assert config_hash(cfg_a) != config_hash(cfg_b)
